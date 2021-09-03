# contains designed heuristics
# which could be fine tuned

import math, random
import numpy as np
import builtins as __builtin__

from typing import List
from lux import game

from lux.game import Game, Player, Unit, Mission, Missions
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_position import Position
from lux.game_constants import GAME_CONSTANTS
from lux import annotate


def find_best_cluster(game_state: Game, unit: Unit, distance_multiplier = -0.1, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    cooldown = GAME_CONSTANTS["PARAMETERS"]["UNIT_ACTION_COOLDOWN"]["WORKER"]
    travel_range = max(1, game_state.turns_to_night // cooldown + unit.night_travel_range - 2)
    if unit.night_turn_survivable > game_state.turns_to_dawn and not game_state.is_day_time:
        travel_range = GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"] // cooldown + unit.night_travel_range
    if unit.night_turn_survivable > GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]:
        travel_range = GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"] // cooldown + unit.night_travel_range
    # [TODO] fix bug regarding nighttime travel, but just let them die perhaps

    score_matrix_wrt_pos = game_state.init_zero_matrix()

    best_position = unit.pos
    best_cell_value = -1

    consider_different_cluster = False
    current_leader = game_state.xy_to_resource_group_id.find(tuple(unit.pos))
    if current_leader:
        units_mining_on_current_cluster = game_state.resource_leader_to_locating_units[current_leader]
        if len(units_mining_on_current_cluster) > 1:
            consider_different_cluster = True

    # design your matrices here
    matrix = game_state.calculate_dominance_matrix(game_state.resource_rate_matrix**0.01)
    for y in range(game_state.map_height):
        for x in range(game_state.map_width):
            if (x,y) in game_state.targeted_xy_set:
                continue
            if (x,y) in game_state.opponent_city_tile_xy_set:
                continue
            if (x,y) in game_state.player_city_tile_xy_set:
                continue
            if (x,y) == tuple(unit.pos):
                continue

            # [TODO] make it smarter than random

            # if current cluster size has more than two agents mining
            # if the targeted cluster is not targeted and mined
            # prefer to target the other cluster
            target_bonus = 1

            # current_leader = game_state.opponent_city_tile_xy_set[]
            if consider_different_cluster:
                target_leader = game_state.xy_to_resource_group_id.find((x,y))
                if target_leader:
                    units_targeting_or_mining_on_target_cluster = \
                        game_state.resource_leader_to_locating_units[target_leader] | \
                        game_state.resource_leader_to_targeting_units[target_leader]
                    if len(units_targeting_or_mining_on_target_cluster) == 0:
                        target_bonus = 10

            # if distance_multiplier > 0:
            #     if game_state.xy_to_resource_group_id.find((x,y),) in game_state.targeted_leaders:
            #         target_bonus = 1

            empty_tile_bonus = 1
            if game_state.distance_from_resource[y,x] == 1:
                empty_tile_bonus = 4

            dx, dy = abs(unit.pos.x - x), abs(unit.pos.y - y)
            if matrix[y,x] > 0:
                distance = max(1, dx + dy)
                if distance <= travel_range:
                    # encourage going far away
                    # [TODO] discourage returning to explored territory
                    # [TODO] discourage going to planned locations
                    cell_value = empty_tile_bonus * target_bonus * matrix[y,x] * distance ** distance_multiplier
                    score_matrix_wrt_pos[y,x] = int(cell_value)

                    if cell_value > best_cell_value:
                        best_cell_value = cell_value
                        best_position = Position(x,y)

    print(travel_range)
    print(score_matrix_wrt_pos)

    return best_position, best_cell_value
