import hashlib
import subprocess
from os import PathLike
from pathlib import Path
from typing import Callable, Optional

from jinja2 import Template

PROJECT_ROOT = Path().absolute()
TEMPLATES_DIR = PROJECT_ROOT / "collagen" / "_templates"
STATIC_DIR = PROJECT_ROOT / "collagen" / "_static"

print(f"Collagen root: {PROJECT_ROOT}")
print(f"Collagen templates: {TEMPLATES_DIR}")
print(f"Collagen static files: {STATIC_DIR}")


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


def render_jinja_file(template_path: str, output_path: str, data: dict):
    with open(template_path, "r") as t:
        template_text = t.read()

    template = Template(template_text)
    rendered = template.render(**data)

    with open(output_path, "w") as out_t:
        out_t.write(rendered)


def exec_shell(*commands: str):
    for command in commands:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()


def make_init_files(path_iterator: PathIterator):
    for path in path_iterator:
        touch(path / "__init__.py")
