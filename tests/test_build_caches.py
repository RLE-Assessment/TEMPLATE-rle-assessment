"""Tests for build_caches URL derivation and comment-preserving config write-back."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_caches as bc  # noqa: E402


def test_derive_cache_urls_is_project_and_data_keyed():
    urls = bc.derive_cache_urls("myproj", "https://h/ECOSISTEMAS_MEC_122024.parquet")
    assert urls["optimized_data"] == (
        "gs://myproj-rle-cogs/cache/ECOSISTEMAS_MEC_122024_sorted.parquet"
    )
    assert urls["aoo_grid_cache_url"] == (
        "gs://myproj-rle-cogs/cache/ECOSISTEMAS_MEC_122024_aoo_grid.parquet"
    )


def test_data_stem_strips_query_and_trailing_slash():
    assert bc._data_stem("https://h/map.parquet?token=abc") == "map"
    assert bc._data_stem("gs://b/dir/map.parquet/") == "map"


def test_require_project_rejects_missing_and_placeholder():
    with pytest.raises(SystemExit):
        bc._require_project(None)
    with pytest.raises(SystemExit):
        bc._require_project("goog-rle-assessments")
    assert bc._require_project("real-proj") == "real-proj"


def test_record_urls_inserts_under_ecosystem_source_preserving_comments(tmp_path):
    cfg = tmp_path / "country_config.yaml"
    cfg.write_text(
        "country_name: Ruritania\n"
        "ecosystem_source:\n"
        "  # keep this comment\n"
        "  data: https://h/map.parquet\n"
        "  ecosystem_name_column: ecos_general\n"
        "view_state:\n"
        "  zoom: 10\n"
    )
    bc.record_urls_in_config(
        cfg,
        {"optimized_data": "gs://b/cache/map_sorted.parquet",
         "aoo_grid_cache_url": "gs://b/cache/map_aoo_grid.parquet"},
    )
    text = cfg.read_text()
    assert "  # keep this comment" in text            # comment preserved
    lines = text.splitlines()
    es = lines.index("ecosystem_source:")
    vs = lines.index("view_state:")
    inserted = [i for i, ln in enumerate(lines) if "optimized_data:" in ln][0]
    assert es < inserted < vs                          # inserted inside the block
    assert "  optimized_data: gs://b/cache/map_sorted.parquet" in lines
    assert "  aoo_grid_cache_url: gs://b/cache/map_aoo_grid.parquet" in lines


def test_record_urls_when_ecosystem_source_is_last_block(tmp_path):
    cfg = tmp_path / "country_config.yaml"
    cfg.write_text(
        "country_name: Ruritania\n"
        "ecosystem_source:\n"
        "  data: https://h/map.parquet\n"
        "  ecosystem_name_column: ecos_general\n"
    )
    bc.record_urls_in_config(cfg, {"optimized_data": "gs://b/cache/map_sorted.parquet"})
    lines = cfg.read_text().splitlines()
    assert lines[-1] == "  optimized_data: gs://b/cache/map_sorted.parquet"
