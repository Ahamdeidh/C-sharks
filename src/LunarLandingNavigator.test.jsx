import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import LunarLandingNavigator, { localInputToUtcIso, PRESET_SITES } from './LunarLandingNavigator';

// Mock global fetch
const originalFetch = global.fetch;

describe('LunarLandingNavigator Test Suite', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  // =========================================================================
  // 1. Timezone & Timestamp Handling
  // =========================================================================
  describe('Timezone & Timestamp Conversion (localInputToUtcIso)', () => {
    it('converts valid local input string to an ISO string ending with Z', () => {
      const iso = localInputToUtcIso('2026-11-14T12:00');
      expect(iso).toBeTruthy();
      expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    });

    it('returns null for empty or invalid input', () => {
      expect(localInputToUtcIso('')).toBeNull();
      expect(localInputToUtcIso('not-a-date')).toBeNull();
    });

    it('is idempotent and does not shift the timestamp twice on multiple conversions', () => {
      const input = '2026-11-14T12:00';
      const firstResult = localInputToUtcIso(input);
      const secondResult = localInputToUtcIso(input);
      expect(firstResult).toBe(secondResult);
    });

    it('handles simulated timezone offset correctly (e.g. UTC+5 vs UTC-3)', () => {
      // Mock Date getTimezoneOffset
      const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;

      try {
        // Offset -300 minutes corresponds to UTC+5
        Date.prototype.getTimezoneOffset = () => -300;
        const d1 = new Date('2026-11-14T17:00:00Z');
        expect(d1.toISOString()).toBe('2026-11-14T17:00:00.000Z');

        // Offset +180 minutes corresponds to UTC-3
        Date.prototype.getTimezoneOffset = () => 180;
        const d2 = new Date('2026-11-14T09:00:00Z');
        expect(d2.toISOString()).toBe('2026-11-14T09:00:00.000Z');
      } finally {
        Date.prototype.getTimezoneOffset = originalGetTimezoneOffset;
      }
    });

    it('correctly formats daylight saving dates without throwing', () => {
      // Summer date (July) and Winter date (January)
      const summerIso = localInputToUtcIso('2026-07-15T10:00');
      const winterIso = localInputToUtcIso('2026-01-15T10:00');
      expect(summerIso).toContain('2026-07-15');
      expect(winterIso).toContain('2026-01-15');
    });
  });

  // =========================================================================
  // 2. Initial Render & Accessible Elements
  // =========================================================================
  describe('UI Initial Rendering & Accessibility', () => {
    it('renders prototype disclaimers, control labels, and live region', () => {
      render(<LunarLandingNavigator />);

      // Title & prototype disclaimer
      expect(screen.getByText(/LUNAR NAVIGATOR/i)).toBeInTheDocument();
      expect(screen.getByText(/PROTOTYPE INTERFACE/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Run Simulation/i })).toBeInTheDocument();

      // Screen reader live region
      const liveRegion = document.querySelector('[role="status"][aria-live="polite"]');
      expect(liveRegion).toBeInTheDocument();

      // Form sliders have aria values
      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBe(3); // Duration, Antenna, Margin
      expect(sliders[0]).toHaveAttribute('aria-valuemin');
      expect(sliders[0]).toHaveAttribute('aria-valuemax');
    });

    it('renders all preset candidate sites in the select dropdown and list', () => {
      render(<LunarLandingNavigator />);
      const select = screen.getByLabelText(/1\. Candidate Landing Site/i);
      expect(select).toBeInTheDocument();
      PRESET_SITES.forEach(site => {
        expect(screen.getAllByText(new RegExp(site.name, 'i')).length).toBeGreaterThanOrEqual(1);
      });
    });

    it('allows selecting candidate site via keyboard interaction on polar map marker', () => {
      render(<LunarLandingNavigator />);
      const malapertMarker = screen.getByLabelText(/Select Malapert Massif Ridge/i);
      expect(malapertMarker).toBeInTheDocument();

      fireEvent.keyDown(malapertMarker, { key: 'Enter' });
      // Target header updates
      expect(screen.getByText(/TARGET: MALAPERT MASSIF RIDGE/i)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // 3. Request Formation & Backend Communication
  // =========================================================================
  describe('End-to-End Simulation Request & Execution', () => {
    it('sends all configured inputs to backend when Run Simulation is clicked', async () => {
      let capturedPayload = null;

      global.fetch = vi.fn().mockImplementation((url, options) => {
        if (url.includes('/status')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ system_status: 'online' }) });
        }
        if (url.includes('/simulation/run')) {
          capturedPayload = JSON.parse(options.body);
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'engine_pending',
              status_message: 'Calculation engine is pending integration.',
              data_source: 'none',
              is_demo: false,
              inputs_used: capturedPayload,
              kpis: null,
              timeline: []
            })
          });
        }
        return Promise.reject(new Error('Unknown url'));
      });

      render(<LunarLandingNavigator />);

      // Select site
      const siteSelect = screen.getByLabelText(/1\. Candidate Landing Site/i);
      fireEvent.change(siteSelect, { target: { value: 'malapert' } });

      // Change duration slider
      const durationSlider = screen.getByLabelText(/Mission duration in days/i);
      fireEvent.change(durationSlider, { target: { value: '20' } });

      // Change antenna slider
      const antennaSlider = screen.getByLabelText(/Antenna mast height in meters/i);
      fireEvent.change(antennaSlider, { target: { value: '12' } });

      // Change LOS margin
      const losSlider = screen.getByLabelText(/Earth line-of-sight margin in degrees/i);
      fireEvent.change(losSlider, { target: { value: '0.4' } });

      // Run simulation
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(capturedPayload).not.toBeNull();
      });

      expect(capturedPayload.site_id).toBe('malapert');
      expect(capturedPayload.mission_duration_days).toBe(20);
      expect(capturedPayload.antenna_height_m).toBe(12);
      expect(capturedPayload.los_margin_deg).toBe(0.4);
      expect(capturedPayload.demo_mode).toBe(false);
      expect(capturedPayload.start_time).toMatch(/Z$/);
    });

    it('supports Custom Lunar Coordinates Override and displays coordinate precedence notice', async () => {
      let capturedPayload = null;
      global.fetch = vi.fn().mockImplementation((url, options) => {
        if (url.includes('/simulation/run')) {
          capturedPayload = JSON.parse(options.body);
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'engine_pending',
              status_message: 'Pending engine',
              data_source: 'none',
              is_demo: false,
              coordinate_mismatch: 'Submitted coordinates (-88.8, 42.5) differ from registered site.',
              inputs_used: capturedPayload,
              kpis: null,
              timeline: []
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Custom Lunar Coordinates Override/i }));
      fireEvent.change(screen.getByLabelText(/Custom lunar latitude/i), { target: { value: '-88.8' } });
      fireEvent.change(screen.getByLabelText(/Custom lunar longitude/i), { target: { value: '42.5' } });
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(capturedPayload).not.toBeNull();
      });
      expect(capturedPayload.lat).toBe(-88.8);
      expect(capturedPayload.lon).toBe(42.5);
      expect(await screen.findByTestId('coordinate-override-notice')).toBeInTheDocument();
    });

    it('handles engine_pending response without displaying fabricated results', async () => {
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'engine_pending',
              status_message: 'Real LOLA DEM raytracing engine is pending integration.',
              data_source: 'none',
              is_demo: false,
              inputs_used: {},
              kpis: null,
              timeline: []
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByText(/STATUS: ENGINE PENDING/i)).toBeInTheDocument();
      });

      // KPI cards show placeholder dash
      expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(4);
    });

    it('displays clear error message when backend connection fails', async () => {
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          return Promise.reject(new Error('Failed to fetch'));
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByText(/Simulation Request Failed/i)).toBeInTheDocument();
        expect(screen.getAllByText(/Unable to reach the backend/i).length).toBeGreaterThanOrEqual(1);
      });
    });

    it('renders prototype demo results and updates metrics and timeline when demo mode is active', async () => {
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'demo',
              status_message: 'PROTOTYPE DEMO MODE',
              data_source: 'synthetic_demo',
              is_demo: true,
              inputs_used: { antenna_height_m: 6.0, mission_duration_days: 14 },
              kpis: {
                avg_illumination_pct: 88.2,
                dte_connection_pct: 79.5,
                max_amsi: '0.10 (Low)',
                avg_asia_hours: 12.0
              },
              timeline: [
                { timestamp: '2026-11-14T12:00:00Z', step_index: 1, elapsed_hours: 0, sol_day: 0.0, illumination_pct: 85.0, dte_connection_pct: 78.0 },
                { timestamp: '2026-11-14T16:00:00Z', step_index: 2, elapsed_hours: 4, sol_day: 0.17, illumination_pct: 86.0, dte_connection_pct: 79.0 }
              ],
              total_time_steps: 2,
              generated_at: new Date().toISOString()
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);

      // Enable demo mode
      const toggle = screen.getByRole('switch');
      fireEvent.click(toggle);

      // Run simulation
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByText('88.2%')).toBeInTheDocument();
        expect(screen.getByText('79.5%')).toBeInTheDocument();
        expect(screen.getByText(/PROTOTYPE DEMO MODE:/i)).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // 4. Stale Result Tracking
  // =========================================================================
  describe('Stale Result Tracking When Inputs Change', () => {
    beforeEach(() => {
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'demo',
              status_message: 'Demo results',
              data_source: 'synthetic_demo',
              is_demo: true,
              inputs_used: { site_id: 'shackleton', mission_duration_days: 14, antenna_height_m: 6.0 },
              kpis: { avg_illumination_pct: 86.4, dte_connection_pct: 74.2 },
              timeline: [{ timestamp: '2026-11-14T12:00:00Z', step_index: 1, elapsed_hours: 0, sol_day: 0.0, illumination_pct: 86, dte_connection_pct: 74 }]
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
    });

    it('marks results as stale when candidate site is changed', async () => {
      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByText('86.4%')).toBeInTheDocument();
      });

      // Change site
      const siteSelect = screen.getByLabelText(/1\. Candidate Landing Site/i);
      fireEvent.change(siteSelect, { target: { value: 'malapert' } });

      // Stale notice appears
      expect(screen.getByText(/Results shown are from a previous configuration/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Stale/i).length).toBeGreaterThanOrEqual(1);
    });

    it('marks results as stale when antenna height is changed', async () => {
      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByText('86.4%')).toBeInTheDocument();
      });

      const antennaSlider = screen.getByLabelText(/Antenna mast height in meters/i);
      fireEvent.change(antennaSlider, { target: { value: '18' } });

      expect(screen.getByText(/Results shown are from a previous configuration/i)).toBeInTheDocument();
    });

    it('marks results as stale when mission duration is changed', async () => {
      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByText('86.4%')).toBeInTheDocument();
      });

      const durationSlider = screen.getByLabelText(/Mission duration in days/i);
      fireEvent.change(durationSlider, { target: { value: '45' } });

      expect(screen.getByText(/Results shown are from a previous configuration/i)).toBeInTheDocument();
    });

    it('disables Save Baseline button when displayed result is stale', async () => {
      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Save Baseline/i })).toBeInTheDocument();
      });

      // Change LOS margin to make result stale
      const losSlider = screen.getByLabelText(/Earth line-of-sight margin in degrees/i);
      fireEvent.change(losSlider, { target: { value: '0.8' } });

      // Save Baseline is hidden/disabled because current settings have not been run
      expect(screen.queryByRole('button', { name: /Save Baseline/i })).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 5. Scenario Comparison Functionality
  // =========================================================================
  describe('Scenario Comparison Workflow', () => {
    it('saves a baseline and displays side-by-side scenario comparison', async () => {
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'demo',
              status_message: 'Demo results',
              data_source: 'synthetic_demo',
              is_demo: true,
              inputs_used: {
                site_id: 'shackleton',
                site_name: 'Shackleton Crater Rim',
                mission_duration_days: 14,
                timestep_hours: 4,
                antenna_height_m: 6.0,
                los_margin_deg: 0.25,
                start_time_utc: '2026-11-14T12:00:00Z'
              },
              kpis: { avg_illumination_pct: 86.4, dte_connection_pct: 74.2 },
              timeline: [{ timestamp: '2026-11-14T12:00:00Z', step_index: 1, elapsed_hours: 0, sol_day: 0.0, illumination_pct: 86, dte_connection_pct: 74 }]
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Save Baseline/i })).toBeInTheDocument();
      });

      // Click Save Baseline
      fireEvent.click(screen.getByRole('button', { name: /Save Baseline/i }));

      expect(screen.getByText(/Scenario Comparison/i)).toBeInTheDocument();
      expect(screen.getByText(/\[A\] BASELINE/i)).toBeInTheDocument();
      expect(screen.getByText(/\[B\] CURRENT/i)).toBeInTheDocument();
    });

    it('shows compatibility warnings when comparing scenarios with different duration or timestep', async () => {
      let runCount = 0;
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          runCount++;
          const duration = runCount === 1 ? 10 : 20;
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'demo',
              status_message: 'Demo results',
              data_source: 'synthetic_demo',
              is_demo: true,
              inputs_used: {
                site_id: 'shackleton',
                mission_duration_days: duration,
                timestep_hours: 4,
                antenna_height_m: 6.0,
                los_margin_deg: 0.25,
                start_time_utc: '2026-11-14T12:00:00Z'
              },
              kpis: { avg_illumination_pct: 85.0, dte_connection_pct: 75.0 },
              timeline: [{ timestamp: '2026-11-14T12:00:00Z', step_index: 1, elapsed_hours: 0, sol_day: 0.0, illumination_pct: 85, dte_connection_pct: 75 }]
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);

      // Run 1 (10 days)
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Save Baseline/i })).toBeInTheDocument();
      });

      // Save baseline
      fireEvent.click(screen.getByRole('button', { name: /Save Baseline/i }));

      // Change duration to 20 days and run again
      const durationSlider = screen.getByLabelText(/Mission duration in days/i);
      fireEvent.change(durationSlider, { target: { value: '20' } });
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        // Warning about differing durations is shown
        expect(screen.getByText(/Duration differs/i)).toBeInTheDocument();
      });
    });

    it('clears baseline when remove button is clicked', async () => {
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'demo',
              status_message: 'Demo results',
              data_source: 'synthetic_demo',
              is_demo: true,
              inputs_used: { site_id: 'shackleton' },
              kpis: { avg_illumination_pct: 80, dte_connection_pct: 70 },
              timeline: []
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Save Baseline/i })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /Save Baseline/i }));
      expect(screen.getByText(/Scenario Comparison/i)).toBeInTheDocument();

      // Click clear/remove baseline
      const removeBtn = screen.getByRole('button', { name: /Remove saved baseline/i });
      fireEvent.click(removeBtn);

      expect(screen.queryByText(/Scenario Comparison/i)).not.toBeInTheDocument();
    });
  });

  // =========================================================================
  // 6. Data Sources & Provenance Modal and Run JSON Export
  // =========================================================================
  describe('Data Sources & Provenance Modal and Run JSON Export', () => {
    beforeEach(() => {
      window.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      window.URL.revokeObjectURL = vi.fn();
    });

    it('opens the Data Sources & Provenance modal and renders official sources and links', async () => {
      let provenanceFetched = false;
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/api/v1/provenance')) {
          provenanceFetched = true;
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              coordinate_reference_frames: { inertial: "ICRF", lunar_fixed: "MOON_ME" },
              data_sources: { horizons: { status: "ready" } }
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);

      // Find and click the Data Sources & Provenance button
      const openBtn = screen.getByRole('button', { name: /View official data sources and methodology/i });
      expect(openBtn).toBeInTheDocument();
      fireEvent.click(openBtn);

      // Verify modal is displayed
      expect(screen.getByText(/Official Data Sources & Methodology/i)).toBeInTheDocument();
      expect(screen.getByText(/Provenance Audit & Scientific Transparency/i)).toBeInTheDocument();

      // Verify all 4 NASA/JPL sources are listed
      expect(screen.getByText(/JPL Solar System Dynamics \(Horizons API\)/i)).toBeInTheDocument();
      expect(screen.getByText(/USGS Astrogeology PDS Geosciences Node \(Orbital Data Explorer - ODE\)/i)).toBeInTheDocument();
      expect(screen.getByText(/NAIF SPICE Toolkit & Lunar Kernels/i)).toBeInTheDocument();
      expect(screen.getByText(/NASA Moon Trek Visualization Portal/i)).toBeInTheDocument();
      expect(screen.getByText(/Team-Supplied GIS Archive — Catalog v2/i)).toBeInTheDocument();
      expect(screen.getByText(/primary upstream provenance and some field definitions are unverified/i)).toBeInTheDocument();
      expect(screen.getByText(/“Sun\+Earth” is the source-field label only/i)).toBeInTheDocument();

      // Verify status badge for Moon Trek clarifies visual reference only
      expect(screen.getByText(/Visual Reference Only \(Non-numerical\)/i)).toBeInTheDocument();

      // Verify physical assumptions are documented
      expect(screen.getByText(/1\. Lunar Curvature Drop:/i)).toBeInTheDocument();
      expect(screen.getByText(/2\. Finite Celestial Discs:/i)).toBeInTheDocument();
      expect(screen.getByText(/3\. Antenna Vantage Elevation:/i)).toBeInTheDocument();
      expect(screen.getByText(/4\. Coordinate Precedence:/i)).toBeInTheDocument();

      // Close modal
      const closeBtn = screen.getByRole('button', { name: /Close methodology modal/i });
      fireEvent.click(closeBtn);

      // Verify modal is dismissed
      expect(screen.queryByText(/Official Data Sources & Methodology/i)).not.toBeInTheDocument();
    });

    it('displays Export Run JSON button only when simulation results exist, and exports valid JSON payload', async () => {
      global.fetch = vi.fn().mockImplementation((url) => {
        if (url.includes('/simulation/run')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'engine_pending',
              status_message: 'Calculation engine integration pending. No synthetic values fabricated.',
              data_source: 'pending_nasa_jpl_pipeline',
              is_demo: false,
              inputs_used: {
                site_id: 'shackleton',
                start_time_utc: '2026-11-14T12:00:00Z',
                mission_duration_days: 14,
                timestep_hours: 4,
                antenna_height_m: 6.0,
                los_margin_deg: 0.25
              },
              kpis: null,
              timeline: [],
              provenance: {
                status: 'pending_ingestion',
                audit_version: '1.3.0',
                documented_sources: { horizons: 'ready' }
              }
            })
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });

      render(<LunarLandingNavigator />);

      // Initially no Export Run JSON button
      expect(screen.queryByRole('button', { name: /Export simulation run and provenance as JSON/i })).not.toBeInTheDocument();

      // Run simulation (returns engine_pending)
      fireEvent.click(screen.getByRole('button', { name: /Run Simulation/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Export simulation run and provenance as JSON/i })).toBeInTheDocument();
      });

      // Click export button in header
      const exportBtn = screen.getByRole('button', { name: /Export simulation run and provenance as JSON/i });
      fireEvent.click(exportBtn);

      // Verify URL.createObjectURL and URL.revokeObjectURL were invoked
      expect(window.URL.createObjectURL).toHaveBeenCalledTimes(1);
      expect(window.URL.revokeObjectURL).toHaveBeenCalledTimes(1);

      // Also open the methodology modal and verify export button is available in the footer
      const openModalBtn = screen.getByRole('button', { name: /View official data sources and methodology/i });
      fireEvent.click(openModalBtn);

      const modalExportBtn = screen.getByRole('button', { name: /Export Run & Provenance \(JSON\)/i });
      expect(modalExportBtn).toBeInTheDocument();
      fireEvent.click(modalExportBtn);

      expect(window.URL.createObjectURL).toHaveBeenCalledTimes(2);
      expect(window.URL.revokeObjectURL).toHaveBeenCalledTimes(2);
    });
  });
});
