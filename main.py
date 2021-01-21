from pathlib import Path

from collagen.build_marketplace_docs import BuildMarketplaceDocs

if __name__ == "__main__":
    build = BuildMarketplaceDocs(
        source="/home/michaell/marketplace_demo/functions",
        git_repo="https://github.com/Michaelliv/marketplace-docs.git",
        target="/home/michaell/marketplace_demo/marketplace-docs",
    )
    build.build()
