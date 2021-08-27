from typing import Dict, List, Tuple

import numpy as np

from .constants import Constants
from .game_map import GameMap, RESOURCE_TYPES
from .game_objects import Player, Unit, City, CityTile, Position
from .game_constants import GAME_CONSTANTS

INPUT_CONSTANTS = Constants.INPUT_CONSTANTS


class Game:
    # def _update_with_observation(self, observation: Observation):
    #     if observation["step"] == 0:
    #         self._initialize(observation["updates"])
    #         self._update(observation["updates"][2:])
    #         self.player_id = observation.player
    #     else:
    #         self._update(observation["updates"])


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

        # [TODO] Use constants here
        self.night_turns_left = (360 - self.turn)//40 * 10 + min(10, (360 - self.turn)%40)
        self.turns_to_night = (30 - self.turn)%40
        self.turns_to_dawn = (40 - self.turn%40)
        self.is_day_time = self.turns_to_dawn > 11


    def _end_turn(self):
        print("D_FINISH")


    def _reset_player_states(self):
        self.players[0].units = []
        self.players[0].cities = {}
        self.players[0].city_tile_count = 0
        self.players[1].units = []
        self.players[1].cities = {}
        self.players[1].city_tile_count = 0

        self.player = self.players[self.player_id]
        self.opponent = self.players[1 - self.player_id]


    def _update(self, messages):
        """
        update state
        """
        self.map = GameMap(self.map_width, self.map_height)
        self.turn += 1
        self._reset_player_states()

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
                self.players[team].units.append(Unit(team, unittype, unitid, x, y, cooldown, wood, coal, uranium))
                self.map.get_cell(x, y).unit = Unit(team, unittype, unitid, x, y, cooldown, wood, coal, uranium)

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

        # # update statistics [TODO] this might not be necessary
        # self.night_turns_left = (360 - self.turn)//40 * 10 + min(10, (360 - self.turn)%40)
        # self.turns_to_night = (30 - self.turn)%40
        # self.turns_to_dawn = (40 - self.turn%40)

        # update matrices
        self.calculate_matrix()
        self.calculate_resource_matrix()
        self.calculate_resource_maxpool_matrix()

        # make indexes
        self.player.make_index_units_by_id()
        self.opponent.make_index_units_by_id()


    def calculate_matrix(self):
        def init_zero_matrix():
            # [TODO] check if order of map_height and map_width is correct
            return [[0 for _ in range(self.map_height)] for _ in range(self.map_width)]

        self.empty_tile_matrix = init_zero_matrix()

        self.wood_amount_matrix = init_zero_matrix()
        self.coal_amount_matrix = init_zero_matrix()
        self.uranium_amount_matrix = init_zero_matrix()

        self.player_city_tile_matrix = init_zero_matrix()
        self.opponent_city_tile_matrix = init_zero_matrix()

        self.player_units_matrix = init_zero_matrix()
        self.opponent_units_matrix = init_zero_matrix()

        self.empty_tile_matrix = init_zero_matrix()

        for y in range(self.map_width):
            for x in range(self.map_height):
                cell = self.map.get_cell(x, y)

                if cell.has_resource():
                    if cell.resource.type == RESOURCE_TYPES.WOOD:
                        self.wood_amount_matrix[y][x] += cell.resource.amount
                    if cell.resource.type == RESOURCE_TYPES.COAL:
                        self.coal_amount_matrix[y][x] += cell.resource.amount
                    if cell.resource.type == RESOURCE_TYPES.URANIUM:
                        self.uranium_amount_matrix[y][x] += cell.resource.amount

                elif cell.citytile:
                    if cell.citytile.team == self.player_id:
                        self.player_city_tile_matrix[y][x] += 1
                    else:   # city tile belongs to opponent
                        self.opponent_city_tile_matrix[y][x] += 1

                elif cell.unit:
                    if cell.unit.team == self.player_id:
                        self.player_units_matrix[y][x] += 1
                    else:   # unit belongs to opponent
                        self.opponent_units_matrix[y][x] += 1

                else:
                    self.empty_tile_matrix[y][x] += 1

        self.convert_into_sets()


    def convert_into_sets(self):
        # or should we use dict?
        self.empty_tile_xy_set = set()
        self.wood_amount_xy_set = set()
        self.coal_amount_xy_set = set()
        self.uranium_amount_xy_set = set()
        self.player_city_tile_xy_set = set()
        self.opponent_city_tile_xy_set = set()
        self.player_units_xy_set = set()
        self.opponent_units_xy_set = set()
        self.empty_tile_xy_set = set()

        for set_object, matrix in [
            [self.empty_tile_xy_set,            self.empty_tile_matrix],
            [self.wood_amount_xy_set,           self.wood_amount_matrix],
            [self.coal_amount_xy_set,           self.coal_amount_matrix],
            [self.uranium_amount_xy_set,        self.uranium_amount_matrix],
            [self.player_city_tile_xy_set,      self.player_city_tile_matrix],
            [self.opponent_city_tile_xy_set,    self.opponent_city_tile_matrix],
            [self.player_units_xy_set,          self.player_units_matrix],
            [self.opponent_units_xy_set,        self.opponent_units_matrix],
            [self.empty_tile_xy_set,            self.empty_tile_matrix]]:

            for y in range(self.map.width):
                for x in range(self.map.height):
                    if matrix[y][x] > 0:
                        set_object.add((x,y))

        self.map.set_occupied_xy = (self.player_units_xy_set | self.opponent_units_xy_set | self.player_city_tile_xy_set) \
                                   - self.player_city_tile_xy_set


    def calculate_resource_matrix(self):

        wood_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.WOOD.upper()]
        fuel_matrix = np.array(self.wood_amount_matrix) * wood_fuel_rate
        rate_matrix = (fuel_matrix > 0) * wood_fuel_rate

        if self.player.researched_coal():
            coal_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.COAL.upper()]
            coal_fuel_matrix = np.array(self.coal_amount_matrix)
            fuel_matrix += coal_fuel_matrix * coal_fuel_rate
            rate_matrix += (coal_fuel_matrix > 0) * coal_fuel_rate

        if self.player.researched_uranium():
            uranium_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.URANIUM.upper()]
            uranium_fuel_matrix = np.array(self.uranium_amount_matrix)
            fuel_matrix += uranium_fuel_matrix * uranium_fuel_rate
            rate_matrix += (uranium_fuel_matrix > 0) * uranium_fuel_rate

        def convolve(matrix):
            new_matrix = matrix.copy()
            new_matrix[:-1,:] += matrix[1:,:]
            new_matrix[:,:-1] += matrix[:,1:]
            new_matrix[1:,:] += matrix[:-1,:]
            new_matrix[:,1:] += matrix[:,:-1]
            return new_matrix.tolist()

        self.resource_fuel_matrix = fuel_matrix
        self.resource_rate_matrix = rate_matrix
        self.convolved_fuel_matrix = convolve(fuel_matrix)
        self.convolved_rate_matrix = convolve(rate_matrix)


    def calculate_dominance_matrix(self):
        # [TODO]
        return


    def calculate_resource_maxpool_matrix(self) -> List[List[int]]:
        width, height = self.map_width, self.map_height
        maxpool_scores_matrix = [[0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                for dx,dy in [(1,0),(0,1),(-1,0),(0,-1)]:
                    xx,yy = x+dx,y+dy
                    if not (0 <= xx < width and 0 <= yy < height):
                        continue
                    if self.convolved_fuel_matrix[yy][xx] + dx * 0.2 + dy * 0.1 > self.convolved_fuel_matrix[y][x]:
                        break
                else:
                    maxpool_scores_matrix[y][x] = self.convolved_fuel_matrix[y][x]

        return maxpool_scores_matrix


    def get_nearest_empty_tile_and_distance(self, current_position: Position) -> Tuple[Position, int]:
        if tuple(current_position) in self.player_units_xy_set:
            return current_position, 0

        width, height = self.map_width, self.map_height

        nearest_distance = width + height
        nearest_position: Position = None

        for y in range(height):
            for x in range(width):
                if self.empty_tile_matrix[y][x] == 0:  # not empty
                    continue

                # if (y+x)%3 == 0:  # enforce checkerboard
                #     continue

                position = Position(x, y)
                distance = position - current_position
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_position = position

        return nearest_position, nearest_distance
