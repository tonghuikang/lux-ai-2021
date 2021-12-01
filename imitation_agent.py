import os
import numpy as np
import torch

from typing import Set
from lux import annotate
from lux.game import Game, Observation, Unit
import builtins as __builtin__
import random


path = os.path.dirname(os.path.realpath(__file__))
model = torch.jit.load(f'{path}/model.pth')
model.eval()


def make_input(obs: Observation, unit_id: str):
    width, height = obs['width'], obs['height']
    x_shift = (32 - width) // 2
    y_shift = (32 - height) // 2
    cities = {}

    b = np.zeros((20, 32, 32), dtype=np.float32)

    for update in obs['updates']:
        strs = update.split(' ')
        input_identifier = strs[0]

        if input_identifier == 'u':
            x = int(strs[4]) + x_shift
            y = int(strs[5]) + y_shift
            wood = int(strs[7])
            coal = int(strs[8])
            uranium = int(strs[9])
            if unit_id == strs[3]:
                # Position and Cargo
                b[:2, x, y] = (
                    1,
                    (wood + coal + uranium) / 100
                )
            else:
                # Units
                team = int(strs[2])
                cooldown = float(strs[6])
                idx = 2 + (team - obs['player']) % 2 * 3
                b[idx:idx + 3, x, y] = (
                    1,
                    cooldown / 6,
                    (wood + coal + uranium) / 100
                )
        elif input_identifier == 'ct':
            # CityTiles
            team = int(strs[1])
            city_id = strs[2]
            x = int(strs[3]) + x_shift
            y = int(strs[4]) + y_shift
            idx = 8 + (team - obs['player']) % 2 * 2
            b[idx:idx + 2, x, y] = (
                1,
                cities[city_id]
            )
        elif input_identifier == 'r':
            # Resources
            r_type = strs[1]
            x = int(strs[2]) + x_shift
            y = int(strs[3]) + y_shift
            amt = int(float(strs[4]))
            b[{'wood': 12, 'coal': 13, 'uranium': 14}[r_type], x, y] = amt / 800
        elif input_identifier == 'rp':
            # Research Points
            team = int(strs[1])
            rp = int(strs[2])
            b[15 + (team - obs['player']) % 2, :] = min(rp, 200) / 200
        elif input_identifier == 'c':
            # Cities
            city_id = strs[2]
            fuel = float(strs[3])
            lightupkeep = float(strs[4])
            cities[city_id] = min(fuel / lightupkeep, 10) / 10

    # Day/Night Cycle
    b[17, :] = obs['step'] % 40 / 40
    # Turns
    b[18, :] = obs['step'] / 360
    # Map Size
    b[19, x_shift:32 - x_shift, y_shift:32 - y_shift] = 1

    return b


def probabilistic_sort(logits):
    probs = np.exp(logits)
    probs = probs/np.sum(probs)

    pool = [(i,x) for i,x in enumerate(probs)]

    order = []
    while pool:
        (i,x), = random.choices(pool, weights=[x for i,x in pool])
        order.append(i)
        pool.remove((i,x))
    return order


def call_func(obj, method, args=[]):
    return getattr(obj, method)(*args)


unit_actions = [('move', 'n'), ('move', 's'), ('move', 'w'), ('move', 'e'), ('build_city',), ('move', 'c')]
def get_action(policy, game_state: Game, unit: Unit, dest: Set, DEBUG=False, use_probabilistic_sort=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    order = np.argsort(policy)[::-1]
    if use_probabilistic_sort:
        order = probabilistic_sort(policy)

    print(np.round(policy, 2))
    print(order)
    annotations = []
    for label in order:
        act = unit_actions[label]
        pos = unit.pos.translate(act[-1], 1) or unit.pos
        if tuple(pos) not in dest or unit.pos == pos:
            if act[0] == 'build_city' and tuple(unit.pos) not in game_state.buildable_tile_xy_set:
                continue
            if act[0] == 'build_city' or unit.pos != pos:
                unit.cooldown += 2
            if act[0] != ('move', 'c'):
                annotations.append(annotate.x(pos.x, pos.y))
            return call_func(unit, *act), pos, annotations

    return unit.move('c'), unit.pos, annotations


def get_imitation_action(observation: Observation, game_state: Game, unit: Unit, DEBUG=False, use_probabilistic_sort=False):
    if DEBUG: print = __builtin__.print
    else: print = lambda *args: None

    # Worker Actions
    dest = game_state.occupied_xy_set
    state = make_input(observation, unit.id)
    with torch.no_grad():
        p = model(torch.from_numpy(state).unsqueeze(0))

    policy = p.squeeze(0).numpy()

    action, pos, annotations = get_action(policy, game_state, unit, dest, DEBUG=DEBUG, use_probabilistic_sort=use_probabilistic_sort)
    dest.add(tuple(pos))
    print(unit.id, unit.pos, pos, action)
    print()

    return [action] + annotations
