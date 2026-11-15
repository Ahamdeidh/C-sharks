"""
Ephemeris Provider — real NASA JPL Horizons angles in every simulation response
===============================================================================
Supplies the apparent topocentric azimuth/elevation of the Sun ('10') and the
Earth ('399') for the requested site and time grid, using ONLY real NASA data:

  1. LIVE   : JPL Horizons REST API — opt-in via the environment variable
              ENABLE_LIVE_HORIZONS=1 (off by default so tests and offline
              demos are deterministic). Any network/parse error falls through.
  2. RECORDED: coordinate-matched JSON fixtures in backend/data/fixtures/ (a
              48-hour Shackleton fixture plus additional multi-site fixtures, when
              present). Used only when the requested coordinates match the site; values between the recorded
              6-hour samples are linearly interpolated, and steps outside the
              recorded window are simply not reported (never extrapolated).

If neither source covers any requested step, `get_ephemeris_check` returns
None: nothing is fabricated.

IMPORTANT LIMITS (also repeated in the response text):
  * "Above local horizontal" compares each body's elevation with the local
    horizontal plane (0 deg). Terrain horizon masks, lunar-curvature dip with
    site elevation and the Sun/Earth angular discs are NOT applied here — that
    requires terrain processing; a 601 × 601 central DEM subset is bundled, but this panel reports raw angles only.
  * This is geometry only; it is not a terrain-aware illumination or DTE result.
"""

import logging
import json
import os
import glob
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .horizons_service import (
    HorizonsService,
    HorizonsServiceError,
    parse_horizons_time,
)

logger = logging.getLogger(__name__)

# Coordinates are considered "the same site" when both lat and lon agree to this tolerance.
FIXTURE_COORD_TOL_DEG = 0.01

Series = List[Tuple[datetime, float, float]]  # (time_utc, azimuth_deg, elevation_deg)


def _interp_azimuth(a0: float, a1: float, frac: float) -> float:
    """Interpolates azimuths along the shortest arc (handles the 360 -> 0 wrap)."""
    delta = ((a1 - a0 + 180.0) % 360.0) - 180.0
    return (a0 + delta * frac) % 360.0


def _samples_to_series(samples: List[Dict[str, Any]]) -> Series:
    series: Series = [
        (parse_horizons_time(s["time_str"]), float(s["azimuth_deg"]), float(s["elevation_deg"]))
        for s in samples
    ]
    series.sort(key=lambda row: row[0])
    return series


def _interpolate(series: Series, when: datetime) -> Optional[Tuple[float, float]]:
    """Returns (azimuth, elevation) at `when`, or None if outside the series' time span."""
    if not series or when < series[0][0] or when > series[-1][0]:
        return None
    for i in range(len(series) - 1):
        t0, az0, el0 = series[i]
        t1, az1, el1 = series[i + 1]
        if t0 <= when <= t1:
            span = (t1 - t0).total_seconds()
            frac = 0.0 if span <= 0 else (when - t0).total_seconds() / span
            return _interp_azimuth(az0, az1, frac), el0 + (el1 - el0) * frac
    # `when` equals the last sample exactly (single-sample series or exact end point)
    return series[-1][1], series[-1][2]


