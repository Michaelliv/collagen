import json
from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import rmtree
from typing import List

import yaml
from bs4 import BeautifulSoup
from sphinx.cmd.build import main as sphinx_build_cmd
from sphinx.ext.apidoc import main as sphinx_apidoc_cmd

from common import PathIterator, STATIC_DIR, TEMPLATES_DIR, render_jinja_file, ChangeLog
from files import copy_file
from files import unlink


class BuildMarketplaceDocs:
    def __init__(self, source: str, target: str):
        self.source = Path(source)
        self.target = Path(target)

        self.temp_docs = self.target / "temp_docs"

        # For iterating source directories
        self.source_item_iterator = PathIterator(
            path=self.source, rule=item_path_filter, recursive=False
        )

        # For iterating notebook files
        self.notebook_path_iterator = PathIterator(
            path=self.source, rule=notebook_filter, recursive=True
        )

        # For iterating target directories
        self.target_item_iterator = PathIterator(
            path=self.target, rule=item_path_filter, recursive=False
        )

    def build(self):
        # Document modules from source dir into self.temp_docs, remove temp conf.py, replace with template
        apidoc_command = f"-F -o {self.temp_docs} {self.source}".split(" ")
        print(f"Running sphinx api doc... [{apidoc_command}]")
        sphinx_apidoc_cmd(apidoc_command)
        conf_py_target = str(self.temp_docs / "conf.py")

        unlink(conf_py_target)
        data = asdict(
            SphinxKWArgs(
                sphinx_docs_target=str(self.source),
                project_name="",
                copyright="",
                author="",
            )
        )
        print("Rendering conf.py...")
        render_jinja_file(str(TEMPLATES_DIR / "conf.template"), conf_py_target, data)

        print("Replacing .rst files with available notebooks...")
        for notebook in self.notebook_path_iterator:
            unlink(self.temp_docs / f"{notebook.stem}.rst", ignore_errors=True)
            copy_file(source=notebook, target=(self.temp_docs / notebook.name))

        build_command = f"-b html {self.temp_docs} {self.temp_docs / '_build'}"
        print(f"Running sphinx build... [{build_command}]")
        sphinx_build_cmd(build_command.split(" "))

        change_log = ChangeLog()
        for source_dir in self.source_item_iterator:
            update_or_create_item(source_dir, self.target, self.temp_docs, change_log)

        target_static = self.target / "_static/_static"
        if not target_static.exists():
            copy_file(self.temp_docs / "_build/_static", target_static)

        build_catalog_json(self.target_item_iterator, str(self.target))

        rmtree(str(self.temp_docs))

        # Render index.html
        render_index(self.target_item_iterator, self.target)
        render_pages(self.target_item_iterator, self.target / "_static")

        copy_file(STATIC_DIR / "styles.css", self.target / "_static" / "styles.css")

        with open(self.target / "README.md", "w+") as f:
            compiled_change_log = change_log.compile()
            content = f.read()
            f.seek(0, 0)
            f.write(compiled_change_log)
            f.write(content)


@dataclass
class SphinxKWArgs:
    sphinx_docs_target: str
    project_name: str
    copyright: str
    author: str
    version: str = "latest"
    release: str = "latest"
    repository_url: str = ""
    repository_branch: str = ""
    html_title: str = ""
    html_logo: str = ""
    html_favicon: str = ""


def item_path_filter(directory: Path) -> bool:
    # If file
    if not directory.is_dir():
        return False

    # If private
    if directory.name.startswith(".") or directory.name.startswith("_"):
        return False

    # If can't turn into item
    if not (directory / "function.yaml").exists():
        return False

    return True


def notebook_filter(path: Path) -> bool:
    if path.name.endswith(".ipynb"):
        return True
    return False


def update_html_resource_paths(html_path: Path, relative_path: str):
    if html_path.exists():
        with open(html_path, "r") as html:
            parsed = BeautifulSoup(html.read(), features="html.parser")

        # Update css links
        nodes = parsed.find_all(
            lambda node: node.name == "link" and "_static" in node.get("href", "")
        )
        for node in nodes:
            node["href"] = f"{relative_path}{node['href']}"

        # Update js scripts
        nodes = parsed.find_all(
            lambda node: node.name == "script"
            and node.get("src", "").startswith("_static")
        )
        for node in nodes:
            node["src"] = f"{relative_path}{node['src']}"

        with open(html_path, "w") as new_html:
            new_html.write(str(parsed))


