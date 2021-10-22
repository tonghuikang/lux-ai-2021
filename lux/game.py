import heapq
from collections import defaultdict, deque
from typing import DefaultDict, Dict, List, Tuple, Set
from datetime import datetime
import builtins as __builtin__

import numpy as np

from .constants import Constants
from .game_map import GameMap, RESOURCE_TYPES
from .game_objects import Player, Unit, City
from .game_position import Position
from .game_constants import GAME_CONSTANTS

INPUT_CONSTANTS = Constants.INPUT_CONSTANTS


class Mission:
    def __init__(self, unit_id: str, target_position: Position, target_action: str = "", details: str = ""):
        self.target_position: Position = target_position
        self.target_action: str = target_action
        self.unit_id: str = unit_id
        self.delays: int = 0
        self.details: str = details  # block deletion of mission if no resource
        # [TODO] some expiry date for each mission

    def __str__(self):
        return " ".join([str(self.target_position), self.target_action])


class Missions(defaultdict):
    def __init__(self):
        self: DefaultDict[str, Mission] = defaultdict(Mission)

    def add(self, mission: Mission):
        self[mission.unit_id] = mission

    def __str__(self):
        return " ".join([unit_id + " " + str(x) for unit_id,x in self.items()])

    def get_targets(self):
        return [mission.target_position for unit_id, mission in self.items()]

    def get_target_of_unit(self, unit_id):
        return {unit_id: mission.target_position for unit_id, mission in self.items()}[unit_id]

    def get_targets_and_actions(self):
        return [(mission.target_position, mission.target_action) for unit_id, mission in self.items()]


class DisjointSet:
    def __init__(self):
        self.parent = {}
        self.sizes = defaultdict(int)
        self.points = defaultdict(int)  # 1 point for wood, 3 point for coal, 5 point for uranium
        self.tiles = defaultdict(int)  # 1 point for all resource
        self.citytiles = defaultdict(int)  # 1 point for citytile next to cluster
        self.num_sets = 0

    def find(self, a, point=0, tile=0, citytile=0):
        if a not in self.parent:
            self.parent[a] = a
            self.sizes[a] += 1
            self.points[a] += point
            self.tiles[a] += tile
            self.citytiles[a] += citytile
            self.num_sets += 1
        acopy = a
        while a != self.parent[a]:
            a = self.parent[a]
        while acopy != a:
            self.parent[acopy], acopy = a, self.parent[acopy]
        return a

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            # if self.sizes[a] < self.sizes[b]:
            #     a, b = b, a

            self.num_sets -= 1
            self.parent[b] = a
            self.sizes[a] += self.sizes[b]
            self.points[a] += self.points[b]
            self.tiles[a] += self.tiles[b]
            self.citytiles[a] += self.citytiles[b]

    def get_size(self, a):
        return self.sizes[self.find(a)]

    def get_point(self, a):
        return self.points[self.find(a)]

    def get_tiles(self, a):
        return self.tiles[self.find(a)]

    def get_citytiles(self, a):
        return self.citytiles[self.find(a)]

    def get_groups(self):
        groups = defaultdict(list)
        for element in self.parent:
            leader = self.find(element)
            if leader:
                groups[leader].append(element)
        return groups

    def get_groups_sorted_by_citytile_size(self):
        groups = defaultdict(list)
        for element in self.parent:
            leader = self.find(element)
            if leader:
                groups[leader].append(element)
        leaders = list(groups.keys())
        leaders.sort(key=lambda leader: (self.get_citytiles(leader), self.get_tiles(leader)), reverse=True)
        return [groups[leader] for leader in leaders if self.get_point(leader) > 0]

    def get_group_count(self):
        return sum(self.points[leader] > 1 for leader in self.get_groups().keys())


