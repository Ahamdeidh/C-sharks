# Changelog — Lunar Landing Site Navigator

## Revision 11 — Full Evaluation Report Remediation (`v11`)
1. **Fixed `vertical_solar_array_gain` Benchmark & All 12 Backend Test Failures (`89/89 PASSED`)**:
   - Fixed 4-decimal rounding quantization in `compute_operational_windows` (`backend/services/horizon_and_ops_service.py`) by computing `vertical_vs_horizontal_flux_multiplier` from the exact unrounded solar elevation cosine/sine sums (`37.6x`) while separately reporting terrain-weighted cosine/sine factors.
   - Updated `backend/test_main.py`, `backend/test_services.py`, and `backend/test_terrain_engine.py` to align with disabling synthetic Demo fabrication (`demo_mode_available = False`) and active `terrain_aware` execution when `LDEM_80S_80MPP_ADJ.TIF` is present in `backend/data/dem/`.
2. **Synchronized All Documentation & Status Endpoints with Bundled `LDEM_80S_80MPP_ADJ.TIF`**:
   - Updated `README.md`, `REVIEW_REPORT_AR.md`, `backend/data/dem/README.md`, `main.py`, `simulation_engine.py`, `challenge_alignment_service.py`, `impact_brief_service.py`, `judge_evidence_service.py`, `scientific_validation_service.py`, and `src/LunarLandingNavigator.jsx` to reflect that `LDEM_80S_80MPP_ADJ.TIF` is bundled, verified, and actively ray-traced.
3. **Added Independent Geodetic Control-Point & Projection Verification (`16/16 Benchmarks PASSED`)**:
   - Added `verify_dem_geodesy_and_control_points` in `backend/services/terrain_engine.py` and two new benchmarks (`geodetic_control_points` and `bundled_nasa_dem_integrity`) in `backend/services/verification_suite.py`, verifying Polar Stereographic radii $r = 2R\tan(\chi/2)$, conformal scale factor $k = \sec^2(\chi/2)$, round-trip coordinates, and DEM pixel sampling across 6 IAU/LOLA South Pole landmarks.
4. **Added 5-Domain Pad-Scale Risk & DSN X-Band RF Link Budget Service (`landing_risk_service.py` + `LandingRiskPanel.jsx`)**:
   - Computes bidirectional East–West and North–South DEM slopes + fractal Hurst scaling ($H=0.75$) to a 15 m lander pad span, LRO Diviner boulder height clearance ($D_{99}/H_{99}$), Lunar Sourcebook Terzaghi regolith bearing capacity & sinkage, supersonic exhaust plume scouring (PSI), and 8.42 GHz DSN 34 m X-band link budget (`+9.22 dB` margin when LOS is clear), while preserving an explicit Strict Flight-Certification Gate toggle.
5. **Explicit UI Tagging of Illustrative vs. Terrain-Aware Values**:
   - Added `[Illustrative Preset]`, `[DEM + Horizons Verified]`, and `[Curated Reference]` badges across `src/LunarLandingNavigator.jsx` and `src/HorizonAndOpsPanel.jsx`.
6. **Added Explicit `terrain_aware` & Risk Assessment Test Suites**:
   - Added `test_bundled_nasa_lola_dem_executes_terrain_aware_and_verifies_geodesy` in `backend/test_terrain_engine.py`, 7 tests in `backend/test_landing_risk.py`, and `src/LandingRiskPanel.test.jsx` (**89/89 backend tests** and **40/40 frontend tests** passing).


## UI redesign (2026-11-15)
- Reworked the visual system with a refined lunar mission-control aesthetic, layered space backgrounds, glass-like top navigation, cleaner control surfaces, and more legible KPI cards.
- Improved responsive behavior for tablet and mobile widths while preserving the existing simulation workflows, panels, state, and API integration.
- Added consistent control styling, visible keyboard focus, and smoother interaction feedback.
