"""
JPL Horizons Ephemeris Integration Service
==========================================
Official Documentation & References:
- JPL Solar System Dynamics (SSD): https://ssd.jpl.nasa.gov/
- JPL Horizons Web Interface: https://ssd.jpl.nasa.gov/horizons/app.html#/
- JPL Horizons API Specification: https://ssd-api.jpl.nasa.gov/doc/horizons.html

API Query Settings:
- Endpoint: https://ssd.jpl.nasa.gov/api/horizons.api
- Target Body (COMMAND): '10' (Sun) or '399' (Earth)
- Observing Center (CENTER): 'coord@301' (Topocentric observer on Moon body 301)
- Coordinate System (COORD_TYPE): 'GEODETIC' (selenographic lon/lat/height)
- Reference Frame (REF_SYSTEM): 'ICRF'
- Quantities (QUANTITIES): '4' (Apparent Azimuth and Elevation)
- Light-time Correction (CORR): 'LT' (apparent position, corrected for photon transit time)
- Angle Format (ANG_FORMAT): 'DEG' (degrees)
- Time System: UTC
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import requests

logger = logging.getLogger(__name__)

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

class HorizonsServiceError(Exception):
    """Raised when JPL Horizons query fails or returns invalid response."""
    pass

class HorizonsTimeoutError(HorizonsServiceError):
    """Raised when JPL Horizons query times out."""
    pass

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def parse_horizons_time(time_str: str) -> datetime:
    """
    Parses a Horizons calendar timestamp such as '2026-Nov-14 12:00' into a
    timezone-aware UTC datetime (locale-independent; Horizons output is UT/UTC).
    """
    try:
        date_part, clock_part = time_str.strip().split()
        year_s, mon_s, day_s = date_part.split("-")
        hour_s, minute_s = clock_part.split(":")[:2]
        return datetime(int(year_s), _MONTHS[mon_s.title()[:3]], int(day_s),
                        int(hour_s), int(minute_s), tzinfo=timezone.utc)
    except (ValueError, KeyError) as exc:
        raise HorizonsServiceError(f"Unrecognised Horizons timestamp '{time_str}'") from exc


class HorizonsService:
    """
    Client for querying official NASA JPL Horizons REST API.
    Includes in-memory caching, timeout control, and response parsing.
    """
    def __init__(self, timeout_seconds: float = 8.0, enable_network: bool = True):
        self.timeout_seconds = timeout_seconds
        self.enable_network = enable_network
        self._cache: Dict[str, Dict[str, Any]] = {}

    @property
    def provenance_metadata(self) -> Dict[str, Any]:
        return {
            "source_name": "NASA JPL Solar System Dynamics (SSD) Horizons System",
            "source_url": "https://ssd.jpl.nasa.gov/api/horizons.api",
            "documentation_url": "https://ssd-api.jpl.nasa.gov/doc/horizons.html",
            "ephemeris_type": "OBSERVER",
            "quantities": "4 (Apparent Azimuth and Elevation)",
            "center": "coord@301 (Lunar Topocentric Coordinates)",
            "reference_system": "ICRF (International Celestial Reference Frame)",
            "correction": "LT (Light-Time corrected apparent position)",
            "angle_units": "degrees",
            "time_system": "UTC",
            "timeout_seconds": self.timeout_seconds
        }

    def _generate_cache_key(self, params: Dict[str, str]) -> str:
        serialized = json.dumps(params, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def build_query_params(
        self,
        target_id: str,
        lat: float,
        lon: float,
        elevation_km: float,
        start_time_utc: datetime,
        stop_time_utc: datetime,
        step_hours: int
    ) -> Dict[str, str]:
        """
        Constructs standardized JPL Horizons API query parameters.
        Site coordinates for lunar observer:
        SITE_COORD format in Horizons: 'lon,lat,alt_km' where lon is East longitude [0, 360] or [-180, 180].
        """
        # Normalize longitude to [0, 360]
        norm_lon = (lon + 360.0) % 360.0

        start_str = start_time_utc.strftime("'%Y-%m-%d %H:%M'")
        stop_str = stop_time_utc.strftime("'%Y-%m-%d %H:%M'")
        step_str = f"'{step_hours} h'"

        return {
            "format": "json",
            "EPHEM_TYPE": "OBSERVER",
            "COMMAND": f"'{target_id}'",
            "CENTER": "'coord@301'",
            "COORD_TYPE": "'GEODETIC'",
            "SITE_COORD": f"'{norm_lon:.4f},{lat:.4f},{elevation_km:.3f}'",
            "START_TIME": start_str,
            "STOP_TIME": stop_str,
            "STEP_SIZE": step_str,
            "QUANTITIES": "'4'",  # Apparent Azimuth & Elevation
            "REF_SYSTEM": "'ICRF'",
            "CAL_FORMAT": "'CAL'",
            "ANG_FORMAT": "'DEG'",
            "TIME_DIGITS": "'MINUTES'",
            "CSV_FORMAT": "'YES'"
        }

    def parse_horizons_csv(self, result_text: str) -> List[Dict[str, Any]]:
        """
        Parses the observer table between '$$SOE' and '$$EOE' markers.
        Format in Horizons CSV:
          Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),
        Where optional columns between Date and Azimuth contain solar/lunar illumination markers ('*', 'm', ' ').
        Numeric azimuth and elevation are robustly extracted from trailing numeric fields.
        """
        soe_idx = result_text.find("$$SOE")
        eoe_idx = result_text.find("$$EOE")

        if soe_idx == -1 or eoe_idx == -1:
            raise HorizonsServiceError(
                "JPL Horizons output does not contain expected '$$SOE' and '$$EOE' ephemeris block."
            )

        data_block = result_text[soe_idx + 5 : eoe_idx].strip()
        lines = [line.strip() for line in data_block.splitlines() if line.strip()]

        samples: List[Dict[str, Any]] = []

        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue

            time_str = parts[0]
            # Extract numeric tokens from the line
            numeric_tokens: List[float] = []
            for token in parts[1:]:
                # Match floating point numbers (positive or negative)
                if re.match(r'^-?\d+(?:\.\d+)?$', token):
                    try:
                        numeric_tokens.append(float(token))
                    except ValueError:
                        pass

            if len(numeric_tokens) >= 2:
                azimuth = numeric_tokens[0]
                elevation = numeric_tokens[1]
                samples.append({
                    "time_str": time_str,
                    "azimuth_deg": azimuth,
                    "elevation_deg": elevation
                })
            else:
                logger.warning(f"Could not extract azimuth/elevation from Horizons line: {line}")

        if not samples:
            raise HorizonsServiceError("Failed to parse valid azimuth/elevation samples from Horizons output.")

        return samples

    def query_observer_ephemeris(
        self,
        target_id: str,
        lat: float,
        lon: float,
        elevation_km: float,
        start_time_utc: datetime,
        stop_time_utc: datetime,
        step_hours: int
    ) -> List[Dict[str, Any]]:
        """
        Queries Horizons for Sun ('10') or Earth ('399') apparent topocentric az/el.
        Uses in-memory cache and enforces timeout.
        """
        if not self.enable_network:
            raise HorizonsServiceError("Network queries to JPL Horizons are currently disabled by configuration.")

        params = self.build_query_params(
            target_id=target_id,
            lat=lat,
            lon=lon,
            elevation_km=elevation_km,
            start_time_utc=start_time_utc,
            stop_time_utc=stop_time_utc,
            step_hours=step_hours
        )

        cache_key = self._generate_cache_key(params)
        if cache_key in self._cache:
            logger.info("Serving Horizons ephemeris query from cache.")
            return self._cache[cache_key]["samples"]

        try:
            response = requests.get(
                HORIZONS_API_URL,
                params=params,
                timeout=self.timeout_seconds,
                headers={"Accept": "application/json"}
            )
        except requests.exceptions.Timeout as te:
            raise HorizonsTimeoutError(
                f"JPL Horizons API timed out after {self.timeout_seconds}s. SSD service may be busy or unreachable."
            ) from te
        except requests.exceptions.RequestException as re_err:
            raise HorizonsServiceError(
                f"Failed to connect to JPL Horizons API at {HORIZONS_API_URL}: {str(re_err)}"
            ) from re_err

        if response.status_code != 200:
            raise HorizonsServiceError(
                f"JPL Horizons API returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            payload = response.json()
        except Exception as e:
            raise HorizonsServiceError(f"Invalid JSON response from JPL Horizons API: {e}")

        result_text = payload.get("result", "")
        samples = self.parse_horizons_csv(result_text)

        self._cache[cache_key] = {
            "samples": samples,
            "queried_at": datetime.now(timezone.utc).isoformat(),
            "target_id": target_id
        }

        return samples

    def load_recorded_fixture(self, fixture_path: Optional[str] = None, target_id: str = "10") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Loads pre-recorded, verified JPL Horizons ephemeris fixture from disk.
        Returns parsed samples and fixture metadata.
        Used for offline testing, regression benchmarks, and validation without live network dependency.
        """
        if fixture_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fixture_path = os.path.join(base_dir, "data", "fixtures", "horizons_sun_earth_sample.json")

        if not os.path.exists(fixture_path):
            raise HorizonsServiceError(f"Horizons fixture file not found at {fixture_path}")

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        key = "sun_query" if target_id == "10" else "earth_query"
        raw_result = data.get(key, {}).get("result", "")
        if not raw_result:
            raise HorizonsServiceError(f"No result found for target '{target_id}' in fixture at {fixture_path}")

        samples = self.parse_horizons_csv(raw_result)
        metadata = {
            "is_fixture": True,
            "fixture_file": fixture_path,
            "recorded_metadata": data.get("metadata", {}),
            "target_id": target_id
        }
        return samples, metadata
