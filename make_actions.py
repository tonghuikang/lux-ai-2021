# functions executing the actions

import builtins as __builtin__
from typing import Tuple, List

from lux.game import Game, Mission, Missions
from lux.game_objects import CityTile, Unit
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
    missions.cleanup(player,
                     game_state.player_city_tile_xy_set,
                     game_state.opponent_city_tile_xy_set,
                     game_state.convolved_collectable_tiles_xy_set)
    game_state.repopulate_targets(missions)

    units_cap = sum([len(x.citytiles) for x in player.cities.values()])
    units_cnt = len(player.units)  # current number of units

    actions: List[str] = []

    def do_research(city_tile: CityTile):
        action = city_tile.research()
        game_state.player.research_points += 1
        actions.append(action)
        actions.append(annotate.text(city_tile.pos.x, city_tile.pos.y, "R"))

    def build_workers(city_tile: CityTile):
        nonlocal units_cnt
        action = city_tile.build_worker()
        actions.append(action)
        units_cnt += 1
        game_state.citytiles_with_new_units_xy_set.add(tuple(city_tile.pos))

    city_tiles: List[CityTile] = []
    for city in player.cities.values():
        for city_tile in city.citytiles:
            city_tiles.append(city_tile)
    if not city_tiles:
        return []

    city_tiles.sort(key=lambda city_tile:
        (city_tile.pos.x*game_state.x_order_coefficient, city_tile.pos.y*game_state.y_order_coefficient))

    for city_tile in city_tiles:
        if not city_tile.can_act():
            continue

        unit_limit_exceeded = (units_cnt >= units_cap)

        if player.researched_uranium() and unit_limit_exceeded:
            print("skip city", city_tile.cityid, tuple(city_tile.pos))
            continue

        if not player.researched_uranium() and game_state.turns_to_night < 3:
            # give up researching to allow building of units at turn 359
            if game_state.turn < 350:
                print("research and dont build units at night", tuple(city_tile.pos))
                do_research(city_tile)
                continue

        nearest_resource_distance = game_state.distance_from_collectable_resource[city_tile.pos.y, city_tile.pos.x]
        travel_range = game_state.turns_to_night // GAME_CONSTANTS["PARAMETERS"]["UNIT_ACTION_COOLDOWN"]["WORKER"]
        resource_in_travel_range = nearest_resource_distance < travel_range

        cluster_leader = game_state.xy_to_resource_group_id.find(tuple(city_tile.pos))
        cluster_unit_limit_exceeded = \
            game_state.xy_to_resource_group_id.get_point(tuple(city_tile.pos)) <= len(game_state.resource_leader_to_locating_units[cluster_leader])

        if resource_in_travel_range and not unit_limit_exceeded and not cluster_unit_limit_exceeded:
            print("build_worker", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range)
            build_workers(city_tile)
            continue

        if not player.researched_uranium():
            # give up researching to allow building of units at turn 359
            if game_state.turn < 350:
                print("research", tuple(city_tile.pos))
                do_research(city_tile)
                continue

        # build workers at end of game
        if game_state.turn == 359:
            print("build_worker", city_tile.cityid, city_tile.pos.x, city_tile.pos.y, nearest_resource_distance, travel_range)
            build_workers(city_tile)
            continue

        # otherwise don't do anything

    return actions