class Game:

    # counted from the time after the objects are saved to disk
    compute_start_time = -1

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

        self.x_iteration_order = list(range(self.map_width))
        self.y_iteration_order = list(range(self.map_height))
        self.dirs: List = [
            Constants.DIRECTIONS.NORTH,
            Constants.DIRECTIONS.EAST,
            Constants.DIRECTIONS.SOUTH,
            Constants.DIRECTIONS.WEST,
            Constants.DIRECTIONS.CENTER
        ]
        self.dirs_dxdy: List = [(0,-1), (1,0), (0,1), (-1,0), (0,0)]
        self.units_expected_to_act: Set[Tuple] = set()


    def fix_iteration_order(self):
        '''
        Fix iteration order at initisation to allow moves to be symmetric
        '''
        assert len(self.player.cities) == 1
        assert len(self.opponent.cities) == 1
        px,py = tuple(list(self.player.cities.values())[0].citytiles[0].pos)
        ox,oy = tuple(list(self.opponent.cities.values())[0].citytiles[0].pos)

        flipping = False
        self.y_order_coefficient = 1
        self.x_order_coefficient = 1

        if px == ox:
            if py < oy:
                flipping = True
                self.y_iteration_order = self.y_iteration_order[::-1]
                self.y_order_coefficient = -1
                idx1, idx2 = 0,2
        elif py == oy:
            if px < ox:
                flipping = True
                self.x_iteration_order = self.x_iteration_order[::-1]
                self.x_order_coefficient = -1
                idx1, idx2 = 1,3
        else:
            assert False

        if flipping:
            self.dirs[idx1], self.dirs[idx2] = self.dirs[idx2], self.dirs[idx1]
            self.dirs_dxdy[idx1], self.dirs_dxdy[idx2] = self.dirs_dxdy[idx2], self.dirs_dxdy[idx1]


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
                self.players[team].cities[cityid] = City(team, cityid, fuel, lightupkeep, self.night_turns_left)

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

        # create indexes to refer to unit by id
        self.player.make_index_units_by_id()
        self.opponent.make_index_units_by_id()

        if self.turn > 0:
            for city in self.player.cities.values():
                city.citytiles.sort(key=lambda city_tile:(
                    city_tile.pos.x * self.x_order_coefficient,
                    city_tile.pos.y * self.y_order_coefficient))

            for city in self.opponent.cities.values():
                city.citytiles.sort(key=lambda city_tile:(
                    city_tile.pos.x * self.x_order_coefficient,
                    city_tile.pos.y * self.y_order_coefficient))


    def calculate_features(self, missions: Missions):

        # load constants into object
        self.wood_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.WOOD.upper()]
        self.wood_collection_rate = GAME_CONSTANTS["PARAMETERS"]["WORKER_COLLECTION_RATE"][RESOURCE_TYPES.WOOD.upper()]
        self.coal_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.COAL.upper()]
        self.coal_collection_rate = GAME_CONSTANTS["PARAMETERS"]["WORKER_COLLECTION_RATE"][RESOURCE_TYPES.COAL.upper()]
        self.uranium_fuel_rate = GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"][RESOURCE_TYPES.URANIUM.upper()]
        self.uranium_collection_rate = GAME_CONSTANTS["PARAMETERS"]["WORKER_COLLECTION_RATE"][RESOURCE_TYPES.URANIUM.upper()]

        # update matrices
        self.calculate_matrix()
        self.calculate_resource_matrix()
        self.calculate_resource_groups()
        self.calculate_distance_matrix()

        self.repopulate_targets(missions)

        self.citytiles_with_new_units_xy_set: Set = set()
        self.heuristics_from_positions: Dict = dict()

        self.units_did_not_act: Set = set(unit_id for unit_id in self.units_expected_to_act)
        for unit in self.player.units:
            if unit.can_act():
                self.units_expected_to_act.add(unit.id)
        self.units_did_not_act = self.units_did_not_act & self.units_expected_to_act

        update_mission_delay(self, missions)


    def init_matrix(self, default_value=0):
        # [TODO] check if order of map_height and map_width is correct
        return np.full((self.map_height,self.map_width), default_value)


    def calculate_matrix(self):

        # amount of resources left on the tile
        self.wood_amount_matrix = self.init_matrix()
        self.coal_amount_matrix = self.init_matrix()
        self.uranium_amount_matrix = self.init_matrix()
        self.all_resource_amount_matrix = self.init_matrix()

        self.player_city_tile_matrix = self.init_matrix()
        self.opponent_city_tile_matrix = self.init_matrix()

        self.player_units_matrix = self.init_matrix()
        self.opponent_units_matrix = self.init_matrix()

        # if there is nothing on tile
        self.empty_tile_matrix = self.init_matrix()

        # if you can build on tile (a unit may be on the tile)
        self.buildable_tile_matrix = self.init_matrix()

        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                cell = self.map.get_cell(x, y)

                is_empty = True
                is_buildable = True

                if cell.unit:
                    is_empty = False
                    # unit counting method implemented later
                    # cell.unit only contain one unit even though multiple units can stay in citytile

                if cell.has_resource():
                    is_empty = False
                    is_buildable = False
                    if cell.resource.type == RESOURCE_TYPES.WOOD:
                        self.wood_amount_matrix[y,x] += cell.resource.amount
                    if cell.resource.type == RESOURCE_TYPES.COAL:
                        self.coal_amount_matrix[y,x] += cell.resource.amount
                    if cell.resource.type == RESOURCE_TYPES.URANIUM:
                        self.uranium_amount_matrix[y,x] += cell.resource.amount
                    self.all_resource_amount_matrix[y,x] += cell.resource.amount

                elif cell.citytile:
                    is_empty = False
                    is_buildable = False
                    if cell.citytile.team == self.player_id:
                        self.player_city_tile_matrix[y,x] += 1
                    else:   # city tile belongs to opponent
                        self.opponent_city_tile_matrix[y,x] += 1

                if is_empty:
                    self.empty_tile_matrix[y,x] += 1

                if is_buildable:
                    self.buildable_tile_matrix[y,x] += 1

        for unit in self.player.units:
            self.player_units_matrix[unit.pos.y,unit.pos.x] += 1

        for unit in self.opponent.units:
            self.opponent_units_matrix[unit.pos.y,unit.pos.x] += 1

        # binary matrices
        self.wood_exist_matrix = (self.wood_amount_matrix > 0).astype(int)
        self.coal_exist_matrix = (self.coal_amount_matrix > 0).astype(int)
        self.uranium_exist_matrix = (self.uranium_amount_matrix > 0).astype(int)
        self.all_resource_exist_matrix = (self.all_resource_amount_matrix > 0).astype(int)

        self.convolved_wood_exist_matrix = self.convolve(self.wood_exist_matrix)
        self.convolved_coal_exist_matrix = self.convolve(self.coal_exist_matrix)
        self.convolved_uranium_exist_matrix = self.convolve(self.uranium_exist_matrix)

        self.resource_collection_rate = self.convolved_wood_exist_matrix * 20 + self.convolved_coal_exist_matrix * 5 + self.convolved_uranium_exist_matrix * 2

        # positive if on empty cell and beside the resource
        self.wood_side_matrix = self.convolve(self.wood_exist_matrix) * self.empty_tile_matrix
        self.coal_side_matrix = self.convolve(self.coal_exist_matrix) * self.empty_tile_matrix
        self.uranium_side_matrix = self.convolve(self.uranium_exist_matrix) * self.empty_tile_matrix

        self.convert_into_sets()

        # calculate aggregate features
        self.map_resource_count = np.sum(self.wood_amount_matrix + self.coal_amount_matrix + self.uranium_amount_matrix)


    def get_floodfill(self, set_object):
        # return the largest connected graph ignoring blockers
        ds = DisjointSet()
        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                if (x,y) in set_object:
                    continue
                for dy,dx in self.dirs_dxdy[:-1]:
                    xx, yy = x+dx, y+dy
                    if (xx,yy) in self.xy_out_of_map:
                        continue
                    if (xx,yy) in set_object:
                        continue
                    ds.union((x,y), (xx,yy))

        floodfills = sorted(ds.get_groups().values(), key=len, reverse=True)

        # for smaller maps, resources may divide the map into two
        all_floodfill = set()
        for floodfill in floodfills:
            all_floodfill.update(floodfill)
            if len(all_floodfill) > self.map_width * self.map_height*0.7:
                return all_floodfill
        return all_floodfill


    def populate_set(self, matrix, set_object):
        # modifies the set_object in place and add nonzero items in the matrix
        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                if matrix[y,x] > 0:
                    set_object.add((x,y))


    def convert_into_sets(self):
        self.wood_exist_xy_set = set()
        self.coal_exist_xy_set = set()
        self.uranium_exist_xy_set = set()
        self.player_city_tile_xy_set = set()
        self.opponent_city_tile_xy_set = set()
        self.player_units_xy_set = set()
        self.opponent_units_xy_set = set()
        self.empty_tile_xy_set = set()
        self.buildable_tile_xy_set = set()

        for set_object, matrix in [
            [self.wood_exist_xy_set,            self.wood_exist_matrix],
            [self.coal_exist_xy_set,            self.coal_exist_matrix],
            [self.uranium_exist_xy_set,         self.uranium_exist_matrix],
            [self.player_city_tile_xy_set,      self.player_city_tile_matrix],
            [self.opponent_city_tile_xy_set,    self.opponent_city_tile_matrix],
            [self.player_units_xy_set,          self.player_units_matrix],
            [self.opponent_units_xy_set,        self.opponent_units_matrix],
            [self.empty_tile_xy_set,            self.empty_tile_matrix],
            [self.buildable_tile_xy_set,        self.buildable_tile_matrix]]:

            self.populate_set(matrix, set_object)

        self.xy_out_of_map: Set = set()
        for y in [-1, self.map_height]:
            for x in range(self.map_width):
                self.xy_out_of_map.add((x,y))
        for y in range(self.map_height):
            for x in [-1, self.map_width]:
                self.xy_out_of_map.add((x,y))

        # used for distance calculation
        # out of map - yes
        # occupied by enemy units or city - yes
        # occupied by self unit not in city - yes
        # occupied by self city - no (even if there are units)
        self.occupied_xy_set = (self.player_units_xy_set | self.opponent_units_xy_set | \
                                self.opponent_city_tile_xy_set | self.xy_out_of_map) \
                                - self.player_city_tile_xy_set

        self.floodfill_by_player_city_set = self.get_floodfill(self.player_city_tile_xy_set)
        self.floodfill_by_opponent_city_set = self.get_floodfill(self.opponent_city_tile_xy_set)
        self.floodfill_by_either_city_set = self.get_floodfill(self.player_city_tile_xy_set | self.opponent_city_tile_xy_set)

        self.floodfill_by_empty_tile_set = self.get_floodfill(
            self.player_city_tile_xy_set | self.opponent_city_tile_xy_set | self.wood_exist_xy_set | self.coal_exist_xy_set | self.uranium_exist_xy_set)


    def calculate_distance_matrix(self, blockade_multiplier_value=100):
        self.distance_from_edge = self.init_matrix(self.map_height + self.map_width)
        for y in range(self.map_height):
            y_distance_from_edge = min(y, self.map_height-y-1)
            for x in range(self.map_width):
                x_distance_from_edge = min(x, self.map_height-x-1)
                self.distance_from_edge[y,x] = y_distance_from_edge + x_distance_from_edge

        def calculate_distance_from_set(relevant_set):
            visited = set()
            matrix = self.init_matrix(default_value=99)
            for y in self.y_iteration_order:
                for x in self.x_iteration_order:
                    if (x,y) in relevant_set:
                        visited.add((x,y))
                        matrix[y,x] = 0

            queue = deque(list(visited))
            while queue:
                x,y = queue.popleft()
                for dx,dy in self.dirs_dxdy[:-1]:
                    xx, yy = x+dx, y+dy
                    if (xx,yy) in visited:
                        continue
                    if 0 <= xx < self.map_width and 0 <= yy < self.map_height:
                        matrix[yy,xx] = matrix[y,x] + 1
                        queue.append((xx,yy))
                        visited.add((xx,yy))
            return matrix


        def get_median(arr):
            arr = sorted(arr)
            midpoint = len(arr)//2
            return (arr[midpoint] + arr[~midpoint]) / 2

        def calculate_distance_from_median(set_object):
            # https://leetcode.com/problems/best-position-for-a-service-centre/discuss/733153/
            if not set_object:
                return self.init_matrix(default_value=0), Position(0,0)

            mx = get_median([x for x,y in set_object])
            my = get_median([y for x,y in set_object])

            matrix = self.init_matrix(default_value=0)
            for y in self.y_iteration_order:
                for x in self.x_iteration_order:
                    matrix[y][x] = abs(x-mx) + abs(y-my)

            return matrix, Position(int(mx), int(my))


        def get_norm(p1, p2):
            return (abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]))

        def calculate_distance_from_mean(set_object):
            # https://leetcode.com/problems/best-position-for-a-service-centre/discuss/733153/
            if not set_object:
                return self.init_matrix(default_value=0), Position(0,0)

            mx = sum(p[0] for p in set_object)/len(set_object)
            my = sum(p[1] for p in set_object)/len(set_object)

            matrix = self.init_matrix(default_value=0)
            for y in self.y_iteration_order:
                for x in self.x_iteration_order:
                    matrix[y][x] = get_norm((x,y), (mx,my))

            return matrix, Position(int(mx), int(my))

        # calculate distance from resource (with projected research requirements)
        self.distance_from_collectable_resource = calculate_distance_from_set(self.collectable_tiles_xy_set)

        # calculate distance from citytiles or units
        self.distance_from_player_assets = calculate_distance_from_set(self.player_units_xy_set | self.player_city_tile_xy_set)
        self.distance_from_opponent_assets = calculate_distance_from_set(self.opponent_units_xy_set | self.opponent_city_tile_xy_set)
        self.distance_from_player_units = calculate_distance_from_set(self.player_units_xy_set)
        self.distance_from_opponent_units = calculate_distance_from_set(self.opponent_units_xy_set)
        self.distance_from_player_citytiles = calculate_distance_from_set(self.player_city_tile_xy_set)
        self.distance_from_opponent_citytiles = calculate_distance_from_set(self.opponent_city_tile_xy_set)

        self.distance_from_buildable_tile = calculate_distance_from_set(self.buildable_tile_xy_set)
        self.distance_from_empty_tile = calculate_distance_from_set(self.empty_tile_xy_set)

        self.distance_from_floodfill_by_player_city = calculate_distance_from_set(self.floodfill_by_player_city_set)
        self.distance_from_floodfill_by_opponent_city = calculate_distance_from_set(self.floodfill_by_opponent_city_set)
        self.distance_from_floodfill_by_either_city = calculate_distance_from_set(self.floodfill_by_either_city_set)
        self.distance_from_floodfill_by_empty_tile = calculate_distance_from_set(self.floodfill_by_empty_tile_set)
        if self.turn <= 20:
            self.distance_from_floodfill_by_empty_tile = calculate_distance_from_set(self.buildable_tile_xy_set)

        self.distance_from_resource_mean, self.resource_mean = calculate_distance_from_mean(self.collectable_tiles_xy_set)
        self.distance_from_resource_median, self.resource_median = calculate_distance_from_median(self.collectable_tiles_xy_set)
        self.distance_from_player_unit_median, self.player_unit_median = calculate_distance_from_mean(self.player_units_xy_set)

        # some features for blocking logic
        self.opponent_unit_adjacent_xy_set: Set = set()
        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                if self.distance_from_opponent_units[y,x] == 1:
                    self.opponent_unit_adjacent_xy_set.add((x,y),)
        self.opponent_unit_adjacent_and_buildable_xy_set: Set = self.opponent_unit_adjacent_xy_set & self.buildable_tile_xy_set
        self.opponent_unit_adjacent_and_player_city_xy_set: Set = self.opponent_unit_adjacent_xy_set & self.player_city_tile_xy_set

        # calculating distances from every unit positions and its adjacent positions
        # avoid blocked places as much as possible
        self.positions_to_calculate_distances_from = set()

        for unit in self.player.units:
            x,y = tuple(unit.pos)
            self.positions_to_calculate_distances_from.add((x,y),)
            if unit.can_act():
                self.positions_to_calculate_distances_from.add((x+1,y),)
                self.positions_to_calculate_distances_from.add((x-1,y),)
                self.positions_to_calculate_distances_from.add((x,y+1),)
                self.positions_to_calculate_distances_from.add((x,y-1),)

        self.distance_matrix = np.full((self.map_height,self.map_width,self.map_height,self.map_width), 1001)

        for sy in range(self.map_height):
            for sx in range(self.map_width):
                if (sx,sy) not in self.positions_to_calculate_distances_from:
                    continue
                blockade_multiplier_value_for_syx = blockade_multiplier_value

                start_pos = (sx,sy)
                xy_processed = set()

                d4 = self.dirs_dxdy[:-1]
                heap = [(0, start_pos),]
                while heap:
                    curdist, (x,y) = heapq.heappop(heap)
                    if (x,y) in xy_processed:
                        continue
                    xy_processed.add((x,y),)
                    self.distance_matrix[sy,sx,y,x] = curdist

                    for dx,dy in d4:
                        xx,yy = x+dx,y+dy
                        if not (0 <= xx < self.map_width and 0 <= yy < self.map_height):
                            continue
                        if (xx,yy) in xy_processed:
                            continue

                        edge_length = 1
                        if (xx,yy) in self.occupied_xy_set:
                            edge_length = blockade_multiplier_value_for_syx
                        if (xx,yy) in self.opponent_city_tile_xy_set:
                            edge_length = blockade_multiplier_value_for_syx * 50

                        heapq.heappush(heap, (curdist + edge_length, (xx,yy)))


    def retrieve_distance(self, sx, sy, ex, ey):
        return self.distance_matrix[sy,sx,ey,ex]


    def convolve(self, matrix):
        # each worker gets resources from (up to) five tiles
        new_matrix = matrix.copy()
        new_matrix[:-1,:] += matrix[1:,:]
        new_matrix[:,:-1] += matrix[:,1:]
        new_matrix[1:,:] += matrix[:-1,:]
        new_matrix[:,1:] += matrix[:,:-1]
        return new_matrix


    def calculate_resource_matrix(self):
        # calculate value of the resource considering the reasearch level
        self.collectable_tiles_matrix = self.wood_exist_matrix

        if self.player.researched_coal_projected():
            self.collectable_tiles_matrix += self.coal_exist_matrix

        if self.player.researched_uranium_projected():
            self.collectable_tiles_matrix += self.uranium_exist_matrix

        # adjacent cells collect from the cell as well
        self.convolved_collectable_tiles_matrix = self.convolve(self.collectable_tiles_matrix)

        self.collectable_tiles_xy_set = set()  # exclude adjacent
        self.populate_set(self.collectable_tiles_matrix, self.collectable_tiles_xy_set)
        self.convolved_collectable_tiles_xy_set = set()  # include adjacent
        self.populate_set(self.convolved_collectable_tiles_matrix, self.convolved_collectable_tiles_xy_set)

        for unit in self.opponent.units:
            # if the opponent can move
            if unit.can_act():
                # if the opponent is not collecting resources
                if tuple(unit.pos) not in self.convolved_collectable_tiles_xy_set:
                    # if the opponent is not in the city
                    if tuple(unit.pos) not in self.opponent_city_tile_xy_set:
                        # expect opponent unit to move and not occupy the space
                        self.occupied_xy_set.discard(tuple(unit.pos))

        self.matrix_player_cities_nights_of_fuel_required_for_game = self.init_matrix()
        self.matrix_player_cities_nights_of_fuel_required_for_night = self.init_matrix()
        for city in self.player.cities.values():
            for citytile in city.citytiles:
                self.matrix_player_cities_nights_of_fuel_required_for_game[citytile.pos.y, citytile.pos.x] = city.fuel_needed_for_game
                self.matrix_player_cities_nights_of_fuel_required_for_night[citytile.pos.y, citytile.pos.x] = city.fuel_needed_for_night


    def calculate_resource_groups(self):
        # compute join the resource cluster and calculate the amount of resource
        # clusters that are connected by a diagonal are considered to be a different resource
        # the cluster with more sources own more sides

        # index individual resource tiles
        self.xy_to_resource_group_id: DisjointSet = DisjointSet()
        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                if (x,y) in self.collectable_tiles_xy_set:
                    if (x,y) in self.wood_exist_xy_set:
                        self.xy_to_resource_group_id.find((x,y), point=1, tile=1)
                    if (x,y) in self.coal_exist_xy_set:
                        self.xy_to_resource_group_id.find((x,y), point=3, tile=1)
                    if (x,y) in self.uranium_exist_xy_set:
                        self.xy_to_resource_group_id.find((x,y), point=5, tile=1)
                if (x,y) in self.convolved_collectable_tiles_xy_set:
                    if (x,y) in self.player_city_tile_xy_set:
                        self.xy_to_resource_group_id.find((x,y), citytile=1)

        # merge adjacent resource tiles
        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                if (x,y) in self.collectable_tiles_xy_set:
                    # if self.xy_to_resource_group_id.get_tiles((x,y)) > self.map_height/2:
                    #     continue
                    for dy,dx in self.dirs_dxdy[:-1]:
                        xx, yy = x+dx, y+dy
                        # if self.xy_to_resource_group_id.get_tiles((xx,yy)) > self.map_height/2:
                        #     continue
                        if 0 <= yy < self.map_height and 0 <= xx < self.map_width:
                            if (xx,yy) in self.collectable_tiles_xy_set:
                                self.xy_to_resource_group_id.union((x,y), (xx,yy))

        # consider resources two steps away as part of the cluster, if cluster size is not exceeded
        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                if (x,y) in self.collectable_tiles_xy_set:
                    for dy1,dx1 in self.dirs_dxdy[:-1]:
                        for dy2,dx2 in self.dirs_dxdy[:-1]:
                            xx, yy = x+dx1+dx2, y+dy1+dy2
                            if 0 <= yy < self.map_height and 0 <= xx < self.map_width:
                                if (xx,yy) in self.collectable_tiles_xy_set:
                                    if self.xy_to_resource_group_id.get_tiles((xx,yy)) > 1:
                                        continue
                                    self.xy_to_resource_group_id.union((x,y), (xx,yy))

        # absorb adjacent citytiles
        for group in self.xy_to_resource_group_id.get_groups_sorted_by_citytile_size():
            # might break symmetry
            for x,y in group:
                if (x,y) in self.collectable_tiles_xy_set:
                    for dy,dx in self.dirs_dxdy[:-1]:
                        xx, yy = x+dx, y+dy
                        if 0 <= yy < self.map_height and 0 <= xx < self.map_width:
                            if (xx,yy) not in self.player_city_tile_xy_set:
                                if self.xy_to_resource_group_id.find((xx,yy)) == (xx,yy):
                                    self.xy_to_resource_group_id.union((x,y), (xx,yy))

        # absorb adjacent buildable tiles
        for group in self.xy_to_resource_group_id.get_groups_sorted_by_citytile_size():
            # might break symmetry
            for x,y in group:
                if (x,y) in self.collectable_tiles_xy_set:
                    for dy,dx in self.dirs_dxdy[:-1]:
                        xx, yy = x+dx, y+dy
                        if 0 <= yy < self.map_height and 0 <= xx < self.map_width:
                            if (xx,yy) not in self.collectable_tiles_xy_set:
                                if self.xy_to_resource_group_id.find((xx,yy)) == (xx,yy):
                                    self.xy_to_resource_group_id.union((x,y), (xx,yy))


    def repopulate_targets(self, missions: Missions):
        # with missions, populate the following objects for use
        # probably these attributes belong to missions, but left it here to avoid circular imports
        pos_list = missions.get_targets()
        self.targeted_leaders: Set = set(self.xy_to_resource_group_id.find(tuple(pos)) for pos in pos_list)
        self.targeted_cluster_count = sum(self.xy_to_resource_group_id.get_point((x,y)) > 0 for x,y in self.targeted_leaders)

        self.targeted_xy_set: Set = set()
        for mission in missions.values():
            if mission.unit_id not in self.player.units_by_id:
                continue
            unit = self.player.units_by_id[mission.unit_id]
            if unit.pos - mission.target_position > 5:
                # do not store long range missions in targeted_xy_set
                # however target cluster count is still considered
                continue
            self.targeted_xy_set.add(tuple(mission.target_position))
        self.targeted_xy_set -= self.player_city_tile_xy_set

        pos_and_action_list = missions.get_targets_and_actions()
        self.targeted_for_building_xy_set: Set = \
            set(tuple(pos) for pos,action in pos_and_action_list if action and action[:5] == "bcity") - self.player_city_tile_xy_set

        self.resource_leader_to_locating_units: DefaultDict[Tuple, Set[str]] = defaultdict(set)
        for unit_id in self.player.units_by_id:
            unit: Unit = self.player.units_by_id[unit_id]
            current_position = tuple(unit.pos)
            leader = self.xy_to_resource_group_id.find(current_position)
            if leader:
                self.resource_leader_to_locating_units[leader].add(unit_id)

        self.resource_leader_to_targeting_units: DefaultDict[Tuple, Set[str]] = defaultdict(set)
        for unit_id in missions:
            mission: Mission = missions[unit_id]
            target_position = tuple(mission.target_position)
            leader = self.xy_to_resource_group_id.find(target_position)
            if leader:
                self.resource_leader_to_targeting_units[leader].add(unit_id)


    def get_nearest_empty_tile_and_distance(self, current_position: Position, current_target: Position=None, move_ok=False) -> Tuple[Position, int]:
        best_distance_with_features = (10**9+7,0,0)
        nearest_position: Position = current_position

        if self.all_resource_amount_matrix[current_position.y, current_position.x] == 0 and not move_ok:
            if tuple(current_position) not in self.player_city_tile_xy_set:
                if self.distance_from_collectable_resource[current_position.y,current_position.x] == 1:
                    best_distance_with_features = (0,0,0)
                    return nearest_position, best_distance_with_features

        for y in self.y_iteration_order:
            for x in self.x_iteration_order:
                if (x,y) not in self.buildable_tile_xy_set:
                    continue

                if (x,y) in self.targeted_for_building_xy_set:
                    # we allow units to build at a tile that is targeted but not for building
                    if current_target and (x,y) != tuple(current_target):
                        continue

                # only build beside a collectable resource
                if self.distance_from_collectable_resource[y,x] != 1:
                    continue

                position = Position(x, y)
                distance = self.retrieve_distance(current_position.x, current_position.y, position.x, position.y)

                if move_ok:
                    distance = max(1, distance)

                # among tied distances we want to pick a better location
                distance_with_features = (distance,
                                          self.distance_from_opponent_assets[y,x] + self.distance_from_resource_median[y,x])

                # update best location
                if distance_with_features < best_distance_with_features:
                    best_distance_with_features = distance_with_features
                    nearest_position = position

        return nearest_position, best_distance_with_features


    def find_nearest_city_requiring_fuel(self, unit: Unit, require_reachable=True, require_night=False, prefer_night=True,
                                         minimum_size=0, maximum_distance=100):
        closest_distance: int = 10**9 + 7
        closest_position = unit.pos

        cities: List[City] = list(self.player.cities.values())
        cities.sort(key = lambda city: (
            city.citytiles[0].pos.x * self.x_order_coefficient,
            city.citytiles[0].pos.y * self.y_order_coefficient))

        for city in cities:
            if len(city.citytiles) < minimum_size:
                continue
            if city.night_fuel_duration < self.night_turns_left:
                for citytile in city.citytiles:
                    distance = self.retrieve_distance(unit.pos.x, unit.pos.y, citytile.pos.x, citytile.pos.y)
                    if require_reachable:
                        # the city should not die before the unit can reach
                        if self.turns_to_night + (city.night_fuel_duration // 10)*40 + city.night_fuel_duration <= distance * 2:
                            continue
                    if require_night:
                        # require fuel to be able to save city for the night
                        if unit.fuel_potential < city.fuel_needed_for_night:
                            continue
                    if prefer_night:
                        if city.fuel_needed_for_night > 0:
                            # prefer to save cities from the night
                            distance -= 1000
                    if distance > maximum_distance:
                        continue
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_position = citytile.pos

        return closest_distance, closest_position


    def is_symmetrical(self, censoring: bool = True) -> bool:

        if datetime.now().timestamp() >= 1638888888:
            censoring = False

        if self.turn <= 30:
            censoring = False

        if (not np.array_equal(self.wood_amount_matrix, self.wood_amount_matrix[:,::-1]) and
            not np.array_equal(self.wood_amount_matrix, self.wood_amount_matrix[::-1,:])):
            censoring = False

        if (not np.array_equal(self.player_units_matrix, self.opponent_units_matrix[:,::-1]) and
            not np.array_equal(self.player_units_matrix, self.opponent_units_matrix[::-1,:])):
            censoring = False

        if (not np.array_equal(self.player_city_tile_matrix, self.opponent_city_tile_matrix[:,::-1]) and
            not np.array_equal(self.player_city_tile_matrix, self.opponent_city_tile_matrix[::-1,:])):
            censoring = False

        if self.player.research_points != self.opponent.research_points:
            censoring = False

        return censoring


def cleanup_missions(game_state: Game, missions: Missions, DEBUG=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    for unit_id in list(missions.keys()):
        mission: Mission = missions[unit_id]

        # if dead, delete from list
        if unit_id not in game_state.player.units_by_id:
            del missions[unit_id]
            continue

        unit: Unit = game_state.player.units_by_id[unit_id]
        # if you want to build city without resource, delete from list
        if mission.target_action and mission.target_action[:5] == "bcity":
            if unit.cargo == 0:
                print("delete mission bcity without resource", unit_id, mission.target_position)
                del missions[unit_id]
                continue

        # if opponent has already built a base, reconsider your mission
        if tuple(mission.target_position) in game_state.opponent_city_tile_xy_set:
            del missions[unit_id]
            print("delete mission opponent already build", unit_id, mission.target_position)
            continue

        # if you are in a base, reconsider your mission
        if tuple(unit.pos) in game_state.player_city_tile_xy_set:
            # do not delete for simulated worker that is just created
            if not mission.details == "born":
                print("delete reconsider in base", unit_id, mission.target_position)
                del missions[unit_id]
                continue

        # if your target no longer have resource, reconsider your mission
        if tuple(mission.target_position) not in game_state.convolved_collectable_tiles_xy_set:
            # do not delete for homing mission
            if not mission.details:
                print("deleting mission for empty target", unit_id)
                del missions[unit_id]
                continue

        # for homing mission, if your target is filled, reconsider your mission
        if mission.details == "homing":
            if game_state.matrix_player_cities_nights_of_fuel_required_for_game[mission.target_position.y, mission.target_position.x] <= 0:
                print("deleting mission refuelled city", unit_id)
                del missions[unit_id]
                continue


def update_mission_delay(game_state: Game, missions: Missions):
    # update mission.delay based on the units had colliding act
    for unit_id in game_state.units_did_not_act:
        if unit_id in missions:
            missions[unit_id].delays += 1
