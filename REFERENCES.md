# References and provenance

This list distinguishes source material actually identified in the project from unverified provenance. Package versions below are the versions installed in the inspected project environment; `backend/requirements.txt` and `package.json` specify version ranges rather than pinning every version.

## Software libraries

| Component | Observed version | Declared dependency |
|---|---:|---|
| React | 18.3.1 | `^18.2.0` |
| React DOM | 18.3.1 | `^18.2.0` |
| Recharts | 2.15.4 | `^2.12.0` |
| Vite | 7.3.8 | `^7.3.8` |
| Vitest | 5.1.0 | `^5.1.0` |
| `@vitejs/plugin-react` | 5.2.0 | `^5.2.0` |
| `lucide-react` | 0.344.0 | `^0.344.0` |
| Tailwind CSS | 3.4.19 | `^3.4.1` |
| FastAPI | 0.162.0 | `>=0.110,<1` |
| Uvicorn | 0.54.0 | `uvicorn[standard]>=0.27,<1` |
| Pydantic | 2.14.2 | `>=2.6,<3` |
| NumPy | 2.5.4 | `>=1.26,<3` |
| Requests | 2.34.2 | `>=2.31,<3` |
| HTTPX | 0.28.1 | `>=0.27,<1` |
| pytest | 8.4.2 | `>=8,<9` |
| pyshp | 2.3.1 | `==2.3.1` |
| Rasterio | 1.5.2 | `>=1.3,<2` |
| tifffile | 2026.11.12 | `>=2023.7,<2027` |

Frontend versions were read from `package-lock.json`/the installed npm tree; backend versions are observed in the installed Python environment. They are environment observations, not claims that all deployments are locked to these versions.

## Data products and services

- **LRO LOLA DEM product family:** the bundled `LDEM_80S_80MPP_ADJ.TIF` identifies product `LDEM_80S_80MPP_ADJ`, dataset ID `LRO-L-LOLA-4-GDR-V1.0`, 80 m/pixel, and the 1,737.4 km reference sphere in its sidecar metadata. The file in this project is a **601 × 601 central subset**, approximately **48 × 48 km** at the stated nominal pixel spacing—not the full 7,600 × 7,600 product. The metadata records this product-family source URL: [USGS Astrogeology PDS Geosciences LOLA archive](https://pds-geosciences.wustl.edu/lro/lro-l-lola-4-gdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/). Coverage-dependent conclusions apply only inside the raster bounds; distant sites are not represented by this subset.
- **JPL Horizons:** the project describes its recorded Shackleton ephemeris fixture as originating from JPL Horizons, with live queries optional. Service documentation: [JPL Horizons](https://ssd.jpl.nasa.gov/horizons/). The original fixture covers 48 hours at Shackleton. Five additional recorded fixtures were generated for southern polar sites (Nov 14–20, 2026) and are stored separately under `backend/data/fixtures/horizons/`. Each file remains site/time limited and must not be extrapolated.
- **Regional illumination and PSR catalog (`backend/data/reference/lunar_catalog_v2.json`):** the catalog's own `provenance_warning` says “User-supplied archives” and that primary upstream provenance and field definitions are **not verified**. It contains 336 raster records and 141 PSR polygons covering 21 named areas, but the project has no verified evidence here establishing their original producer or NASA authorship. Do not cite or label these files as NASA-authored. Their displayed values should be treated as unverified reference/archive material, not an authoritative source.

## Scientific literature and technical references

Only references explicitly listed in `backend/data/fixtures/external_literature_benchmarks.json` are reproduced here. That fixture groups several sources under some benchmark entries; the DOI links below resolve to the cited paper where available. No additional claims of independent validation are implied by listing them.

1. Rosenburg, M. A., Aharonson, O., Head, J. W., et al. (2011). “Global surface slopes and roughness of the Moon from the Lunar Orbiter Laser Altimeter.” *Journal of Geophysical Research: Planets*, 116, E02001. [DOI: 10.1029/2010JE003716](https://doi.org/10.1029/2010JE003716).
2. Bandfield, J. L., Ghent, R. R., Vasavada, A. R., et al. (2011). “Lunar surface rock abundance and regolith fines temperatures derived from LRO Diviner Radiometer data.” *Journal of Geophysical Research: Planets*, 116, E00H02. [DOI: 10.1029/2011JE003866](https://doi.org/10.1029/2011JE003866).
3. Cintala, M. J., & McBride, K. M. (1995). NASA Technical Memorandum 4680, cited in the benchmark fixture for Surveyor and Apollo boulder morphometry. [NASA NTRS record search](https://ntrs.nasa.gov/search?q=NASA%20TM-4680).
4. Carrier, W. D., Olhoeft, G. R., & Mendell, W. (1991). “Physical Properties of the Lunar Surface.” In *Lunar Sourcebook: A User’s Guide to the Moon*, Chapter 9, pp. 475–567. [Lunar Sourcebook, LPI](https://www.lpi.usra.edu/publications/books/lunar_sourcebook/).
5. Metzger, P. T., Smith, J., & Lane, J. E. (2011). “Phenomenology of soil erosion due to rocket exhaust on the Moon and the Mauna Kea lunar test site.” *Journal of Geophysical Research: Planets*, 116, E06005. [DOI: 10.1029/2010JE003745](https://doi.org/10.1029/2010JE003745).
6. Immer, C., et al. (2011). Apollo 12 / Surveyor III exhaust-scouring analysis, cited by the benchmark fixture. The fixture provides no title, DOI, or direct URL; no more specific bibliographic details are asserted here.
7. NASA Jet Propulsion Laboratory (2022). *DSN Telecommunications Link Design Handbook*, 810-005, Rev. E, Module 104: 34-m BWG Stations. [DSN documentation](https://deepspace.jpl.nasa.gov/dsndocs/810-005/).

## Important interpretation limits

A citation in the benchmark fixture identifies a reference used to parameterize or compare a model; it does not by itself demonstrate that the model is flight-qualified, that an input is measured at each target site, or that the archive catalog is verified. In particular, project documentation should not present the catalog as NASA-authored absent independent provenance evidence.
