import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import ChallengeAlignmentPanel from './ChallengeAlignmentPanel';

vi.mock('./config', () => ({ API_BASE_URL: 'http://api.test' }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const data = {
  alignment_type: 'challenge_traceability_matrix',
  summary: 'Every challenge-facing claim is mapped.',
  coverage: { criteria_mapped: 4 },
  criteria: [{ id: 'nasa-data-core', challenge_goal: 'Use NASA/JPL data meaningfully.', status: 'implemented_scoped_integration', project_response: 'JPL Horizons panel.', gap: 'Terrain remains pending.', data_role: 'Real ephemeris angles.', evidence: ['ephemeris_check'] }],
  honesty_note: 'Alignment does not imply scientific completeness.'
};

describe('ChallengeAlignmentPanel', () => {
  it('renders challenge goal, data evidence and explicit gap', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => data }));
    render(<ChallengeAlignmentPanel />);
    expect(await screen.findByRole('heading', { name: /Challenge Alignment Matrix/i })).toBeInTheDocument();
    expect(screen.getByText(/Use NASA\/JPL data meaningfully/i)).toBeInTheDocument();
    expect(screen.getByText(/Terrain remains pending/i)).toBeInTheDocument();
    expect(screen.getByText(/ephemeris_check/i)).toBeInTheDocument();
  });
});
