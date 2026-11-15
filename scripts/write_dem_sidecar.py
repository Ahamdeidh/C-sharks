#!/usr/bin/env python3
"""Write the <name>.meta.json sidecar required by the terrain-aware engine."""
import argparse
import json
import os


def _read_shape(path: str):
    try:
        import tifffile
        return tifffile.imread(path).shape
    except ImportError:
        from PIL import Image
        import numpy as np
        return np.array(Image.open(path)).shape


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tif")
    ap.add_argument("--product-id", required=True)
    ap.add_argument("--resolution-m", type=float, required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--pole-row", type=float, help="pixel row of the south pole (default: raster centre - VERIFY)")
    ap.add_argument("--pole-col", type=float, help="pixel col of the south pole (default: raster centre - VERIFY)")
    ap.add_argument("--synthetic", action="store_true", help="flag the raster as a synthetic test DEM")
    a = ap.parse_args()
    rows, cols = _read_shape(a.tif)
    meta = {
        "product_id": a.product_id, "resolution_m_per_px": a.resolution_m,
        "pole_row": a.pole_row if a.pole_row is not None else (rows - 1) / 2.0,
        "pole_col": a.pole_col if a.pole_col is not None else (cols - 1) / 2.0,
        "elevation_units": "meters", "vertical_datum": "1737.4 km reference sphere",
        "projection": "polar_stereographic_south_lon0", "source_url": a.source_url,
        "nodata_value": -32768.0, "is_synthetic": a.synthetic,
    }
    out = os.path.splitext(a.tif)[0] + ".meta.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(f"wrote {out}; verify pole_row/pole_col against the product label")


if __name__ == "__main__":
    main()
