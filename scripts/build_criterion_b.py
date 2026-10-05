"""Write the computed Criterion B (B1/B2) categories into each ecosystem.yaml.

For every config/ecosystems/{code}/ecosystem.yaml, computes the ecosystem's EOO
and AOO (the same way the assessment pages do) and records the categories met
under the B1 (EOO) and B2 (AOO) spatial thresholds in ``criteria_status.B``. The
summary table on content/3_ecosystem_description.qmd reads these values, so it
can list every ecosystem without loading any spatial data at render time.

B3 and the a-c sub-conditions are left as authored. Files are rewritten only when
a value changes, so re-running is cheap to review (idempotent).

Run after the ecosystem configs exist and whenever ecosystem_source changes, then
commit the updated configs:
    pixi run build-criterion-b
"""

import argparse
from pathlib import Path

import yaml

from _config import ensure_vector_source, load_country_config
from _criteria import with_criterion_b

ECOSYSTEMS_DIR = Path("config/ecosystems")


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()

    from rle.core import Ecosystems

    source = load_country_config()["ecosystem_source"]
    # Mirrors templates/assessment.qmd: prefer the ecosystem-sorted copy so each
    # filter() reads only that ecosystem's rows (parquet predicate pushdown).
    ecosystems = Ecosystems.from_file(
        ensure_vector_source(source.get("optimized_data") or source["data"]),
        ecosystem_column=source.get("ecosystem_code_column") or source.get("ecosystem_name_column"),
        ecosystem_name_column=source.get("ecosystem_name_column"),
        functional_group_column=source.get("functional_group_column"),
    )

    changed = 0
    for eco_file in sorted(ECOSYSTEMS_DIR.glob("*/ecosystem.yaml")):
        with open(eco_file) as f:
            eco = yaml.safe_load(f)
        code = eco["global_classification"]
        ecosystem = ecosystems.filter(code)
        if ecosystem.size() == 0:
            print(f"  WARNING: no spatial data for {code} — skipping")
            continue
        updated = with_criterion_b(eco, eoo_km2=ecosystem.eoo, aoo_cells=ecosystem.aoo)
        b = updated["criteria_status"]["B"]
        if updated == eco:
            print(f"  Unchanged {eco_file} (B1={b['B1']}, B2={b['B2']})")
            continue
        with open(eco_file, "w") as f:
            yaml.dump(updated, f, default_flow_style=False, sort_keys=False,
                      allow_unicode=True)
        changed += 1
        print(f"  Set B1={b['B1']}, B2={b['B2']} in {eco_file}")

    print(f"\nDone. Updated {changed} ecosystem config(s).")


if __name__ == "__main__":
    main()
