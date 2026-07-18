"""Shared helpers for reading and validating config/country_config.yaml.

Kept dependency-light (stdlib + PyYAML) so it can be imported from the build
scripts and from the rendered Quarto templates alike.
"""

from pathlib import Path

import yaml

CONFIG_PATH = Path("config/country_config.yaml")

# Raster (COG) extensions that must NOT appear in ecosystem_source.data.
_RASTER_SUFFIXES = (".tif", ".tiff")


def load_country_config(path=CONFIG_PATH):
    """Parse the country config YAML."""
    with open(path) as f:
        return yaml.safe_load(f)


def ensure_vector_source(data):
    """Fail fast when ``ecosystem_source.data`` is a raster instead of a vector.

    The scripts and templates read ``ecosystem_source.data`` with geopandas,
    which only understands vector formats (.parquet, .geojson, .gpkg,
    shapefile, GeoDatabase). A raster COG (.tif/.tiff) otherwise raises a
    cryptic pyogrio "not recognized as being in a supported file format" error
    deep in GDAL. Catch it here with an actionable message. Raster COGs belong
    under ``ecosystem_raster.cog_url``.

    Returns ``data`` unchanged so callers can wrap the value inline.
    """
    stem = str(data).split("?")[0].rstrip("/").lower()  # strip ?query and trailing /
    if stem.endswith(_RASTER_SUFFIXES):
        raise SystemExit(
            f"ecosystem_source.data points at a raster file:\n  {data}\n\n"
            "It must be a VECTOR source (.parquet, .geojson, .gpkg, shapefile, "
            "or GeoDatabase) that geopandas can read.\n"
            "Raster COGs (.tif/.tiff) belong under ecosystem_raster.cog_url in "
            "config/country_config.yaml."
        )
    return data
