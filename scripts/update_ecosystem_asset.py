"""Update the ecosystem GEE asset ID in country_config.yaml."""

import argparse

import yaml

CONFIG_PATH = "config/country_config.yaml"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "asset_id",
        help="Earth Engine asset ID (e.g. projects/my-project/assets/my-ecosystems)",
    )
    args = parser.parse_args()

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    config["ecosystem_gee_asset"]["id"] = args.asset_id

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Updated {CONFIG_PATH}: ecosystem_gee_asset.id = {args.asset_id}")


if __name__ == "__main__":
    main()
