"""
USGS ODE & LRO LOLA Digital Elevation Model (DEM) Service
=========================================================
Official Documentation & Data Sources:
- USGS Astrogeology PDS Geosciences Node - Orbital Data Explorer (ODE): https://ode.rsl.wustl.edu/
- NASA LRO LOLA Experiment Overview: https://science.nasa.gov/mission/lro/lola/
- PDS Geosciences LOLA Data Node: https://pds-geosciences.wustl.edu/lro/lro-l-lola-4-gdr-v1/lrolol_1xxx/
- Standard Product: LRO-L-LOLA-4-GDR-V1.0 (LDEM_80S_100M / LDEM_85S_20M)

Projection & Coordinate Reference System:
- Projection: Polar Stereographic
- Center Latitude: -90.0° (Lunar South Pole)
- Center Longitude: 0.0° (Prime Meridian)
- Reference Sphere Radius: 1737.400 km (1,737,400 m)
- Vertical Reference: Elevation in meters relative to 1737.4 km reference sphere
- NoData Value: -32768 (or -3.402822655e+38)
"""

import math
import os
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

LUNAR_RADIUS_M = 1737400.0  # 1737.4 km standard IAU reference sphere

class DemMetadata:
    """Encapsulates verified metadata for a LOLA DEM raster."""
    def __init__(
        self,
        product_id: str,
        resolution_m_per_px: float,
        bounds_lat_min: float,
        bounds_lat_max: float,
        bounds_lon_min: float,
        bounds_lon_max: float,
        crs_name: str = "Polar Stereographic (Moon 2000)",
        vertical_datum: str = "1737.4 km reference sphere",
        elevation_units: str = "meters",
        nodata_value: float = -32768.0,
        is_synthetic: bool = False
    ):
        self.product_id = product_id
        self.resolution_m_per_px = resolution_m_per_px
        self.bounds_lat_min = bounds_lat_min
        self.bounds_lat_max = bounds_lat_max
        self.bounds_lon_min = bounds_lon_min
        self.bounds_lon_max = bounds_lon_max
        self.crs_name = crs_name
        self.vertical_datum = vertical_datum
        self.elevation_units = elevation_units
        self.nodata_value = nodata_value
        self.is_synthetic = is_synthetic

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "resolution_m_per_px": self.resolution_m_per_px,
            "geographic_extent": {
                "lat_min": self.bounds_lat_min,
                "lat_max": self.bounds_lat_max,
                "lon_min": self.bounds_lon_min,
                "lon_max": self.bounds_lon_max
            },
            "coordinate_reference_system": self.crs_name,
            "vertical_datum": self.vertical_datum,
            "elevation_units": self.elevation_units,
            "nodata_value": self.nodata_value,
            "is_synthetic_benchmark": self.is_synthetic
        }


