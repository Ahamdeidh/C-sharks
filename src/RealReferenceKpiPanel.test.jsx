import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import RealReferenceKpiPanel from './RealReferenceKpiPanel';

afterEach(cleanup);

const reference = {
  label: 'Real JPL Horizons angles, smooth-sphere horizon (no terrain)',
  steps_evaluated: 9, steps_requested: 9,
  avg_illumination_pct: 100, geometric_dte_visibility_pct: 0,
  longest_continuous_darkness_hours: 0, longest_earth_blackout_hours: 48,
  assumptions: ['Horizon is the smooth-sphere dip for the antenna height; local terrain is NOT applied.'],
  interpretation_limit: 'Use as a transparent real-data baseline, not a landing result.',
};

describe('RealReferenceKpiPanel', () => {
  it('shows real-data KPIs with the no-terrain disclosure', () => {
    render(<RealReferenceKpiPanel reference={reference} terrainInfo={{ dem_ingestion: {} }} />);
    expect(screen.getByRole('heading', { name: /Real-Data Reference KPIs/i })).toBeInTheDocument();
    expect(screen.getByText('NO TERRAIN')).toBeInTheDocument();
    expect(screen.getByText(/local terrain is NOT applied/i)).toBeInTheDocument();
    expect(screen.getByText('48')).toBeInTheDocument();
  });
  it('marks terrain as applied when a DEM ran', () => {
    render(<RealReferenceKpiPanel reference={reference} terrainInfo={{ dem_product: 'X' }} />);
    expect(screen.getByText('TERRAIN APPLIED')).toBeInTheDocument();
  });
  it('renders nothing when stale or without data', () => {
    const { container, rerender } = render(<RealReferenceKpiPanel reference={null} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<RealReferenceKpiPanel reference={reference} stale />);
    expect(container).toBeEmptyDOMElement();
  });
});
