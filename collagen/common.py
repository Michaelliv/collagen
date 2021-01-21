import hashlib
import os
from os import PathLike
from pathlib import Path
from typing import Callable, Optional

PROJECT_ROOT = Path().absolute()
TEMPLATES_DIR = PROJECT_ROOT / "collagen" / "_templates"
STATIC_DIR = PROJECT_ROOT / "collagen" / "_static"
SPHINX_BUILD = "/home/michaell/programs/miniconda3/envs/mlrun/bin/sphinx-build"
SPHINX_API_DOC = "/home/michaell/programs/miniconda3/envs/mlrun/bin/sphinx-apidoc"
FUNCTIONS_DIR = Path().absolute().parent / "functions"
DOCS_DIR = Path().absolute().parent / "docs"
HTML_BUILD_DIR = DOCS_DIR / "_build" / "html"


class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, new_path: PathLike):
        self.new_path = os.path.expanduser(new_path)

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self):
        os.chdir(self.saved_path)


class PathIterator:
    def __init__(
        self,
        path: PathLike,
        rule: Optional[Callable[[Path], bool]] = None,
        recursive: bool = False,
    ) -> None:
        self.path = Path(path)
        self.rule = rule
        self.recursive = recursive

    def __iter__(self):
        iterator = self.path.rglob("*") if self.recursive else self.path.iterdir()
        for inner_path in iterator:
            if self.rule is None:
                yield inner_path
            elif self.rule(inner_path):
                yield inner_path
            else:
                continue


def touch(path: PathLike):
    open(path, "a")


def file_md5(path: str, buffer: int = 100_000):
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            data = f.read(buffer)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()
