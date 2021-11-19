import os
import time
import pickle

import builtins as __builtin__

from lux.game import Game, Missions

from make_actions import make_city_actions, make_unit_missions, make_unit_actions, make_unit_actions_supplementary
from make_annotations import annotate_game_state, annotate_missions, annotate_movements, filter_cell_annotations


game_state = Game()
missions = Missions()


def game_logic(game_state: Game, missions: Missions, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    game_state.compute_start_time = time.time()
    game_state.calculate_features(missions)
    censoring = game_state.is_symmetrical()
    state_annotations = annotate_game_state(game_state)
    reset_missions, actions_by_cities = make_city_actions(game_state, missions, DEBUG=DEBUG)
    if reset_missions:
        print("reset_missions")
        missions.reset_missions(game_state.player.research_points,
                                game_state.convolve(game_state.coal_exist_matrix),
                                game_state.convolve(game_state.uranium_exist_matrix))
        game_state.calculate_features(missions)
    actions_by_units_initial = make_unit_actions_supplementary(game_state, missions, initial=True, DEBUG=DEBUG)
    cluster_annotations_and_ejections_pre = make_unit_missions(game_state, missions, is_initial_plan=True, DEBUG=DEBUG)
    missions, pre_actions_by_units = make_unit_actions(game_state, missions, DEBUG=DEBUG)
    cluster_annotations_and_ejections = make_unit_missions(game_state, missions, DEBUG=DEBUG)
    mission_annotations = annotate_missions(game_state, missions, DEBUG=DEBUG)
    missions, actions_by_units = make_unit_actions(game_state, missions, DEBUG=DEBUG)
    actions_by_units_supplementary = make_unit_actions_supplementary(game_state, missions, DEBUG=DEBUG)
    movement_annotations = annotate_movements(game_state, actions_by_units)

    print("actions_by_cities", actions_by_cities)
    print("actions_by_units_initial", actions_by_units_initial)
    print("cluster_annotations_and_ejections_pre", cluster_annotations_and_ejections_pre)
    print("pre_actions_by_units", pre_actions_by_units)
    print("cluster_annotations_and_ejections", cluster_annotations_and_ejections)
    print("mission_annotations", mission_annotations)
    print("actions_by_units", actions_by_units)
    print("actions_by_units_supplementary", actions_by_units_supplementary)
    print("state_annotations", state_annotations)
    print("movement_annotations", movement_annotations)
    actions = actions_by_cities + actions_by_units_initial + pre_actions_by_units + actions_by_units + actions_by_units_supplementary
    actions += cluster_annotations_and_ejections + cluster_annotations_and_ejections_pre
    actions += mission_annotations + movement_annotations + state_annotations
    actions = filter_cell_annotations(actions)
    if censoring: actions = []
    return actions, game_state, missions


def agent(observation, configuration, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    del configuration  # unused
    global game_state, missions

    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state.player_id = observation.player
        game_state._update(observation["updates"][2:])
        game_state.fix_iteration_order()
    else:
        # actually rebuilt and recomputed from scratch
        game_state._update(observation["updates"])

    if not os.environ.get('GFOOTBALL_DATA_DIR', ''):  # on Kaggle compete, do not save items
        str_step = str(observation["step"]).zfill(3)
        with open('snapshots/observation-{}-{}.pkl'.format(str_step, game_state.player_id), 'wb') as handle:
            pickle.dump(observation, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open('snapshots/game_state-{}-{}.pkl'.format(str_step, game_state.player_id), 'wb') as handle:
            pickle.dump(game_state, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open('snapshots/missions-{}-{}.pkl'.format(str_step, game_state.player_id), 'wb') as handle:
            pickle.dump(missions, handle, protocol=pickle.HIGHEST_PROTOCOL)

    actions, game_state, missions = game_logic(game_state, missions)
    return actions
