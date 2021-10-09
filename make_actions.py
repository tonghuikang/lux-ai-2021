# functions executing the actions

import builtins as __builtin__
from typing import Tuple, List

from lux.game import Game, Mission, Missions, cleanup_missions
from lux.game_objects import Cargo, CityTile, Unit
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

    def do_research(city_tile: CityTile, annotation: str=""):
        action = city_tile.research()
        game_state.player.research_points += 1
        actions.append(action)
        if annotation:
            actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, annotation))
        city_tile.cooldown += 10

    def build_worker(city_tile: CityTile, annotation: str=""):
        nonlocal units_cnt
        action = city_tile.build_worker()
        actions.append(action)
        units_cnt += 1
        game_state.citytiles_with_new_units_xy_set.add(tuple(city_tile.pos))
        if annotation:
            actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, annotation))
        city_tile.cooldown += 10

        # fake unit and mission to simulate targeting
        unit = Unit(game_state.player_id, 0, city_tile.cityid, city_tile.pos.x, city_tile.pos.y,
                    cooldown=6, wood=0, coal=0, uranium=0)  # add dummy unit for targeting purposes
        game_state.players[game_state.player_id].units.append(unit)
        game_state.player.units_by_id[city_tile.cityid] = unit
        mission = Mission(city_tile.cityid, city_tile.pos, details="born")
        missions.add(mission)
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
        return []

    city_tiles.sort(key=lambda city_tile:(
        - game_state.distance_from_player_units[city_tile.pos.y,city_tile.pos.x],
        - game_state.distance_from_opponent_assets[city_tile.pos.y,city_tile.pos.x],
        - game_state.distance_from_collectable_resource[city_tile.pos.y,city_tile.pos.x],
        - game_state.distance_from_edge[city_tile.pos.y,city_tile.pos.x],
        city_tile.pos.x * game_state.x_order_coefficient,
        city_tile.pos.y * game_state.y_order_coefficient))

    for city_tile in city_tiles:
        if not city_tile.can_act():
            continue

        unit_limit_exceeded = (units_cnt >= units_cap)

        if player.researched_uranium() and unit_limit_exceeded:
            # you cannot build units because you have reached your limits
            print("limit reached", city_tile.cityid, tuple(city_tile.pos))
            continue

        nearest_resource_distance = game_state.distance_from_collectable_resource[city_tile.pos.y, city_tile.pos.x]
        travel_range = 1 + game_state.turns_to_night // GAME_CONSTANTS["PARAMETERS"]["UNIT_ACTION_COOLDOWN"]["WORKER"]
        resource_in_travel_range = nearest_resource_distance <= travel_range

        cluster_leader = game_state.xy_to_resource_group_id.find(tuple(city_tile.pos))
        cluster_unit_limit_exceeded = \
            game_state.xy_to_resource_group_id.get_point(tuple(city_tile.pos)) <= len(game_state.resource_leader_to_locating_units[cluster_leader])

        # standard requirements of building workers
        if resource_in_travel_range and not unit_limit_exceeded and not cluster_unit_limit_exceeded:
            print("build_worker WA", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range)
            build_worker(city_tile, "WA")
            continue

        # allow cities to build workers even if cluster_unit_limit_exceeded, if research limit is reached
        if player.researched_uranium() and resource_in_travel_range:
            # but do not build workers beside wood to conserve wood
            if game_state.wood_side_matrix[city_tile.pos.y, city_tile.pos.x] == 0:
                print("supply workers WS", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range)
                build_worker(city_tile, "WS")
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

        # easter egg - build carts for fun when there is no resource left
        if game_state.map_resource_count == 0 and game_state.is_day_time:
            if not unit_limit_exceeded:
                print("research NC", tuple(city_tile.pos))
                build_cart(city_tile, "NC")

        # build workers at end of game
        if game_state.turn == 359:
            print("build_worker WE", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range)
            build_cart(city_tile, "WE")
            continue

        # otherwise don't do anything

    return actions


