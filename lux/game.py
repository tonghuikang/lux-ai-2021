from typing import Dict, List, Tuple, Set

import numpy as np

from .constants import Constants
from .game_map import GameMap, RESOURCE_TYPES
from .game_objects import Player, Unit, City, CityTile, Position
from .game_constants import GAME_CONSTANTS

INPUT_CONSTANTS = Constants.INPUT_CONSTANTS


class Game:

    def _initialize(self, messages):
        """
        initialize state
        """
        self.player_id: int = int(messages[0])
        self.turn: int = -1
        # get some other necessary initial input
        mapInfo = messages[1].split(" ")
        self.map_width: int = int(mapInfo[0])
        self.map_height: int = int(mapInfo[1])
        self.map: GameMap = GameMap(self.map_width, self.map_height)
        self.players: List[Player] = [Player(0), Player(1)]

        self.targeted_xy_set: Set = set()


    def _end_turn(self):
        print("D_FINISH")


    def _reset_player_states(self):
        self.players[0].units = []
        self.players[0].cities = {}
        self.players[0].city_tile_count = 0
        self.players[1].units = []
        self.players[1].cities = {}
        self.players[1].city_tile_count = 0

        self.player: Player = self.players[self.player_id]
        self.opponent: Player = self.players[1 - self.player_id]


    def _update(self, messages):
        """
        update state
        """
        self.map = GameMap(self.map_width, self.map_height)
        self.turn += 1
        self._reset_player_states()

        # [TODO] Use constants here
        self.night_turns_left = (360 - self.turn)//40 * 10 + min(10, (360 - self.turn)%40)

        self.turns_to_night = (30 - self.turn)%40
        self.turns_to_night = 0 if self.turns_to_night > 30 else self.turns_to_night

        self.turns_to_dawn = (40 - self.turn%40)
        self.turns_to_dawn = 0 if self.turns_to_dawn > 10 else self.turns_to_dawn

        self.is_day_time = self.turns_to_dawn == 0


        for update in messages:
            if update == "D_DONE":
                break
            strs = update.split(" ")
            input_identifier = strs[0]

            if input_identifier == INPUT_CONSTANTS.RESEARCH_POINTS:
                team = int(strs[1])   # probably player_id
                self.players[team].research_points = int(strs[2])

            elif input_identifier == INPUT_CONSTANTS.RESOURCES:
                r_type = strs[1]
                x = int(strs[2])
                y = int(strs[3])
                amt = int(float(strs[4]))
                self.map._setResource(r_type, x, y, amt)

            elif input_identifier == INPUT_CONSTANTS.UNITS:
                unittype = int(strs[1])
                team = int(strs[2])
                unitid = strs[3]
                x = int(strs[4])
                y = int(strs[5])
                cooldown = float(strs[6])
                wood = int(strs[7])
                coal = int(strs[8])
                uranium = int(strs[9])
                unit = Unit(team, unittype, unitid, x, y, cooldown, wood, coal, uranium)
                self.players[team].units.append(unit)
                self.map.get_cell(x, y).unit = unit

            elif input_identifier == INPUT_CONSTANTS.CITY:
                team = int(strs[1])
                cityid = strs[2]
                fuel = float(strs[3])
                lightupkeep = float(strs[4])
                self.players[team].cities[cityid] = City(team, cityid, fuel, lightupkeep)

            elif input_identifier == INPUT_CONSTANTS.CITY_TILES:
                team = int(strs[1])
                cityid = strs[2]
                x = int(strs[3])
                y = int(strs[4])
                cooldown = float(strs[5])
                city = self.players[team].cities[cityid]
                citytile = city._add_city_tile(x, y, cooldown)
                self.map.get_cell(x, y).citytile = citytile
                self.players[team].city_tile_count += 1

            elif input_identifier == INPUT_CONSTANTS.ROADS:
                x = int(strs[1])
                y = int(strs[2])
                road = float(strs[3])
                self.map.get_cell(x, y).road = road

        # update matrices
        self.calculate_matrix()
        self.calculate_resource_matrix()

        # make indexes
        self.player.make_index_units_by_id()
        self.opponent.make_index_units_by_id()

    def init_zero_matrix(self):
        # [TODO] check if order of map_height and map_width is correct
        return np.zeros((self.map_height,self.map_width))

    def calculate_matrix(self):

        self.empty_tile_matrix = self.init_zero_matrix()

        self.wood_amount_matrix = self.init_zero_matrix()
        self.coal_amount_matrix = self.init_zero_matrix()
        self.uranium_amount_matrix = self.init_zero_matrix()
        self.resource_amount_matrix = self.init_zero_matrix()

        self.player_city_tile_matrix = self.init_zero_matrix()
        self.opponent_city_tile_matrix = self.init_zero_matrix()

        self.player_units_matrix = self.init_zero_matrix()
        self.opponent_units_matrix = self.init_zero_matrix()

        self.empty_tile_matrix = self.init_zero_matrix()

        for y in range(self.map_height):
            for x in range(self.map_width):
                cell = self.map.get_cell(x, y)

                is_empty = True

                if cell.unit:
                    is_empty = False
                    if cell.unit.team == self.player_id:
                        self.player_units_matrix[y,x] += 1
                    else:   # unit belongs to opponent
                        self.opponent_units_matrix[y,x] += 1

                if cell.has_resource():
                    is_empty = False
                    if cell.resource.type == RESOURCE_TYPES.WOOD:
                        self.wood_amount_matrix[y,x] += cell.resource.amount
                    if cell.resource.type == RESOURCE_TYPES.COAL:
                        self.coal_amount_matrix[y,x] += cell.resource.amount
                    if cell.resource.type == RESOURCE_TYPES.URANIUM:
                        self.uranium_amount_matrix[y,x] += cell.resource.amount
                    self.resource_amount_matrix[y,x] += cell.resource.amount

                elif cell.citytile:
                    is_empty = False
                    if cell.citytile.team == self.player_id:
                        self.player_city_tile_matrix[y,x] += 1
                    else:   # city tile belongs to opponent
                        self.opponent_city_tile_matrix[y,x] += 1

                if is_empty:
                    self.empty_tile_matrix[y,x] += 1

        self.convert_into_sets()


    def convert_into_sets(self):
        # or should we use dict?
        self.wood_amount_xy_set = set()
        self.coal_amount_xy_set = set()
        self.uranium_amount_xy_set = set()
        self.resource_amount_xy_set = set()
        self.player_city_tile_xy_set = set()
        self.opponent_city_tile_xy_set = set()
        self.player_units_xy_set = set()
        self.opponent_units_xy_set = set()
        self.empty_tile_xy_set = set()

        for set_object, matrix in [
            [self.wood_amount_xy_set,           self.wood_amount_matrix],
            [self.coal_amount_xy_set,           self.coal_amount_matrix],
            [self.uranium_amount_xy_set,        self.uranium_amount_matrix],
            [self.resource_amount_xy_set,       self.resource_amount_matrix],
            [self.player_city_tile_xy_set,      self.player_city_tile_matrix],
            [self.opponent_city_tile_xy_set,    self.opponent_city_tile_matrix],
            [self.player_units_xy_set,          self.player_units_matrix],
            [self.opponent_units_xy_set,        self.opponent_units_matrix],
            [self.empty_tile_xy_set,            self.empty_tile_matrix]]:

            for y in range(self.map.height):
                for x in range(self.map.width):
                    if matrix[y,x] > 0:
                        set_object.add((x,y))

        out_of_map = set()
        for y in [-1, self.map_height]:
            for x in range(self.map_width):
                out_of_map.add((x,y))
        for y in range(self.map_height):
            for x in [-1, self.map_width]:
                out_of_map.add((x,y))

        self.occupied_xy_set = (self.player_units_xy_set | self.opponent_units_xy_set | self.player_city_tile_xy_set | out_of_map) \
                                - self.player_city_tile_xy_set


    def convolve(self, matrix):
        new_matrix = matrix.copy()
        new_matrix[:-1,:] += matrix[1:,:]
        new_matrix[:,:-1] += matrix[:,1:]
        new_matrix[1:,:] += matrix[:-1,:]
        new_matrix[:,1:] += matrix[:,:-1]
        return new_matrix


    def calculate_resource_matrix(self):

        wood_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.WOOD.upper()]
        wood_count_rate = GAME_CONSTANTS["PARAMETERS"]["WORKER_COLLECTION_RATE"][RESOURCE_TYPES.COAL.upper()]
        # fuel - fuel amount if converted
        # count - how many remaining
        # rate - rate of extraction
        self.resource_fuel_matrix = self.wood_amount_matrix * wood_fuel_rate
        self.resource_count_matrix = (self.resource_fuel_matrix > 0) * wood_count_rate
        self.resource_rate_matrix = (self.resource_fuel_matrix > 0) * wood_fuel_rate * wood_count_rate

        if self.player.researched_coal():
            coal_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.COAL.upper()]
            coal_count_rate = GAME_CONSTANTS["PARAMETERS"]["WORKER_COLLECTION_RATE"][RESOURCE_TYPES.COAL.upper()]
            coal_fuel_matrix = self.coal_amount_matrix
            self.resource_fuel_matrix += coal_fuel_matrix * coal_fuel_rate
            self.resource_count_matrix += (coal_fuel_matrix > 0) * coal_count_rate
            self.resource_rate_matrix += (coal_fuel_matrix > 0) * coal_fuel_rate * coal_count_rate

        if self.player.researched_uranium():
            uranium_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.URANIUM.upper()]
            uranium_count_rate = GAME_CONSTANTS["PARAMETERS"]["WORKER_COLLECTION_RATE"][RESOURCE_TYPES.URANIUM.upper()]
            uranium_fuel_matrix = self.uranium_amount_matrix
            self.resource_fuel_matrix += uranium_fuel_matrix * uranium_fuel_rate
            self.resource_count_matrix += (uranium_fuel_matrix > 0) * uranium_count_rate
            self.resource_rate_matrix += (uranium_fuel_matrix > 0) * uranium_fuel_rate * uranium_count_rate

        # from the position
        self.convolved_fuel_matrix = self.convolve(self.resource_fuel_matrix)
        self.convolved_count_matrix = self.convolve(self.resource_count_matrix)
        self.convolved_rate_matrix = self.convolve(self.resource_rate_matrix)


    def repopulate_targets(self, pos_list: List[Position]):
        self.targeted_xy_set: Set = set(tuple(pos) for pos in pos_list) - self.player_city_tile_xy_set


    def calculate_dominance_matrix(self, feature_matrix, masking_factor = 0.5, exempted=(-1,-1)):
        mask = (1 - masking_factor * self.player_units_matrix)
        feature_matrix = self.convolve(feature_matrix)
        masked_matrix = mask * feature_matrix
        if exempted != (-1,-1):
            # the exempted cell is the position of the unit
            masked_matrix[exempted[0],exempted[1]] = feature_matrix[exempted[0],exempted[1]]
        return masked_matrix


    def get_nearest_empty_tile_and_distance(self, current_position: Position) -> Tuple[Position, int]:
        if tuple(current_position) not in self.resource_amount_xy_set:
            if tuple(current_position) not in self.player_city_tile_xy_set:
                return current_position, 0

        width, height = self.map_width, self.map_height

        nearest_distance = width + height
        nearest_position: Position = None

        for y in range(height):
            for x in range(width):
                if self.empty_tile_matrix[y,x] == 0:  # not empty
                    continue

                position = Position(x, y)
                distance = position - current_position
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_position = position

        return nearest_position, nearest_distance
