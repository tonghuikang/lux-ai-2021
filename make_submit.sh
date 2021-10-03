[ -e submission.tar.gz ] && rm -- submission.tar.gz
tar --exclude='*.ipynb' --exclude="*.pyc" --exclude="*.pkl" --exclude="replay.json" -czf submission.tar.gz *
python3 generate_notebook.py