def make_unit_missions(game_state: Game, missions: Missions, DEBUG=False) -> Missions:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player = game_state.player
    cleanup_missions(game_state, missions, DEBUG=DEBUG)
    actions_ejections = []

    unit_ids_with_missions_assigned_this_turn = set()
    cluster_annotations = []

    player.units.sort(key=lambda unit:
        (unit.pos.x*game_state.x_order_coefficient, unit.pos.y*game_state.y_order_coefficient, unit.encode_tuple_for_cmp()))

    # attempt to eject, unit is the one ejecting
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue

        # source unit not in empty tile
        if tuple(unit.pos) in game_state.empty_tile_xy_set:
            continue

        # source unit has almost full resources
        if unit.get_cargo_space_left() > 4:
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

            # temporarily augment night travel range
            adj_unit.cargo.wood += 100
            adj_unit.compute_travel_range()
            best_position, best_cell_value, cluster_annotation = find_best_cluster(game_state, adj_unit, DEBUG=DEBUG, explore=True)
            adj_unit.cargo.wood -= 100
            adj_unit.compute_travel_range()

            print("eligible mission ejection", unit.id, unit.pos, best_cell_value)

            # no suitable candidate found
            if best_cell_value == [0,0,0,0]:
                continue

            # do not eject and return to the same cluster
            if game_state.xy_to_resource_group_id.find(tuple(best_position)) == game_state.xy_to_resource_group_id.find(tuple(unit.pos)):
                continue

            # add missions for ejection
            print("plan mission ejection", adj_unit.id, adj_unit.pos, "->", best_position, best_cell_value)
            if adj_unit.id in missions:
                del missions[adj_unit.id]
            mission = Mission(adj_unit.id, best_position)
            missions.add(mission)
            unit_ids_with_missions_assigned_this_turn.add(adj_unit.id)
            cluster_annotations.extend(cluster_annotation)

            # execute actions for ejection
            # the amount is a stopgap measure to prevent the unit planning bcity mission immediately after ejection
            action_1 = unit.transfer(adj_unit.id, unit.cargo.get_most_common_resource(), 95)
            for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
                xx,yy = adj_unit.pos.x + dx, adj_unit.pos.y + dy
                if (xx,yy) in game_state.empty_tile_xy_set:
                    print("ejecting", unit.id, unit.pos, adj_unit.id, adj_unit.pos)
                    action_2 = adj_unit.move(direction)
                    actions_ejections.append(action_1)
                    actions_ejections.append(action_2)
                    actions_ejections.append(annotate.text(unit.pos.x, unit.pos.y, "🔴", 50))
                    unit.cargo = Cargo()
                    unit.cooldown += 2
                    adj_unit.cooldown += 2
                    game_state.player_units_matrix[adj_unit.pos.y,adj_unit.pos.x] -= 1
                    break

            # break loop since partner for unit is found
            if not unit.can_act():
                break


    for unit in player.units:
        # mission is planned regardless whether the unit can act
        current_mission: Mission = missions[unit.id] if unit.id in missions else None
        current_target_position = current_mission.target_position if current_mission else None

        # avoid sharing the same target
        game_state.repopulate_targets(missions)

        # do not make missions from a fortress
        if game_state.distance_from_floodfill_by_either_city[unit.pos.y, unit.pos.x] > 1:
            # if you are carrying some wood
            if unit.cargo.wood >= 40:
                # assuming resources have yet to be exhausted
                if game_state.map_resource_count:
                    print("no mission from fortress", unit.id)
                    continue

        # do not make missions if you could mine uranium from a citytile that is not fueled to the end
        if game_state.matrix_player_cities_nights_of_fuel_required_for_game[unit.pos.y, unit.pos.x] > 0:
            if game_state.player.researched_uranium():
                if game_state.convolved_uranium_exist_matrix[unit.pos.y, unit.pos.x] > 0:
                    if tuple(unit.pos) not in game_state.citytiles_with_new_units_xy_set:
                        # unless the citytile is producing new units
                        continue

        # do not make missions if you could mine coal from a citytile that is not fueled for the night
        if game_state.matrix_player_cities_nights_of_fuel_required_for_night[unit.pos.y, unit.pos.x] > 0:
            if game_state.player.researched_coal():
                if game_state.convolved_coal_exist_matrix[unit.pos.y, unit.pos.x] > 0:
                    if tuple(unit.pos) not in game_state.citytiles_with_new_units_xy_set:
                        # unless the citytile is producing new units
                        continue

        # if the unit is waiting for dawn at the side of resource
        stay_up_till_dawn = (unit.get_cargo_space_left() <= 4 and (game_state.turn%40 >= 32 or game_state.turn%40 == 0))
        # if the unit is full and it is going to be day the next few days
        # go to an empty tile and build a citytile
        # print(unit.id, unit.get_cargo_space_left())
        if unit.get_cargo_space_left() == 0 or stay_up_till_dawn:
            nearest_position, distance_with_features = game_state.get_nearest_empty_tile_and_distance(unit.pos, current_target_position)
            if distance_with_features[0] > 1:
                # not really near
                pass
            elif stay_up_till_dawn or distance_with_features[0] * 2 <= game_state.turns_to_night:
                print("plan mission to build citytile", unit.id, unit.pos, "->", nearest_position)
                mission = Mission(unit.id, nearest_position, unit.build_city())
                missions.add(mission)
                continue

        if unit.id in missions:
            mission: Mission = missions[unit.id]
            if mission.target_position == unit.pos:
                # take action and not make missions if already at position
                continue

        # preemptive homing mission
        if unit.cargo.uranium >= 90:
            # if there is a citytile nearby already
            if game_state.distance_from_floodfill_by_player_city[unit.pos.y, unit.pos.x] <= 2:
                homing_distance, homing_position = game_state.find_nearest_city_requiring_fuel(
                    unit.pos, require_reachable=True, minimum_size=5, maximum_distance=10)
                if unit.pos != homing_position:
                    mission = Mission(unit.id, homing_position, details="homing")
                    missions.add(mission)
                    unit_ids_with_missions_assigned_this_turn.add(unit.id)

        if unit.id in missions:
            # the mission will be recaluated if the unit fails to make a move after make_unit_actions
            continue

        best_position, best_cell_value, cluster_annotation = find_best_cluster(game_state, unit, DEBUG=DEBUG)
        distance_from_best_position = game_state.retrieve_distance(unit.pos.x, unit.pos.y, best_position.x, best_position.y)
        if best_cell_value > [0,0,0,0]:
            print("plan mission adaptative", unit.id, unit.pos, "->", best_position, best_cell_value)
            mission = Mission(unit.id, best_position)
            missions.add(mission)
            unit_ids_with_missions_assigned_this_turn.add(unit.id)
            cluster_annotations.extend(cluster_annotation)
            continue

        # homing mission
        if unit.get_cargo_space_left() < 100:
            homing_distance, homing_position = game_state.find_nearest_city_requiring_fuel(unit.pos)
            print("homing mission", unit.id, unit.pos, "->", homing_position, homing_distance)
            mission = Mission(unit.id, homing_position, "homing")
            missions.add(mission)
            unit_ids_with_missions_assigned_this_turn.add(unit.id)
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
                print("do not build city at last light", unit.id)
                actions.append(annotate.text(unit.pos.x, unit.pos.y, "NB"))
                del missions[unit.id]
                continue

            if action:
                actions.append(action)
                unit.cooldown += 2
            del missions[unit.id]
            continue

        # attempt to move the unit
        direction = attempt_direction_to(game_state, unit, mission.target_position)
        if direction != "c":
            units_with_mission_but_no_action.discard(unit.id)
            action = unit.move(direction)
            print("make move", unit.id, unit.pos, direction, unit.pos.translate(direction, 1))
            game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1
            actions.append(action)
            continue


    # probably should reduce code repetition in the following lines
    def make_random_move(unit: Unit, annotation: str = ""):
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) not in game_state.occupied_xy_set:
                if game_state.distance_from_player_citytiles[yy,xx] > game_state.distance_from_player_citytiles[unit.pos.y,unit.pos.x]:
                    # attempt to move away from your assets
                    break

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
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) in game_state.player_city_tile_xy_set:
                break

        if (xx,yy) not in game_state.occupied_xy_set:
            if (xx,yy) not in game_state.player_city_tile_xy_set:
                game_state.occupied_xy_set.add((xx,yy))
            action = unit.move(direction)
            actions.append(action)
            if annotation:
                actions.append(annotate.text(unit.pos.x, unit.pos.y, annotation))
            unit.cooldown += 2
            game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1


    def make_random_move_to_city_sustain(unit: Unit, annotation: str = ""):
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) in game_state.player_city_tile_xy_set:
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


    # if moving to a city can let it sustain the night, move into the city
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        make_random_move_to_city_sustain(unit, "🟢")


    # no cluster rule
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if game_state.player_units_matrix[unit.pos.y,unit.pos.x] > 1:
            print("dispersing", unit.id, unit.pos)
            make_random_move(unit, "KD")


    # no sitting duck
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if tuple(unit.pos) in game_state.convolved_collectable_tiles_xy_set:
            continue
        make_random_move(unit, "KS")


    # if you have near full resources but not moving, dump it into a nearby citytile
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue

        # check for full resources
        if unit.get_cargo_space_left() > 4:
            continue
        # if you are in our fortress, dump only if the wood is more than 450
        if game_state.distance_from_floodfill_by_player_city[unit.pos.y, unit.pos.x] >= 2:
            if game_state.wood_amount_matrix[unit.pos.y, unit.pos.x] >= 450:
                print("FA make_random_move_to_city", unit.id)
                make_random_move_to_city(unit, "FA")
        # if you are near opponent assets
        if game_state.distance_from_opponent_assets[unit.pos.y, unit.pos.x] <= 2:
            print("FB make_random_move_to_city", unit.id)
            make_random_move_to_city(unit, "FB")


    # if the unit is not able to make an action, delete the mission
    for unit_id in units_with_mission_but_no_action:
        mission: Mission = missions[unit_id]
        mission.delays += 1
        if mission.delays >= 1:
            del missions[unit_id]

    return missions, actions


