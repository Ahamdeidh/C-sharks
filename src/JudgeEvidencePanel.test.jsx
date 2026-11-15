import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import JudgeEvidencePanel from './JudgeEvidencePanel';

vi.mock('./config', () => ({ API_BASE_URL: 'http://api.test' }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const pack = {
  purpose: 'One coherent review path.',
  walkthrough: [
    { step: 1, title: 'Start with the mission problem', question: 'Why?', answer: 'Decision value.', evidence: ['Mission Decision Brief'] },
    { step: 2, title: 'Change the mission concept', question: 'What is creative?', answer: 'Counterfactual modes.', evidence: ['Mission Design Lab'] },
  ],
  score_support: { impact: ['brief'], creativity: ['modes'], validity: ['benchmarks'], relevance: ['alignment'] },
};

describe('JudgeEvidencePanel', () => {
  it('renders the walkthrough and criterion evidence', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => pack }));
    render(<JudgeEvidencePanel />);
    expect(await screen.findByRole('heading', { name: /Judge Evidence Pack/i })).toBeInTheDocument();
    expect(screen.getByText(/Start with the mission problem/i)).toBeInTheDocument();
    expect(screen.getByText(/benchmarks/i)).toBeInTheDocument();
  });
});
