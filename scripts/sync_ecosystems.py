"""Keep config/ecosystems/ in sync with ecosystem_source in country_config.yaml.

The per-ecosystem configs under config/ecosystems/ (and the assessment pages under
content/3_ecosystem_assessments/) are generated from country_config.yaml's
`ecosystem_source` by scripts 2 and 3. This script records the `ecosystem_source`
that produced them in config/ecosystems/.source.yaml and, on every render, checks
whether it still matches.

Behaviour:
  * In sync  -> no-op (no dataset download, no writes).
  * Out of sync with generated content still present -> print an actionable error
    and exit 1. It never deletes anything, because config/ecosystems/*/ecosystem.yaml
    may contain manual edits. The user commits + deletes, then re-runs.
  * Out of sync with no generated content (dirs already cleared) -> regenerate via
    scripts 2 and 3, then record the new provenance.

Run from the project root (the pixi task working directory).
"""

import subprocess
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path("config/country_config.yaml")
ECOSYSTEMS_DIR = Path("config/ecosystems")
PAGES_DIR = Path("content/3_ecosystem_assessments")
MANIFEST_PATH = ECOSYSTEMS_DIR / ".source.yaml"
SCRIPTS_DIR = Path("scripts")


def current_source():
    """The ecosystem_source mapping currently declared in country_config.yaml."""
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    return config.get("ecosystem_source")


def recorded_source():
    """The ecosystem_source that produced the current config/ecosystems/, or None."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            return yaml.safe_load(f)
    return None


def has_generated_content():
    """True if any generated ecosystem config or assessment page exists."""
    return (
        any(ECOSYSTEMS_DIR.glob("*/ecosystem.yaml"))
        or any(PAGES_DIR.glob("*/*.qmd"))
    )


def regenerate(source):
    """Run scripts 2 and 3 (into a cleared location) and record provenance."""
    print("Regenerating config/ecosystems/ from ecosystem_source...")
    # No --overwrite: the dirs are absent/empty, so scripts 2 and 3 neither prompt
    # nor run shutil.rmtree. This keeps the automated path strictly non-destructive.
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "2_build_ecosystems_config.py")],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "3_build_ecosystem_pages.py")],
        check=True,
    )
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        yaml.safe_dump(source, f, sort_keys=False, allow_unicode=True)
    print(f"Recorded provenance in {MANIFEST_PATH}")


def out_of_sync_error(recorded, current):
    """Print actionable guidance and exit non-zero. Deletes nothing."""
    recorded_data = recorded.get("data") if recorded else "none"
    current_data = current.get("data") if current else "none"
    print(
        f"\nERROR: {ECOSYSTEMS_DIR}/ is out of sync with ecosystem_source in "
        f"{CONFIG_PATH}.\n"
        f"    recorded source: {recorded_data}\n"
        f"    current source:  {current_data}\n\n"
        f"{ECOSYSTEMS_DIR}/*/ecosystem.yaml holds your hand-written assessment content;\n"
        "it will NOT be deleted automatically. Regenerating would re-scaffold it from the\n"
        f"new source. ({PAGES_DIR}/ is auto-generated from those files and is safe to\n"
        "regenerate.) To regenerate against the current ecosystem_source:\n\n"
        "  1. Commit so your assessment edits are preserved and recoverable in version\n"
        "     control:\n"
        f"       git add {ECOSYSTEMS_DIR} {PAGES_DIR} && git commit -m \"Save ecosystem assessments\"\n"
        "  2. Delete the generated directories:\n"
        f"       rm -rf {ECOSYSTEMS_DIR} {PAGES_DIR}\n"
        "  3. Re-run the render (pixi run quarto-render / pixi run preview) to regenerate\n"
        "     scaffolds from the current ecosystem_source, then restore any still-relevant\n"
        "     assessment text from the commit in step 1.\n",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    source = current_source()
    if source is None:
        print(f"No ecosystem_source in {CONFIG_PATH}; skipping ecosystem sync.")
        return

    recorded = recorded_source()
    if recorded == source:
        print(f"{ECOSYSTEMS_DIR}/ is in sync with ecosystem_source.")
        return

    if has_generated_content():
        out_of_sync_error(recorded, source)

    regenerate(source)


if __name__ == "__main__":
    main()
