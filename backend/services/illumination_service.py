"""
Lunar Horizon, Solar Illumination & Direct-to-Earth (DTE) Raytracing Service
============================================================================
Physical & Geometric Models:
1. Lunar Spherical Curvature:
   A terrain obstacle at distance r drops below the observer's tangent plane by:
   Delta_z_curv(r) = r^2 / (2 * R_Moon)
   where R_Moon = 1,737,400 meters.

2. Antenna Mast Height:
   The observer's effective elevation is z_obs = z_ground + h_antenna.
   The apparent elevation angle to terrain at distance r and elevation z(r) is:
   tan(alpha) = [z(r) - z_obs - r^2 / (2 * R_Moon)] / r

3. Horizon Obstruction Profile:
   The horizon elevation angle H(theta) along azimuth theta is:
   H(theta) = max_{r} arctan(tan(alpha(r, theta)))

4. Apparent Angular Diameters of Celestial Bodies:
   - Solar angular radius R_Sun ≈ 0.260° (15.6 arcminutes at 1 AU)
   - Earth angular radius R_Earth ≈ 0.900° (54.0 arcminutes viewed from Moon distance)

5. Illumination Conditions:
   - Full Sunlight (100%): el_Sun - R_Sun > H(az_Sun)
   - Penumbra / Partial: |el_Sun - H(az_Sun)| <= R_Sun
     Fraction = (el_Sun - H(az_Sun) + R_Sun) / (2 * R_Sun)
   - Umbra / Total Shadow (0%): el_Sun + R_Sun < H(az_Sun)

6. Direct-to-Earth (DTE) Line of Sight:
   - Line of sight is clear when:
     el_Earth - R_Earth > H(az_Earth) + los_margin_deg
"""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

LUNAR_RADIUS_M = 1737400.0  # 1737.4 km
SOLAR_ANGULAR_RADIUS_DEG = 0.260   # ~15.6 arcminutes
EARTH_ANGULAR_RADIUS_DEG = 0.900   # ~54.0 arcminutes

