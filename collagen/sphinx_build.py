from dataclasses import asdict, dataclass

from collagen.files import unlink
from collagen.common import TEMPLATES_DIR, render_jinja_file, exec_shell


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


def sphinx_build(
    sphinx_api_doc: str,
    sphinx_docs_source: str,
    sphinx_docs_target: str,
    sphinx_kwargs: SphinxKWArgs,
):
    exec_shell(f"{sphinx_api_doc} -F -o {sphinx_docs_target} {sphinx_docs_source}")
    unlink(sphinx_docs_target + "/conf.py")
    conf_py_template = str(TEMPLATES_DIR / "conf.template")
    conf_py_target = sphinx_docs_target + "/conf.py"
    data = asdict(sphinx_kwargs)
    render_jinja_file(conf_py_template, conf_py_target, data)
