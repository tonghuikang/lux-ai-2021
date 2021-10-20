[ -e submission.tar.gz ] && rm -- submission.tar.gz
tar --exclude='*.ipynb' --exclude="*.pyc" --exclude="*.pkl" --exclude="replay.json" --exclude="*.png" -czf submission.tar.gz *
python3 generate_notebook.py
kaggle kernels push
