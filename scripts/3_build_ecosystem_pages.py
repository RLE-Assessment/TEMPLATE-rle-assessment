"""Generate Quarto pages for each ecosystem from template notebooks.

For each config/ecosystems/*/ecosystem.yaml, creates two pages under
content/3_ecosystem_assessments/{ecosystem_code}/:
  - {ecosystem_code}.qmd         — from templates/assessment.qmd
  - {ecosystem_code}_crit_b.qmd  — from templates/crit_b.qmd

Each generated file is a copy of the template with the ecosystem_code
line replaced. Templates are renderable on their own for development.

Existing files are not overwritten unless --overwrite is passed.
"""

import argparse
import hashlib
import re
import shutil
from pathlib import Path

import yaml

CACHE_DIR = Path(".cache")
CONFIG_DIR = Path("config/ecosystems")
OUTPUT_DIR = Path("content/3_ecosystem_assessments")
TEMPLATE_DIR = Path("templates")
QUARTO_YML = Path("_quarto.yml")

# Pattern matching the ecosystem_code assignment line in templates.
_CODE_PATTERN = re.compile(r"^(ecosystem_code\s*=\s*)['\"].*['\"]", re.MULTILINE)

# Default ecosystem code and name used in templates.
_DEFAULT_CODE = "M1.1.1"
_DEFAULT_NAME = "Null Island Marine Shelf"


def _replace_ecosystem_code(template_text: str, code: str, name: str,
                            config_hash: str | None = None) -> str:
    """Replace the ecosystem_code assignment and heading text in a template.

    When ``config_hash`` is given, it is embedded as a comment on the
    ``ecosystem_code`` line. The generated page is otherwise byte-identical no
    matter what the source ``ecosystem.yaml`` contains, so without this Quarto's
    ``freeze: auto`` cache would serve a stale render after the config is edited.
    Threading the config hash into the page invalidates that cache on any edit.
    """
    replacement = rf"\g<1>'{code}'"
    if config_hash is not None:
        replacement += f"  # source-config sha256: {config_hash}"
    text = _CODE_PATTERN.sub(replacement, template_text)
    text = text.replace(f"{_DEFAULT_NAME} ({_DEFAULT_CODE})", f"{name} ({code})")
    text = text.replace(f"{_DEFAULT_CODE} Criterion B", f"{code} Criterion B")
    return text


def _update_quarto_yml(eco_configs: list[Path]) -> None:
    """Update _quarto.yml to include ecosystem assessment pages.

    Inserts ecosystem pages before 'references.qmd' in the chapters list.
    Removes any previously inserted ecosystem assessment entries first.
    """
    text = QUARTO_YML.read_text()

    # Build per-ecosystem part entries
    new_entries = []
    for eco_path in eco_configs:
        with open(eco_path) as f:
            eco = yaml.safe_load(f)
        code = eco["global_classification"]
        name = eco.get("ecosystem_name", code)
        prefix = f"{OUTPUT_DIR}/{code}/{code}"
        new_entries.append(f'    - part: "{code} - {name}"')
        new_entries.append(f"      chapters:")
        new_entries.append(f"        - {prefix}.qmd")
        new_entries.append(f"        - {prefix}_crit_b.qmd")

    # Remove existing ecosystem assessment blocks
    lines = text.splitlines()
    filtered = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("- part:") and i + 1 < len(lines):
            j = i + 1
            while j < len(lines) and (
                lines[j].strip() in ("chapters:", "contents:")
                or f"{OUTPUT_DIR}/" in lines[j]
            ):
                j += 1
            if j > i + 1:
                i = j
                continue
        if f"{OUTPUT_DIR}/" in lines[i]:
            i += 1
            continue
        filtered.append(lines[i])
        i += 1

    # Insert new entries before references.qmd
    result = []
    for ln in filtered:
        if ln.strip() == "- references.qmd":
            result.extend(new_entries)
        result.append(ln)

    QUARTO_YML.write_text("\n".join(result) + "\n")
    print(f"  Updated {QUARTO_YML}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing .qmd files",
    )
    args = parser.parse_args()

    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print(f"  Cleared {CACHE_DIR}/")

    overwrite = args.overwrite
    if not overwrite and OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        response = input(
            f"  Existing pages found in {OUTPUT_DIR}/. "
            f"Overwrite all? [y/N] "
        )
        if response.lower() != 'y':
            print("  Aborting.")
            return
        overwrite = True

    if overwrite and OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        print(f"  Cleared {OUTPUT_DIR}/")

    # Read templates
    assessment_template = (TEMPLATE_DIR / "assessment.qmd").read_text()
    crit_b_template = (TEMPLATE_DIR / "crit_b.qmd").read_text()

    eco_configs = sorted(CONFIG_DIR.glob("*/ecosystem.yaml"))
    if not eco_configs:
        print(f"No ecosystem configs found in {CONFIG_DIR}/")
        return

    for eco_path in eco_configs:
        with open(eco_path) as f:
            eco = yaml.safe_load(f)
        # Hash the source config so freeze re-executes the assessment page when it
        # is edited. Only the assessment page reads ecosystem.yaml; crit_b derives
        # from the spatial data, so it gets no hash (avoids needless AOO/EOO reruns).
        config_hash = hashlib.sha256(eco_path.read_bytes()).hexdigest()

        code = eco["global_classification"]
        name = eco.get("ecosystem_name", code)
        out_dir = OUTPUT_DIR / code
        out_dir.mkdir(parents=True, exist_ok=True)

        for page_name, template, page_hash in [
            (f"{code}.qmd", assessment_template, config_hash),
            (f"{code}_crit_b.qmd", crit_b_template, None),
        ]:
            page_path = out_dir / page_name
            page_path.write_text(
                _replace_ecosystem_code(template, code, name, page_hash)
            )
            print(f"  Created {page_path}")

    # Update _quarto.yml chapters list
    _update_quarto_yml(eco_configs)

    print(f"\nDone. Pages are in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
