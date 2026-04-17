"""Generate per-ecosystem config files from the country ecosystem source.

Reads config/country_config.yaml, loads the ecosystem data, and creates
a scaffold YAML file for each unique ecosystem under
config/ecosystems/{ecosystem_code}/ecosystem.yaml.

Existing files are not overwritten.
"""

import argparse
import shutil
from pathlib import Path

import yaml

CACHE_DIR = Path(".cache")
CONFIG_PATH = Path("config/country_config.yaml")
ECOSYSTEMS_DIR = Path("config/ecosystems")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "max_ecosystems", type=int,
        help="Maximum number of ecosystems to generate config files for",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing ecosystem config files",
    )
    args = parser.parse_args()

    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print(f"  Cleared {CACHE_DIR}/")

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    country_name = config["country_name"]
    source = config["ecosystem_source"]

    print(f"Loading ecosystem data from {source['data']}...")
    from iucn_get_data import open_ecosystem_map

    eco_map = open_ecosystem_map(
        source["data"],
        get_level3_column=source["functional_group_column"],
        get_level456_column=source["ecosystem_code_column"],
    )

    df = eco_map.functional_group_dataframe()

    # df has a MultiIndex of (functional_group_column, ecosystem_code_column)
    fg_col = source["functional_group_column"]
    eco_col = source["ecosystem_code_column"]

    indices = df.index[:args.max_ecosystems]
    print(f"Generating config for {len(indices)} of {len(df)} ecosystems...")

    overwrite = args.overwrite
    if not overwrite and ECOSYSTEMS_DIR.exists() and any(ECOSYSTEMS_DIR.iterdir()):
        response = input(
            f"  Existing config files found in {ECOSYSTEMS_DIR}/. "
            f"Overwrite all? [y/N] "
        )
        if response.lower() != 'y':
            print("  Aborting.")
            return
        overwrite = True

    if overwrite and ECOSYSTEMS_DIR.exists():
        shutil.rmtree(ECOSYSTEMS_DIR)
        print(f"  Cleared {ECOSYSTEMS_DIR}/")

    for (functional_group, ecosystem_code) in indices:
        eco_dir = ECOSYSTEMS_DIR / ecosystem_code
        eco_file = eco_dir / "ecosystem.yaml"

        eco_dir.mkdir(parents=True, exist_ok=True)

        # Extract ecosystem name if available in the row
        row = df.loc[(functional_group, ecosystem_code)]
        eco_name = ""
        for col in ["ECO_NAME", "ecosystem_name", "name"]:
            if col in row.index:
                eco_name = str(row[col])
                break

        scaffold = {
            "ecosystem_name": eco_name,
            "country_name": country_name,
            "authors": ["John Smith", "Jane Smith"],
            "biome": "TODO",
            "functional_group": functional_group,
            "global_classification": ecosystem_code,
            "iucn_status": "TODO",
            "description": "TODO",
            "distribution": "TODO",
            "characteristic_native_biota": "TODO",
            "abiotic_environment": "TODO",
            "key_processes_and_interactions": "TODO",
            "major_threats": "TODO",
            "ecosystem_collapse_definition": "TODO",
            "assessment_summary": "TODO",
            "criteria_status": {
                "A": {"A1": "NE", "A2a": "NE", "A2b": "NE", "A3": "NE"},
                "B": {"B1": "NE", "B2": "NE", "subcriteria": "NE", "B3": "NE"},
                "C": {"C1": "NE", "C2a": "NE", "C2b": "NE", "C3": "NE"},
                "D": {"D1": "NE", "D2a": "NE", "D2b": "NE", "D3": "NE"},
                "E": {"E": "NE"},
            },
            "assessment_outcome": "TODO",
            "year_published": "TODO",
            "date_assessed": "TODO",
            "assessment_credits": {
                "assessed_by": "TODO",
                "reviewed_by": "TODO",
                "contributions_by": "TODO",
            },
            "criterion_a_description": "TODO",
            "criterion_b_description": "TODO",
            "criterion_c_description": "TODO",
            "criterion_d_description": "TODO",
            "criterion_e_description": "TODO",
        }

        with open(eco_file, "w") as f:
            yaml.dump(scaffold, f, default_flow_style=False, sort_keys=False,
                      allow_unicode=True)

        print(f"  Created {eco_file}")

    print(f"\nDone. Ecosystem configs are in {ECOSYSTEMS_DIR}/")


if __name__ == "__main__":
    main()
