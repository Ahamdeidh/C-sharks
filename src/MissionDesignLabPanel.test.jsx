import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import MissionDesignLabPanel from './MissionDesignLabPanel';

vi.mock('./config', () => ({ API_BASE_URL: 'http://api.test' }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const scenario = (id, label) => ({ mode_id: id, label, description: `${label} description`, creative_question: 'Which region moves?', ranked_regions: [{ area_id: 'a', name: 'Peak near Shackleton', rank: 1, score: 100, contribution: { solar: 50, communications: 30, science: 20 } }] });
const lab = { concept: 'Explore counterfactual priorities.', scenarios: [scenario('balanced', 'Balanced Scout'), scenario('solar_first', 'Solar Continuity')], novelty: ['Counterfactual weighting.'], limitations: [], sensitivity: { interpretation: 'Peak near Shackleton ranks first in 78.3% of random weightings.', draws: 4000, seed: 2026, regions: [{ area_id: 'a', name: 'Peak near Shackleton', top_rank_share_pct: 78.3, best_rank: 1, worst_rank: 2 }] } };

describe('MissionDesignLabPanel', () => {
  it('renders the lab and switches mission priority modes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => lab }));
    render(<MissionDesignLabPanel />);
    expect(await screen.findByRole('heading', { name: /Mission Design Lab/i })).toBeInTheDocument();
    expect(screen.getByText(/Balanced Scout description/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /Solar Continuity/i }));
    expect(screen.getByText(/Solar Continuity description/i)).toBeInTheDocument();
  });
  it('shows weight-sensitivity robustness', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => lab }));
    render(<MissionDesignLabPanel />);
    expect(await screen.findByLabelText(/Weight sensitivity analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/ranks first in 78.3% of random weightings/i)).toBeInTheDocument();
    expect(screen.getByText(/78.3% first/)).toBeInTheDocument();
  });
});
