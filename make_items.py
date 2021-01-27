from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from mlrun import import_function


def make_items(path_iterator):
    for path in path_iterator:
        make_item(str(path))


def make_item(path: str):
    path = Path(path)
    item = item_to_dict(path / "function.yaml")
    with open(path / "item.yaml", "w") as f:
        yaml.dump(item, f)


@dataclass
class Spec:
    filename: str = ""
    handler: str = ""
    requirements: List[str] = field(default_factory=list)
    kind: str = ""
    image: str = ""


@dataclass
class Maintainer:
    name: str = ""
    email: str = ""


@dataclass
class Item:
    api_version: str = "v1"
    org: str = "Iguazio"
    name: str = ""
    version: str = ""
    mlrun_version: str = ""
    platform_version: str = ""
    description: str = ""
    doc: str = ""
    example: str = ""
    icon: str = ""
    url: str = ""
    generationDate: str = ""
    categories: List[str] = field(default_factory=list)
    labels: Dict[str, Union[str, int, float]] = field(default_factory=dict)
    spec: Spec = field(default_factory=Spec)
    maintainers: List[Maintainer] = field(default_factory=list)
    marketplaceType: str = ""


def snake_case_to_lower_camel_case(string: str) -> str:
    if "_" not in string:
        return string
    else:
        components = string.split("_")
        return components[0] + "".join(c.title() for c in components[1:])


def locate_py_file(dir_path: Path) -> Optional[str]:
    default_py_file = dir_path / "function.py"

    if default_py_file.exists:
        return "function.py"

    py_file = list(filter(lambda d: d.suffix == ".py", dir_path.iterdir()))

    if len(py_file) > 1:
        raise RuntimeError(
            "Failed to infer business logic python file name, found multiple python files"
        )
    elif len(py_file) == 1:
        return py_file[0].name

    return None


def get_image(model):
    try:
        return model.spec.image
    except Exception:
        try:
            return model.spec.build.base_image
        except Exception:
            return ""


def function_to_item(function_yaml: Path) -> Item:
    model = import_function(str(function_yaml.absolute()))
    item = Item(
        name=model.metadata.name or "",
        version=model.metadata.tag or "0.1",
        mlrun_version="",
        platform_version="",
        description=model.spec.description or "",
        doc="",
        example="",
        icon="",
        url="",
        generationDate=str(datetime.utcnow()),
        categories=model.metadata.categories or [],
        labels=model.metadata.labels or {},
        spec=Spec(
            filename=locate_py_file(function_yaml.parent) or "",
            handler=model.spec.default_handler or "",
            requirements=[],
            kind=model.kind or "",
            image=get_image(model),
        ),
        maintainers=[],
    )
    return item


def item_to_dict(function_yaml: Path) -> dict:
    item = function_to_item(function_yaml)
    item = {snake_case_to_lower_camel_case(k): v for k, v in asdict(item).items()}
    return item
