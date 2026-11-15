#!/usr/bin/env python3
"""Build the runtime reference catalog from the supplied lunar GIS archives.

Usage:
  python scripts/build_reference_catalog.py --source-root /path/to/Extracted_Archives

This extracts only point attributes, not the large source rasters. It does not
convert the archive products into elevation or mission-time simulation data.
Requires pyshp and rasterio; see backend/requirements.txt.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import rasterio
import shapefile


def build(source_root: Path, output: Path) -> None:
    shp_candidates = list(source_root.rglob("LandingSites.shp"))
    if not shp_candidates:
        raise SystemExit(f"LandingSites.shp not found below {source_root}")
    shp = shp_candidates[0]
    if not shp.with_suffix(".dbf").is_file() or not shp.with_suffix(".prj").is_file():
        raise SystemExit("LandingSites shapefile is incomplete; .dbf and .prj sidecars are required")

    reader = shapefile.Reader(str(shp), encoding="utf-8")
    fields = [field[0] for field in reader.fields[1:]]
    features = []
    for index, record in enumerate(reader.records(), start=1):
        properties = {
            key: (None if value in ("/", "") else value)
            for key, value in zip(fields, record)
        }
        try:
            latitude = float(properties["Latitude"])
            longitude = float(properties["Longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit(f"Invalid geographic coordinates in DBF record {index}: {exc}")
        if not (-90 <= latitude <= 90 and -360 <= longitude <= 360):
            raise SystemExit(f"Out-of-range geographic coordinates in DBF record {index}")
        feature_id = str(properties.get("ID") or index)
        features.append({
            "type": "Feature",
            "id": feature_id,
            "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
            "properties": properties,
        })

    rasters = []
    pattern = re.compile(r"(.+)_MaxConsecDaysOfSun(\+Earth)?_Midsummer(20\d{2})GT\.tif$", re.I)
    for raster_path in sorted(source_root.rglob("*.tif")):
        match = pattern.fullmatch(raster_path.name)
        if not match:
            continue
        with rasterio.open(raster_path) as dataset:
            stats = dataset.statistics(1, approx=True)
            rasters.append({
                "file": raster_path.name,
                "site_area": match.group(1),
                "year": int(match.group(3)),
                "measure": "sun_plus_earth" if match.group(2) else "sun_only",
                "width": dataset.width,
                "height": dataset.height,
                "pixel_size_m": round(abs(dataset.res[0]), 3),
                "dtype": dataset.dtypes[0],
                "crs_wkt": dataset.crs.to_wkt() if dataset.crs else None,
                "bounds_projected_m": [dataset.bounds.left, dataset.bounds.bottom, dataset.bounds.right, dataset.bounds.top],
                "nodata": dataset.nodata,
                "observed_min": stats.min,
                "observed_max": stats.max,
                "observed_mean": round(stats.mean, 4),
            })

    catalog = {
        "title": "Supplied Lunar South Pole Candidate Site Reference Dataset",
        "version": "1.0",
        "source": {
            "description": "Derived from user-supplied PSR_Volatile_Estimates archive; original LandingSites shapefile and sidecars retained outside application.",
            "source_file": "LandingSites.shp + .dbf/.shx/.prj/.cpg",
            "crs_name": "Moon2000_spole (Moon 2000 south-pole stereographic; radius 1,737,400 m)",
            "coordinates_in_api": "GeoJSON Point [longitude_deg, latitude_deg] from Latitude/Longitude DBF attributes; not projected x/y.",
            "limitations": [
                "The source archive does not include complete scientific citations or definitions for every DBF field.",
                "SunDays and SunEarth values are supplied source attributes; they are not simulator-generated results.",
                "The accompanying illumination README defines table values as consecutive illuminated days; raster values count 12-hour increments and require division by two.",
                "These products are not an elevation DEM and do not provide arbitrary-time mission simulations.",
            ],
        },
        "count": len(features),
        "features": features,
        "illumination_raster_products": rasters,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {output}: {len(features)} sites, {len(rasters)} regional raster products")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Root folder of the extracted GIS archives")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "backend/data/reference/lunar_candidate_sites.json")
    args = parser.parse_args()
    build(args.source_root, args.output)


if __name__ == "__main__":
    main()
