import os, re
import math
import time
import collections

import numpy as np

os.environ["notebook_debug"] = "YES"
NOTEBOOK_DEBUG = os.environ["notebook_debug"]

from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

from agnostic_helper import *
from actions import *
from heuristics import *

game_state = Game()
missions = collections.defaultdict(collections.deque)  # unit id to list of movements planned


def agent(observation: Observation, configuration):
    del configuration  # unused
    global game_state, missions

    game_state._update_with_observation(observation) 
    print(game_state.player.city_tile_count)
    actions = []

    # game_state.resource_scores_matrix
    # game_state.maxpool_scores_matrix
    # game_state.city_tile_matrix
    # game_state.empty_tile_matrix
    # print(np.array([game_state.empty_tile_matrix]))
    # print()

    resource_tiles = find_resources(game_state)

    actions_cities = make_city_actions(game_state)
    actions.extend(actions_cities)
    
    # we want to build new tiles only if we have a lot of fuel in all cities
    can_build = True
    for city in game_state.player.cities.values():            
        if city.fuel / (city.get_light_upkeep() + 30) < min(game_state.night_turns_left, 20):
            can_build = False

    steps_until_night = 30 - observation["step"] % 40
    
    
    # we will keep all tiles where any unit wants to move in this set to avoid collisions
    taken_tiles = set()
    for unit in game_state.player.units:
        # it is too strict but we don't allow to go to the the currently occupied tile
        taken_tiles.add((unit.pos.x, unit.pos.y))
        find_best_cluster(game_state, unit.pos)

    for city in game_state.opponent.cities.values():
        for city_tile in city.citytiles:
            taken_tiles.add((city_tile.pos.x, city_tile.pos.y))
    
    # we can collide in cities so we will use this tiles as exceptions
    city_tiles = {(tile.pos.x, tile.pos.y) for city in game_state.player.cities.values() for tile in city.citytiles}

    for unit in game_state.player.units:
        if unit.can_act():
            closest_resource_tile, closest_resource_dist = find_closest_resources(unit.pos, game_state.player, resource_tiles)
            # print(pretty_print(unit), closest_resource_tile, closest_resource_dist)
            closest_city_tile, closest_city_dist = find_closest_city_tile(unit.pos, game_state.player)
            
            # we will keep possible actions in a priority order here
            directions = []
            
            # if we can build and we are near the city let's do it
            if unit.is_worker() and unit.can_build(game_state.map) and ((closest_city_dist == 1 and can_build) or 
                                                                        (closest_city_dist is None)):
                # build a new cityTile
                action = unit.build_city()
                actions.append(action)  
                can_build = False
                continue
            
            # base cooldown for different units types
            base_cd = 2 if unit.is_worker() else 3
            
            # how many steps the unit needs to get back to the city before night (without roads)
            steps_to_city = unit.cooldown + base_cd * closest_city_dist
            
            # if we are far from the city in the evening or just full let's go home
            if (steps_to_city + 3 > steps_until_night or unit.get_cargo_space_left() == 0) and closest_city_tile is not None:
                actions.append(annotate.line(unit.pos.x, unit.pos.y, closest_city_tile.pos.x, closest_city_tile.pos.y))
                directions = [unit.pos.direction_to(closest_city_tile.pos)]
            else:
                # if there is no risks and we are not mining resources right now let's move toward resources
                if closest_resource_dist != 0 and closest_resource_tile is not None:
                    actions.append(annotate.line(unit.pos.x, unit.pos.y, closest_resource_tile.pos.x, closest_resource_tile.pos.y))
                    directions = [unit.pos.direction_to(closest_resource_tile.pos)]
                    # optionally we can add random steps
                    for _ in range(2):
                        directions.append(get_random_step())

            moved = False
            for next_step_direction in directions:
                next_step_position = unit.pos.translate(next_step_direction, 1)
                next_step_coordinates = (next_step_position.x, next_step_position.y)
                # make only moves without collision
                if next_step_coordinates not in taken_tiles or next_step_coordinates in city_tiles:
                    action = unit.move(next_step_direction)
                    actions.append(action)
                    taken_tiles.add(next_step_coordinates)
                    moved = True
                    break
            
            if not moved:
                # if we are not moving the tile is occupied
                taken_tiles.add((unit.pos.x,unit.pos.y))
    
    print(actions)
    return actions