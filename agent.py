import os
import pickle

import numpy as np
import builtins as __builtin__

from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux.annotate import pretty_print

from actions import *
from heuristics import *

game_state = Game()
missions = Missions()


def game_logic(game_state, missions, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    actions_by_cities = make_city_actions(game_state, DEBUG=DEBUG)
    missions = make_unit_missions(game_state, missions, DEBUG=DEBUG)

    print("missions")
    print(missions)

    missions, actions_by_units = make_unit_actions(game_state, missions, DEBUG=DEBUG)

    actions = actions_by_cities + actions_by_units
    return actions, game_state, missions


def print_game_state(game_state, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    print("Citytile count: ", game_state.player.city_tile_count)
    print("Unit count: ", len(game_state.player.units))

    # you can print the objects from saved game_state

    return


def agent(observation, configuration, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    del configuration  # unused
    global game_state, missions

    if not os.environ.get('GFOOTBALL_DATA_DIR', ''):  # on Kaggle compete, do not save items
        str_step = str(observation["step"]).zfill(3)
        with open('snapshots/observation-{}.pkl'.format(str_step), 'wb') as handle:
            pickle.dump(observation, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open('snapshots/game_state-{}.pkl'.format(str_step), 'wb') as handle:
            pickle.dump(game_state, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open('snapshots/missions-{}.pkl'.format(str_step), 'wb') as handle:
            pickle.dump(missions, handle, protocol=pickle.HIGHEST_PROTOCOL)

    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.player_id = observation.player
    else:
        # actually rebuilt from scratch
        game_state._update(observation["updates"])

    print_game_state(game_state)
    actions, game_state, missions = game_logic(game_state, missions)

    if os.environ.get('GFOOTBALL_DATA_DIR', ''):  # on Kaggle compete, always print actions
        print(actions)

    return actions
