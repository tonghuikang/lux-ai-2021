from typing import Dict
import sys
from agent import agent
from lux.game import Observation

if __name__ == "__main__":

    def read_input():
        """
        Reads input from stdin
        """
        try:
            return input()
        except EOFError as eof:
            raise SystemExit(eof)
    step = 0
    observation = Observation()
    observation["updates"] = []
    observation["step"] = 0
    player_id = 0
    while True:
        inputs = read_input()
        observation["updates"].append(inputs)

        if inputs == "D_DONE":
            if step == 0:  # the codefix
                player_id = int(observation["updates"][0])
                observation.player = player_id
                observation["player"] = player_id
                observation["width"], observation["height"] = map(int, observation["updates"][1].split())
            actions = agent(observation, None)
            observation["updates"] = []
            step += 1
            observation["step"] = step
            print(",".join(actions))
            print("D_FINISH")
