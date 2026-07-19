"""Fail fast when the ecosystem caches a render depends on are missing/insufficient.

Rendering ``crit_b`` recomputes the national AOO grid in memory, which OOM-kills CI
runners for large (e.g. national) ecosystem maps. The fix is to precompute caches
offline (``pixi run build-caches``) and point ``optimized_data`` /
``aoo_grid_cache_url`` at them. This guard runs in the deploy *before* the
expensive render and fails with an actionable message when:

  * a configured cache (``optimized_data`` / ``aoo_grid_cache_url``) does not exist
    at its URL — it was never built, or ``ecosystem_source.data`` changed and the
    caches were not rebuilt; or
  * no caches are configured but ``ecosystem_source.data`` is large enough that the
    render will likely OOM (default threshold 2 GB; override with
    ``CHECK_CACHES_MAX_UNCACHED_GB``).

It intentionally does NOT build the caches in CI — that is the very memory-heavy
work the caches exist to move offline. It only reads HTTP HEAD metadata (the cache
and data buckets are public), so it needs no GCP credentials.
"""

import os
import sys
import urllib.request
from urllib.error import HTTPError, URLError

from _config import load_country_config

DEFAULT_MAX_UNCACHED_GB = 2.0
_CACHE_KEYS = ("optimized_data", "aoo_grid_cache_url")


def _to_http(url: str) -> str:
    """Map a ``gs://`` URI to its public https URL; pass http(s) through."""
    if url.startswith("gs://"):
        return "https://storage.googleapis.com/" + url[len("gs://"):]
    return url


def _head(url: str):
    """Return the HEAD response for ``url``, or None on error."""
    req = urllib.request.Request(_to_http(url), method="HEAD")
    try:
        return urllib.request.urlopen(req, timeout=30)
    except (HTTPError, URLError, ValueError):
        return None


def remote_exists(url: str) -> bool:
    resp = _head(url)
    return resp is not None and 200 <= resp.status < 300


def remote_size(url: str):
    """Content-Length in bytes, or None if unknown."""
    resp = _head(url)
    if resp is None:
        return None
    cl = resp.headers.get("Content-Length")
    return int(cl) if cl and cl.isdigit() else None


def evaluate(*, configured, missing, data_size_bytes, max_uncached_gb):
    """Pure decision. Returns ``(ok: bool, message: str)``.

    ``configured`` is the {key: url} of cache URLs that are set; ``missing`` is the
    subset [(key, url), ...] that do not exist; ``data_size_bytes`` is the size of
    ``ecosystem_source.data`` (only consulted when no caches are configured).
    """
    if configured:
        if missing:
            lines = "\n".join(f"  - {name}: {url}" for name, url in missing)
            return False, (
                "Ecosystem cache(s) referenced in config/country_config.yaml do not "
                "exist (never built, or ecosystem_source.data changed and they were "
                f"not rebuilt):\n{lines}\n\n"
                "Run `pixi run build-caches` on a machine with enough RAM, then re-deploy."
            )
        return True, "All configured ecosystem caches are present."

    if data_size_bytes is not None and data_size_bytes >= max_uncached_gb * 1024 ** 3:
        gb = data_size_bytes / 1024 ** 3
        return False, (
            f"ecosystem_source.data is {gb:.1f} GB and no caches are configured "
            "(optimized_data / aoo_grid_cache_url). The render loads/recomputes the "
            "whole map in memory and will likely OOM the CI runner.\n\n"
            "Configure optimized_data + aoo_grid_cache_url and run "
            "`pixi run build-caches` on a big-RAM machine, then re-deploy.\n"
            f"(To override this guard, set CHECK_CACHES_MAX_UNCACHED_GB above {gb:.1f}.)"
        )
    return True, "Ecosystem data is small enough to render without caches."


def main() -> None:
    config = load_country_config()
    source = config["ecosystem_source"]

    configured = {k: source[k] for k in _CACHE_KEYS if source.get(k)}
    missing = [(k, url) for k, url in configured.items() if not remote_exists(url)]

    data_size_bytes = None if configured else remote_size(source["data"])

    max_uncached_gb = float(
        os.environ.get("CHECK_CACHES_MAX_UNCACHED_GB", DEFAULT_MAX_UNCACHED_GB)
    )
    ok, message = evaluate(
        configured=configured,
        missing=missing,
        data_size_bytes=data_size_bytes,
        max_uncached_gb=max_uncached_gb,
    )
    if ok:
        print(f"check-caches: {message}")
    else:
        sys.exit(f"check-caches: {message}")


if __name__ == "__main__":
    main()
