"""
NAIF SPICE Toolkit & Reference Frame Transformation Service
============================================================
Official Documentation & Kernel Sources:
- NAIF SPICE Toolkit: https://naif.jpl.nasa.gov/naif/toolkit.html
- NAIF SPICE Kernels Repository: https://naif.jpl.nasa.gov/naif/data.html
- NASA LRO Lunar SPICE Kernels Dataset: https://data.nasa.gov/dataset/lro-lunar-spice-kernels-v1-0-171aa
- Lunar Coordinate Systems & Frames: https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/planets/moon_080317.tf

Reference Frames & Transformation Chain:
1. ICRF (International Celestial Reference Frame) - Inertial
2. MOON_ME (Mean Earth / Polar Axis) - Lunar Body-Fixed (IAU/IAG standard selenographic system)
3. MOON_PA (Principal Axes) - Lunar dynamic frame derived from lunar laser ranging (LLR)
4. Topocentric ENU (East, North, Up) - Local tangent plane at observer location (lat, lon, elev)
   - Up (+Z_topo): Outward surface normal (Zenith direction)
   - North (+Y_topo): Points toward Lunar North Pole along local meridian
   - East (+X_topo): Points Eastward along local parallel of latitude
"""

import math
import os
from typing import Dict, List, Optional, Tuple, Any

class SpiceKernelStatus:
    """Records required SPICE kernels and checks local file availability."""
    REQUIRED_KERNELS = [
        {
            "name": "naif0012.tls",
            "type": "LSK (Leapseconds Kernel)",
            "role": "Converts UTC time strings to Ephemeris Time (ET / TDB seconds past J2000).",
            "source_url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls"
        },
        {
            "name": "pck00010.tpc",
            "type": "PCK (Text Planetary Constants Kernel)",
            "role": "Defines IAU physical constants, triaxial ellipsoidal radiuses, and base orientation.",
            "source_url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00010.tpc"
        },
        {
            "name": "moon_pa_de421_1900-2050.bpc",
            "type": "PCK (Binary High-Precision Lunar Orientation)",
            "role": "Provides sub-meter accurate orientation for MOON_PA and MOON_ME reference frames.",
            "source_url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc"
        },
        {
            "name": "de430.bsp",
            "type": "SPK (Solar System Ephemeris)",
            "role": "Planetary, Sun, and Earth barycentric ephemeris state vectors in ICRF.",
            "source_url": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de430.bsp"
        }
    ]

    def __init__(self, kernels_dir: Optional[str] = None):
        if kernels_dir is None:
            # Default to backend/data/kernels
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            kernels_dir = os.path.join(base_dir, "data", "kernels")
        self.kernels_dir = kernels_dir

    def evaluate_kernel_coverage(self) -> Dict[str, Any]:
        """Checks which required kernels are present on disk."""
        available_files = set(os.listdir(self.kernels_dir)) if os.path.exists(self.kernels_dir) else set()

        kernel_states = []
        all_available = True

        for k in self.REQUIRED_KERNELS:
            is_present = k["name"] in available_files
            if not is_present:
                all_available = False
            kernel_states.append({
                "name": k["name"],
                "type": k["type"],
                "role": k["role"],
                "source_url": k["source_url"],
                "available_locally": is_present,
                "local_path": os.path.join(self.kernels_dir, k["name"]) if is_present else None
            })

        return {
            "all_kernels_available": all_available,
            "kernels_dir": self.kernels_dir,
            "kernel_inventory": kernel_states,
            "status_message": (
                "All required SPICE kernels are present."
                if all_available
                else "SPICE kernels missing on disk. Download required kernels from NAIF repository into backend/data/kernels/ to activate SPICE engine."
            )
        }


class LocalFrameTransform:
    """
    Mathematical transformation from Lunar Body-Fixed frame (MOON_ME)
    into local Topocentric Horizon frame (East-North-Up / ENU).
    """

    @staticmethod
    def body_fixed_to_topocentric_basis(lat_deg: float, lon_deg: float) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]:
        """
        Calculates local Topocentric ENU basis unit vectors in the body-fixed frame.
        lat_deg: Selenographic latitude in degrees [-90, +90]
        lon_deg: Selenographic longitude in degrees [-180, +360]

        Returns:
            (u_E, u_N, u_U): Three orthogonal unit vectors in MOON_ME coordinates
        """
        phi = math.radians(lat_deg)
        lam = math.radians(lon_deg)

        cos_phi = math.cos(phi)
        sin_phi = math.sin(phi)
        cos_lam = math.cos(lam)
        sin_lam = math.sin(lam)

        # Up (Zenith) unit vector: normal to the sphere
        u_U = (cos_phi * cos_lam, cos_phi * sin_lam, sin_phi)

        # North unit vector: direction of increasing latitude
        u_N = (-sin_phi * cos_lam, -sin_phi * sin_lam, cos_phi)

        # East unit vector: direction of increasing longitude
        u_E = (-sin_lam, cos_lam, 0.0)

        # At the exact poles (phi = +/- 90°), North and East become singular;
        # convention defines 0° meridian as North reference direction.
        if abs(lat_deg + 90.0) < 1e-6:
            # South Pole: Zenith is (0, 0, -1).
            # Looking down at South Pole, North points toward prime meridian (+X)
            u_U = (0.0, 0.0, -1.0)
            u_N = (1.0, 0.0, 0.0)
            u_E = (0.0, 1.0, 0.0)
        elif abs(lat_deg - 90.0) < 1e-6:
            # North Pole: Zenith is (0, 0, +1).
            u_U = (0.0, 0.0, 1.0)
            u_N = (-1.0, 0.0, 0.0)
            u_E = (0.0, 1.0, 0.0)

        return u_E, u_N, u_U

    @classmethod
    def vector_to_azimuth_elevation(
        cls,
        vector_body_fixed: Tuple[float, float, float],
        lat_deg: float,
        lon_deg: float
    ) -> Tuple[float, float]:
        """
        Transforms a 3D target vector in the Lunar Body-Fixed frame into
        local Topocentric Azimuth (degrees from North clockwise) and Elevation (degrees above horizon).

        vector_body_fixed: (x, y, z) vector in body-fixed frame (e.g. MOON_ME)
        Returns:
            (azimuth_deg, elevation_deg)
            azimuth_deg in [0, 360), elevation_deg in [-90, +90]
        """
        vx, vy, vz = vector_body_fixed
        norm = math.sqrt(vx * vx + vy * vy + vz * vz)
        if norm < 1e-9:
            raise ValueError("Target vector has near-zero magnitude; cannot derive direction.")

        u_E, u_N, u_U = cls.body_fixed_to_topocentric_basis(lat_deg, lon_deg)

        # Project vector onto local ENU axes
        v_E = vx * u_E[0] + vy * u_E[1] + vz * u_E[2]
        v_N = vx * u_N[0] + vy * u_N[1] + vz * u_N[2]
        v_U = vx * u_U[0] + vy * u_U[1] + vz * u_U[2]

        # Elevation: arcsin(Up / norm)
        sin_el = max(-1.0, min(1.0, v_U / norm))
        el_deg = math.degrees(math.asin(sin_el))

        # Azimuth: atan2(East, North) clockwise from North
        az_deg = math.degrees(math.atan2(v_E, v_N)) % 360.0

        return az_deg, el_deg
