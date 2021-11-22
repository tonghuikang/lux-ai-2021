# contains designed heuristics
# which could be fine tuned
import math
import time

import numpy as np
import builtins as __builtin__

from typing import Dict
from lux import annotate
from lux import game

from lux.game import Game, Unit
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_position import Position
from lux.game_constants import GAME_CONSTANTS


def find_best_cluster(game_state: Game, unit: Unit, DEBUG=False, explore=False, require_empty_target=False, ref_pos:Position=None):

    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    # for debugging
    score_matrix_wrt_pos = game_state.init_matrix()

    # default response is not to move
    best_position = unit.pos
    best_cell_value = [0,0,0,0]
    cluster_annotation = []

    if time.time() - game_state.compute_start_time > 3:
        # running out of time
        return best_position, best_cell_value, cluster_annotation

    # if at night, if near enemy or almost dawn, if city is going to die, if staying can keep the city alive
    if not game_state.is_day_time:
        cityid = game_state.map.get_cityid_of_cell(unit.pos.x, unit.pos.y)
        if cityid:
            city = game_state.player.cities[cityid]
            if game_state.distance_from_opponent_assets[unit.pos.y,unit.pos.x] <= 2 or city.fuel_needed_for_night <= len(city.citytiles) * 120:
                if city.fuel_needed_for_night > 0:
                    if city.fuel_needed_for_night - game_state.fuel_collection_rate[unit.pos.y, unit.pos.x] * game_state.turns_to_dawn <= 0:
                        best_cell_value = [10**9,0,0,0]
                        print("staying SU", unit.id, unit.pos)
                        annotation = annotate.text(unit.pos.x, unit.pos.y, "SU")
                        cluster_annotation.append(annotation)

    # anticipate ejection
    if tuple(unit.pos) in game_state.player_city_tile_xy_set:
      if game_state.xy_to_resource_group_id.get_point(tuple(unit.pos)) <= 3:
        for dy,dx in game_state.dirs_dxdy[:-1]:
            xx,yy = unit.pos.x+dx, unit.pos.y+dy
            if (xx,yy) not in game_state.player.units_by_xy:
                continue
            adj_unit: Unit = game_state.player.units_by_xy[xx,yy]
            if int(adj_unit.cooldown) != 1:
                continue
            if game_state.convolved_wood_exist_matrix[yy,xx] < 1:
                continue
            print("staying SX", unit.id, unit.pos)
            best_cell_value = [10**9,0,0,0]
            annotation = annotate.text(unit.pos.x, unit.pos.y, "SX")
            cluster_annotation.append(annotation)

    # only consider other cluster if the current cluster has more than one agent mining
    consider_different_cluster = False
    # must consider other cluster if the current cluster has more agent than tiles
    consider_different_cluster_must = explore

    # calculate how many resource tiles and how many units on the current cluster
    current_leader = game_state.xy_to_resource_group_id.find(tuple(unit.pos))
    units_mining_on_current_cluster = game_state.resource_leader_to_locating_units[current_leader] & game_state.resource_leader_to_targeting_units[current_leader]
    resource_size_of_current_cluster = game_state.xy_to_resource_group_id.get_point(current_leader)
    if game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] > 10:
        if resource_size_of_current_cluster > 1:
            resource_size_of_current_cluster = resource_size_of_current_cluster//2

    # only consider other cluster if another unit is targeting and mining in the current cluster
    if len(units_mining_on_current_cluster - set([unit.id])) >= 1:
        consider_different_cluster = True

    # if you are in a barren field you must consider a different cluster
    if tuple(unit.pos) not in game_state.convolved_collectable_tiles_xy_set:
        consider_different_cluster_must = True

    if len(units_mining_on_current_cluster) >= resource_size_of_current_cluster:
        # must consider if you have more than enough workers in the current cluster
        consider_different_cluster_must = True

    print("finding best cluster for", unit.id, unit.pos, consider_different_cluster, consider_different_cluster_must)

    best_citytile_of_cluster: Dict = dict()
    target_bonus_for_current_cluster_logging = -999

    for y in game_state.y_iteration_order:
        for x in game_state.x_iteration_order:

            # what not to target
            if (x,y) in game_state.targeted_for_building_xy_set:
                continue
            if (x,y) in game_state.opponent_city_tile_xy_set:
                continue
            if (x,y) in game_state.player_city_tile_xy_set:
                continue

            if ref_pos:
                if abs(ref_pos.x - x) + abs(ref_pos.y - y) < abs(unit.pos.x - x) + abs(unit.pos.y - y):
                    continue

            # allow multi targeting of uranium mines
            if game_state.convolved_uranium_exist_matrix[y,x] == 0 or \
                not game_state.player.researched_uranium_projected() or \
                    game_state.matrix_player_cities_nights_of_fuel_required_for_night[y,x] <= 0:
                if (x,y) in game_state.targeted_xy_set:
                    continue

            if require_empty_target and len(units_mining_on_current_cluster) <= 2:
                continue

            distance = game_state.retrieve_distance(unit.pos.x, unit.pos.y, x, y)

            # cluster targeting logic

            # target bonus should have the same value for the entire cluster
            target_bonus = 1
            target_leader = game_state.xy_to_resource_group_id.find((x,y))
            if consider_different_cluster or consider_different_cluster_must:
                # if the target is a cluster and not the current cluster
                if target_leader:

                    units_targeting_or_mining_on_target_cluster = \
                        game_state.resource_leader_to_locating_units[target_leader] | \
                        game_state.resource_leader_to_targeting_units[target_leader]

                    if require_empty_target and units_targeting_or_mining_on_target_cluster:
                        continue
                    resource_size_of_target_cluster = game_state.xy_to_resource_group_id.get_point(target_leader)

                    # target bonus depends on how many resource tiles and how many units that are mining or targeting
                    target_bonus = resource_size_of_target_cluster/\
                                   (1 + len(units_targeting_or_mining_on_target_cluster))

                    # avoid targeting overpopulated clusters
                    if len(units_targeting_or_mining_on_target_cluster) > resource_size_of_target_cluster:
                        target_bonus = target_bonus * 0.1

                    # if none of your units is targeting the cluster and definitely reachable
                    if len(units_targeting_or_mining_on_target_cluster) == 0:
                        if distance <= game_state.distance_from_opponent_assets[y,x]:
                            target_bonus = target_bonus * 10

                    # discourage targeting depending are you the closest unit to the resource
                    distance_bonus = max(1,game_state.distance_from_player_assets[y,x])/max(1,distance)

                    if require_empty_target and distance_bonus < 1:
                        continue

                    if consider_different_cluster_must:
                        distance_bonus = max(1/2, distance_bonus)

                    target_bonus = target_bonus * distance_bonus**2

                    if distance_bonus == 1:
                        # extra bonus if you are closest to the target
                        target_bonus = target_bonus * 10

                    # travel penalty
                    target_bonus = target_bonus / math.log(4 + game_state.xy_to_resource_group_id.get_dist_from_player((x,y),), 2)

                    # if targeted cluster is much closer to enemy, do not target if cannot survive the night
                    # resources is required for invasion
                    if game_state.distance_from_opponent_assets[y,x] + 5 < \
                       game_state.xy_to_resource_group_id.get_dist_from_player((x,y),):
                        if unit.night_turn_survivable < 10:
                            target_bonus = target_bonus * 0.01

                    # slightly discourage targeting clusters closer to enemy
                    if game_state.xy_to_resource_group_id.get_dist_from_opponent((x,y),) < \
                       game_state.xy_to_resource_group_id.get_dist_from_player((x,y),):
                        target_bonus = target_bonus * 0.9

            if target_leader and target_leader == current_leader:
                # if targeting same cluster do not move more than five
                if distance > 5:
                    continue

            if consider_different_cluster_must and target_leader != current_leader:
                # enforce targeting of other clusters
                target_bonus = target_bonus * 10

            if not consider_different_cluster_must and target_leader == current_leader:
                target_bonus = target_bonus * 2

            # only target cells where you can collect resources
            if game_state.convolved_collectable_tiles_matrix_projected[y,x] == 0:
                continue

            if unit.night_turn_survivable < 10:
                if game_state.convolved_collectable_tiles_matrix[y,x] == 0:
                    continue

            # identation to retain commit history
            if True:
                # do not plan overnight missions if you are the only unit mining
                if tuple(unit.pos) in game_state.convolved_collectable_tiles_xy_set:
                    if len(units_mining_on_current_cluster) <= 1 and distance > 15:
                        continue

                # estimate target score
                if distance <= unit.travel_range:
                    cell_value = [target_bonus,
                                  - game_state.distance_from_floodfill_by_empty_tile[y,x],
                                  - game_state.distance_from_resource_median[y,x]
                                  - distance - game_state.distance_from_opponent_assets[y,x]
                                  - distance + game_state.distance_from_player_unit_median[y,x],
                                  - distance - game_state.opponent_units_matrix[y,x] * 2]

                    # penalty on parameter preference
                    # if not collectable and not buildable, penalise
                    if (x,y) not in game_state.collectable_tiles_xy_set and (x,y) not in game_state.buildable_tile_xy_set:
                        cell_value[1] -= 1

                    # prefer to mine advanced resources faster
                    if unit.get_cargo_space_left() > 8:
                        if game_state.player.researched_coal_projected():
                            cell_value[1] += 2*game_state.convolved_coal_exist_matrix[y,x]
                        if game_state.player.researched_uranium_projected():
                            cell_value[1] += 2*game_state.convolved_uranium_exist_matrix[y,x]

                    # if mining advanced resource, stand your ground unless there is a direct path
                    if game_state.convolved_coal_exist_matrix[unit.pos.y,unit.pos.x] or game_state.convolved_uranium_exist_matrix[unit.pos.y,unit.pos.x]:
                        if distance > abs(unit.pos.x - x) + abs(unit.pos.y - y):
                            continue

                    # discourage if the target is one unit closer to the enemy, in the early game
                    # specific case to avoid this sort of targeting (A -> X)
                    #    X
                    # WABW
                    # WWWW
                    if game_state.distance_from_opponent_assets[y,x] + 1 == game_state.distance_from_player_units[y,x]:
                        if game_state.turn < 80:
                            cell_value[2] -= 2

                    # for first target prefer B over A
                    #   X
                    # BWWW
                    #  WWW
                    #  AX
                    if game_state.distance_from_opponent_assets[y,x] == 1 and game_state.distance_from_player_assets[y,x] > 2:
                        if game_state.turn < 1:
                            cell_value[2] -= 2

                    # discourage if you are in the citytile, and you are targeting the location beside you with one wood side
                    # specific case to avoid this sort of targeting (A -> X), probably encourage (A -> Z) or (A -> Y)
                    #
                    #   AX
                    #  ZWWY
                    if tuple(unit.pos) in game_state.player_city_tile_xy_set:
                        if Position(x,y) - unit.pos == 1:
                            if game_state.convolved_wood_exist_matrix[y,x] == 1 and game_state.resource_collection_rate[y,x] == 20:
                                if game_state.distance_from_opponent_units[y,x] > 2:
                                    cell_value[2] -= 5


                    # if more than 20 uranium do not target a wood cluster so that it can home
                    if unit.cargo.uranium > 20:
                        if game_state.convolved_wood_exist_matrix[y,x]*20 == game_state.resource_collection_rate[y,x]:
                            cell_value[0] = -1

                    # for debugging
                    score_matrix_wrt_pos[y,x] = cell_value[2]

                    # update best target
                    if cell_value > best_cell_value:
                        best_cell_value = cell_value
                        best_position = Position(x,y)

                    if target_leader not in best_citytile_of_cluster:
                        best_citytile_of_cluster[target_leader] = (cell_value,x,y)
                    if (cell_value,x,y) > best_citytile_of_cluster[target_leader]:
                        best_citytile_of_cluster[target_leader] = (cell_value,x,y)

                    if target_leader == current_leader:
                        target_bonus_for_current_cluster_logging = max(target_bonus_for_current_cluster_logging, target_bonus)

    # annotate if target bonus is more than one
    if best_cell_value[0] > target_bonus_for_current_cluster_logging > -999:
        for cell_value,x,y in sorted(best_citytile_of_cluster.values())[:10]:
            annotation = annotate.text(x,y,f"{int(cell_value[0])}")
            cluster_annotation.append(annotation)
            annotation = annotate.line(unit.pos.x,unit.pos.y,x,y)
            cluster_annotation.append(annotation)

    # for debugging
    game_state.heuristics_from_positions[tuple(unit.pos)] = score_matrix_wrt_pos

    return best_position, best_cell_value, cluster_annotation
