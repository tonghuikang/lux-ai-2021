import os
import numpy as np
import torch
import time

from typing import Set
from lux import annotate
from lux.game import Game, Observation, Unit
import builtins as __builtin__
import random

random.seed(42)


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
    probs = np.exp(logits)/np.sum(np.exp(logits))
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

transforms = [
    (lambda x: np.rot90(x,              axes=(1, 2),    k=0).copy(),  [1,2,3,4]),
    (lambda x: np.rot90(np.flip(x,1),   axes=(1, 2),    k=0).copy(),  [1,2,4,3]),
    (lambda x: np.rot90(x,              axes=(1, 2),    k=1).copy(),  [3,4,2,1]),
    (lambda x: np.rot90(np.flip(x,1),   axes=(1, 2),    k=1).copy(),  [4,3,2,1]),
    (lambda x: np.rot90(x,              axes=(1, 2),    k=2).copy(),  [2,1,4,3]),
    (lambda x: np.rot90(np.flip(x,1),   axes=(1, 2),    k=2).copy(),  [2,1,3,4]),
    (lambda x: np.rot90(x,              axes=(1, 2),    k=3).copy(),  [4,3,1,2]),
    (lambda x: np.rot90(np.flip(x,1),   axes=(1, 2),    k=3).copy(),  [3,4,1,2]),
]
random.shuffle(transforms)


def invert_permute(permute):
    inv_permute = [-1 for _ in range(4)]
    for i,x in enumerate(permute):
        x -= 1
        inv_permute[x] = i
    inv_permute = np.array(inv_permute)
    return inv_permute

transforms = [(transform, invert_permute(permute)) for transform, permute in transforms]


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
        if (tuple(pos) not in dest) or (unit.pos == pos) or (unit.fuel_potential > 0 and tuple(pos) in game_state.player_city_tile_xy_set):
            if act[0] == 'build_city':
                if unit.get_cargo_space_used() != 100:
                    continue
                if tuple(unit.pos) not in game_state.buildable_tile_xy_set:
                    continue
                if tuple(unit.pos) in game_state.avoid_building_citytiles_xy_set:
                    print("avoid building", unit.pos, unit.id)
                    continue
            if tuple(pos) in game_state.sinking_cities_xy_set:
                continue
            if tuple(pos) in game_state.opponent_city_tile_xy_set:
                continue
            if unit.fuel_potential == 0 and game_state.turn %40 >= 30:
                if game_state.fuel_collection_rate[pos.y, pos.x] == 0 and tuple(pos) not in game_state.player_city_tile_xy_set:
                    continue
            if unit.fuel_potential > 0 and game_state.matrix_player_cities_nights_of_fuel_required_for_game[pos.y, pos.x] < -20:
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

    start_time = time.time()

    # Worker Actions
    dest = game_state.occupied_xy_set
    state = make_input(observation, unit.id)

    average_policy = np.zeros(6)
    ranked_policy = np.zeros(6)
    NUMBER_OF_TRANSFORMS = game_state.number_of_transforms
    # NUMBER_OF_TRANSFORMS = 1

    with torch.no_grad():

        transformed_states = np.zeros((NUMBER_OF_TRANSFORMS, 20, 32, 32), dtype=np.float32)
        for i, (transform, inv_permute) in enumerate(transforms[:NUMBER_OF_TRANSFORMS]):
            transformed_state = transform(state)
            transformed_states[i,:,:,:] = transformed_state
        transformed_states = torch.from_numpy(transformed_states)

        p = model(transformed_states)
        for (transform, inv_permute), policy in zip(transforms, p.numpy()):
            policy[:4] = policy[inv_permute]
            print(np.round(policy, 2))
            # booster considering transfer actions are discarded
            if tuple(unit.pos) in game_state.wood_exist_xy_set:
                policy[-1] += 0.25

            if game_state.player.researched_coal_projected():
                if tuple(unit.pos) in game_state.coal_exist_xy_set:
                    policy[-1] += 0.75

            if game_state.player.researched_uranium():
                policy[-1] += game_state.convolved_uranium_exist_matrix[unit.pos.y, unit.pos.x]

            if game_state.player.researched_uranium_projected():
                if tuple(unit.pos) in game_state.uranium_exist_xy_set:
                    policy[-1] += 1.25

            average_policy += policy/NUMBER_OF_TRANSFORMS
            ranked_policy += policy.argsort().argsort()

    print(ranked_policy)
    print(average_policy)

    action, pos, annotations = get_action(average_policy, game_state, unit, dest, DEBUG=DEBUG, use_probabilistic_sort=use_probabilistic_sort)
    if tuple(pos):
        dest.add(tuple(pos))
    print(unit.id, unit.pos, pos, action, time.time() - start_time)
    print()

    return [action] + annotations
