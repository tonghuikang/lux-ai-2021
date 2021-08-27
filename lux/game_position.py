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

    def direction_to(self, target_pos: 'Position', set_occupied_xy: Set[Tuple[int]] = set()) -> DIRECTIONS:
        """
        Return closest position to target_pos from this position
        """
        check_dirs = [
            DIRECTIONS.NORTH,
            DIRECTIONS.EAST,
            DIRECTIONS.SOUTH,
            DIRECTIONS.WEST,
        ]
        random.shuffle(check_dirs)
        closest_dist = self.distance_to(target_pos)
        closest_dir = DIRECTIONS.CENTER
        closest_pos = Position(self.x, self.y)

        for direction in check_dirs:
            newpos = self.translate(direction, 1)

            dist = target_pos.distance_to(newpos)

            if (newpos.x, newpos.y) in set_occupied_xy:
                continue

            # [TODO] do not go into a city tile if you are carry substantial wood in the early game

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
