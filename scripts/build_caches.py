"""Precompute the cached artifacts renders read instead of the national map.

Building these from the full ``ecosystem_source.data`` map peaks at many GB of
RAM, which OOM-kills CI runners. This script runs the heavy work once — on a
machine with enough memory — and writes small artifacts that renders read
cheaply:

  * ``optimized_data`` — an ecosystem-sorted copy of the map with small row
    groups, so filtering to one ecosystem uses parquet predicate pushdown
    (reads only that ecosystem's rows) instead of loading the whole map.
  * ``aoo_grid_cache_url`` — the precomputed national AOO grid.

When neither URL is configured, the destinations are derived from the GCP
project + the data filename (bucket ``{project}-rle-cogs``, keys
``cache/{data-stem}_sorted.parquet`` / ``cache/{data-stem}_aoo_grid.parquet``)
and recorded back into the config — the same project/data-keyed scheme
``rasterize_ecosystem_to_cog.py`` uses for the COG, so changing
``ecosystem_source.data`` points at fresh paths automatically. Explicitly
configured URLs are respected (only those are built).

Usage:
    pixi run build-caches --project my-gcp-project
    # or set GOOGLE_CLOUD_PROJECT; or pre-set optimized_data/aoo_grid_cache_url.
"""

import argparse
import os
import sys
from pathlib import Path

import yaml

from _config import ensure_vector_source

CONFIG_PATH = Path("config/country_config.yaml")

# Small row groups let pyarrow prune to a single ecosystem's rows on read.
_ROW_GROUP_SIZE = 10_000
_PLACEHOLDER_PROJECT = "goog-rle-assessments"


def _bucket_name(project: str) -> str:
    """Derive the cache bucket name from the GCP project ID."""
    return f"{project}-rle-cogs"


def _data_stem(data: str) -> str:
    """Filename stem of ``data`` (query string / trailing slash stripped)."""
    return Path(str(data).split("?")[0].rstrip("/")).stem or "ecosystems"


def derive_cache_urls(project: str, data: str) -> dict:
    """gs:// URLs for the sorted parquet + AOO grid, keyed by project + data."""
    bucket = _bucket_name(project)
    stem = _data_stem(data)
    return {
        "optimized_data": f"gs://{bucket}/cache/{stem}_sorted.parquet",
        "aoo_grid_cache_url": f"gs://{bucket}/cache/{stem}_aoo_grid.parquet",
    }


def _require_project(project) -> str:
    """Return a usable project id, or exit with an actionable message."""
    if not project:
        sys.exit(
            "Set --project or GOOGLE_CLOUD_PROJECT so build-caches can derive the "
            "cache URLs (bucket {project}-rle-cogs), or pre-set "
            "ecosystem_source.optimized_data / aoo_grid_cache_url in the config."
        )
    if project == _PLACEHOLDER_PROJECT:
        sys.exit(
            f"'{_PLACEHOLDER_PROJECT}' is the template's placeholder project. "
            "Pass --project <your-gcp-project> (or set GOOGLE_CLOUD_PROJECT)."
        )
    return project


def record_urls_in_config(config_path: Path, updates: dict) -> None:
    """Insert ``updates`` keys under ``ecosystem_source:`` in the YAML file.

    A targeted line insertion (rather than a full ``yaml.dump``) so the rest of
    the file — comments, ordering, formatting — is preserved.
    """
    lines = config_path.read_text().splitlines(keepends=True)
    start = next(
        (i for i, ln in enumerate(lines)
         if not ln[:1].isspace() and ln.lstrip().startswith("ecosystem_source:")),
        None,
    )
    if start is None:
        raise SystemExit(f"No ecosystem_source: block in {config_path}")

    end = len(lines)
    for i in range(start + 1, len(lines)):
        ln = lines[i]
        if ln.strip() and not ln[:1].isspace():  # next top-level key ends the block
            end = i
            break
    if end > 0 and not lines[end - 1].endswith("\n"):
        lines[end - 1] += "\n"

    lines[end:end] = [f"  {k}: {v}\n" for k, v in updates.items()]
    config_path.write_text("".join(lines))


def build_caches(config_path: Path = CONFIG_PATH, project=None) -> None:
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

    data = ensure_vector_source(source["data"])

    # Destinations: respect explicitly-configured URLs; otherwise (neither set)
    # derive both from the project + data and record them back into the config.
    optimized = source.get("optimized_data")
    cache_url = source.get("aoo_grid_cache_url")
    derived: dict = {}
    if not optimized and not cache_url:
        derived = derive_cache_urls(_require_project(project), data)
        optimized = derived["optimized_data"]
        cache_url = derived["aoo_grid_cache_url"]

    from rle.core import Ecosystems
    from rle.core.aoo import make_aoo_grid

    eco = Ecosystems.from_file(
        data,
        ecosystem_column=ecosystem_column,
        ecosystem_name_column=source.get("ecosystem_name_column"),
        functional_group_column=source.get("functional_group_column"),
    )
    print(f"Loading {data} ...")
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

    if derived:
        record_urls_in_config(config_path, derived)
        print(f"Recorded {', '.join(derived)} in {config_path}")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=CONFIG_PATH,
        help=f"Path to country_config.yaml (default: {CONFIG_PATH})",
    )
    parser.add_argument(
        "--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="GCP project ID used to derive cache URLs when they are not "
             "configured (default: $GOOGLE_CLOUD_PROJECT).",
    )
    args = parser.parse_args()
    build_caches(args.config, args.project)


if __name__ == "__main__":
    main()
