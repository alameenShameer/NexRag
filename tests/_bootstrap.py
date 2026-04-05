from pathlib import Path
import os
import sys


def ensure_repo_root():
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)

    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    os.chdir(repo_root)
    return repo_root
