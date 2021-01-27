import shutil
from pathlib import Path
from typing import List, Union

from common import PathIterator, file_md5


def unlink(paths: Union[str, List[str], PathIterator], ignore_errors: bool = False):
    if isinstance(paths, str) or isinstance(paths, Path):
        paths = [paths]

    for path in paths:
        path = Path(path)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=ignore_errors)
        else:
            path.unlink(missing_ok=ignore_errors)


def copy_file(
    source: str, target: str, unlink_target: bool = False, ignore_errors: bool = False,
):
    source = Path(source)
    target = Path(target)

    if not source.exists():
        if ignore_errors:
            return
        else:
            raise FileNotFoundError(f"{source} does not exist")

    if target.exists():
        if not unlink_target:
            source_md5 = file_md5(str(source))
            target_md5 = file_md5(str(target))
            if source_md5 == target_md5:
                return
            if not ignore_errors:
                raise RuntimeError(
                    f"{target} already exists, and is not similar to {source}. "
                    "Either set remove_target=True, to remove target before copy or resolve differences."
                )
        else:
            unlink(target)

    try:
        if source.is_file():
            shutil.copy(source, target)
        elif source.is_dir():
            shutil.copytree(source, target)
    except Exception as e:
        if ignore_errors:
            return
        else:
            raise e
