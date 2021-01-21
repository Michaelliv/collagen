from pathlib import Path
from shutil import rmtree

from git import Repo


def clone_repository(repository_path: str, target_path: str, remove_if_already_exists):
    if Path(target_path).exists():
        if remove_if_already_exists:
            rmtree(target_path)
        else:
            raise RuntimeError(f"Target {target_path} already exists")
    Repo.clone_from(repository_path, target_path)
