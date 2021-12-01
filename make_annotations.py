import time
from itertools import chain
from typing import List

import builtins as __builtin__

from lux.game import Game, Mission, Missions, Player, Unit
import lux.annotate as annotate


def annotate_game_state(game_state: Game, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    print("Turn number: ", game_state.turn)
    print("Citytile count: ", game_state.player.city_tile_count)
    print("Unit count: ", len(game_state.player.units))

    if game_state.player_id == 1:
        # reduce clutter for mirror matchup
        return []

    annotations = []

    for city in chain(game_state.player.cities.values(), game_state.opponent.cities.values()):
        for citytile in city.citytiles:
            if city.night_fuel_duration >= game_state.night_turns_left:
                annotation = annotate.circle(citytile.pos.x, citytile.pos.y)
                annotations.append(annotation)
            else:
                annotation = annotate.text(citytile.pos.x, citytile.pos.y, str(city.night_fuel_duration))
                annotations.append(annotation)


    for unit in chain(game_state.player.units, game_state.opponent.units):
        if unit.cargo.get_shorthand():
            annotation = annotate.text(unit.pos.x, unit.pos.y, unit.cargo.get_shorthand())
            annotations.append(annotation)

    annotation = annotate.text(int(game_state.resource_median.x), int(game_state.resource_median.y), "MD")
    annotations.append(annotation)
    annotation = annotate.text(int(game_state.resource_mean.x), int(game_state.resource_mean.y), "ME")
    annotations.append(annotation)
    annotation = annotate.text(int(game_state.player_unit_median.x), int(game_state.player_unit_median.y), "PD")
    annotations.append(annotation)
    annotation = annotate.text(int(game_state.player_city_median.x), int(game_state.player_city_median.y), "PE")
    annotations.append(annotation)

    # you can also read the pickled game_state and print its attributes
    return annotations


def annotate_missions(game_state: Game, missions: Missions, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    print("Missions")
    print(missions)
    # you can also read the pickled missions and print its attributes

    annotations: List[str] = []
    player: Player = game_state.player

    for unit_id, mission in missions.items():
        mission: Mission = mission
        unit: Unit = player.units_by_id[unit_id]

        annotation = annotate.line(unit.pos.x, unit.pos.y, mission.target_position.x, mission.target_position.y)
        annotations.append(annotation)

        # if mission.target_action and mission.target_action.split(" ")[0] == "bcity":
        #     annotation = annotate.x(mission.target_position.x, mission.target_position.y)
        #     annotations.append(annotation)
        # else:
        #     annotation = annotate.circle(mission.target_position.x, mission.target_position.y)
        #     annotations.append(annotation)

    annotation = annotate.sidetext("Unit Count: {}-{} Citytiles: {}-{} Groups: {}/{} Runtime: {:.3f}".format(
        len(game_state.player.units), len(game_state.opponent.units),
        len(game_state.player_city_tile_xy_set), len(game_state.opponent_city_tile_xy_set),
        game_state.targeted_cluster_count, game_state.xy_to_resource_group_id.get_group_count(),
        time.time() - game_state.compute_start_time))
    annotations.append(annotation)

    return annotations


def annotate_movements(game_state: Game, actions_by_units: List[str]):
    annotations = []
    dirs = game_state.dirs
    d5 = game_state.dirs_dxdy

    for action_by_units in actions_by_units:
        if action_by_units[:2] != "m ":
            continue
        unit_id, dir = action_by_units.split(" ")[1:]
        unit = game_state.player.units_by_id[unit_id]
        x, y = unit.pos.x, unit.pos.y
        dx, dy = d5[dirs.index(dir)]
        annotation = annotate.line(x, y, x+dx, y+dy)
        annotations.append(annotation)

    return annotations


def filter_cell_annotations(actions: List[str], game_state: Game):
    annotated_cell_xy_set = set()
    filtered_actions: List[str] = []
    for action in actions:
        instruction, *info = action.split()
        if instruction == "dt":
            if (info[0],info[1]) in annotated_cell_xy_set:
                continue
            annotated_cell_xy_set.add((info[0],info[1]))
        if action[:2] == "m " and action[-2:] == ' c':
            continue
        filtered_actions.append(action)
    for unit in game_state.player.units:
        if unit.cooldown < 1:
            no_action = unit.move("c")
            filtered_actions.append(no_action)
    return filtered_actions
