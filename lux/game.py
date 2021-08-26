from typing import Dict

from .constants import Constants
from .game_map import GameMap, RESOURCE_TYPES
from .game_objects import Player, Unit, City, CityTile, Position
from .game_constants import GAME_CONSTANTS

INPUT_CONSTANTS = Constants.INPUT_CONSTANTS

from typing import List, Tuple

class Observation(Dict[str, any]):
    def __init__(self, player=0) -> None:
        self.player = player
        # self.updates = []
        # self.step = 0


class Game:
    def _update_with_observation(self, observation: Observation):
        if observation["step"] == 0:
            self._initialize(observation["updates"])
            self._update(observation["updates"][2:])
            self.player_id = observation.player
        else:
            self._update(observation["updates"])


    def _initialize(self, messages):
        """
        initialize state
        """
        self.player_id = int(messages[0])
        self.turn = -1
        # get some other necessary initial input
        mapInfo = messages[1].split(" ")
        self.map_width = int(mapInfo[0])
        self.map_height = int(mapInfo[1])
        self.map = GameMap(self.map_width, self.map_height)
        self.players = [Player(0), Player(1)]

        self.night_turns_left = (360 - self.turn)//40 * 10 + min(10, (360 - self.turn)%40)
        self.turns_to_night = (30 - self.turn)%40
        self.turns_to_dawn = (40 - self.turn%40)

        self.resource_scores_matrix = None
        self.resource_rate_matrix = None
        self.maxpool_scores_matrix = None
        self.city_tile_matrix = None
        self.empty_tile_matrix = None


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
                team = int(strs[1])
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

        # update statistics
        self.night_turns_left = (360 - self.turn)//40 * 10 + min(10, (360 - self.turn)%40)
        self.turns_to_night = (30 - self.turn)%40
        self.turns_to_dawn = (40 - self.turn%40)
        
        # update matrices
        self.calculate_resource_scores_and_rates_matrix()
        self.maxpool_scores_matrix = self.calculate_resource_maxpool_matrix()
        self.city_tile_matrix = self.get_city_tile_matrix()
        self.empty_tile_matrix = self.get_empty_tile_matrix()

        # make index
        self.player.make_index_units_by_id()
        self.opponent.make_index_units_by_id()


    def calculate_resource_scores_and_rates_matrix(self):
        width, height = self.map_width, self.map_height
        player = self.player
        resource_scores_matrix = [[0 for _ in range(width)] for _ in range(height)]
        resource_rates_matrix = [[0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                resource_score_cell = 0
                resource_rate_cell = 0
                for dx,dy in [(1,0),(0,1),(-1,0),(0,-1),(0,0)]:
                    xx,yy = x+dx,y+dy
                    if 0 <= xx < width and 0 <= yy < height:
                        cell = self.map.get_cell(xx, yy)
                        if not cell.has_resource():
                            continue
                        if not player.researched_coal() and cell.resource.type == RESOURCE_TYPES.COAL:
                            continue
                        if not player.researched_uranium() and cell.resource.type == RESOURCE_TYPES.URANIUM:
                            continue
                        fuel = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][str(cell.resource.type).upper()]
                        mining_rate = GAME_CONSTANTS["PARAMETERS"]["WORKER_COLLECTION_RATE"][str(cell.resource.type).upper()]
                        resource_score_cell += fuel * cell.resource.amount
                        resource_rate_cell += fuel * mining_rate
                resource_scores_matrix[y][x] = resource_score_cell
                resource_rates_matrix[y][x] = resource_rate_cell
        
        self.resource_scores_matrix = resource_scores_matrix
        self.resource_rates_matrix = resource_rates_matrix


    def calculate_resource_maxpool_matrix(self) -> List[List[int]]:
        width, height = self.map_width, self.map_height
        maxpool_scores_matrix = [[0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                for dx,dy in [(1,0),(0,1),(-1,0),(0,-1)]:
                    xx,yy = x+dx,y+dy
                    if not (0 <= xx < width and 0 <= yy < height):
                        continue
                    if self.resource_scores_matrix[yy][xx] + dx * 0.2 + dy * 0.1 > self.resource_scores_matrix[y][x]:
                        break
                else:
                    maxpool_scores_matrix[y][x] = self.resource_scores_matrix[y][x]

        return maxpool_scores_matrix


    def get_city_tile_matrix(self) -> List[List[int]]:
        width, height = self.map_width, self.map_height
        player = self.player
        city_tile_matrix = [[0 for _ in range(width)] for _ in range(height)]

        for city_id, city in player.cities.items():
            for city_tile in city.citytiles:
                city_tile_matrix[city_tile.pos.y][city_tile.pos.x] += 1
        
        return city_tile_matrix


    def get_empty_tile_matrix(self) -> List[List[int]]:
        width, height = self.map_width, self.map_height
        empty_tile_matrix = [[0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                cell = self.map.get_cell(x, y)
                if cell.has_resource():
                    continue
                if cell.citytile:
                    continue
                empty_tile_matrix[y][x] = 1

        return empty_tile_matrix


    def get_nearest_empty_tile_and_distance(self, current_position: Position) -> Tuple[Position, int]:
        width, height = self.map_width, self.map_height

        nearest_distance = width + height
        nearest_position = None

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


