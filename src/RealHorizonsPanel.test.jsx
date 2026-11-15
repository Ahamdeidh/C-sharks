import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import RealHorizonsPanel from './RealHorizonsPanel';

const eph = {
  source: 'jpl_horizons_recorded_fixture',
  coverage: { steps_requested: 2, steps_with_real_ephemeris: 2 },
  summary: { sun_above_local_horizontal_pct: 100, earth_above_local_horizontal_pct: 0 },
  samples: [
    { timestamp: '2026-11-14T12:00:00+00:00', sun_elevation_deg: 1.506, earth_elevation_deg: -4.022 },
    { timestamp: '2026-11-14T18:00:00+00:00', sun_elevation_deg: 1.51, earth_elevation_deg: -3.743 },
  ],
};

describe('RealHorizonsPanel (real NASA Horizons data)', () => {
  it('shows an honest empty state when no real ephemeris covers the request', () => {
    render(<RealHorizonsPanel ephemeris={null} />);
    expect(screen.getByText(/No real NASA ephemeris covers this request/i)).toBeTruthy();
    expect(screen.queryByTestId('earth-below-finding')).toBeNull();
  });

  it('renders source badge, summary values and the Earth-below-horizon finding', () => {
    render(<RealHorizonsPanel ephemeris={eph} />);
    expect(screen.getByText(/Recorded NASA JPL Horizons response/i)).toBeTruthy();
    expect(screen.getByText('-4.022° to -3.743°')).toBeTruthy();
    expect(screen.getByTestId('earth-below-finding')).toBeTruthy();
  });

  it('states the scope limitation (no terrain applied)', () => {
    render(<RealHorizonsPanel ephemeris={eph} />);
    expect(screen.getByText(/LOLA terrain masks and Sun\/Earth discs are not applied/i)).toBeTruthy();
  });
});
