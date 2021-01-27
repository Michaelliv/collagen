import sys
from pathlib import Path
from typing import List

from collagen.build_marketplace_docs import BuildMarketplaceDocs


def main(argv: List[str]):
    source = Path(argv[0])
    target = Path(argv[1])

    assert source.exists()
    assert target.exists()

    build = BuildMarketplaceDocs(source=str(source), target=str(target))
    build.build()


if __name__ == "__main__":
    main(sys.argv[1:])
