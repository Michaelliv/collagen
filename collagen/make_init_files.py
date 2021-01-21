from collagen.common import PathIterator, touch


def make_init_files(path_iterator: PathIterator):
    for path in path_iterator:
        touch(path / "__init__.py")
