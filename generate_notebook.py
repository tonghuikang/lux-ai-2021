# produces warnings which can be ignored, but I hope to resolve this
# upload the notebook_generated.ipynb onto Kaggle and "Save & Run All"

from IPython.nbformat import current as nbf


cells = []

preamble = """
# Devastation Strategy
To be described.
"""



cells.append(nbf.new_text_cell('markdown', preamble))

init_code = """\
!pip install kaggle-environments -U
!cp -r ../input/lux-ai-2021/* .
"""
cells.append(nbf.new_code_cell(init_code))



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
env = make("lux_ai_2021", debug=True, configuration={"width":12, "height":12})
steps = env.run(["agent.py", "simple_agent"])
"""
cells.append(nbf.new_code_cell(runner_code))

cells.append(nbf.new_text_cell('markdown', "# Simulation"))

render_code = """\
env.render(mode="ipython", width=900, height=800)
"""
cells.append(nbf.new_code_cell(render_code))

cells.append(nbf.new_text_cell('markdown', "# Debugging"))



debugging_code = """\
import numpy as np
import pickle
from agent import game_logic

str_step = "010"
with open('snapshots/game_state-{}.pkl'.format(str_step), 'rb') as handle:
    game_state = pickle.load(handle)
with open('snapshots/missions-{}.pkl'.format(str_step), 'rb') as handle:
    missions = pickle.load(handle)

print(np.array(game_state.convolved_fuel_matrix))
game_logic(game_state, missions, DEBUG=True)
"""
cells.append(nbf.new_code_cell(debugging_code))



cells.append(nbf.new_text_cell('markdown', "# Submission"))

zip_code = """\
!rm snapshots/*.pkl
!tar --exclude='*.ipynb' --exclude="*.pyc" --exclude="*.pkl" -czf submission.tar.gz *
!rm *.py && !rm -rf __pycache__/ && !rm -rf lux/
"""
cells.append(nbf.new_code_cell(zip_code))

nb = nbf.new_notebook()
nb['worksheets'].append(nbf.new_worksheet(cells=cells))

with open('notebook_generated.ipynb', 'w') as f:
    nbf.write(nb, f, 'ipynb', version=4)
