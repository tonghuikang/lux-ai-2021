# contains designed heuristics
# which could be fine tuned

import numpy as np
import builtins as __builtin__

from typing import List
from lux import game

from lux.game import Game, Unit
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_position import Position
from lux.game_constants import GAME_CONSTANTS


def find_best_cluster(game_state: Game, unit: Unit, distance_multiplier = -0.1, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    unit.compute_travel_range((game_state.turns_to_night, game_state.turns_to_dawn, game_state.is_day_time),)

    # for printing
    score_matrix_wrt_pos = game_state.init_zero_matrix()

    best_position = unit.pos
    best_cell_value = (0,0,0)

    # only consider other cluster if the current cluster has more than one agent mining
    consider_different_cluster = False
    # must consider other cluster if the current cluster has more agent than tiles
    consider_different_cluster_must = False

    current_leader = game_state.xy_to_resource_group_id.find(tuple(unit.pos))
    # if not in the middle of transit between clusters
    if current_leader:
        units_mining_on_current_cluster = game_state.resource_leader_to_locating_units[current_leader]
        if len(units_mining_on_current_cluster) > 1:
            consider_different_cluster = True
        resource_size_of_current_cluster = game_state.xy_to_resource_group_id.get_size(current_leader)
        if len(units_mining_on_current_cluster) >= resource_size_of_current_cluster:
            consider_different_cluster_must = True

    # give very slight preference to richer matrices
    matrix = game_state.convolved_rate_matrix**0.01

    for y in range(game_state.map_height):
        for x in range(game_state.map_width):
            if (x,y) in game_state.targeted_xy_set:
                continue
            if (x,y) in game_state.opponent_city_tile_xy_set:
                continue
            if (x,y) in game_state.player_city_tile_xy_set:
                continue

            # if the targeted cluster is not targeted and mined
            # prefer to target the other cluster
            target_bonus = 1
            target_leader = game_state.xy_to_resource_group_id.find((x,y))
            if consider_different_cluster:
                if target_leader and target_leader != current_leader:
                    units_targeting_or_mining_on_target_cluster = \
                        game_state.resource_leader_to_locating_units[target_leader] | \
                        game_state.resource_leader_to_targeting_units[target_leader]
                    if len(units_targeting_or_mining_on_target_cluster) == 0:
                        target_bonus = 100
                    if consider_different_cluster_must:
                        target_bonus = 100/(1+len(units_targeting_or_mining_on_target_cluster))
            elif target_leader == current_leader:
                target_bonus = 2

            # prefer empty tile because you can build afterwards
            empty_tile_bonus = 1
            if game_state.distance_from_resource[y,x] == 1:
                empty_tile_bonus = 2

            # scoring function
            if matrix[y,x] > 0:
                # using simple distance
                distance = abs(unit.pos.x - x) + abs(unit.pos.y - y)
                distance = max(0.9, distance)  # prevent zero error

                if distance <= unit.travel_range:
                    cell_value = (target_bonus, empty_tile_bonus * matrix[y,x] * distance ** distance_multiplier, game_state.distance_from_edge[y,x])
                    score_matrix_wrt_pos[y,x] = cell_value[0]

                    if cell_value > best_cell_value:
                        best_cell_value = cell_value
                        best_position = Position(x,y)

    # print(travel_range)
    # print(score_matrix_wrt_pos)

    return best_position, best_cell_value
