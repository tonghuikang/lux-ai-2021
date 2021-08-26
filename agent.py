import os, re
import math
import time
import collections

import numpy as np

os.environ["notebook_debug"] = "YES"
NOTEBOOK_DEBUG = os.environ["notebook_debug"]

from lux.game import Game, Observation
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

from agnostic_helper import *
from actions import *
from heuristics import *

game_state = Game()
missions = Missions()

def agent(observation: Observation, configuration):
    del configuration  # unused
    global game_state, missions

    game_state._update_with_observation(observation) 
    print("counts", game_state.player.city_tile_count, len(game_state.player.units))
    print([(unit.pos.x,unit.pos.y) for unit in game_state.player.units])

    # game_state.resource_scores_matrix
    # game_state.maxpool_scores_matrix
    # game_state.city_tile_matrix
    # game_state.empty_tile_matrix
    print(np.array([game_state.resource_scores_matrix]))
    # print()

    actions_cities = make_city_actions(game_state)
    
    missions = make_unit_missions(game_state, missions)
    print(missions)

    missions, actions_units = make_unit_actions(game_state, missions)

    actions = actions_cities + actions_units
    print(actions)
    return actions
