import argparse
from pathlib import Path

from build_marketplace_docs import BuildMarketplaceDocs

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="source directory path")
    parser.add_argument("-t", "--target", help="target directory path")
    args = parser.parse_args()

    source = Path(args.source).absolute()
    target = Path(args.target).absolute()

    assert source.exists()
    assert target.exists()

    print(f"Source: {source}")
    print(f"Target: {target}")

    print(f"Starting to build marketplace docs...")
    build = BuildMarketplaceDocs(source=str(source), target=str(target))
    build.build()
