import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import VerificationSuitePanel from './VerificationSuitePanel';

vi.mock('./config', () => ({ API_BASE_URL: 'http://api.test' }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const suite = {
  meaning: 'Verifies the geometry code. It does not validate a landing site.',
  total: 2, passed: 1, all_passed: false,
  results: [
    { id: 'a', title: 'Pillar horizon angle', reference: 'alpha = atan(...)', passed: true },
    { id: 'b', title: 'Mast effect', reference: 'delta', passed: false },
  ],
  not_covered: ['No second ephemeris.'],
};

describe('VerificationSuitePanel', () => {
  it('renders pass counts, failures and what is not covered', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => suite }));
    render(<VerificationSuitePanel />);
    expect(await screen.findByRole('heading', { name: /Independent Verification Suite/i })).toBeInTheDocument();
    expect(screen.getByText('1/2 PASSED')).toBeInTheDocument();
    expect(screen.getByText('Pillar horizon angle')).toBeInTheDocument();
    expect(screen.getByText(/No second ephemeris/i)).toBeInTheDocument();
  });
  it('degrades gracefully when the endpoint fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) }));
    render(<VerificationSuitePanel />);
    expect(await screen.findByText(/Verification suite is unavailable/i)).toBeInTheDocument();
  });
});
