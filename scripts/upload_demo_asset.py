"""Upload the Null Island demo ecosystem FeatureCollection to Earth Engine."""

import argparse
import os
import time

import ee
import google.auth


def upload_demo_asset(project: str) -> None:
    """Upload a 2-feature demo FeatureCollection (land + water) at Null Island."""
    asset_id = f"projects/{project}/assets/demo/null_island_ecosystems"

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/earthengine"],
    )
    ee.Initialize(credentials=credentials, project=project)

    # Skip if already exists
    try:
        ee.data.getAsset(asset_id)
        print(f"Asset already exists: {asset_id}")
        return
    except ee.EEException:
        pass

    # Create demo/ folder
    folder_id = f"projects/{project}/assets/demo"
    try:
        ee.data.createAsset({"type": "FOLDER"}, folder_id)
    except ee.EEException:
        pass  # folder exists

    # Two ecosystem classes at Null Island (0°N, 0°E)
    land = ee.Feature(
        ee.Geometry.Polygon([[
            [-0.005, -0.005], [0.0, -0.005],
            [0.0, 0.005], [-0.005, 0.005],
        ]]),
        {
            "EFG1": "T1.1",
            "Glob_Typol": "T1.1_NullIsland_forest_D01",
            "ECO_NAME": "Null Island Tropical Forest",
            "COD": "D01",
        },
    )
    water = ee.Feature(
        ee.Geometry.Polygon([[
            [0.0, -0.005], [0.005, -0.005],
            [0.005, 0.005], [0.0, 0.005],
        ]]),
        {
            "EFG1": "M1.1",
            "Glob_Typol": "M1.1_NullIsland_marine_shelf_D02",
            "ECO_NAME": "Null Island Marine Shelf",
            "COD": "D02",
        },
    )
    fc = ee.FeatureCollection([land, water])

    task = ee.batch.Export.table.toAsset(
        collection=fc,
        description="null_island_ecosystems",
        assetId=asset_id,
    )
    task.start()
    print("Uploading demo asset…")

    while task.active():
        time.sleep(2)

    status = task.status()
    if status["state"] == "COMPLETED":
        print(f"Done: {asset_id}")
    else:
        print(f"Failed: {status.get('error_message', 'unknown error')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="GCP project ID (default: $GOOGLE_CLOUD_PROJECT)",
    )
    args = parser.parse_args()
    if not args.project:
        parser.error("Provide --project or set GOOGLE_CLOUD_PROJECT")
    upload_demo_asset(args.project)
