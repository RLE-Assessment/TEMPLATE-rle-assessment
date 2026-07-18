"""Precompute the cached artifacts renders read instead of the national map.

Building these from the full ``ecosystem_source.data`` map peaks at many GB of
RAM, which OOM-kills CI runners. This script runs the heavy work once — on a
machine with enough memory — and writes small artifacts that renders read
cheaply:

  * ``optimized_data`` — an ecosystem-sorted copy of the map with small row
    groups, so filtering to one ecosystem uses parquet predicate pushdown
    (reads only that ecosystem's rows) instead of loading the whole map.
  * ``aoo_grid_cache_url`` — the precomputed national AOO grid.

Only the artifacts whose URLs are configured are written. Re-run whenever
``ecosystem_source.data`` changes; artifacts are overwritten.

Usage:
    pixi run build-caches
    # or: python scripts/build_caches.py [--config PATH]
"""

import argparse
from pathlib import Path

import yaml

CONFIG_PATH = Path("config/country_config.yaml")

# Small row groups let pyarrow prune to a single ecosystem's rows on read.
_ROW_GROUP_SIZE = 10_000


def build_caches(config_path: Path = CONFIG_PATH) -> None:
    """Load ``ecosystem_source.data`` once and write the configured caches."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    source = config["ecosystem_source"]

    # ecosystem_code_column is optional: fall back to the name column so the
    # sort key and grid columns match how crit_b filters ecosystems.
    ecosystem_column = source.get("ecosystem_code_column") or source.get("ecosystem_name_column")
    if ecosystem_column is None:
        raise SystemExit(
            "ecosystem_source needs ecosystem_code_column or ecosystem_name_column "
            f"in {config_path}"
        )

    optimized = source.get("optimized_data")
    cache_url = source.get("aoo_grid_cache_url")
    if not optimized and not cache_url:
        raise SystemExit(
            "Nothing to build: set ecosystem_source.optimized_data and/or "
            f"aoo_grid_cache_url in {config_path}."
        )

    from rle.core import Ecosystems
    from rle.core.aoo import make_aoo_grid

    eco = Ecosystems.from_file(
        source["data"],
        ecosystem_column=ecosystem_column,
        ecosystem_name_column=source.get("ecosystem_name_column"),
        functional_group_column=source.get("functional_group_column"),
    )
    print(f"Loading {source['data']} ...")
    gdf = eco.load()
    print(f"  {len(gdf)} features")

    if optimized:
        print(f"Writing ecosystem-sorted parquet -> {optimized}")
        (
            gdf.sort_values(ecosystem_column)
            .reset_index(drop=True)
            .to_parquet(optimized, row_group_size=_ROW_GROUP_SIZE)
        )

    if cache_url:
        print(f"Computing AOO grid -> {cache_url}")
        aoo = make_aoo_grid(eco).compute()
        print(f"  {aoo.cell_count} grid cells")
        aoo.to_parquet(cache_url)

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=CONFIG_PATH,
        help=f"Path to country_config.yaml (default: {CONFIG_PATH})",
    )
    args = parser.parse_args()
    build_caches(args.config)


if __name__ == "__main__":
    main()
