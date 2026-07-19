"""Tests for the ecosystem-cache readiness guard (scripts/check_caches.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from check_caches import evaluate  # noqa: E402

_GB = 1024 ** 3


def test_configured_and_present_passes():
    ok, _ = evaluate(
        configured={"optimized_data": "gs://b/x.parquet"},
        missing=[],
        data_size_bytes=None,
        max_uncached_gb=2.0,
    )
    assert ok


def test_configured_but_missing_fails():
    ok, msg = evaluate(
        configured={"aoo_grid_cache_url": "gs://b/g.parquet"},
        missing=[("aoo_grid_cache_url", "gs://b/g.parquet")],
        data_size_bytes=None,
        max_uncached_gb=2.0,
    )
    assert not ok
    assert "build-caches" in msg


def test_no_caches_large_data_fails():
    ok, msg = evaluate(
        configured={},
        missing=[],
        data_size_bytes=int(11 * _GB),
        max_uncached_gb=2.0,
    )
    assert not ok
    assert "OOM" in msg
    assert "11.0 GB" in msg


def test_no_caches_small_data_passes():
    ok, _ = evaluate(
        configured={},
        missing=[],
        data_size_bytes=50 * 1024 * 1024,  # 50 MB
        max_uncached_gb=2.0,
    )
    assert ok


def test_no_caches_unknown_size_passes():
    ok, _ = evaluate(
        configured={}, missing=[], data_size_bytes=None, max_uncached_gb=2.0
    )
    assert ok


def test_threshold_override_allows_large_data():
    ok, _ = evaluate(
        configured={},
        missing=[],
        data_size_bytes=int(11 * _GB),
        max_uncached_gb=20.0,  # raised above the data size
    )
    assert ok
