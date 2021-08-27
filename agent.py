import os
import pickle

import numpy as np

from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux.annotate import pretty_print

from actions import *
from heuristics import *

game_state = Game()
missions = Missions()


def game_logic(observation, game_state, missions, DEBUG=False):

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.player_id = observation.player
    else:
        game_state._update(observation["updates"])
    
    if DEBUG: print("Tile and unit counts:", game_state.player.city_tile_count, len(game_state.player.units))
    if DEBUG: print([(unit.pos.x,unit.pos.y) for unit in game_state.player.units])

    # game_state.resource_scores_matrix
    # game_state.maxpool_scores_matrix
    # game_state.city_tile_matrix
    # game_state.empty_tile_matrix
    if DEBUG:
        print(np.array([game_state.resource_scores_matrix]))

    actions_cities = make_city_actions(game_state, DEBUG=DEBUG)
    
    missions = make_unit_missions(game_state, missions, DEBUG=DEBUG)
    if DEBUG: print(missions)

    missions, actions_units = make_unit_actions(game_state, missions, DEBUG=DEBUG)

    actions = actions_cities + actions_units
    return actions, game_state, missions


def agent(observation, configuration) -> List[str]:
    del configuration  # unused
    global game_state, missions, DEBUG

    str_step = str(observation["step"]).zfill(3)
    with open('snapshots/observation-{}.pkl'.format(str_step), 'wb') as handle:
        pickle.dump(observation, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with open('snapshots/game_state-{}.pkl'.format(str_step), 'wb') as handle:
        pickle.dump(game_state, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with open('snapshots/missions-{}.pkl'.format(str_step), 'wb') as handle:
        pickle.dump(missions, handle, protocol=pickle.HIGHEST_PROTOCOL)

    actions, game_state, missions = game_logic(observation, game_state, missions)

    if os.environ.get('GFOOTBALL_DATA_DIR', ''):  # on Kaggle compete
        print(actions)
    
    return actions
