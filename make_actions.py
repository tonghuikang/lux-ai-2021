# functions executing the actions

import builtins as __builtin__
from typing import Tuple, List, Set
from lux import game

from lux.game import Game, Mission, Missions, cleanup_missions
from lux.game_objects import Cargo, CityTile, Unit, City
from lux.game_position import Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
import lux.annotate as annotate

from heuristics import find_best_cluster

DIRECTIONS = Constants.DIRECTIONS


def make_city_actions(game_state: Game, missions: Missions, DEBUG=False) -> List[str]:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player = game_state.player
    cleanup_missions(game_state, missions, DEBUG=DEBUG)
    game_state.repopulate_targets(missions)

    units_cap = sum([len(x.citytiles) for x in player.cities.values()])
    units_cnt = len(player.units)  # current number of units

    actions: List[str] = []
    reset_missions = False

    def do_research(city_tile: CityTile, annotation: str=""):
        nonlocal reset_missions
        action = city_tile.research()
        game_state.player.research_points += 1
        actions.append(action)
        if annotation:
            actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, annotation))
        city_tile.cooldown += 10

        # reset all missions
        if game_state.player.research_points == 50:
            print("delete missions at 50 rp")
            reset_missions = True
        if game_state.player.research_points == 200:
            print("delete missions at 200 rp")
            reset_missions = True

    def build_worker(city_tile: CityTile, annotation: str=""):
        nonlocal units_cnt
        action = city_tile.build_worker()
        actions.append(action)
        units_cnt += 1
        game_state.citytiles_with_new_units_xy_set.add(tuple(city_tile.pos))
        if annotation:
            actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, annotation))
        city_tile.cooldown += 10

        # fake unit and mission to simulate targeting current position
        # if unit limit is not reached
        if units_cnt <= units_cap:
            unit = Unit(game_state.player_id, 0, city_tile.cityid, city_tile.pos.x, city_tile.pos.y,
                        cooldown=6, wood=0, coal=0, uranium=0)  # add dummy unit for targeting purposes
            game_state.players[game_state.player_id].units.append(unit)
            game_state.player.units_by_id[city_tile.cityid] = unit
            mission = Mission(city_tile.cityid, city_tile.pos, details="born", delays=99)
            missions.add(mission)
            game_state.unit_ids_with_missions_assigned_this_turn.add(city_tile.cityid)
            print(missions)

    def build_cart(city_tile: CityTile, annotation: str=""):
        nonlocal units_cnt
        action = city_tile.build_cart()
        actions.append(action)
        units_cnt += 1
        game_state.citytiles_with_new_units_xy_set.add(tuple(city_tile.pos))
        if annotation:
            actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, annotation))
        city_tile.cooldown += 10

    city_tiles: List[CityTile] = []
    for city in player.cities.values():
        for city_tile in city.citytiles:
            city_tiles.append(city_tile)
    if not city_tiles:
        return False, []


    def calculate_city_cluster_bonus(pos: Position):
        current_leader = game_state.xy_to_resource_group_id.find(tuple(pos))
        units_mining_on_current_cluster = game_state.resource_leader_to_locating_units[current_leader] & game_state.resource_leader_to_targeting_units[current_leader]
        resource_size_of_current_cluster = game_state.xy_to_resource_group_id.get_point(current_leader)
        return resource_size_of_current_cluster / (1+len(units_mining_on_current_cluster))


    city_tiles.sort(key=lambda city_tile:(
        - calculate_city_cluster_bonus(city_tile.pos),
        - max(1, game_state.distance_from_player_units[city_tile.pos.y,city_tile.pos.x])  # max because we assume that it will leave
        + max(3, game_state.distance_from_opponent_assets[city_tile.pos.y,city_tile.pos.x]),
        - game_state.distance_from_collectable_resource[city_tile.pos.y,city_tile.pos.x],
        - game_state.distance_from_edge[city_tile.pos.y,city_tile.pos.x],
        city_tile.pos.x * game_state.x_order_coefficient,
        city_tile.pos.y * game_state.y_order_coefficient))


    for city_tile in city_tiles:
        if not city_tile.can_act():
            continue

        print("city_tile values", -calculate_city_cluster_bonus(city_tile.pos),
        - max(1, game_state.distance_from_player_units[city_tile.pos.y,city_tile.pos.x])  # max because we assume that it will leave
        + game_state.distance_from_opponent_assets[city_tile.pos.y,city_tile.pos.x],
        - game_state.distance_from_collectable_resource[city_tile.pos.y,city_tile.pos.x],
        - game_state.distance_from_edge[city_tile.pos.y,city_tile.pos.x],
        city_tile.pos.x * game_state.x_order_coefficient,
        city_tile.pos.y * game_state.y_order_coefficient)

        unit_limit_exceeded = (units_cnt >= units_cap)

        if player.researched_uranium() and unit_limit_exceeded:
            # you cannot build units because you have reached your limits
            print("limit reached", city_tile.cityid, tuple(city_tile.pos))
            continue

        nearest_resource_distance = game_state.distance_from_collectable_resource[city_tile.pos.y, city_tile.pos.x]
        travel_range_emptyhanded = 1 + game_state.turns_to_night // GAME_CONSTANTS["PARAMETERS"]["UNIT_ACTION_COOLDOWN"]["WORKER"]
        resource_in_travel_range = nearest_resource_distance <= travel_range_emptyhanded

        cluster_leader = game_state.xy_to_resource_group_id.find(tuple(city_tile.pos))
        cluster_unit_limit_exceeded = \
            game_state.xy_to_resource_group_id.get_point(tuple(city_tile.pos)) <= len(game_state.resource_leader_to_locating_units[cluster_leader])

        # standard process of building workers
        if resource_in_travel_range and not unit_limit_exceeded and not cluster_unit_limit_exceeded:
            print("build_worker WA", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range_emptyhanded)
            build_worker(city_tile, "WA")
            continue

        # allow cities to build workers even if cluster_unit_limit_exceeded
        # because uranium is researched or scouting for advanced resources
        # require resource_in_travel_range
        if player.researched_uranium() or (units_cnt <= units_cap//4 and game_state.turn%40 < 10):
            if resource_in_travel_range:
                # but do not build workers beside wood to conserve wood
                if game_state.wood_side_matrix[city_tile.pos.y, city_tile.pos.x] == 0:
                    print("supply workers WB", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range_emptyhanded)
                    build_worker(city_tile, "WB")
                    continue

        # build worker and move to adjacent if there are no workers nearby
        if nearest_resource_distance == 2 and game_state.distance_from_player_units[city_tile.pos.y, city_tile.pos.x] > 2:
            print("supply workers WC", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range_emptyhanded)
            build_worker(city_tile, "WC")
            continue


        if not player.researched_uranium():
            # give up researching to allow building of units at turn 359
            if game_state.turn < 10:
                actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, "NS"))
            elif game_state.turn < 350:
                print("research RA", tuple(city_tile.pos))
                do_research(city_tile, "RA")
                continue
            else:
                actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, "NE"))

        # extend carts to fetch resource
        if 10 < game_state.player.cities[city_tile.cityid].night_fuel_duration < 30 and game_state.is_day_time:
            if game_state.player.cities[city_tile.cityid].citytiles.__len__() > 5:
                if not unit_limit_exceeded:
                    build_cart(city_tile, "NC")

        # easter egg - build carts or research for fun when there is no resource left
        if game_state.map_resource_count == 0 and game_state.is_day_time:
            if not unit_limit_exceeded:
                if game_state.player.cities[city_tile.cityid].fuel_needed_for_game < 0:
                    print("research NC", tuple(city_tile.pos))
                    do_research(city_tile, "RA")
                else:
                    build_cart(city_tile, "NC")

        # build workers at end of game
        if game_state.turn == 359:
            print("build_worker WE", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range_emptyhanded)
            build_cart(city_tile, "WE")
            continue

        # otherwise don't do anything

    return reset_missions, actions


