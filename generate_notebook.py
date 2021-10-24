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
with open(f'snapshots/missions-{str_step}-{player_id}.pkl', 'rb') as handle:
    missions = pickle.load(handle)

game_logic(game_state, missions, DEBUG=True)
plt.imshow(game_state.convolved_collectable_tiles_matrix)
plt.colorbar()
plt.show()\
"""
cells.append(nbf.new_code_cell(debugging_code, metadata={"_kg_hide-input": True}))





preamble_evaluation = """\
# Evaluation
We run the agent against the imitation agent for a few matches.
"""
cells.append(nbf.new_markdown_cell(preamble_evaluation))


evaluation_code = """\
!npm install -g @lux-ai/2021-challenge@latest &> /dev/null
!pip install kaggle-environments -U &> /dev/null\
"""
cells.append(nbf.new_code_cell(evaluation_code, metadata={"_kg_hide-input": True}))


evaluation_code = """\
%%bash
REF_DIR="/kaggle/input/lux-ai-imitation-learning/submission.tar.gz"
mkdir -p ref/  # imitation agent
cp -r $REF_DIR ref/
cd ref && tar -xvzf *.tar.gz &> /dev/null\
"""
cells.append(nbf.new_code_cell(evaluation_code, metadata={"_kg_hide-input": True}))


evaluation_code = """\
!cp main.py ref/main.py  # fix main.py\
"""
cells.append(nbf.new_code_cell(evaluation_code, metadata={"_kg_hide-input": True}))


evaluation_code = """\
!GFOOTBALL_DATA_DIR=C lux-ai-2021 --loglevel 0 --width 12 --height 12 main.py ref/main.py\
"""
cells.append(nbf.new_code_cell(evaluation_code, metadata={"_kg_hide-input": True}))


evaluation_code = """\
%%bash
MAP_SIZE=12
for run in {1..5};
    do GFOOTBALL_DATA_DIR=C lux-ai-2021 --seed $run --loglevel 1 --maxtime 10000 \\
    --height $MAP_SIZE --width $MAP_SIZE --storeReplay=false --storeLogs=false \\
    main.py ref/main.py >> logs-$MAP_SIZE.txt;
done\
"""
cells.append(nbf.new_code_cell(evaluation_code, metadata={"_kg_hide-input": True}))


evaluation_code = '''\
wins_template = """
    { rank: 1, agentID: 0, name: 'main.py' },
    { rank: 2, agentID: 1, name: 'ref/main.py' }
"""

draw_template = """
    { rank: 1, agentID: 0, name: 'main.py' },
    { rank: 1, agentID: 1, name: 'ref/main.py' }
"""

lose_template = """
    { rank: 1, agentID: 1, name: 'ref/main.py' },
    { rank: 2, agentID: 0, name: 'main.py' }
"""

map_sizes = [12]
total_score = 0
for map_size in map_sizes:
    logfile_name = f"logs-{map_size}.txt"
    with open(logfile_name) as f:
        data_string = f.read()
        wins = data_string.count(wins_template)
        lose = data_string.count(draw_template)
        draw = data_string.count(lose_template)
        score = (wins + lose / 2)/(wins + lose + draw)*100
        total_score += score/len(map_sizes)
        print(f"Map size: {map_size}, Score: {score:.3f}, Stats: {wins}/{lose}/{draw}")
print(f"Total score: {total_score:.3f}")\
'''

cells.append(nbf.new_code_cell(evaluation_code, metadata={"_kg_hide-input": True}))


cells.append(nbf.new_markdown_cell("# Make Submission"))


zip_code = """\
!rm snapshots/*.pkl
!tar --exclude='*.ipynb' --exclude="*.pyc" --exclude="*.pkl" --exclude="replays/" --exclude="ref/" -czf submission.tar.gz *
!rm *.py && rm -rf __pycache__/ && rm -rf lux/\
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
