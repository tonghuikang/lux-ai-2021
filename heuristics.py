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


def find_best_cluster(game_state: Game, unit: Unit, distance_multiplier = -0.5, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    unit.compute_travel_range((game_state.turns_to_night, game_state.turns_to_dawn, game_state.is_day_time),)

    # for printing
    score_matrix_wrt_pos = game_state.init_matrix()

    best_position = unit.pos
    best_cell_value = (0,0,0)

    # only consider other cluster if the current cluster has more than one agent mining
    consider_different_cluster = False
    # must consider other cluster if the current cluster has more agent than tiles
    consider_different_cluster_must = False

    current_leader = game_state.xy_to_resource_group_id.find(tuple(unit.pos))
    units_mining_on_current_cluster = game_state.resource_leader_to_locating_units[current_leader] & game_state.resource_leader_to_targeting_units[current_leader]
    if len(units_mining_on_current_cluster) >= 1:
        consider_different_cluster = True
    resource_size_of_current_cluster = game_state.xy_to_resource_group_id.get_point(current_leader)
    if len(units_mining_on_current_cluster) >= resource_size_of_current_cluster:
        consider_different_cluster_must = True

    # value heuristic
    matrix = game_state.convolved_collectable_tiles_matrix

    for y in game_state.y_iteration_order:
        for x in game_state.x_iteration_order:
            if (x,y) in game_state.targeted_xy_set:
                continue
            if (x,y) in game_state.targeted_for_building_xy_set:
                continue
            if (x,y) in game_state.opponent_city_tile_xy_set:
                continue
            if (x,y) in game_state.player_city_tile_xy_set:
                continue

            # if the targeted cluster is not targeted and mined
            # prefer to target the other cluster
            target_bonus = 1
            target_leader = game_state.xy_to_resource_group_id.find((x,y))
            if consider_different_cluster or consider_different_cluster_must:
                if target_leader and target_leader != current_leader:
                    units_targeting_or_mining_on_target_cluster = \
                        game_state.resource_leader_to_locating_units[target_leader] | \
                        game_state.resource_leader_to_targeting_units[target_leader]
                    if len(units_targeting_or_mining_on_target_cluster) == 0:
                        target_bonus = game_state.xy_to_resource_group_id.get_point(target_leader)/\
                            (1+ len(game_state.resource_leader_to_locating_units[target_leader] &
                                    game_state.resource_leader_to_targeting_units[target_leader]))
                    if consider_different_cluster_must:
                        target_bonus = 100
            elif target_leader == current_leader:
                target_bonus = 2

            # prefer empty tile because you can build afterwards quickly
            empty_tile_bonus = 1/(0.5+game_state.distance_from_buildable_tile[y,x])

            # scoring function
            if matrix[y,x] > 0:
                # using simple distance
                distance = game_state.retrieve_distance(unit.pos.x, unit.pos.y, x, y)
                distance = max(0.9, distance)  # prevent zero error

                if distance <= unit.travel_range:
                    cell_value = (target_bonus, empty_tile_bonus * matrix[y,x] * distance ** distance_multiplier, game_state.distance_from_edge[y,x])
                    score_matrix_wrt_pos[y,x] = cell_value[0]*100*100 + cell_value[1]*100 + cell_value[2]

                    if cell_value > best_cell_value:
                        best_cell_value = cell_value
                        best_position = Position(x,y)

    game_state.heuristics_from_positions[tuple(unit.pos)] = score_matrix_wrt_pos

    return best_position, best_cell_value