def make_unit_missions(game_state: Game, missions: Missions, DEBUG=False) -> Missions:
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    player = game_state.player
    missions.cleanup(player,
                     game_state.player_city_tile_xy_set,
                     game_state.opponent_city_tile_xy_set,
                     game_state.convolved_collectable_tiles_xy_set)

    unit_ids_with_missions_assigned_this_turn = set()

    player.units.sort(key=lambda unit:
        (unit.pos.x*game_state.x_order_coefficient, unit.pos.y*game_state.y_order_coefficient, unit.encode_tuple_for_cmp()))

    for unit in player.units:
        # mission is planned regardless whether the unit can act
        current_mission: Mission = missions[unit.id] if unit.id in missions else None
        current_target_position = current_mission.target_position if current_mission else None

        # avoid sharing the same target
        game_state.repopulate_targets(missions)

        # do not make missions from your fortress
        if game_state.distance_from_floodfill_by_player_city[unit.pos.y, unit.pos.x] > 1:
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
        stay_up_till_dawn = (unit.get_cargo_space_left() <= 4 and (game_state.turn%40 >= 36 or game_state.turn%40 == 0))
        # if the unit is full and it is going to be day the next few days
        # go to an empty tile and build a citytile
        # print(unit.id, unit.get_cargo_space_left())
        if unit.get_cargo_space_left() == 0 or stay_up_till_dawn:
            nearest_position, distance_with_features = game_state.get_nearest_empty_tile_and_distance(unit.pos, current_target_position)
            if distance_with_features[0] > 3:
                # not really near
                pass
            elif stay_up_till_dawn or distance_with_features[0] * 2 <= game_state.turns_to_night - 2:
                print("plan mission to build citytile", unit.id, unit.pos, "->", nearest_position)
                mission = Mission(unit.id, nearest_position, unit.build_city())
                missions.add(mission)
                continue

        if unit.id in missions:
            mission: Mission = missions[unit.id]
            if mission.target_position == unit.pos:
                # take action and not make missions if already at position
                continue

        if unit.id in missions:
            # the mission will be recaluated if the unit fails to make a move after make_unit_actions
            continue

        best_position, best_cell_value = find_best_cluster(game_state, unit, DEBUG=DEBUG)
        # [TODO] what if best_cell_value is zero
        distance_from_best_position = game_state.retrieve_distance(unit.pos.x, unit.pos.y, best_position.x, best_position.y)
        if best_cell_value > (0,0,0,0):
            print("plan mission adaptative", unit.id, unit.pos, "->", best_position, best_cell_value)
            mission = Mission(unit.id, best_position, None)
            missions.add(mission)
            unit_ids_with_missions_assigned_this_turn.add(unit.id)
            continue

        # homing mission
        if unit.get_cargo_space_left() < 100:
            homing_distance, homing_position = game_state.find_nearest_city_requiring_fuel(unit.pos)
            print("homing mission", unit.id, unit.pos, "->", homing_position, homing_distance)
            mission = Mission(unit.id, homing_position, None)
            missions.add(mission)
            unit_ids_with_missions_assigned_this_turn.add(unit.id)
            continue

    return missions


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
            if action and action[:5] == "bcity" and game_state.turn%40 == 30:
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

        # [TODO] make it possible for units to swap positions


    # attempt to eject
    prev_actions_len = -1
    while prev_actions_len < len(actions):
        prev_actions_len = len(actions)

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
                if game_state.distance_from_empty_tile[adj_unit.pos.y, adj_unit.pos.x] == 1:

                    # execute actions for ejection
                    action_1 = unit.transfer(adj_unit.id, unit.cargo.get_most_common_resource(), 2000)
                    for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
                        xx,yy = adj_unit.pos.x + dx, adj_unit.pos.y + dy
                        if (xx,yy) in game_state.empty_tile_xy_set:
                            print("ejecting", unit.id, unit.pos, adj_unit.id, adj_unit.pos)
                            action_2 = adj_unit.move(direction)
                            actions.append(action_1)
                            actions.append(action_2)
                            actions.append(annotate.text(unit.pos.x, unit.pos.y, "E"))
                            unit.cooldown += 2
                            adj_unit.cooldown += 2
                            game_state.player_units_matrix[adj_unit.pos.y,adj_unit.pos.x] -= 1
                            break

                # break loop
                if not unit.can_act():
                    break


    # no cluster rule
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if game_state.player_units_matrix[unit.pos.y,unit.pos.x] > 1:
            for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
                xx,yy = unit.pos.x + dx, unit.pos.y + dy
                if (xx,yy) not in game_state.occupied_xy_set:
                    print("dispersing", unit.id, unit.pos)
                    game_state.occupied_xy_set.add((xx,yy))
                    action = unit.move(direction)
                    actions.append(action)
                    actions.append(annotate.text(unit.pos.x, unit.pos.y, "D"))
                    unit.cooldown += 2
                    game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1
                    break


    # no sitting duck
    for unit in player.units:
        unit: Unit = unit
        if not unit.can_act():
            continue
        if tuple(unit.pos) in game_state.convolved_collectable_tiles_xy_set:
            continue
        for direction,(dx,dy) in zip(game_state.dirs, game_state.dirs_dxdy[:-1]):
            xx,yy = unit.pos.x + dx, unit.pos.y + dy
            if (xx,yy) not in game_state.occupied_xy_set:
                print("unseating sitting duck", unit.id, unit.pos)
                game_state.occupied_xy_set.add((xx,yy))
                action = unit.move(direction)
                actions.append(action)
                actions.append(annotate.text(unit.pos.x, unit.pos.y, "S"))
                unit.cooldown += 2
                game_state.player_units_matrix[unit.pos.y,unit.pos.x] -= 1
                break


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
        if tuple(newpos) in game_state.player_city_tile_xy_set and unit.cargo.wood >= 60:
            # only in early game
            if game_state.turn <= 80:
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
