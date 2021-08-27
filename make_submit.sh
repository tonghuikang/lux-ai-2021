[ -e submission.tar.gz ] && rm -- submission.tar.gz
tar --exclude='*.ipynb' --exclude="*.pyc" -czf submission.tar.gz *
