# functions executing the actions

import os
import builtins as __builtin__

from lux.game import Game, Player
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.game_objects import City, CityTile
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux.annotate import pretty_print

from typing import Tuple, Dict

from heuristics import *


def make_city_actions(game_state: Game, DEBUG=False) -> List[str]:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player = game_state.player

    units_cap = sum([len(x.citytiles) for x in player.cities.values()])
    units_cnt = len(player.units)  # current number of units    
    
    actions: List[str] = []
    
    def do_research(city_tile: CityTile):
        action = city_tile.research()
        actions.append(action)

    def build_workers(city_tile: CityTile):
        nonlocal units_cnt
        action = city_tile.build_worker()
        actions.append(action)
        units_cnt += 1

    city_tiles: List[CityTile] = []
    for city in player.cities.values():
        for city_tile in city.citytiles:
            city_tiles.append(city_tile)
    if not city_tiles:
        return []

    city_tiles = sorted(city_tiles, 
                        key=lambda city_tile: find_best_cluster(game_state, city_tile.pos)[1],
                        reverse=True)

    for city_tile in city_tiles:
        if not city_tile.can_act():
            continue

        unit_limit_exceeded = (units_cnt >= units_cap)  # recompute every time

        if player.researched_uranium() and unit_limit_exceeded:
            continue

        if not player.researched_coal() and len(city_tiles) > 6 and len(city_tiles)%2:
            # accelerate coal reasearch
            print("research for coal", city_tile.pos.x, city_tile.pos.y)
            do_research(city_tile)

        best_position, best_cell_value = find_best_cluster(game_state, city_tile.pos)
        if not unit_limit_exceeded and best_cell_value > 100:
            print("build_workers", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, best_cell_value)
            build_workers(city_tile)
            continue

        if not player.researched_uranium():
            # [TODO] dont bother researching uranium for smaller maps
            print("research", city_tile.pos.x, city_tile.pos.y)
            do_research(city_tile)
            continue

        # otherwise don't do anything

    return actions


class Missions:
    def __init__(self):
        # unit_id as key
        self.target_positions: Dict[str, Position] = {}
        self.target_actions: Dict[str, str] = {}

        # [TODO] some expiry date for missions

    def __str__(self):
        return str({unit_id: (pos.x, pos.y) for unit_id, pos in self.target_positions.items()}) + "\n" + str(self.target_actions)
    
    def delete(self, unit_id):
        if unit_id in self.target_positions:
            del self.target_positions[unit_id]
        if unit_id in self.target_actions:
            del self.target_actions[unit_id]


def make_unit_missions(game_state: Game, missions: Missions, DEBUG=False) -> Missions:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player = game_state.player

    for unit in player.units:
        if not unit.can_act():
            continue

        nearest_position, nearest_distance = game_state.get_nearest_empty_tile_and_distance(unit.pos)

        # if the unit is full and it is going to be day the next few days
        # go to an empty tile and build a city
        # print(unit.id, unit.get_cargo_space_left())
        if unit.get_cargo_space_left() == 0:
            # print("check")
            if nearest_distance < game_state.turns_to_night:
                # print("build city")
                missions.target_positions[unit.id] = nearest_position
                missions.target_actions[unit.id] = unit.build_city()
                continue
                
        if unit.id in missions.target_positions:  # there is already a mission
            continue

        if game_state.resource_rates_matrix[unit.pos.y][unit.pos.x] >= 80: # continue camping
            continue

        # once a unit is built (detected as having full space)
        # go to the best cluster
        if unit.get_cargo_space_left() == 100:
            best_position, best_cell_value = find_best_cluster(game_state, unit.pos)
            missions.target_positions[unit.id] = best_position
            missions.target_actions[unit.id] = unit.move("c")
            continue

        # if a unit is not receiving any resources
        # move to a place with resources
        if game_state.resource_scores_matrix[unit.pos.y][unit.pos.x] <= 20:
            best_position, best_cell_value = find_best_cluster(game_state, unit.pos, distance_multiplier=-0.3)
            unit.target_pos = best_position
            unit.target_action = None
            continue

        # otherwise just camp and farm resources

        # [TODO] when you can secure a city all the way to the end of time, do it

        # [TODO] avoid overlapping missions
    
    return missions


def make_unit_actions(game_state: Game, missions: Missions, DEBUG=False) -> Tuple[Missions, List[str]]:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player, opponent = game_state.player, game_state.opponent
    actions = []


    for unit in player.units:
        if not unit.can_act():
            continue

        # if there is no mission, continue
        if (unit.id not in missions.target_positions) and (unit.id not in missions.target_actions):
            continue

        # if the location is reached, take action
        if unit.pos == missions.target_positions[unit.id]:
            action = missions.target_actions[unit.id]
            if action:
                actions.append(action)
            
            missions.delete(unit.id)
            continue

        # the unit will need to move
        direction, game_state.map.set_occupied_xy = unit.pos.direction_to(missions.target_positions[unit.id], 
                                                                          game_state.map.set_occupied_xy)
        action = unit.move(direction)
        actions.append(action)

        # [TODO] make it possible for units to swap position

    return missions, actions
        