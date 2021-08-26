# functions executing the actions

from lux.game import Game, Player
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

from agnostic_helper import pretty_print
from heuristics import *


def make_city_actions(game_state: Game):
    player = game_state.player
    # https://www.lux-ai.org/specs-2021#CityTiles
    
    actions = []
    
    # max number of units available
    units_cap = sum([len(x.citytiles) for x in player.cities.values()])
    units = len(player.units)  # current number of units
    
    cities = list(player.cities.values())
    if len(cities) > 0:
        city = cities[0]
        created_worker = (units >= units_cap)
        for city_tile in city.citytiles[::-1]:
            if city_tile.can_act():
                if created_worker:
                    # let's do research
                    action = city_tile.research()
                    actions.append(action)
                else:
                    # let's create one more unit in the last created city tile if we can
                    action = city_tile.build_worker()
                    actions.append(action)
                    created_worker = True
    return actions
