# LOLA DEM subset: `LDEM_80S_80MPP_ADJ.TIF`

The bundled GeoTIFF is a **central 601 × 601 raster subset**, not a full 7,600 × 7,600 LOLA tile. Its sidecar (`LDEM_80S_80MPP_ADJ.meta.json`) records product ID `LDEM_80S_80MPP_ADJ`, dataset ID `LRO-L-LOLA-4-GDR-V1.0`, nominal resolution 80 m/pixel, elevation units in metres, and the 1,737.4 km reference sphere. At that nominal spacing, the raster spans approximately **48 × 48 km**.

The sidecar identifies this product-family archive URL: [USGS Astrogeology PDS Geosciences LOLA archive](https://pds-geosciences.wustl.edu/lro/lro-l-lola-4-gdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/). This statement identifies the metadata's source URL, not independent authentication of every processing step or claim about complete-tile coverage.

## Coverage and interpretation

Terrain-derived values are only supported within the actual raster bounds. A requested site outside those bounds is not covered by this DEM; in particular, do not infer that all lunar south-polar sites or distant sites have terrain verification from this small subset. Check application/API coverage behavior before relying on an individual result. The DEM is an input to the prototype, not flight-qualified terrain certification.

The sidecar records the pole pixel at row 300, column 300. Interpret those indices using the raster reader's indexing convention and geotransform; do not substitute full-tile center coordinates.

## Metadata

- Projection label in sidecar: `polar_stereographic_south_lon0`
- Nominal pixel spacing: 80 m
- Sidecar grid dimensions: 601 × 601
- Sidecar pole row/column: 300 / 300
- Elevation units: metres; vertical reference: 1,737.4 km sphere
- Sidecar `is_synthetic`: `false`

No claim is made here that the raster is the full product, that all locations have been independently verified, or that a replacement/full tile is present.

## Subset and anomaly limitations
The delivered TIFF is 601 × 601 pixels, about 48.08 × 48.08 km in projected pixel dimensions at 80 m/px. It is a centered subset, not a complete 7,600 × 7,600 tile; sites outside its pixel footprint are not DEM-backed.

Rows 295–305 near the center column contain valid but varying elevations with high residual variation relative to adjacent columns. The raster has no embedded geotransform, and no original full-tile comparison or processing log is bundled. Available evidence does not establish whether this is a processing artifact or real topography. Leave the TIFF unchanged and flag the area for comparison against the source data rather than repairing or interpolating it.
