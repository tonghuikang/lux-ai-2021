# contains designed heuristics
# which could be fine tuned

import numpy as np
import builtins as __builtin__

from typing import Dict
from lux import annotate

from lux.game import Game, Unit
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_position import Position
from lux.game_constants import GAME_CONSTANTS


def find_best_cluster(game_state: Game, unit: Unit, DEBUG=False, explore=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    # passing game_state attributes to compute travel range
    unit.compute_travel_range((game_state.turns_to_night, game_state.turns_to_dawn, game_state.is_day_time),)

    # for debugging
    score_matrix_wrt_pos = game_state.init_matrix()

    # default response is not to move
    best_position = unit.pos
    best_cell_value = [0,0,0,0]
    cluster_annotation = []

    # only consider other cluster if the current cluster has more than one agent mining
    consider_different_cluster = False
    # must consider other cluster if the current cluster has more agent than tiles
    consider_different_cluster_must = explore

    # calculate how resource tiles and how many units on the current cluster
    current_leader = game_state.xy_to_resource_group_id.find(tuple(unit.pos))
    units_mining_on_current_cluster = game_state.resource_leader_to_locating_units[current_leader] & game_state.resource_leader_to_targeting_units[current_leader]
    resource_size_of_current_cluster = game_state.xy_to_resource_group_id.get_point(current_leader)

    # only consider other cluster if another unit is targeting and mining in the current cluster
    if len(units_mining_on_current_cluster) >= 1:
        consider_different_cluster = True

    if len(units_mining_on_current_cluster) >= resource_size_of_current_cluster:
        # must consider if you have more than enough workers in the current cluster
        consider_different_cluster_must = True

    best_citytile_of_cluster: Dict = dict()

    for y in game_state.y_iteration_order:
        for x in game_state.x_iteration_order:

            # what not to target
            if (x,y) in game_state.targeted_for_building_xy_set:
                continue
            if (x,y) in game_state.opponent_city_tile_xy_set:
                continue

            # allow multi targeting of uranium mines
            if game_state.convolved_uranium_exist_matrix[y,x] == 0 or not game_state.player.researched_uranium_projected():
                if (x,y) in game_state.targeted_xy_set:
                    continue
                if (x,y) in game_state.player_city_tile_xy_set:
                    continue

            distance = game_state.retrieve_distance(unit.pos.x, unit.pos.y, x, y)

            # cluster targeting logic
            target_bonus = 1
            target_leader = game_state.xy_to_resource_group_id.find((x,y))
            if consider_different_cluster or consider_different_cluster_must:
                # if the target is a cluster and not the current cluster
                if target_leader and target_leader != current_leader:

                    units_targeting_or_mining_on_target_cluster = \
                        game_state.resource_leader_to_locating_units[target_leader] | \
                        game_state.resource_leader_to_targeting_units[target_leader]

                    # target bonus depends on how many resource tiles and how many units that are mining or targeting
                    if len(units_targeting_or_mining_on_target_cluster) == 0:
                        target_bonus = game_state.xy_to_resource_group_id.get_point(target_leader)/\
                                       (1 + len(game_state.resource_leader_to_locating_units[target_leader] &
                                                game_state.resource_leader_to_targeting_units[target_leader]))

                    # discourage targeting depending are you the closet unit to the resource
                    distance_bonus = game_state.distance_from_player_assets[y,x]/max(3,distance)
                    target_bonus = target_bonus * distance_bonus**2

                    if distance_bonus < 1/2:
                        # if you are far from being the closest to the new cluster, do not target
                        target_bonus = 1

                    if distance_bonus == 1:
                        # extra bonus if you are closest to the target
                        target_bonus = target_bonus * 10

            if consider_different_cluster_must:
                # enforce targeting of other clusters
                target_bonus = target_bonus * 2

            if target_leader == current_leader:
                target_bonus = 2

            # only target cells where you can collect resources
            if game_state.convolved_collectable_tiles_matrix[y,x] > 0:

                # # do not plan long missions in initial turns
                # if game_state.turn < 40 and distance > 1+game_state.player.city_tile_count*2:
                #     continue

                # estimate target score
                if distance <= unit.travel_range:
                    cell_value = [target_bonus,
                                  - game_state.distance_from_floodfill_by_empty_tile[y,x],
                                  - 2*distance - max(2,game_state.distance_from_opponent_assets[y,x])
                                  + game_state.distance_from_edge[y,x]
                                  - game_state.opponent_units_matrix[y,x] * 2]

                    # prefer to mine advanced resources faster
                    if unit.get_cargo_space_left() > 8:
                        if game_state.player.researched_coal_projected():
                            cell_value[1] += 2*game_state.convolved_coal_exist_matrix[y,x]
                        if game_state.player.researched_uranium_projected():
                            cell_value[1] += 2*game_state.convolved_uranium_exist_matrix[y,x]

                    score_matrix_wrt_pos[y,x] = cell_value[2]

                    # update best target
                    if cell_value > best_cell_value:
                        best_cell_value = cell_value
                        best_position = Position(x,y)

                    if target_leader not in best_citytile_of_cluster:
                        best_citytile_of_cluster[target_leader] = (cell_value,x,y)
                    if cell_value > best_citytile_of_cluster[target_leader][0]:
                        best_citytile_of_cluster[target_leader] = (cell_value,x,y)

    # annotate if target bonus is more than one
    if best_cell_value[0] > 2:
        for cell_value,x,y in best_citytile_of_cluster.values():
            annotation = annotate.text(x,y,f"{int(cell_value[0])}")
            cluster_annotation.append(annotation)
            annotation = annotate.line(unit.pos.x,unit.pos.y,x,y)
            cluster_annotation.append(annotation)

    # for debugging
    game_state.heuristics_from_positions[tuple(unit.pos)] = score_matrix_wrt_pos

    return best_position, best_cell_value, cluster_annotation
