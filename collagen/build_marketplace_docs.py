import json
from dataclasses import dataclass, asdict
from pathlib import Path
from shutil import rmtree
from typing import List

import yaml
from bs4 import BeautifulSoup

from collagen.common import (
    SPHINX_API_DOC,
    SPHINX_BUILD,
    PathIterator,
    TEMPLATES_DIR,
    STATIC_DIR,
)
from collagen.files import copy_file, unlink
from collagen.git import clone_repository
from collagen.render_jinja import render_jinja_file
from collagen.shell import exec_shell
from collagen.sphinx_build import sphinx_build, SphinxKWArgs


class BuildMarketplaceDocs:
    def __init__(self, source: str, git_repo: str, target: str):
        self.source = Path(source)
        self.git_repo = git_repo
        self.target = Path(target)
        self.temp_docs = self.target / "temp_docs"

    def build(self):
        # For iterating source directories
        source_item_iterator = PathIterator(
            path=self.source, rule=item_path_filter, recursive=False
        )
        source_item_names = set(map(lambda p: p.stem, source_item_iterator))

        # For iterating notebook files
        notebook_path_iterator = PathIterator(
            path=self.source, rule=notebook_filter, recursive=True
        )

        # Clone target repository
        if not self.target.exists():
            clone_repository(
                repository_path=self.git_repo,
                target_path=self.target,
                remove_if_already_exists=True,
            )

        sphinx_build(
            SPHINX_API_DOC,
            str(self.source),
            str(self.temp_docs),
            SphinxKWArgs(
                sphinx_docs_target=str(self.source),
                project_name="",
                copyright="",
                author="",
            ),
        )

        for notebook in notebook_path_iterator:
            unlink(self.temp_docs / f"{notebook.stem}.rst", ignore_errors=True)
            copy_file(source=str(notebook), target=str(self.temp_docs / notebook.name))

        exec_shell(
            f"{SPHINX_BUILD} -b html {self.temp_docs} {self.temp_docs / '_build'}"
        )

        # For iterating target directories
        target_item_iterator = PathIterator(
            path=self.target, rule=item_path_filter, recursive=False
        )

        # Copy source directories to target directories, if target already has the directory, archive previous version
        # and copy latest source to
        for source_dir in source_item_iterator:
            # If its the first source is encountered, copy source to target
            target_dir = self.target / source_dir.stem
            if not target_dir.exists():
                copy_file(source_dir, target_dir)
            else:
                target_yaml = yaml.load(open(target_dir / "item.yaml", "r"))
                target_version = target_yaml["version"]
                source_yaml = yaml.load(open(source_dir / "item.yaml", "r"))
                source_version = source_yaml["version"]
                if source_version == target_version:
                    continue
                # If versions are different, move target to archive, then move source to target
                target_archive_dir = target_dir / "archive" / target_version
                # If latest version already exists in versions directory, something went wrong
                if target_archive_dir.exists():
                    raise RuntimeError(
                        f"Version conflict detected between {target_dir} and it's archive"
                    )
                else:
                    # If latest version doesn't exists
                    target_archive_dir.mkdir(parents=True)

                    # Move archive records from target to source
                    source_yaml["archive"] = target_yaml.pop("archive", None) or {}
                    source_yaml["archive"][target_version] = target_yaml

                    # Update yaml files for source and target
                    with open(target_dir / "item.yaml", "w") as f:
                        yaml.dump(target_yaml, f)

                    with open(source_dir / "item.yaml", "w") as f:
                        yaml.dump(source_yaml, f)

                    # Move target content to "archive" directory
                    for file in target_dir.iterdir():
                        # Make sure css/js is still loaded correctly
                        if file.name != "archive":
                            if file.name.endswith(".html"):
                                update_html_resource_paths(
                                    html_path=file, relative_path="../../_static/"
                                )
                            copy_file(str(file), str(target_archive_dir / file.name))
                            unlink(str(file))

                    # Copy source files to target directory
                    for file in source_dir.iterdir():
                        copy_file(str(file), str(target_dir / file.name))

        # For iterating html files
        html_doc_iterator = PathIterator(
            path=self.temp_docs / "_build", rule=lambda p: p.stem in source_item_names,
        )

        for html in html_doc_iterator:
            update_html_resource_paths(html, relative_path="../_static/")
            copy_file(str(html), str(self.target / html.stem / html.name))

        target_static = self.target / "_static/_static"
        if not target_static.exists():
            copy_file(str(self.temp_docs / "_build/_static"), str(target_static))

        build_catalog_json(target_item_iterator, str(self.target))

        rmtree(str(self.temp_docs))

        # Render index.html
        render_index(target_item_iterator, self.target)
        render_pages(target_item_iterator, self.target / "_static")

        copy_file(STATIC_DIR / "styles.css", self.target / "_static" / "styles.css")


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