def make_unit_missions(game_state: Game, missions: Missions, is_initial_plan=False, DEBUG=False) -> Missions:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player = game_state.player
    cleanup_missions(game_state, missions, DEBUG=DEBUG)
    actions_ejections = []

    cluster_annotations = []

    player.units.sort(key=lambda unit: (
        tuple(unit.pos) not in game_state.player_city_tile_xy_set,
        game_state.distance_from_opponent_assets[unit.pos.y,unit.pos.x],
        game_state.distance_from_resource_median[unit.pos.y,unit.pos.x],
        unit.pos.x*game_state.x_order_coefficient,
        unit.pos.y*game_state.y_order_coefficient,
        unit.encode_tuple_for_cmp()))


    # attempt to eject coal/uranium, unit is the one ejecting
    for unit in player.units:
        # unit is the one ejecting
        unit: Unit = unit
        if not unit.can_act():
            continue

        # source unit has lots of fuel (full coal or 50 uranium)
        if not (unit.cargo.uranium > 50 or unit.cargo.coal >= 100):
            continue

        # source unit not in empty tile
        if tuple(unit.pos) not in game_state.convolved_collectable_tiles_xy_set:
            continue

        for adj_unit in player.units:
            # adj_unit is the one being ejected
            adj_unit: Unit = adj_unit
            if not adj_unit.can_act():
                continue

            # source unit is not the target unit
            if adj_unit.id == unit.id:
                continue

            # source unit is not beside target unit
            if adj_unit.pos - unit.pos != 1:
                continue

            # adjacent unit is in city tile
            if tuple(adj_unit.pos) not in game_state.player_city_tile_xy_set:
                continue

            # adjacent unit is beside an empty tile
            if game_state.distance_from_empty_tile[adj_unit.pos.y, adj_unit.pos.x] != 1:
                continue

            # adjacent unit is inside a city that can survive the night
            if game_state.matrix_player_cities_nights_of_fuel_required_for_night[adj_unit.pos.y, adj_unit.pos.x] >= 0:
                continue

            # execute actions for ejection
            action_1 = unit.transfer(adj_unit.id, unit.cargo.get_most_common_resource(), 100)
            for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
                xx,yy = adj_unit.pos.x + dx, adj_unit.pos.y + dy
                if (xx,yy) in game_state.empty_tile_xy_set:
                    print("ejecting", unit.id, unit.pos, adj_unit.id, adj_unit.pos, "->")
                    action_2 = adj_unit.move(direction)
                    actions_ejections.append(action_1)
                    actions_ejections.append(action_2)
                    actions_ejections.append(annotate.text(unit.pos.x, unit.pos.y, "🟡", 50))
                    unit.cargo = Cargo()
                    adj_unit.cargo.wood += 100  # not correct, but simulated
                    unit.cooldown += 2
                    adj_unit.cooldown += 2
                    game_state.player_units_matrix[adj_unit.pos.y,adj_unit.pos.x] -= 1
                    break
            else:
                break

           # add missions for ejection
            print("plan mission ejection success", xx, yy)

            # if successful
            if unit.id in missions:
                print("delete mission because ejecting", unit.id, unit.pos)
                del missions[unit.id]
            if adj_unit.id in missions:
                print("delete mission because ejected", adj_unit.id, adj_unit.pos)
                del missions[adj_unit.id]
            game_state.unit_ids_with_missions_assigned_this_turn.add(adj_unit.id)
            game_state.ejected_units_set.add(adj_unit.id)

            # break loop since partner for unit is found
            if not unit.can_act():
                break


    # attempt to eject, unit is the one ejecting
    for unit in player.units:
        # unit is the one ejecting
        unit: Unit = unit
        if not unit.can_act():
            continue

        if is_initial_plan and game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] < 5:
            continue

        # source unit not in empty tile
        if tuple(unit.pos) in game_state.buildable_tile_xy_set:
            continue

        # source unit has almost full resources
        if unit.get_cargo_space_used() < 96 and unit.cargo.get_most_common_resource_count() < 40:
            continue

        print("considering unit", unit.id)

        for adj_unit in player.units:
            # adj_unit is the one being ejected
            adj_unit: Unit = adj_unit
            if not adj_unit.can_act():
                continue

            # source unit is not the target unit
            if adj_unit.id == unit.id:
                continue

            # source unit is not beside target unit
            if adj_unit.pos - unit.pos != 1:
                continue

            # adjacent unit is in city tile
            if tuple(adj_unit.pos) not in game_state.player_city_tile_xy_set:
                continue

            # adjacent unit is beside an empty tile
            if game_state.distance_from_empty_tile[adj_unit.pos.y, adj_unit.pos.x] != 1:
                continue

            # temporarily augment night travel range
            adj_unit.cargo.wood += unit.cargo.get_most_common_resource_count()
            adj_unit.compute_travel_range((game_state.turns_to_night, game_state.turns_to_dawn, game_state.is_day_time),)
            best_position, best_cell_value, cluster_annotation = find_best_cluster(game_state, adj_unit, DEBUG=DEBUG, explore=True, ref_pos=unit.pos)
            distance_of_best = game_state.retrieve_distance(adj_unit.pos.x, adj_unit.pos.y, best_position.x, best_position.y)
            adj_unit.cargo.wood -= unit.cargo.get_most_common_resource_count()
            adj_unit.compute_travel_range((game_state.turns_to_night, game_state.turns_to_dawn, game_state.is_day_time),)

            print("eligible mission ejection", unit.id, unit.pos, best_cell_value)

            # no suitable candidate found
            if best_cell_value == [0,0,0,0]:
                continue

            # do not eject and return to the same cluster
            if game_state.xy_to_resource_group_id.find(tuple(best_position)) == game_state.xy_to_resource_group_id.find(tuple(unit.pos)):
                continue

            # add missions for ejection
            print("plan mission ejection", adj_unit.id, adj_unit.pos, "->", best_position, best_cell_value)

            # execute actions for ejection
            action_1 = unit.transfer(adj_unit.id, unit.cargo.get_most_common_resource(), 100)
            for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
                xx,yy = adj_unit.pos.x + dx, adj_unit.pos.y + dy
                if (xx,yy) in game_state.empty_tile_xy_set:
                    if game_state.retrieve_distance(xx, yy, best_position.x, best_position.y) > distance_of_best:
                        continue
                    if Position(xx,yy) - best_position > unit.pos - best_position:
                        continue
                    if Position(xx,yy) - best_position > adj_unit.pos - best_position:
                        continue
                    print("ejecting", unit.id, unit.pos, adj_unit.id, adj_unit.pos, direction, "->", best_position)
                    game_state.occupied_xy_set.add((xx,yy),)
                    game_state.empty_tile_xy_set.remove((xx,yy))
                    action_2 = adj_unit.move(direction)
                    actions_ejections.append(action_1)
                    actions_ejections.append(action_2)
                    actions_ejections.append(annotate.text(unit.pos.x, unit.pos.y, "🔴", 50))
                    unit.cargo = Cargo()
                    adj_unit.cargo.wood += 100  # not correct, but simulated
                    unit.cooldown += 2
                    adj_unit.cooldown += 2
                    game_state.player_units_matrix[adj_unit.pos.y,adj_unit.pos.x] -= 1
                    break
            else:
                break

           # add missions for ejection
            print("plan mission ejection success", xx, yy)

            # if successful
            if unit.id in missions:
                print("delete mission because ejecting", unit.id, unit.pos)
                del missions[unit.id]
            if adj_unit.id in missions:
                print("delete mission because ejected", adj_unit.id, adj_unit.pos)
                del missions[adj_unit.id]
            mission = Mission(adj_unit.id, best_position, delays=distance_of_best)
            missions.add(mission)
            game_state.unit_ids_with_missions_assigned_this_turn.add(adj_unit.id)
            game_state.ejected_units_set.add(adj_unit.id)
            cluster_annotations.extend(cluster_annotation)

            # break loop since partner for unit is found
            if not unit.can_act():
                break

    # main sequence
    for unit in player.units:
        if unit.id in game_state.unit_ids_with_missions_assigned_this_turn:
            continue
        # mission is planned regardless whether the unit can act
        current_mission: Mission = missions[unit.id] if unit.id in missions else None
        current_target = current_mission.target_position if current_mission else None

        # avoid sharing the same target
        game_state.repopulate_targets(missions)

        # do not make missions from a fortress
        if game_state.distance_from_floodfill_by_player_city[unit.pos.y, unit.pos.x] > 1:
            # if you are carrying some wood
            if unit.cargo.wood >= 40:
                # assuming uranium has yet to be researched
                if not game_state.player.researched_uranium():
                    # allow building beside sustainable city
                    if not game_state.preferred_buildable_tile_matrix[unit.pos.y,unit.pos.x]:
                        print("no mission from fortress", unit.id)
                        continue

        # do not make missions if you could mine uranium from a citytile that is not fueled for the night
        if game_state.matrix_player_cities_nights_of_fuel_required_for_night[unit.pos.y, unit.pos.x] > 0 or (
            game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] <= 3 and
            game_state.matrix_player_cities_nights_of_fuel_required_for_game[unit.pos.y, unit.pos.x] > 0):
            if game_state.player.researched_uranium():
                if game_state.convolved_uranium_exist_matrix[unit.pos.y, unit.pos.x] > 0:
                    if tuple(unit.pos) not in game_state.citytiles_with_new_units_xy_set:
                        if game_state.player_units_matrix[unit.pos.y, unit.pos.x] == 1:
                            print("stay and mine uranium", unit.id, unit.pos)
                            # unless the citytile is producing new units
                            continue

        # do not make missions if you could mine coal from a citytile that is not fueled for the night
        if game_state.matrix_player_cities_nights_of_fuel_required_for_night[unit.pos.y, unit.pos.x] > 0 or (
            game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] <= 3 and
            game_state.matrix_player_cities_nights_of_fuel_required_for_game[unit.pos.y, unit.pos.x] > 0):
            if game_state.player.researched_coal():
                if game_state.convolved_coal_exist_matrix[unit.pos.y, unit.pos.x] > 0:
                    if tuple(unit.pos) not in game_state.citytiles_with_new_units_xy_set:
                        if game_state.player_units_matrix[unit.pos.y, unit.pos.x] == 1:
                            print("stay and mine coal", unit.id, unit.pos)
                            # unless the citytile is producing new units
                            continue

        current_leader = game_state.xy_to_resource_group_id.find(tuple(unit.pos))
        units_mining_on_current_cluster = game_state.resource_leader_to_locating_units[current_leader] & game_state.resource_leader_to_targeting_units[current_leader]
        resource_size_of_current_cluster = game_state.xy_to_resource_group_id.get_point(current_leader)
        current_cluster_load = len(units_mining_on_current_cluster) / (0.01+resource_size_of_current_cluster)

        # if you are targeting your own cluster you are at and you have at least 60 wood and close to edge
        targeting_current_cluster = unit.id not in missions or (unit.id in missions and \
                                    game_state.xy_to_resource_group_id.find(tuple(unit.pos)) == \
                                    game_state.xy_to_resource_group_id.find(tuple(missions.get_target_of_unit(unit.id))))
        full_resources_on_next_turn = not ((unit.get_cargo_space_used() + game_state.resource_collection_rate[unit.pos.y, unit.pos.x] * (1 + int(unit.cooldown)) < 100
                                           ) or (31 < game_state.turn%40 <= 37))

        print("housing test", unit.id, unit.pos, unit.id in missions, targeting_current_cluster, full_resources_on_next_turn)

        # if far away from enemy units, attempt to send units to empty cluster
        if game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] > 10:
            if not unit.can_act():
                pass
            elif not full_resources_on_next_turn:
                best_position, best_cell_value, cluster_annotation = find_best_cluster(game_state, unit, DEBUG=DEBUG, require_empty_target=True)
                distance_from_best_position = game_state.retrieve_distance(unit.pos.x, unit.pos.y, best_position.x, best_position.y)
                if best_cell_value > [0,0,0,0]:
                    print("force empty cluster", unit.id, unit.pos, "->", best_position, best_cell_value)
                    mission = Mission(unit.id, best_position, delays=distance_from_best_position)
                    missions.add(mission)
                    game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                    cluster_annotations.extend(cluster_annotation)
                    continue


        # you consider building a citytile only if you are currently targeting the cluster you are in
        if targeting_current_cluster:

            def get_best_eligible_tile(xy_set: Set) -> Tuple[Position, int]:

                best_heuristic = -999
                nearest_position: Position = unit.pos
                for dx,dy in game_state.dirs_dxdy[:-1]:
                    xx,yy = unit.pos.x+dx, unit.pos.y+dy
                    if (xx,yy) in xy_set:
                        if (xx,yy) in game_state.player_units_xy_set and (xx,yy) != tuple(unit.pos):
                            continue
                        if (xx,yy) in game_state.targeted_for_building_xy_set:
                            # we allow units to build at a tile that is targeted but not for building
                            if not current_target:
                                # definitely you are not the one targeting it
                                continue
                            if current_target and (xx,yy) != tuple(current_target):
                                continue
                        if unit.get_cargo_space_used() + 2*game_state.resource_collection_rate[yy, xx] >= 100:
                            heuristic = - game_state.distance_from_opponent_assets[yy,xx] - game_state.distance_from_resource_median[yy,xx]
                            if heuristic > best_heuristic:
                                best_heuristic = heuristic
                                nearest_position = Position(xx,yy)
                if best_heuristic > -999:
                    return True, nearest_position
                else:
                    return False, None


            relocation_to_preferred = (game_state.distance_from_preferred_buildable[unit.pos.y, unit.pos.x] <= 1 and
                                       unit.get_cargo_space_used() == 100 and 0 < game_state.turn%40 < 28 and
                                       game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] > 2
                                       ) or (
                                       game_state.distance_from_preferred_buildable[unit.pos.y, unit.pos.x] == 0 and
                                       unit.get_cargo_space_used() == 100 and 0 < game_state.turn%40 <= 31
                                       )

            # if you can move one step to a building that can survive a night, build there
            if relocation_to_preferred:
                has_found, new_pos = get_best_eligible_tile(game_state.preferred_buildable_tile_xy_set)
                if tuple(unit.pos) in game_state.preferred_buildable_tile_xy_set:
                    has_found, new_pos = True, unit.pos
                if has_found:
                    print("relocation_to_preferred", unit.id, unit.pos, "->", new_pos)
                    mission = Mission(unit.id, new_pos, unit.build_city(), delays=2)
                    missions.add(mission)
                    game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                    annotation = annotate.text(unit.pos.x, unit.pos.y, "R1")
                    cluster_annotations.append(annotation)
                    continue

            relocation_to_probable =  (game_state.distance_from_probably_buildable[unit.pos.y, unit.pos.x] <= 1 and
                                       unit.get_cargo_space_used() == 100 and 0 < game_state.turn%40 < 28 and
                                       game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] > 3 and
                                       game_state.turn > 40 and current_cluster_load > 1/2
                                       ) or (
                                       game_state.distance_from_probably_buildable[unit.pos.y, unit.pos.x] == 0 and
                                       unit.get_cargo_space_used() == 100 and 0 < game_state.turn%40 <= 30
                                       )

            # if the cluster is crowded, consider building at a corner (which is not directly collecting resources)
            if relocation_to_probable:
                has_found, new_pos = get_best_eligible_tile(game_state.probably_buildable_tile_xy_set)
                if tuple(unit.pos) in game_state.probably_buildable_tile_xy_set:
                    has_found, new_pos = True, unit.pos
                if has_found:
                    print("relocation_to_probable", unit.id, unit.pos, "->", new_pos)
                    mission = Mission(unit.id, new_pos, unit.build_city(), delays=2)
                    missions.add(mission)
                    game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                    annotation = annotate.text(unit.pos.x, unit.pos.y, "R2")
                    cluster_annotations.append(annotation)
                    continue

            # if you will have full resources on the next turn and on buildable tile, stay and build
            if full_resources_on_next_turn and tuple(unit.pos) in game_state.buildable_tile_xy_set:
                if game_state.distance_from_player_citytiles[unit.pos.y, unit.pos.x] == 1 or \
                    game_state.distance_from_collectable_resource[unit.pos.y, unit.pos.x] == 1:
                    print("stay on location", unit.id, unit.pos)
                    mission = Mission(unit.id, unit.pos, unit.build_city(), delays=2)
                    missions.add(mission)
                    game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                    annotation = annotate.text(unit.pos.x, unit.pos.y, "R3")
                    cluster_annotations.append(annotation)
                    continue

            if not full_resources_on_next_turn:
                has_found, new_pos = get_best_eligible_tile(game_state.buildable_and_convolved_collectable_tile_xy_set)
                if has_found:
                    print("relocation to better one", unit.id, unit.pos, "->", new_pos)
                    mission = Mission(unit.id, new_pos, unit.build_city(), delays=2)
                    missions.add(mission)
                    game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                    annotation = annotate.text(unit.pos.x, unit.pos.y, "R4")
                    cluster_annotations.append(annotation)
                    continue

            if full_resources_on_next_turn:
                has_found, new_pos = get_best_eligible_tile(game_state.buildable_and_convolved_collectable_tile_xy_set)
                if has_found:
                    print("build now", unit.id, unit.pos, "->", new_pos)
                    mission = Mission(unit.id, new_pos, unit.build_city(), delays=2)
                    missions.add(mission)
                    game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                    annotation = annotate.text(unit.pos.x, unit.pos.y, "R5")
                    cluster_annotations.append(annotation)
                    continue


        if is_initial_plan:
            continue

        # preemptive homing mission
        if tuple(unit.pos) not in game_state.convolved_collectable_tiles_xy_set or game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] > 2:
          if unit.cargo.uranium > 0:
            # if there is a citytile nearby already
            homing_distance, homing_position = game_state.find_nearest_city_requiring_fuel(
                unit, require_reachable=True, require_night=True, enforce_night=True, enforce_night_addn=10,
                minimum_size=10, maximum_distance=unit.cargo.uranium//3)
            if unit.pos != homing_position:
                print("homing two", unit.id, unit.pos, homing_position)
                mission = Mission(unit.id, homing_position, details="homing two", delays=homing_distance + 2)
                missions.add(mission)
                game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                annotation = annotate.text(unit.pos.x, unit.pos.y, "H2")
                cluster_annotations.append(annotation)
                continue

        if tuple(unit.pos) not in game_state.convolved_collectable_tiles_xy_set or game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] > 2:
          if unit.cargo.uranium > 0 and unit.cargo.get_most_common_resource() == "uranium":
            # if there is a citytile nearby already
            homing_distance, homing_position = game_state.find_nearest_city_requiring_fuel(
                unit, require_reachable=True, require_night=True, enforce_night=True,
                minimum_size=3, maximum_distance=unit.cargo.uranium//3)
            if unit.pos != homing_position:
                print("homing one", unit.id, unit.pos, homing_position, homing_distance)
                mission = Mission(unit.id, homing_position, details="homing", delays=homing_distance + 2)
                missions.add(mission)
                game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
                annotation = annotate.text(unit.pos.x, unit.pos.y, "H1")
                cluster_annotations.append(annotation)
                continue

        if unit.id in missions:
            mission: Mission = missions[unit.id]
            if mission.target_position == unit.pos:
                # take action and not make missions if already at position
                continue

        if unit.id in missions:
            # the mission will be recaluated if the unit fails to make a move after make_unit_actions
            continue

        best_position, best_cell_value, cluster_annotation = find_best_cluster(game_state, unit, DEBUG=DEBUG)
        print(unit.id, best_position, best_cell_value)
        distance_from_best_position = game_state.retrieve_distance(unit.pos.x, unit.pos.y, best_position.x, best_position.y)
        if best_cell_value > [0,0,0,0]:
            print("plan mission adaptative", unit.id, unit.pos, "->", best_position, best_cell_value)
            mission = Mission(unit.id, best_position, delays=distance_from_best_position)
            missions.add(mission)
            game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
            cluster_annotations.extend(cluster_annotation)
            continue

        # homing mission
        if unit.get_cargo_space_used() > 0:
            homing_distance, homing_position = game_state.find_nearest_city_requiring_fuel(unit)
            print("homing mission", unit.id, unit.pos, "->", homing_position, homing_distance)
            mission = Mission(unit.id, homing_position, "", details="homing", delays=homing_distance + 2)
            missions.add(mission)
            game_state.unit_ids_with_missions_assigned_this_turn.add(unit.id)
            continue

    return actions_ejections + cluster_annotations


def make_unit_actions(game_state: Game, missions: Missions, DEBUG=False) -> Tuple[Missions, List[str]]:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player, opponent = game_state.player, game_state.opponent
    actions = []

    units_with_mission_but_no_action = set(missions.keys())
    prev_actions_len = -1

    # repeat attempting movements for the units until no additional movements can be added
    while prev_actions_len < len(actions):
      prev_actions_len = len(actions)

      for unit in player.units:
        if not unit.can_act():
            units_with_mission_but_no_action.discard(unit.id)
            continue

        # if there is no mission, continue
        if unit.id not in missions:
            units_with_mission_but_no_action.discard(unit.id)
            continue

        mission: Mission = missions[unit.id]
        print("attempting action for", unit.id, unit.pos, "->", mission.target_position)

        # if the location is reached, take action
        if unit.pos == mission.target_position:
            units_with_mission_but_no_action.discard(unit.id)
            print("location reached and make action", unit.id, unit.pos)
            action = mission.target_action

            # do not build city at last light
            if action and action[:5] == "bcity" and 30 <= game_state.turn%40 <= 31:
                if game_state.fuel_collection_rate[unit.pos.y, unit.pos.x] < 23:
                    print("do not build city at last light", unit.id)
                    actions.append(annotate.text(unit.pos.x, unit.pos.y, "NB"))
                    del missions[unit.id]
                    continue

            if action:
                actions.append(action)
                unit.cooldown += 2
            print("mission complete and deleted", unit.id, unit.pos)
            del missions[unit.id]
            continue

        # attempt to move the unit
        direction, pos = attempt_direction_to(game_state, unit, mission.target_position,
                                         avoid_opponent_units=("homing" in mission.details),
                                         DEBUG=DEBUG)
        if direction == "c":
            continue

        # if carrying full wood, and next location has abundant wood, if on buildable, build house now
        if game_state.convolved_wood_exist_matrix[pos.y, pos.x] > 1:
            if unit.cargo.wood == 100:
                if unit.can_build(game_state.map):
                    actions.append(unit.build_city())
                    unit.cooldown += 2
                    continue

        if True:
            units_with_mission_but_no_action.discard(unit.id)
            action = unit.move(direction)
            print("make move", unit.id, unit.pos, direction, unit.pos.translate(direction, 1))
            game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1
            actions.append(action)
            continue

    # if the unit is not able to make an action over two turns, delete the mission
    for unit in game_state.player.units:
        if unit.id not in missions:
            continue
        mission: Mission = missions[unit.id]
        if mission.delays <= 0:
            print("delete mission delay timer over", unit.id, unit.pos, "->", mission.target_position)
            del missions[unit.id]
        elif mission.delays < 2 * (unit.pos - mission.target_position):
            print("delete mission cannot reach in time", unit.id, unit.pos, "->", mission.target_position)
            del missions[unit.id]

    return missions, actions


def make_unit_actions_supplementary(game_state: Game, missions: Missions, initial=False, DEBUG=False) -> Tuple[Missions, List[str]]:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player, opponent = game_state.player, game_state.opponent
    actions = []

    print("units without actions", [unit.id for unit in player.units if unit.can_act()])

    # probably should reduce code repetition in the following lines
    def make_random_move_to_void(unit: Unit, annotation: str = ""):
        if not unit.can_act():
            return
        (xxx,yyy) = (-1,-1)

        # in increasing order of priority

        # attempt to move away from your assets
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) not in game_state.occupied_xy_set:
                if game_state.distance_from_player_assets[yy,xx] > game_state.distance_from_player_assets[unit.pos.y,unit.pos.x]:
                    xxx,yyy = xx,yy
                    break

        # attempt to move toward enemy assets
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) not in game_state.occupied_xy_set and (xx,yy) not in game_state.player_city_tile_xy_set:
                if game_state.distance_from_collectable_resource[yy,xx] < game_state.distance_from_collectable_resource[unit.pos.y,unit.pos.x]:
                    xxx,yyy = xx,yy
                    break

        # cart pave roads
        if unit.is_cart():
            for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
                xx,yy = unit.pos.x + dx, unit.pos.y + dy
                if (xx,yy) not in game_state.occupied_xy_set:
                    if game_state.road_level_matrix[yy,xx] < game_state.road_level_matrix[unit.pos.y,unit.pos.x]:
                        xxx,yyy = xx,yy
                        break

        if (xxx,yyy) == (-1,-1):
            return

        xx,yy = xxx,yyy

        if (xx,yy) not in game_state.occupied_xy_set:
            if (xx,yy) not in game_state.player_city_tile_xy_set:
                game_state.occupied_xy_set.add((xx,yy))
            action = unit.move(direction)
            actions.append(action)
            if annotation:
                actions.append(annotate.text(unit.pos.x, unit.pos.y, annotation))
            unit.cooldown += 2
            game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1


    def make_random_move_to_center(unit: Unit, annotation: str = ""):
        if not unit.can_act():
            return
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) not in game_state.occupied_xy_set:
                if game_state.distance_from_preferred_median[yy,xx] < game_state.distance_from_preferred_median[unit.pos.y,unit.pos.x]:
                    # attempt to collide together and build additional citytile
                    break
        else:
            return

        if (xx,yy) not in game_state.occupied_xy_set:
            if (xx,yy) not in game_state.player_city_tile_xy_set:
                game_state.occupied_xy_set.add((xx,yy))
            action = unit.move(direction)
            actions.append(action)
            if annotation:
                actions.append(annotate.text(unit.pos.x, unit.pos.y, annotation))
            unit.cooldown += 2
            game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1


    # probably should reduce code repetition in the following lines
    def make_random_move_to_collectable(unit: Unit, annotation: str = ""):
        if not unit.can_act():
            return
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) not in game_state.occupied_xy_set:
                if (xx,yy) in game_state.convolved_collectable_tiles_xy_set:
                    # attempt to move away from your assets
                    break
        else:
            return

        if (xx,yy) not in game_state.occupied_xy_set:
            if (xx,yy) not in game_state.player_city_tile_xy_set:
                game_state.occupied_xy_set.add((xx,yy))
            action = unit.move(direction)
            actions.append(action)
            if annotation:
                actions.append(annotate.text(unit.pos.x, unit.pos.y, annotation))
            unit.cooldown += 2
            game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1


    def make_random_move_to_city(unit: Unit, annotation: str = ""):
        if not unit.can_act():
            return
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) in game_state.player_city_tile_xy_set:
                if game_state.player_units_matrix[yy,xx] < 1:
                    if (xx,yy) in game_state.convolved_collectable_tiles_xy_set:
                        break
        else:
            return

        if (xx,yy) not in game_state.occupied_xy_set:
            if (xx,yy) not in game_state.player_city_tile_xy_set:
                game_state.occupied_xy_set.add((xx,yy))
            action = unit.move(direction)
            actions.append(action)
            if annotation:
                actions.append(annotate.text(unit.pos.x, unit.pos.y, annotation))
            unit.cooldown += 2
            game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1
            game_state.player_units_matrix[yy,xx] += 1


    def make_random_move_to_city_sustain(unit: Unit, annotation: str = ""):
        if not unit.can_act():
            return
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) not in game_state.player_city_tile_xy_set:
                continue
            if (xx,yy) in game_state.xy_out_of_map:
                continue
            citytile = game_state.map.get_cell(xx,yy).citytile
            city = game_state.player.cities[citytile.cityid]
            if city.fuel_needed_for_night > 0 and unit.fuel_potential >= city.fuel_needed_for_night:
                print("sustain", unit.id, unit.pos, "->", xx, yy)
                action = unit.move(direction)
                actions.append(action)
                if annotation:
                    actions.append(annotate.text(unit.pos.x, unit.pos.y, annotation))
                unit.cooldown += 2
                game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1


    def make_random_transfer(unit: Unit, annotation: str = "", limit_target = False, allowed_target_xy: set = set()):
        if not unit.can_act():
            return
        if unit.get_cargo_space_used() == 0:
            # nothing to transfer
            return
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) in game_state.xy_out_of_map:
                continue
            if limit_target and (xx,yy) not in allowed_target_xy:
                continue
            adj_unit = game_state.map.get_cell(xx,yy).unit
            if not adj_unit:
                continue
            if adj_unit.id not in game_state.player.units_by_id:
                continue
            if adj_unit.is_worker() and adj_unit.get_cargo_space_used() == 100:
                continue

            # do not transfer to a citytile that can already last for the game
            cityid = game_state.map.get_cityid_of_cell(xx,yy)
            if cityid:
                city: City = game_state.player.cities[cityid]
                if city and city.fuel_needed_for_game < 0:
                    continue

            # if you are on buildable, do not transfer to nonbuildable and noncity
            if tuple(unit.pos) in game_state.buildable_tile_xy_set:
                if (xx,yy) not in game_state.buildable_tile_xy_set and (xx,yy) not in game_state.player_city_tile_xy_set:
                    continue

            print("random transfer", unit.id, unit.pos, "->", adj_unit.id, xx, yy)
            action = unit.transfer(adj_unit.id, unit.cargo.get_most_common_resource(), 2000)
            actions.append(action)
            if annotation:
                actions.append(annotate.text(unit.pos.x, unit.pos.y, annotation))
            actions.append(annotate.line(unit.pos.x, unit.pos.y, adj_unit.pos.x, adj_unit.pos.y))
            unit.cooldown += 2
            break

    if initial:
        return actions

    # if moving to a city can let it sustain the night, move into the city
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if game_state.turn%40 < 20:
            continue
        if tuple(unit.pos) not in game_state.buildable_tile_xy_set or not game_state.is_day_time:
            make_random_transfer(unit, "🟢", True, game_state.player_city_tile_xy_set)
        make_random_move_to_city_sustain(unit, "🟢")


    # no cluster rule
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if tuple(unit.pos) not in game_state.player_city_tile_xy_set:
            continue
        if game_state.player_units_matrix[unit.pos.y,unit.pos.x] > 1:
            print("dispersing", unit.id, unit.pos)
            make_random_move_to_city(unit, "FY")
            make_random_move_to_void(unit, "KD")


    # return to resource to mine
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if tuple(unit.pos) in game_state.convolved_collectable_tiles_xy_set:
            continue
        if unit.cargo.uranium > 0:
            continue
        make_random_move_to_collectable(unit, "KC")


    # dump it into a nearby citytile
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue

        # check for full resources
        if unit.get_cargo_space_left() > 4:
            continue
        # if you are in our fortress, dump only if the wood is more than 500
        if game_state.distance_from_floodfill_by_player_city[unit.pos.y, unit.pos.x] >= 2:
            if game_state.wood_amount_matrix[unit.pos.y, unit.pos.x] >= 500:
                print("FA make_random_move_to_city", unit.id)
                make_random_transfer(unit, "FA1", True, game_state.player_city_tile_xy_set)
                make_random_move_to_city(unit, "FA")
        # if you are in a fortress controlled by both players
        elif game_state.distance_from_floodfill_by_either_city[unit.pos.y, unit.pos.x] >= 2:
            print("FB make_random_move_to_city", unit.id)
            make_random_transfer(unit, "FB1", True, game_state.player_city_tile_xy_set)
            make_random_move_to_city(unit, "FB")
        # if you are near opponent assets and you are not on buildable tile
        if game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] <= 2:
            if tuple(unit.pos) not in game_state.buildable_tile_xy_set:
                print("FX make_random_move_to_city", unit.id)
                make_random_transfer(unit, "FX1", True, game_state.player_city_tile_xy_set)
                make_random_move_to_city(unit, "FX")


    # make random transfers
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if unit.get_cargo_space_left() == 0 and unit.is_worker() and game_state.map_resource_count < 500:
            actions.append(unit.build_city())
            continue
        if unit.get_cargo_space_used() == 0:
            continue
        make_random_transfer(unit, "KT", True, game_state.buildable_tile_xy_set)
        if tuple(unit.pos) in game_state.buildable_tile_xy_set:
            if game_state.distance_from_collectable_resource[unit.pos.y, unit.pos.x] == 1:
                if unit.cargo.get_most_common_resource() == "wood":
                    continue
        make_random_transfer(unit, "KR")


    # no sitting duck not collecting resources
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if tuple(unit.pos) in game_state.convolved_collectable_tiles_xy_set:
            continue
        if unit.fuel_potential == 0:
            if game_state.is_day_time:
                # suicide mission
                make_random_move_to_void(unit, "KS")
        else:
            # move to center so as to consolidate resources
            make_random_move_to_center(unit, "KP")


    # make a movement within the city at night, if near the enemy
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if tuple(unit.pos) not in game_state.player_city_tile_xy_set:
            continue
        if game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] >= 3:
            continue
        make_random_move_to_city(unit, "MC")


    return actions


