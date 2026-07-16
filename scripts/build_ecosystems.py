"""Rebuild the generated ecosystem layer before rendering.

`config/ecosystems/` is the source of truth (hand-editable). The assessment pages
under `content/3_ecosystem_assessments/` and the ecosystem chapters in `_quarto.yml`
are DERIVED from it and are rebuilt here so the book config is always consistent
before Quarto reads it.

Behaviour:
  * If `config/ecosystems/` has no scaffolds (e.g. it was deleted) -> scaffold it from
    `ecosystem_source` (script 2). This is the only time the data is loaded.
  * Always regenerate the derived layer from the current `config/ecosystems/`
    (script 3 --overwrite), which rewrites `content/3_ecosystem_assessments/` and the
    `_quarto.yml` chapter list.

Hand edits in `config/ecosystems/*/ecosystem.yaml` are never modified here: script 2
runs only when the directory is empty, and script 3 only touches the derived layer.

Run from the project root (the pixi task working directory).
"""

import subprocess
import sys
from pathlib import Path

ECOSYSTEMS_DIR = Path("config/ecosystems")
SCRIPTS_DIR = Path("scripts")


def _run(*args):
    """Run a build script, exiting cleanly on failure (the child already
    printed its own error) instead of raising a noisy CalledProcessError."""
    try:
        subprocess.run([sys.executable, *args], check=True)
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)


def main():
    have_configs = any(ECOSYSTEMS_DIR.glob("*/ecosystem.yaml"))
    if not have_configs:
        print(f"{ECOSYSTEMS_DIR}/ is empty — scaffolding from ecosystem_source...")
        _run(str(SCRIPTS_DIR / "2_build_ecosystems_config.py"))

    _run(str(SCRIPTS_DIR / "3_build_ecosystem_pages.py"), "--overwrite")


if __name__ == "__main__":
    main()
