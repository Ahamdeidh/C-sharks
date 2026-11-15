import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import DecisionBriefPanel from './DecisionBriefPanel';

vi.mock('./config', () => ({ API_BASE_URL: 'http://api.test' }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const brief = {
  brief_type: 'evidence_first_mission_triage',
  status: 'reference_triage_only',
  ranked_regions: [
    { area_id: 'PeakNearShackleton', name: 'Peak near Shackleton', rank: 1, triage_index: 100, sun_only_mean_days: 7.66, sun_plus_earth_mean_days: 8.13, approx_psr_polygons: 38, blockers: ['No verified LOLA elevation DEM is connected to the runtime calculation.'], recommended_next_action: 'Ingest a verified DEM.' },
  ],
  recommended_work_packages: [{ priority: 1, action: 'Verify upstream publisher.', unlocks: 'Defensible interpretation.' }],
  provenance: { ranking_formula: '60% normalized Sun-only mean days + 40% normalized source-field mean days.' },
};

describe('DecisionBriefPanel', () => {
  it('renders ranked evidence, blockers and next work package', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => brief }));
    render(<DecisionBriefPanel />);
    expect(await screen.findByRole('heading', { name: /Mission Decision Brief/i })).toBeInTheDocument();
    expect(screen.getByText('Peak near Shackleton')).toBeInTheDocument();
    expect(screen.getByText(/No verified LOLA elevation DEM/i)).toBeInTheDocument();
    expect(screen.getByText(/Verify upstream publisher/i)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('http://api.test/api/v1/mission/decision-brief', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });
});