def attempt_direction_to(game_state: Game, unit: Unit, target_pos: Position, avoid_opponent_units=False, DEBUG=False) -> DIRECTIONS:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    smallest_cost = [2,2,2,2,2]
    closest_dir = DIRECTIONS.CENTER
    closest_pos = unit.pos

    for direction in game_state.dirs:
        newpos = unit.pos.translate(direction, 1)

        cost = [0,0,0,0,0]

        # do not go out of map
        if tuple(newpos) in game_state.xy_out_of_map:
            continue

        # discourage collision among yourself
        # discourage if new position is occupied, not your city tile and not your current position and not your enemy units
        if tuple(newpos) in game_state.occupied_xy_set:
            if tuple(newpos) not in game_state.player_city_tile_xy_set:
                if tuple(newpos) not in game_state.opponent_units_xy_set:
                    if tuple(newpos) != tuple(unit.pos):
                        cost[0] = 3

        if tuple(newpos) in game_state.opponent_units_xy_set:
            if avoid_opponent_units:
                cost[0] = 1
            if tuple(newpos) not in game_state.opponent_units_moveable_xy_set:
                cost[0] = 3

        # discourage going into a city tile if you are carrying substantial wood
        if unit.cargo.wood >= 96:
            if tuple(newpos) in game_state.player_city_tile_xy_set:
                cost[0] = 1

        # discourage going into a city tile if you are carrying substantial wood
        if unit.cargo.wood >= 60:
            if tuple(newpos) in game_state.player_city_tile_xy_set:
                cost[0] = 1

        # no entering opponent citytile
        if tuple(newpos) in game_state.opponent_city_tile_xy_set:
            cost[0] = 4

        # if targeting same cluster, discourage walking on tiles without resources
        targeting_same_cluster = game_state.xy_to_resource_group_id.find(tuple(target_pos)) == game_state.xy_to_resource_group_id.find(tuple(unit.pos))
        if targeting_same_cluster:
            if tuple(newpos) not in game_state.convolved_collectable_tiles_xy_set:
                # unless you have researched uranium or you have some resources
                if not (game_state.player.researched_uranium_projected() or
                        unit.get_cargo_space_used() > 0 or
                        game_state.matrix_player_cities_nights_of_fuel_required_for_night[unit.pos.y, unit.pos.x] < 0):
                    # unless you are very far from opponent
                    if game_state.distance_from_opponent_assets[unit.pos.y,unit.pos.x] < 5:
                        cost[0] = 3

        # discourage going into a fueled city tile if you are carrying substantial coal and uranium
        if unit.cargo.coal + unit.cargo.uranium >= 10:
            if game_state.matrix_player_cities_nights_of_fuel_required_for_game[newpos.y, newpos.x] < 0:
                if tuple(newpos) in game_state.player_city_tile_xy_set:
                    cost[0] = 1

        # path distance as main differentiator
        path_dist = game_state.retrieve_distance(newpos.x, newpos.y, target_pos.x, target_pos.y)
        cost[1] = path_dist

        # manhattan distance to tie break
        manhattan_dist = (newpos - target_pos)
        cost[2] = manhattan_dist

        # prefer to walk on tiles with resources
        aux_cost = game_state.convolved_collectable_tiles_matrix[newpos.y, newpos.x]
        cost[3] = -min(2,aux_cost)

        # prefer to walk closer to opponent
        aux_cost = game_state.distance_from_opponent_assets[newpos.y, newpos.x]
        cost[4] = aux_cost

        # update decision
        if cost < smallest_cost:
            smallest_cost = cost
            closest_dir = direction
            closest_pos = newpos

        print(newpos, cost)

    if closest_dir != DIRECTIONS.CENTER:
        if tuple(closest_pos) not in game_state.opponent_unit_adjacent_xy_set:
            game_state.occupied_xy_set.discard(tuple(unit.pos))
        if tuple(closest_pos) not in game_state.player_city_tile_xy_set:
            game_state.occupied_xy_set.add(tuple(closest_pos))
        unit.cooldown += 2

    return closest_dir, closest_pos