def build_catalog_json(targets: PathIterator, target_path: str):
    catalog_path = Path(target_path) / "catalog.json"
    catalog = json.load(open(catalog_path, "r")) if catalog_path.exists() else {}

    for source_dir in targets:
        item_yaml = source_dir / "item.yaml"
        with open(item_yaml, "r") as yaml_file:
            item = yaml.load(yaml_file)
            if source_dir.name not in catalog:
                catalog[source_dir.name] = item

    json.dump(catalog, open(catalog_path, "w"))


def render_index(target_item_iterator: PathIterator, target_path: str):
    items = []
    for target in target_item_iterator:
        item_path = target / "item.yaml"
        item = yaml.load(open(str(item_path), "r"))
        item["name"] = item["name"].replace("-", " ").replace("_", " ").title()
        items.append(item)

        categories = [
            WebCategory(
                header="filters",
                sub_categories=[
                    WebSubCategory("Official"),
                    WebSubCategory("Third-party functions"),
                ],
            ),
            WebCategory(
                header="category",
                sub_categories=[
                    WebSubCategory("Serving"),
                    WebSubCategory("Dask"),
                    WebSubCategory("Spark"),
                    WebSubCategory("Training"),
                    WebSubCategory("Features"),
                ],
            ),
            WebCategory(
                header="kind",
                sub_categories=[
                    WebSubCategory("Job"),
                    WebSubCategory("Nuclio"),
                    WebSubCategory("Dask"),
                ],
            ),
            WebCategory(
                header="repository",
                sub_categories=[WebSubCategory("MLRun"), WebSubCategory("Storey")],
            ),
        ]

        data = {"items": items, "categories": list(map(asdict, categories))}

        render_jinja_file(
            TEMPLATES_DIR / "index.template",
            str(Path(target_path) / "index.html"),
            data,
        )


@dataclass
class WebSubCategory:
    name: str
    id: str = ""
    checked: str = "checked"

    def __post_init__(self):
        if not self.id:
            self.id = self.name.replace(" ", "-").replace("_", "-").lower()


@dataclass
class WebCategory:
    header: str
    sub_categories: List[WebSubCategory]

    def __post_init__(self):
        if self.header:
            self.header = self.header.upper()


def render_pages(target_item_iterator: PathIterator, target_path: str):
    for target in target_item_iterator:
        item = yaml.load(open(str(target / "item.yaml"), "r"))
        archive = {"current": item["version"], "prev": []}
        for k, _ in item.get("archive", {}).items():
            archive["prev"].append(k)
        render_jinja_file(
            TEMPLATES_DIR / "item.template",
            str(Path(target_path) / f"{item['name']}.html"),
            {"item": item, "archive": archive},
        )


def update_or_create_item(
    source_dir: Path, target: Path, temp_docs: Path, change_log: ChangeLog
):
    # Copy source directories to target directories, if target already has the directory, archive previous version
    source_yaml = yaml.load(open(source_dir / "item.yaml", "r"), Loader=yaml.FullLoader)
    source_version = source_yaml["version"]

    target_dir = target / source_dir.stem
    target_latest = target_dir / "latest"
    target_version = target_dir / source_version

    html_dir = temp_docs / "_build"
    html_file_name = f"{source_dir.stem}.html"
    html_path = html_dir / html_file_name

    update_html_resource_paths(html_path, relative_path="../../_static/")

    # If its the first source is encountered, copy source to target
    if not target_dir.exists():
        copy_file(source_dir, target_latest)
        copy_file(source_dir, target_version)

        copy_file(html_path, target_latest / html_file_name)
        copy_file(html_path, target_version / html_file_name)

        change_log.new_item(source_dir.stem, source_version)

    if target_version.exists() or source_version == target_version:
        return

    rmtree(target_latest)

    copy_file(source_dir, target_latest)
    copy_file(source_dir, target_version)

    copy_file(html_path, target_latest / html_file_name)
    copy_file(html_path, target_version / html_file_name)

    change_log.update_item(source_dir.stem, source_version, target_version.stem)
