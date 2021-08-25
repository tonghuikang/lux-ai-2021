# contains agent agnostic helper functions

import os, re
import math
import numpy as np
import time

os.environ["notebook_debug"] = "YES"
NOTEBOOK_DEBUG = os.environ["notebook_debug"]

from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate


def update_game_state_with_observation(game_state, observation):

    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    return game_state


def calculate_game_statistics(game_state):
    game_statistics = {}

    # TODO check off by one errors    
    game_statistics["current_turn"] = game_state.turn
    game_statistics["night_turns_left"] = (360 - game_state.turn)//40 * 10 + min(10, (360 - game_state.turn)%40)
    game_statistics["turns_to_night"] = (30 - game_state.turn)%40
    game_statistics["turns_to_dawn"] = (40 - game_state.turn%40)

    return game_statistics


def pretty_print(obj, indent=1, rec=0, key=''):
    # https://stackoverflow.com/questions/51753937/python-pretty-print-nested-objects
    s_indent = ' ' * indent * rec
    items = {}
    stg = s_indent

    if key != '': stg += str(key) + ': '

    # Discriminate && Check if final
    if isinstance(obj, list):
        items = enumerate(obj)
    elif isinstance(obj, dict):
        items = obj.items()
    elif '__dict__' in dir(obj):
        items = obj.__dict__.items()
    if not items:
        return stg + str(obj)

    # Recurse
    stg += '(' + type(obj).__name__ + ')\n'
    for k, v in items:
        stg += pretty_print(v, indent=indent, rec=rec+1, key=k) + "\n"

    # Return without empty lines
    return re.sub(r'\n\s*\n', '\n', stg)[:-1]


# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def find_resources(game_state):
    resource_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles


# # the next snippet finds the closest resources that we can mine given position on a map
def find_closest_resources(pos, player, resource_tiles):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        # we skip over resources that we can't mine due to not having researched them
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile, closest_dist


# # find the closest city tile of a player
def find_closest_city_tile(pos, player):
    closest_city_tile = None
    closest_dist = math.inf
    if len(player.cities) > 0:
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile, closest_dist


def get_random_step():
    return np.random.choice(['s','n','w','e'])