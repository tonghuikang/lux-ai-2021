from lux import game
import random
from typing import List, Set, Tuple

from .constants import Constants

DIRECTIONS = Constants.DIRECTIONS


class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __sub__(self, pos) -> int:
        return abs(pos.x - self.x) + abs(pos.y - self.y)

    def distance_to(self, pos):
        """
        Returns Manhattan (L1/grid) distance to pos
        """
        return self - pos

    def is_adjacent(self, pos):
        return (self - pos) <= 1

    def __eq__(self, pos) -> bool:
        return self.x == pos.x and self.y == pos.y

    def equals(self, pos):
        return self == pos

    def translate(self, direction, units) -> 'Position':
        if direction == DIRECTIONS.NORTH:
            return Position(self.x, self.y - units)
        elif direction == DIRECTIONS.EAST:
            return Position(self.x + units, self.y)
        elif direction == DIRECTIONS.SOUTH:
            return Position(self.x, self.y + units)
        elif direction == DIRECTIONS.WEST:
            return Position(self.x - units, self.y)
        elif direction == DIRECTIONS.CENTER:
            return Position(self.x, self.y)

    def direction_to(self, target_pos: 'Position',
                     set_occupied_xy: Set[Tuple[int]] = set(),
                     player_city_tile_xy_set: Set[Tuple[int]] = set(),
                     turn_num: int = 0,
                     wood_carrying: int = 0,
                     turns_to_dawn: int = 0) -> DIRECTIONS:
        # [TODO] bring this outside to allow the reading of game_state
        """
        Return closest position to target_pos from this position
        Lots of input because we cannot take game_state here because it will result in circular import
        Probably should be implemented elsewhere
        """
        check_dirs = [
            DIRECTIONS.NORTH,
            DIRECTIONS.EAST,
            DIRECTIONS.SOUTH,
            DIRECTIONS.WEST,
        ]
        random.shuffle(check_dirs)
        closest_dist = 1000
        closest_dir = check_dirs[0]
        closest_pos = Position(self.x, self.y)

        for direction in check_dirs:
            newpos = self.translate(direction, 1)

            dist = target_pos.distance_to(newpos)

            if tuple(newpos) in set_occupied_xy:
                continue

            # [TODO] do not go into a city tile if you are carry substantial wood in the early game
            if tuple(newpos) in player_city_tile_xy_set and wood_carrying >= min(11, turns_to_dawn)*4:
                continue

            if dist < closest_dist:
                closest_dir = direction
                closest_dist = dist
                closest_pos = newpos

        if closest_dir != DIRECTIONS.CENTER:
            set_occupied_xy.discard((self.x, self.y))
        set_occupied_xy.add((closest_pos.x, closest_pos.y))

        return closest_dir, set_occupied_xy

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __iter__(self):
        for i in (self.x, self.y):
            yield i