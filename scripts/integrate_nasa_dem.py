#!/usr/bin/env python3
"""
Verifies and integrates LDEM_80S_80MPP_ADJ.TIF (either the full 7600x7600 NASA PDS
raster or a centered South Pole sub-tile) by writing/updating its .meta.json sidecar
and running the geodetic control-point and terrain_aware verification checks.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from services.terrain_engine import load_verified_dem, verify_dem_geodesy_and_control_points
from services.simulation_engine import SimulationEngine


def _read_shape(path: str):
    try:
        import tifffile
        return tifffile.imread(path).shape
    except Exception:
        from PIL import Image
        with Image.open(path) as img:
            return img.size[::-1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "tif",
        nargs="?",
        default=os.path.join(ROOT, "backend", "data", "dem", "LDEM_80S_80MPP_ADJ.TIF"),
        help="Path to LDEM_80S_80MPP_ADJ.TIF",
    )
    args = ap.parse_args()
    if not os.path.isfile(args.tif):
        raise SystemExit(f"File not found: {args.tif}")

    rows, cols = _read_shape(args.tif)
    meta = {
        "product_id": "LDEM_80S_80MPP_ADJ",
        "dataset_id": "LRO-L-LOLA-4-GDR-V1.0",
        "resolution_m_per_px": 80.0,
        "pole_row": (rows - 1) / 2.0,
        "pole_col": (cols - 1) / 2.0,
        "full_grid_dimensions": [rows, cols],
        "auto_center_pole_if_resized": True,
        "elevation_units": "meters",
        "vertical_datum": "1737.4 km reference sphere",
        "projection": "polar_stereographic_south_lon0",
        "source_url": "https://pds-geosciences.wustl.edu/lro/lro-l-lola-4-gdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/",
        "nodata_value": -32768.0,
        "is_synthetic": False,
    }
    meta_path = os.path.splitext(args.tif)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    dem_dir = os.path.dirname(os.path.abspath(args.tif))
    dem, report = load_verified_dem(dem_dir)
    if dem is None:
        raise SystemExit(f"DEM verification failed: {report}")

    geodesy = verify_dem_geodesy_and_control_points(dem)
    sim = SimulationEngine(dem_dir=dem_dir).run(
        "shackleton", -89.9, 0.0, "2026-11-14T12:00:00Z", 2, 6, 6.0, 0.25, False
    )
    print(f"DEM accepted: {report['accepted']} shape={rows}x{cols} valid_fraction={report['candidates'][0]['valid_fraction']}")
    print(f"Geodetic control points passed: {geodesy['all_passed']} ({geodesy['control_points_in_dem_bounds']}/{geodesy['control_points_tested']} in bounds)")
    print(f"Simulation status: {sim['status']} | data_source: {sim['data_source']} | is_demo: {sim['is_demo']}")


if __name__ == "__main__":
    main()