class IlluminationService:
    """
    Computes terrain horizon profiles, solar illumination, and DTE availability
    accounting for lunar curvature, antenna mast height, and apparent angular sizes.
    """

    @property
    def methodology_metadata(self) -> Dict[str, Any]:
        return {
            "curvature_correction_formula": "Delta_z = r^2 / (2 * R_Moon), with R_Moon = 1737.4 km",
            "solar_angular_radius_deg": SOLAR_ANGULAR_RADIUS_DEG,
            "earth_angular_radius_deg": EARTH_ANGULAR_RADIUS_DEG,
            "celestial_disc_treatment": "Finite disc considered for both Sun (penumbra/umbra) and Earth",
            "antenna_geometry": "Observer vantage point elevated by h_antenna meters above local surface",
            "los_margin_definition": "Additional elevation buffer above terrain horizon required for robust DTE RF link",
            "time_transition_resampling": "Detects horizon crossing intervals when target elevation crosses H(azimuth)"
        }

    @staticmethod
    def compute_apparent_terrain_elevation_angle(
        distance_m: float,
        terrain_elevation_m: float,
        observer_ground_elevation_m: float,
        antenna_height_m: float,
        r_moon_m: float = LUNAR_RADIUS_M
    ) -> float:
        """
        Computes apparent angular elevation (degrees) to a terrain point at distance_m.
        Includes spherical lunar surface curvature drop and observer antenna height.
        """
        if distance_m <= 0.0:
            return -90.0

        z_obs = observer_ground_elevation_m + antenna_height_m
        delta_z_curv = (distance_m * distance_m) / (2.0 * r_moon_m)
        effective_height_diff = terrain_elevation_m - z_obs - delta_z_curv

        tan_alpha = effective_height_diff / distance_m
        return math.degrees(math.atan(tan_alpha))

    @classmethod
    def compute_horizon_elevation_along_ray(
        cls,
        azimuth_deg: float,
        distance_samples_m: List[float],
        elevation_samples_m: List[float],
        observer_ground_elev_m: float,
        antenna_height_m: float
    ) -> float:
        """
        Computes maximum horizon elevation angle H(azimuth) across sampled terrain profile.
        """
        if not distance_samples_m or not elevation_samples_m:
            return 0.0

        max_angle = -90.0
        for dist, elev in zip(distance_samples_m, elevation_samples_m):
            if dist <= 0:
                continue
            angle = cls.compute_apparent_terrain_elevation_angle(
                distance_m=dist,
                terrain_elevation_m=elev,
                observer_ground_elevation_m=observer_ground_elev_m,
                antenna_height_m=antenna_height_m
            )
            if angle > max_angle:
                max_angle = angle

        return max_angle

    @staticmethod
    def evaluate_solar_illumination(
        sun_elevation_deg: float,
        horizon_elevation_deg: float,
        sun_angular_radius_deg: float = SOLAR_ANGULAR_RADIUS_DEG
    ) -> Dict[str, Any]:
        """
        Evaluates solar illumination considering the Sun's apparent disc.
        Returns:
            - illumination_fraction (0.0 to 1.0)
            - state: 'full_sun', 'penumbra', or 'shadow'
        """
        diff = sun_elevation_deg - horizon_elevation_deg

        if diff >= sun_angular_radius_deg:
            return {
                "fraction": 1.0,
                "percentage": 100.0,
                "state": "full_sun"
            }
        elif diff <= -sun_angular_radius_deg:
            return {
                "fraction": 0.0,
                "percentage": 0.0,
                "state": "shadow"
            }
        else:
            # Linear penumbral transition approximation across solar diameter
            fraction = (diff + sun_angular_radius_deg) / (2.0 * sun_angular_radius_deg)
            fraction = max(0.0, min(1.0, fraction))
            return {
                "fraction": round(fraction, 3),
                "percentage": round(fraction * 100.0, 1),
                "state": "penumbra"
            }

    @staticmethod
    def evaluate_dte_communication(
        earth_elevation_deg: float,
        horizon_elevation_deg: float,
        los_margin_deg: float = 0.25,
        earth_angular_radius_deg: float = EARTH_ANGULAR_RADIUS_DEG
    ) -> Dict[str, Any]:
        """
        Evaluates Direct-to-Earth visibility with LOS clearance margin and Earth disc radius.
        """
        threshold = horizon_elevation_deg + los_margin_deg
        diff = earth_elevation_deg - threshold

        if diff >= earth_angular_radius_deg:
            return {
                "is_connected": True,
                "percentage": 100.0,
                "clearance_deg": round(diff, 2),
                "state": "clear_los"
            }
        elif diff <= -earth_angular_radius_deg:
            return {
                "is_connected": False,
                "percentage": 0.0,
                "clearance_deg": round(diff, 2),
                "state": "occluded"
            }
        else:
            fraction = (diff + earth_angular_radius_deg) / (2.0 * earth_angular_radius_deg)
            fraction = max(0.0, min(1.0, fraction))
            return {
                "is_connected": fraction > 0.5,
                "percentage": round(fraction * 100.0, 1),
                "clearance_deg": round(diff, 2),
                "state": "grazing_margin"
            }

    @staticmethod
    def detect_horizon_crossings(elevation_series: List[float], horizon_series: List[float]) -> List[int]:
        """
        Identifies step indices where elevation crosses the horizon angle between consecutive time steps.
        Enables adaptive resampling or flagging rapid lighting transitions.
        """
        crossings = []
        for i in range(len(elevation_series) - 1):
            diff_curr = elevation_series[i] - horizon_series[i]
            diff_next = elevation_series[i + 1] - horizon_series[i + 1]
            if (diff_curr * diff_next) < 0:
                crossings.append(i)
        return crossings
