import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import HorizonAndOpsPanel from './HorizonAndOpsPanel';

vi.mock('./config', () => ({ API_BASE_URL: 'http://api.test' }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const mockOps = {
  service: 'horizon_and_operational_windows',
  site: { id: 'shackleton', name: 'Shackleton Crater Rim', smooth_sphere_horizon_dip_deg: -0.107 },
  horizon_dynamics: {
    source: 'jpl_horizons_recorded_fixture',
    window_start_utc: '2026-11-14T12:00:00+00:00',
    window_end_utc: '2026-11-16T12:00:00+00:00',
    sun_elevation_min_deg: 1.506,
    sun_elevation_max_deg: 1.544,
    earth_elevation_min_deg: -4.022,
    earth_elevation_max_deg: -1.55,
    earth_elevation_rate_deg_per_hour: 0.0515,
    sunset_status: 'No sunset within the 48.0h verified JPL Horizons window.',
    earth_visibility_status: 'Earth is below the local horizontal for the entire 48.0h verified window.',
    solar_array_power_assessment: {
      vertical_vs_horizontal_flux_multiplier: 37.6,
      engineering_explanation: 'Vertical solar array captures 99.96% vs 2.66% for horizontal deck.',
    },
    skyplot_samples: [
      { step_index: 1, timestamp: '2026-11-14T12:00:00+00:00', elapsed_hours: 0, sun_azimuth_deg: 120.5, sun_elevation_deg: 1.506, sun_horizon_clearance_deg: 1.613, earth_azimuth_deg: 358.1, earth_elevation_deg: -4.022, earth_horizon_clearance_deg: -4.165 },
      { step_index: 2, timestamp: '2026-11-14T18:00:00+00:00', elapsed_hours: 6, sun_azimuth_deg: 117.5, sun_elevation_deg: 1.51, sun_horizon_clearance_deg: 1.617, earth_azimuth_deg: 357.7, earth_elevation_deg: -3.743, earth_horizon_clearance_deg: -3.886 },
    ],
  },
  schedule_slip_sensitivity: {
    in_window_delays: [
      { delay_hours: 0, start_timestamp_utc: '2026-11-14T12:00:00+00:00', initial_sun_elevation_deg: 1.506, initial_earth_elevation_deg: -4.022, operational_impact: 'Baseline T+0h' },
      { delay_hours: 36, start_timestamp_utc: '2026-11-16T00:00:00+00:00', initial_sun_elevation_deg: 1.534, initial_earth_elevation_deg: -2.212, operational_impact: 'Delayed T+36h' },
    ],
  },
  programs: [
    { id: 'apollo11', name: 'Mare Tranquillitatis (Equatorial Benchmark)', program: 'NASA Apollo 11', agency: 'NASA', lat_deg: 0.674, lon_deg: 23.473, solar_regime: '354h day/night', earth_comms_regime: '66 deg elevation', power_array_design: 'Flat array', reference_url: 'https://www.nasa.gov/mission/apollo-11/' },
    { id: 'csa-luv', name: 'South Pole Traverse Corridors', program: 'CSA Moon Exploration — LUV', agency: 'CSA', lat_deg: -89.4, lon_deg: -138.2, solar_regime: '6.25d mean', earth_comms_regime: 'Gateway relay', power_array_design: 'Vertical mast', reference_url: 'https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/' },
  ],
  audience_modes: {
    mission_planner: { label: 'Mission Planner & Systems Engineer Mode', focus: 'Quantitative telemetry', key_takeaways: ['Vertical solar arrays provide a 37.6x geometric flux advantage.'] },
    educator_public: { label: 'Educator, Student & Public Explorer Mode', focus: 'Intuitive explanations', key_takeaways: ['Why the Sun circles the horizon like a lighthouse beam!'] },
  },
};

describe('HorizonAndOpsPanel', () => {
  it('renders 360 horizon panorama, countdown status, solar array multiplier, and switches audience modes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => mockOps }));
    render(<HorizonAndOpsPanel />);
    expect(await screen.findByRole('heading', { name: /360° Horizon Panorama/i })).toBeInTheDocument();
    expect(screen.getByText(/37\.6× Direct Flux Gain/i)).toBeInTheDocument();
    expect(screen.getByText(/No sunset within the 48\.0h/i)).toBeInTheDocument();
    expect(screen.getByText(/CSA Moon Exploration/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Educator & Public Mode/i }));
    expect(screen.getByText(/lighthouse beam/i)).toBeInTheDocument();
  });
});