class EphemerisProvider:
    """Builds the real-data `ephemeris_check` block attached to simulation responses."""

    def __init__(
        self,
        horizons: Optional[HorizonsService] = None,
        live_enabled: Optional[bool] = None,
        fixture_path: Optional[str] = None,
    ):
        self.horizons = horizons or HorizonsService()
        if live_enabled is None:
            live_enabled = os.getenv("ENABLE_LIVE_HORIZONS", "").strip().lower() in {"1", "true", "yes"}
        self.live_enabled = live_enabled
        self.fixture_path = fixture_path
        self._fixture_cache: Dict[str, Tuple[Series, Series, Dict[str, Any]]] = {}

    # ------------------------------------------------------------------ sources
    def _fixture_series(self, lat: float, lon: float) -> Optional[Tuple[Series, Series, Dict[str, Any]]]:
        """Load the first recorded fixture whose site coordinates match the request."""
        if self.fixture_path:
            candidate_paths = [self.fixture_path]
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidate_paths = [
                os.path.join(base_dir, "data", "fixtures", "horizons_sun_earth_sample.json"),
                *sorted(glob.glob(os.path.join(base_dir, "data", "fixtures", "horizons", "*.json"))),
                *sorted(glob.glob(os.path.join(base_dir, "data", "fixtures", "horizons_longrange", "*.json"))),
            ]
        for path in candidate_paths:
            if path.endswith(".meta.json"):
                continue
            meta_path = os.path.splitext(path)[0] + ".meta.json"
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as fh:
                        index_meta = json.load(fh)
                    idx_coords = index_meta.get("coordinates") or {}
                    idx_lat, idx_lon = float(idx_coords["lat_deg"]), float(idx_coords["lon_deg"])
                    idx_lon_diff = abs(((lon - idx_lon + 180.0) % 360.0) - 180.0)
                    if abs(lat - idx_lat) > FIXTURE_COORD_TOL_DEG or idx_lon_diff > FIXTURE_COORD_TOL_DEG:
                        continue
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    continue
            if path in self._fixture_cache:
                sun_series, earth_series, meta = self._fixture_cache[path]
            else:
                try:
                    sun_samples, meta = self.horizons.load_recorded_fixture(path, target_id="10")
                    earth_samples, _ = self.horizons.load_recorded_fixture(path, target_id="399")
                    sun_series, earth_series = _samples_to_series(sun_samples), _samples_to_series(earth_samples)
                    self._fixture_cache[path] = (sun_series, earth_series, meta)
                except (HorizonsServiceError, OSError, ValueError) as exc:
                    logger.warning("Horizons fixture unavailable at %s: %s", path, exc)
                    continue
            coords = (meta.get("recorded_metadata") or {}).get("coordinates") or {}
            try:
                fx_lat, fx_lon = float(coords["lat_deg"]), float(coords["lon_deg"])
            except (KeyError, TypeError, ValueError):
                continue
            lon_diff = abs(((lon - fx_lon + 180.0) % 360.0) - 180.0)
            if abs(lat - fx_lat) <= FIXTURE_COORD_TOL_DEG and lon_diff <= FIXTURE_COORD_TOL_DEG:
                return sun_series, earth_series, meta
        return None

    def _live_series(
        self,
        lat: float,
        lon: float,
        elevation_m: float,
        start_utc: datetime,
        total_steps: int,
        step_hours: int,
    ) -> Tuple[Series, Series]:
        stop_utc = start_utc + timedelta(hours=step_hours * max(1, total_steps - 1))
        kwargs = dict(
            lat=lat,
            lon=lon,
            elevation_km=elevation_m / 1000.0,
            start_time_utc=start_utc,
            stop_time_utc=stop_utc,
            step_hours=step_hours,
        )
        sun = self.horizons.query_observer_ephemeris(target_id="10", **kwargs)
        earth = self.horizons.query_observer_ephemeris(target_id="399", **kwargs)
        return _samples_to_series(sun), _samples_to_series(earth)

    # ------------------------------------------------------------------ public
    def get_ephemeris_check(
        self,
        lat: float,
        lon: float,
        elevation_m: float,
        start_utc: datetime,
        step_hours: int,
        total_steps: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Returns a dict with real Sun/Earth angles for the requested time grid, or None
        when no real source covers any step.
        """
        source: Optional[str] = None
        sun_series: Series = []
        earth_series: Series = []
        live_error: Optional[str] = None
        fixture_meta: Dict[str, Any] = {}

        if self.live_enabled:
            try:
                sun_series, earth_series = self._live_series(
                    lat, lon, elevation_m, start_utc, total_steps, step_hours
                )
                source = "jpl_horizons_live"
            except HorizonsServiceError as exc:
                live_error = str(exc)
                logger.warning("Live Horizons query failed, falling back to recorded fixture: %s", exc)

        if source is None:
            fixture = self._fixture_series(lat, lon)
            if fixture is not None:
                sun_series, earth_series, fixture_meta = fixture
                source = "jpl_horizons_recorded_fixture"

        if source is None:
            return None

        samples: List[Dict[str, Any]] = []
        for step in range(total_steps):
            when = start_utc + timedelta(hours=step * step_hours)
            sun = _interpolate(sun_series, when)
            earth = _interpolate(earth_series, when)
            if sun is None or earth is None:
                continue
            samples.append({
                "timestamp": when.isoformat(),
                "step_index": step + 1,
                "sun_azimuth_deg": round(sun[0], 3),
                "sun_elevation_deg": round(sun[1], 3),
                "earth_azimuth_deg": round(earth[0], 3),
                "earth_elevation_deg": round(earth[1], 3),
                "sun_above_local_horizontal": sun[1] > 0.0,
                "earth_above_local_horizontal": earth[1] > 0.0,
            })

        if not samples:
            return None

        n = len(samples)
        observed_steps = {int(s["step_index"]) for s in samples}
        missing_steps = [i for i in range(1, total_steps + 1) if i not in observed_steps]
        sun_pct = round(100.0 * sum(s["sun_above_local_horizontal"] for s in samples) / n, 1)
        earth_pct = round(100.0 * sum(s["earth_above_local_horizontal"] for s in samples) / n, 1)

        result: Dict[str, Any] = {
            "source": source,
            "provider": "NASA JPL Solar System Dynamics — Horizons (apparent az/el, light-time corrected, ICRF)",
            "coverage": {
                "steps_requested": total_steps,
                "steps_with_real_ephemeris": n,
                "first_timestamp": samples[0]["timestamp"],
                "last_timestamp": samples[-1]["timestamp"],
                "coverage_complete": n == total_steps,
                "missing_step_indices": missing_steps,
            },
            "samples": samples,
            "summary": {
                "sun_above_local_horizontal_pct": sun_pct,
                "earth_above_local_horizontal_pct": earth_pct,
                "note": (
                    "Real NASA Horizons angles compared with the local horizontal plane only. "
                    "Terrain horizon masks, lunar-curvature dip and the Sun/Earth discs are NOT applied "
                    "(the DEM terrain horizon is not applied here), so this is not a terrain-aware illumination or "
                    "Earth line-of-sight result. The illumination/DTE series in the timeline are "
                    "synthetic demo values."
                ),
            },
        }
        if source == "jpl_horizons_recorded_fixture":
            result["fixture"] = {
                "recorded_at_utc": (fixture_meta.get("recorded_metadata") or {}).get("retrieved_at_utc"),
                "time_window": (fixture_meta.get("recorded_metadata") or {}).get("time_window"),
                "interpolation": "linear between recorded samples; steps outside the recorded window are omitted",
                "site": (fixture_meta.get("recorded_metadata") or {}).get("site"),
                "coordinates": (fixture_meta.get("recorded_metadata") or {}).get("coordinates"),
                "source_caveat": (fixture_meta.get("recorded_metadata") or {}).get("source"),
            }
        if live_error:
            result["live_error"] = live_error
        return result