class DemService:
    """
    Manages LOLA Digital Elevation Model inspection, spatial indexing,
    and profile extraction for horizon raytracing.
    """
    def __init__(self, dem_dir: Optional[str] = None):
        if dem_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dem_dir = os.path.join(base_dir, "data", "dem")
        self.dem_dir = dem_dir

    @property
    def official_product_specification(self) -> Dict[str, Any]:
        return {
            "product_name": "LOLA Lunar South Pole Digital Elevation Model",
            "dataset_id": "LRO-L-LOLA-4-GDR-V1.0",
            "standard_tiles": [
                {
                    "product_id": "LDEM_80S_100M",
                    "coverage": "80°S to 90°S",
                    "resolution": "100 meters/pixel (304 pixels/degree at pole)",
                    "projection": "Polar Stereographic (center lat: -90°, center lon: 0°)",
                    "source_pds_url": "https://ode.rsl.wustl.edu/moon/indexProductSearch.aspx"
                },
                {
                    "product_id": "LDEM_85S_20M",
                    "coverage": "85°S to 90°S",
                    "resolution": "20 meters/pixel (1520 pixels/degree at pole)",
                    "projection": "Polar Stereographic (center lat: -90°, center lon: 0°)",
                    "source_pds_url": "https://ode.rsl.wustl.edu/moon/indexProductSearch.aspx"
                }
            ],
            "access_method": "USGS Astrogeology PDS Geosciences Node (ODE REST / direct download)",
            "terms_of_use": "Public domain NASA PDS science data product. Free for public and scientific research.",
            "data_gaps_note": "LOLA laser altimetry coverage is densest at the poles; steep inner crater walls may exhibit interpolation artifacts."
        }

    def check_local_dem_availability(self) -> Dict[str, Any]:
        """Checks whether official LOLA DEM GeoTIFF or IMG files exist on local disk."""
        files = os.listdir(self.dem_dir) if os.path.exists(self.dem_dir) else []
        dem_files = [f for f in files if f.lower().endswith(('.tif', '.tiff', '.img'))]

        return {
            "dem_available": len(dem_files) > 0,
            "dem_files": dem_files,
            "dem_dir": self.dem_dir,
            "status_message": (
                f"Found {len(dem_files)} DEM file(s) in {self.dem_dir}."
                if dem_files
                else "No LOLA DEM files found on disk. Download LDEM_80S_100M.TIF from PDS ODE into backend/data/dem/."
            )
        }

    @staticmethod
    def latlon_to_polar_stereographic(lat_deg: float, lon_deg: float, r_moon: float = LUNAR_RADIUS_M) -> Tuple[float, float]:
        """
        Converts selenographic latitude and longitude to Polar Stereographic planar coordinates (X, Y) in meters.
        Center latitude is -90° (South Pole). Center longitude is 0°.
        """
        lat_rad = math.radians(lat_deg)
        lon_rad = math.radians(lon_deg)

        # Distance from south pole in radians: co-latitude = pi/2 - |lat|
        co_lat = (math.pi / 2.0) - abs(lat_rad)
        r_proj = 2.0 * r_moon * math.tan(co_lat / 2.0)

        x = r_proj * math.sin(lon_rad)
        y = -r_proj * math.cos(lon_rad)

        return x, y

    @staticmethod
    def polar_stereographic_to_latlon(x: float, y: float, r_moon: float = LUNAR_RADIUS_M) -> Tuple[float, float]:
        """Converts Polar Stereographic planar coordinates (X, Y) in meters back to lat/lon in degrees."""
        r_proj = math.sqrt(x * x + y * y)
        if r_proj < 1e-9:
            return -90.0, 0.0

        co_lat = 2.0 * math.atan(r_proj / (2.0 * r_moon))
        lat_rad = -(math.pi / 2.0 - co_lat)
        lon_rad = math.atan2(x, -y)

        lat_deg = math.degrees(lat_rad)
        lon_deg = math.degrees(lon_rad)

        return lat_deg, lon_deg

    @classmethod
    def create_synthetic_benchmark_dem(
        cls,
        grid_size: int = 51,
        resolution_m: float = 100.0,
        center_elev_m: float = 0.0,
        obstacle_distance_m: float = 500.0,
        obstacle_height_m: float = 150.0,
        obstacle_azimuth_deg: float = 0.0
    ) -> Tuple[np.ndarray, DemMetadata]:
        """
        Creates a deterministic small synthetic DEM grid for geometric testing.
        Contains a flat datum at center_elev_m, with a known obstacle barrier
        placed at obstacle_distance_m along obstacle_azimuth_deg.

        NOTE: Explicitly documented as synthetic for unit testing and validation.
        """
        center_idx = grid_size // 2
        raster = np.full((grid_size, grid_size), center_elev_m, dtype=np.float32)

        # Compute obstacle position in grid cells
        obs_x_m = obstacle_distance_m * math.sin(math.radians(obstacle_azimuth_deg))
        obs_y_m = obstacle_distance_m * math.cos(math.radians(obstacle_azimuth_deg))

        obs_col = center_idx + int(round(obs_x_m / resolution_m))
        obs_row = center_idx - int(round(obs_y_m / resolution_m))

        # Place Gaussian obstacle hill
        for r in range(grid_size):
            for c in range(grid_size):
                dist_cells = math.sqrt((r - obs_row) ** 2 + (c - obs_col) ** 2)
                if dist_cells < 4.0:
                    raster[r, c] += obstacle_height_m * math.exp(-0.5 * (dist_cells / 1.5) ** 2)

        metadata = DemMetadata(
            product_id="SYNTHETIC_BENCHMARK_DEM_51x51",
            resolution_m_per_px=resolution_m,
            bounds_lat_min=-90.0,
            bounds_lat_max=-89.0,
            bounds_lon_min=-180.0,
            bounds_lon_max=180.0,
            crs_name="Polar Stereographic Synthetic Test Datum",
            vertical_datum="Local Test Datum (0m)",
            elevation_units="meters",
            nodata_value=-32768.0,
            is_synthetic=True
        )

        return raster, metadata

    @classmethod
    def compute_horizon_profile(
        cls,
        raster: np.ndarray,
        center_row: int,
        center_col: int,
        resolution_m: float,
        antenna_height_m: float = 0.0,
        num_azimuths: int = 72,
        max_radius_m: float = 2500.0,
        r_moon_m: float = LUNAR_RADIUS_M
    ) -> Dict[str, Any]:
        """
        Raytraces radial profiles across the DEM raster to calculate the apparent
        horizon mask H(azimuth) in degrees.
        Includes spherical lunar surface curvature drop: Delta_z = r^2 / (2 * R_Moon)
        and observer antenna mast elevation: z_obs = z_ground + h_antenna.
        """
        rows, cols = raster.shape
        z_ground = float(raster[center_row, center_col])
        z_obs = z_ground + antenna_height_m

        azimuths = np.linspace(0.0, 360.0, num_azimuths, endpoint=False)
        horizon_angles: Dict[float, float] = {}

        # Radii to sample along each ray in steps of resolution_m
        num_radial_steps = max(5, int(max_radius_m / resolution_m))
        radial_distances = np.linspace(resolution_m, max_radius_m, num_radial_steps)

        for az_deg in azimuths:
            az_rad = math.radians(az_deg)
            sin_az = math.sin(az_rad)
            cos_az = math.cos(az_rad)

            max_angle = -90.0

            for dist in radial_distances:
                # Polar stereographic grid coordinates: X is East (sin az), Y is North (cos az)
                delta_col = int(round((dist * sin_az) / resolution_m))
                delta_row = int(round((-dist * cos_az) / resolution_m))

                r = center_row + delta_row
                c = center_col + delta_col

                if 0 <= r < rows and 0 <= c < cols:
                    z_terrain = float(raster[r, c])
                    if z_terrain <= -32000.0:  # Skip NoData
                        continue

                    delta_z_curv = (dist * dist) / (2.0 * r_moon_m)
                    apparent_diff = z_terrain - z_obs - delta_z_curv
                    elev_angle = math.degrees(math.atan2(apparent_diff, dist))

                    if elev_angle > max_angle:
                        max_angle = elev_angle

            horizon_angles[round(float(az_deg), 1)] = round(max_angle, 3)

        return {
            "num_azimuths": num_azimuths,
            "horizon_angles": horizon_angles,
            "min_horizon_deg": min(horizon_angles.values()) if horizon_angles else 0.0,
            "max_horizon_deg": max(horizon_angles.values()) if horizon_angles else 0.0,
            "mean_horizon_deg": round(sum(horizon_angles.values()) / len(horizon_angles), 3) if horizon_angles else 0.0,
            "antenna_height_m": antenna_height_m,
            "z_ground_m": z_ground,
            "z_obs_m": z_obs
        }
