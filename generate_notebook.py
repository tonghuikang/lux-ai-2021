# produces warnings which can be ignored, but I hope to resolve this
# upload the notebook_generated.ipynb onto Kaggle and "Save & Run All"

import nbformat
import nbformat.v4 as nbf





cells = []

preamble_intro = """
# [Lux AI] Working Title Bot
The code structure and logic, and version updates are elaborated in the comment section.

I hope this can be a useful template for you to work on your bot on.
You are recommended to edit on a clone/fork of [my repository](https://github.com/tonghuikang/lux-ai-2021) with your favorite IDE.
You can submit the zip the repository to the competition. This notebook is generated with `generate_notebook.py`.

Regardless, do feel free to clone this notebook and submit `submission.tar.gz` under the "Data" tab.
"""
cells.append(nbf.new_markdown_cell(preamble_intro))


init_code = """\
!pip install kaggle-environments -U > /dev/null
!cp -r ../input/lux-ai-2021/* .\
"""
cells.append(nbf.new_code_cell(init_code, metadata={"_kg_hide-input": True}))





preamble_agent = """\
# Agent Logic
The following scipts contain the algorithms that the agent uses.
The algorithm is described in the comments.
Feel free to ask for more clarification.
"""
cells.append(nbf.new_markdown_cell(preamble_agent))


filenames = [
    "agent.py",
    "make_actions.py",
    "make_annotations.py",
    "heuristics.py",
    "main.py",
]

for filename in filenames:
    savefile_cell_magic = f"%%writefile {filename}\n"
    with open(filename, "r") as f:
        content = savefile_cell_magic + f.read()
    cell = nbf.new_code_cell(content, metadata={"_kg_hide-input": True})
    cells.append(cell)





preamble_kit = """\
# Upgraded Game Kit
The game kit has been edited to include more features for the agent to make decisions on.
"""

cells.append(nbf.new_markdown_cell(preamble_kit))

filenames = [
    "lux/game.py",
    "lux/game_map.py",
    "lux/game_objects.py",
    "lux/game_position.py",
    "lux/game_constants.py",
    "lux/constants.py",
    "lux/annotate.py",
]

for filename in filenames:
    savefile_cell_magic = f"%%writefile {filename}\n"
    with open(filename, "r") as f:
        content = savefile_cell_magic + f.read()
    cell = nbf.new_code_cell(content, metadata={"_kg_hide-input": True})
    cells.append(cell)





preamble_imitation_agent = """\
# Upgraded Game Kit
We defer some game decisions to the imitation agent. The model.pth is stored remotely and downloaded here.
"""

cells.append(nbf.new_markdown_cell(preamble_kit))

cells.append(nbf.new_code_cell("""\
!wget https://tonghuikang.github.io/lux-ai-private-models/111813.pth -O model.pth
# !wget https://tonghuikang.github.io/lux-ai-private-models/111514.pth -O model.pth
# !wget https://tonghuikang.github.io/lux-ai-private-models/111912.pth -O model.pth
# !wget https://tonghuikang.github.io/lux-ai-private-models/112523.pth -O model.pth
# !wget https://tonghuikang.github.io/lux-ai-private-models/112613.pth -O model.pth
# !wget https://tonghuikang.github.io/lux-ai-private-models/112620.pth -O model.pth
# !wget https://tonghuikang.github.io/lux-ai-private-models/112818.pth -O model.pth
""", metadata={"_kg_hide-input": True}))

filenames = [
    "imitation_agent.py",
]

for filename in filenames:
    savefile_cell_magic = f"%%writefile {filename}\n"
    with open(filename, "r") as f:
        content = savefile_cell_magic + f.read()
    cell = nbf.new_code_cell(content, metadata={"_kg_hide-input": True})
    cells.append(cell)





preamble_rendering = """\
# Game Rendering
This is a replay of the agent fighting against itself.

The missions of each unit is annotated.
`X` and `O` indicates target position for the unit to move to.
In addition, `O` indicates that the unit will build a citytile upon arrival at the tile.

`O` on the city tile indicates that the citytile have enough fuel to last to the end of the game.
Otherwise, the number of nights it can endure will be indicated on the tile.

The inscription on the unit indicates the amount of total resources it has, and the majority type of resource.
`F` indicates that it has at least 100 resources. If the unit has moved in the turn, the inscription is annotated on the previous location.
"""
cells.append(nbf.new_markdown_cell(preamble_rendering))


runner_code = """\
!mkdir snapshots
from kaggle_environments import make
env = make("lux_ai_2021", debug=True, configuration={"annotations": True, "width":12, "height":12})
steps = env.run(["agent.py", "agent.py"])\
"""
cells.append(nbf.new_code_cell(runner_code, metadata={"_kg_hide-input": True, "jupyter": {"outputs_hidden":True}}))


render_code = """\
env.render(mode="ipython", width=900, height=800)\
"""
cells.append(nbf.new_code_cell(render_code, metadata={"_kg_hide-input": True}))





preamble_debugging = """\
# Debugging
In the run, we have saved the game state and missions as Python pickle files.

We can rerun the game logic and debug how missions are planned and actions are executed.

For visualisation, we plot `convolved_collectable_tiles_matrix`.
This matrix is used for estimating the best target position of a mission.
You could also print other attributes of `game_state`.
"""
cells.append(nbf.new_markdown_cell(preamble_debugging))


