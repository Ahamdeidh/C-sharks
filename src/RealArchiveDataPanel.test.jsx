import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import catalogV2 from '../backend/data/reference/lunar_catalog_v2.json';
import RealArchiveDataPanel from './RealArchiveDataPanel';

vi.mock('./config', () => ({ API_BASE_URL: 'http://api.test' }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('RealArchiveDataPanel', () => {
  it('loads v2 archive-derived regional summaries and discloses units and scientific limitations', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => catalogV2,
    }));

    render(<RealArchiveDataPanel />);
    const summaryTable = await screen.findByRole('table', { name: /Archive-derived mean consecutive illumination days/ });
    expect(within(summaryTable).getByText('Peak near Shackleton')).toBeInTheDocument();
    expect(screen.getByText('336')).toBeInTheDocument();
    expect(screen.getByText('21')).toBeInTheDocument();
    expect(screen.getByText('141')).toBeInTheDocument();

    const peakRow = within(summaryTable).getByRole('row', { name: /Peak near Shackleton/ });
    expect(peakRow).toHaveTextContent('5.70 / 7.66');
    expect(peakRow).toHaveTextContent('11.04 / 8.13');
    expect(screen.getAllByText(/definition unverified/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/9\.54% of pixels/i)).toBeInTheDocument();
    expect(screen.getByText(/consecutive 12-hour increments/i)).toBeInTheDocument();
    expect(screen.getByText(/not evidence that no PSR exists/i)).toBeInTheDocument();
    expect(screen.getByText(/does not include a verified elevation DEM/i)).toBeInTheDocument();

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      'http://api.test/api/v1/reference/catalog-v2', expect.objectContaining({ signal: expect.any(AbortSignal) })
    ));
  });

  it('updates selected-year regional values while retaining the eight-year mean', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => catalogV2 }));
    render(<RealArchiveDataPanel />);
    const summaryTable = await screen.findByRole('table', { name: /Archive-derived mean consecutive illumination days/ });
    const yearSelect = await screen.findByLabelText('Raster year');
    fireEvent.change(yearSelect, { target: { value: '2026' } });

    const peakRow = within(summaryTable).getByRole('row', { name: /Peak near Shackleton/ });
    expect(peakRow).toHaveTextContent(/8\.73\s*\/\s*7\.66/);
    expect(peakRow).toHaveTextContent(/8\.72\s*\/\s*8\.13/);
  });
});
