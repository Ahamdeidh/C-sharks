"""
Service layer package for Lunar Landing Site Navigator backend.
Separates responsibilities for:
- JPL Horizons ephemeris retrieval
- NAIF SPICE kernel management and frame transformations
- LOLA Digital Elevation Model (DEM) data loading
- Illumination and Line-of-Sight (LOS) obstruction raytracing
- Simulation orchestration and provenance recording
"""