debugging_code = """\
import pickle
import numpy as np
import matplotlib.pyplot as plt
from agent import game_logic

str_step = "010"
player_id = 0
with open(f'snapshots/game_state-{str_step}-{player_id}.pkl', 'rb') as handle:
    game_state = pickle.load(handle)
with open(f'snapshots/observation-{str_step}-{player_id}.pkl', 'rb') as handle:
    observation = pickle.load(handle)
with open(f'snapshots/missions-{str_step}-{player_id}.pkl', 'rb') as handle:
    missions = pickle.load(handle)

game_logic(game_state, missions, observation, DEBUG=True)
plt.imshow(game_state.convolved_collectable_tiles_matrix)
plt.colorbar()
plt.show()\
"""
cells.append(nbf.new_code_cell(debugging_code, metadata={"_kg_hide-input": True}))





preamble_evaluation = """\
# Evaluation
If you want measure the winrate between two agents, you need to play many matches.

For each map size, we play a number of matches. For larger maps, we play a smaller number of matches.

To make scores more comparable, the seed of the matches will have to be consistent over different plays.\
"""
cells.append(nbf.new_markdown_cell(preamble_evaluation))


cells.append(nbf.new_code_cell("""\
!npm install -g @lux-ai/2021-challenge@latest &> /dev/null
!pip install kaggle-environments -U &> /dev/null\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
%%bash
# REF_DIR="/kaggle/input/lux-ai-published-agents/realneuralnetwork/lux-ai-with-il-decreasing-learning-rate/v3/*"
REF_DIR="/kaggle/input/hungry-goose-alphageese-agents/111813_no_curfew/*"
mkdir -p ref/  # imitation agent
cp -r $REF_DIR ref/
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
!mkdir template\
""", metadata={"_kg_hide-input": True}))

filenames = [
    "template/main.py",
]

for filename in filenames:
    savefile_cell_magic = f"%%writefile {filename}\n"
    with open(filename, "r") as f:
        content = savefile_cell_magic + f.read()
    cell = nbf.new_code_cell(content, metadata={"_kg_hide-input": True})
    cells.append(cell)


cells.append(nbf.new_code_cell("""\
!cd ref/ && tar -xvzf *.tar.gz &> /dev/null
!cp template/main.py ref/main.py  # fix main.py\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
!GFOOTBALL_DATA_DIR=C lux-ai-2021 --loglevel 0 --width 12 --height 12 main.py ref/main.py\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
%%writefile evaluate_for_map_size.sh

MAP_SIZE=$1
for run in {1..200};
    do GFOOTBALL_DATA_DIR=C lux-ai-2021 --seed $run --loglevel 1 --maxtime 10000 \\
    --height $MAP_SIZE --width $MAP_SIZE --storeReplay=false --storeLogs=false \\
    ./main.py ./ref/main.py >> logs-$MAP_SIZE.txt;
done\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
!chmod +x ./evaluate_for_map_size.sh\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
!timeout 1h bash ./evaluate_for_map_size.sh 12\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
!timeout 1h bash ./evaluate_for_map_size.sh 16\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
!timeout 2h bash ./evaluate_for_map_size.sh 24\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell("""\
!timeout 4h bash ./evaluate_for_map_size.sh 32\
""", metadata={"_kg_hide-input": True}))


cells.append(nbf.new_code_cell('''\
import os

wins_template = """
    { rank: 1, agentID: 0, name: './main.py' },
    { rank: 2, agentID: 1, name: './ref/main.py' }
"""

draw_template = """
    { rank: 1, agentID: 0, name: './main.py' },
    { rank: 1, agentID: 1, name: './ref/main.py' }
"""

lose_template = """
    { rank: 1, agentID: 1, name: './ref/main.py' },
    { rank: 2, agentID: 0, name: './main.py' }
"""

map_sizes = [12,16,24,32]
map_size_count = 0
total_score = 0
for map_size in map_sizes:
    logfile_name = f"logs-{map_size}.txt"
    if os.path.isfile(logfile_name):
        map_size_count += 1
        with open(logfile_name) as f:
            data_string = f.read()
            wins = data_string.count(wins_template)
            draw = data_string.count(draw_template)
            lose = data_string.count(lose_template)
            score = (wins + draw / 2)/(wins + draw + lose)*100
            total_score += score
            print(f"Map size: {map_size}, Score: {score:.3f}, Stats: {wins}/{draw}/{lose}")
total_score = total_score/map_size_count
print(f"Total score: {total_score:.3f}")\
''', metadata={"_kg_hide-input": True}))


zip_code = """\
!rm snapshots/*.pkl
!tar --exclude='*.ipynb' --exclude="*.pyc" --exclude="*.pkl" --exclude="./replays/" --exclude="./ref/" -czf submission.tar.gz *
!rm *.py && rm -rf __pycache__/ && rm -rf lux/ && rm -rf ref/\
"""

cells.append(nbf.new_code_cell(zip_code, metadata={"_kg_hide-input": True}))


notebook_metadata = {
    "kernelspec": {
        "language": "python",
        "display_name": "Python 3",
        "name": "python3"
    },
    "language_info": {
        "name": "python",
        "version": "3.7.10",
        "mimetype": "text/x-python",
        "codemirror_mode": {
            "name": "ipython",
            "version": 3
        },
        "pygments_lexer": "ipython3",
        "nbconvert_exporter": "python",
        "file_extension": ".py"
    }
}


nb = nbf.new_notebook(cells=nbformat.from_dict(cells), metadata=notebook_metadata)

with open('notebook_generated.ipynb', 'w') as f:
    nbformat.write(nb, f)
