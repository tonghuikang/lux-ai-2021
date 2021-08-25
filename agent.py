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

from agnostic_helper import *


game_state = None
missions = {}  # unit id to list of movements planned


def make_city_actions(player):
    # https://www.lux-ai.org/specs-2021#CityTiles
    
    actions = []
    
    # max number of units available
    units_cap = sum([len(x.citytiles) for x in player.cities.values()])
    # current number of units
    units = len(player.units)
    
    cities = list(player.cities.values())
    if len(cities) > 0:
        city = cities[0]
        created_worker = (units >= units_cap)
        for city_tile in city.citytiles[::-1]:
            if city_tile.can_act():
                if created_worker:
                    # let's do research
                    action = city_tile.research()
                    actions.append(action)
                else:
                    # let's create one more unit in the last created city tile if we can
                    action = city_tile.build_worker()
                    actions.append(action)
                    created_worker = True
    return actions


def agent(observation, configuration):
    del configuration  # unused
    global game_state, missions

    game_state = update_game_state_with_observation(game_state, observation)
    game_statistics = calculate_game_statistics(game_state)
    print(game_statistics)
    
    actions = []

    player = game_state.players[observation.player]
    opponent = game_state.players[1 - observation.player]  # only two players
    pretty_print(player)
    resource_tiles = find_resources(game_state)

    actions_cities = make_city_actions(player)
    actions.extend(actions_cities)
    
    # we want to build new tiles only if we have a lot of fuel in all cities
    can_build = True
    night_steps_left = ((359 - observation["step"]) // 40 + 1) * 10
    for city in player.cities.values():            
        if city.fuel / (city.get_light_upkeep() + 20) < min(night_steps_left, 20):
            can_build = False
       
    steps_until_night = 30 - observation["step"] % 40
    
    
    # we will keep all tiles where any unit wants to move in this set to avoid collisions
    taken_tiles = set()
    for unit in player.units:
        # it is too strict but we don't allow to go to the the currently occupied tile
        taken_tiles.add((unit.pos.x, unit.pos.y))
        
    for city in opponent.cities.values():
        for city_tile in city.citytiles:
            taken_tiles.add((city_tile.pos.x, city_tile.pos.y))
    
    # we can collide in cities so we will use this tiles as exceptions
    city_tiles = {(tile.pos.x, tile.pos.y) for city in player.cities.values() for tile in city.citytiles}

    for unit in player.units:
        if unit.can_act():
            closest_resource_tile, closest_resource_dist = find_closest_resources(unit.pos, player, resource_tiles)
            closest_city_tile, closest_city_dist = find_closest_city_tile(unit.pos, player)
            
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
    return actions