# produces warnings which can be ignored, but I hope to resolve this
# upload the notebook_generated.ipynb onto Kaggle and "Save & Run All"

from IPython.nbformat import current as nbf


cells = []

preamble_intro = """
# [Lux AI] Working Title Bot
The code structure and logic, as well as hints for improvements will be elaborated in the comment section.

I hope this can be a useful template for you to work on your bot on.
You are strongly recommended to edit on a clone/fork of [my repository](https://github.com/tonghuikang/lux-ai-2021) with your favorite IDE.
You can submit the zip the repository to the competition. This notebook is generated with `generate_notebook.py`.

Regardless, do feel free to clone this notebook and submit `submission.tar.gz`.
"""

cells.append(nbf.new_text_cell('markdown', preamble_intro))

init_code = """\
!pip install kaggle-environments -U
!cp -r ../input/lux-ai-2021/* .\
"""
cells.append(nbf.new_code_cell(init_code))




preamble_code = """\
# Code
The following contains code that will be zipped into the submission file.
"""

cells.append(nbf.new_text_cell('markdown', preamble_code))


filenames = [
    "agent.py",
    "actions.py",
    "heuristics.py",
    "main.py",
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
    cell = nbf.new_code_cell(content)
    cells.append(cell)


runner_code = """\
!mkdir snapshots
from kaggle_environments import make
env = make("lux_ai_2021", debug=True, configuration={"annotations": True, "width":12, "height":12})
steps = env.run(["agent.py", "simple_agent"])\
"""
cells.append(nbf.new_code_cell(runner_code))




preamble_rendering = """\
# Game Rendering
Annotations has been made.

`X` and `O` indicates target position for the unit to move to.

In addition, `O` indicates that the unit will build a citytile upon arrival at the tile.
"""

cells.append(nbf.new_text_cell('markdown', preamble_rendering))


render_code = """\
env.render(mode="ipython", width=900, height=800)\
"""
cells.append(nbf.new_code_cell(render_code))




preamble_debugging = """\
# Debugging
You are also able to observe the game state and missions that have been saved as Python pickle files.

The mission plans and the actions has been printed.

The `convolved_rate_matrix`, which is used for estimating the best target position of a mission, is also printed. You could also print other attributes of `game_state`.
"""

cells.append(nbf.new_text_cell('markdown', preamble_debugging))




debugging_code = """\
import numpy as np
import pickle
from agent import game_logic

str_step = "010"
with open('snapshots/game_state-{}.pkl'.format(str_step), 'rb') as handle:
    game_state = pickle.load(handle)
with open('snapshots/missions-{}.pkl'.format(str_step), 'rb') as handle:
    missions = pickle.load(handle)

game_logic(game_state, missions, DEBUG=True)
print(game_state.convolved_rate_matrix)\
"""

cells.append(nbf.new_code_cell(debugging_code))




cells.append(nbf.new_text_cell('markdown', "# Submission"))

zip_code = """\
!rm snapshots/*.pkl
!tar --exclude='*.ipynb' --exclude="*.pyc" --exclude="*.pkl" -czf submission.tar.gz *
!rm *.py && rm -rf __pycache__/ && rm -rf lux/\
"""
cells.append(nbf.new_code_cell(zip_code))



nb = nbf.new_notebook()
nb['worksheets'].append(nbf.new_worksheet(cells=cells))

with open('notebook_generated.ipynb', 'w') as f:
    nbf.write(nb, f, 'ipynb', version=4)