def attempt_direction_to(game_state: Game, unit: Unit, target_pos: Position) -> DIRECTIONS:

    smallest_cost = [2,2,2,2]
    closest_dir = DIRECTIONS.CENTER
    closest_pos = unit.pos

    for direction in game_state.dirs:
        newpos = unit.pos.translate(direction, 1)

        cost = [0,0,0,0]

        # do not go out of map
        if tuple(newpos) in game_state.xy_out_of_map:
            continue

        # discourage if new position is occupied, not your city tile and not your current position
        if tuple(newpos) in game_state.occupied_xy_set:
            if tuple(newpos) not in game_state.player_city_tile_xy_set:
                if tuple(newpos) != tuple(unit.pos):
                    cost[0] = 3

        if tuple(newpos) in game_state.opponent_city_tile_xy_set:
            cost[0] = 3

        # discourage going into a city tile if you are carrying substantial wood
        if unit.cargo.wood >= 60:
            if tuple(newpos) in game_state.player_city_tile_xy_set:
                if game_state.turn <= 80:
                    # only in early game
                    cost[0] = 1

        # discourage going into a fueled city tile if you are carrying substantial coal and uranium
        if unit.cargo.wood + unit.cargo.uranium * 2 > 20:
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
        cost[3] = -aux_cost

        # if starting from the city, consider manhattan distance instead of path distance
        if tuple(unit.pos) in game_state.player_city_tile_xy_set:
            cost[1] = manhattan_dist

        # update decision
        if cost < smallest_cost:
            smallest_cost = cost
            closest_dir = direction
            closest_pos = newpos

    if closest_dir != DIRECTIONS.CENTER:
        game_state.occupied_xy_set.discard(tuple(unit.pos))
        if tuple(closest_pos) not in game_state.player_city_tile_xy_set:
            game_state.occupied_xy_set.add(tuple(closest_pos))
        unit.cooldown += 2

    return closest_dir
