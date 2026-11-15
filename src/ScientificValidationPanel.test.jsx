import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import ScientificValidationPanel from './ScientificValidationPanel';

const report = { status: 'blocked', meaning: 'A quality gate for interpretation, not a scientific certification.', real_data_scope: 'JPL Horizons angles only.', checks: [{ id: 'synthetic_kpis', status: 'blocked', message: 'KPIs are synthetic.' }, { id: 'ephemeris_source', status: 'pass', message: 'JPL source labelled.' }] };

describe('ScientificValidationPanel', () => {
  it('renders pass and blocked scientific checks', () => {
    render(<ScientificValidationPanel report={report} />);
    expect(screen.getByRole('heading', { name: /Scientific Integrity Gate/i })).toBeInTheDocument();
    expect(screen.getByText(/synthetic kpis/i)).toBeInTheDocument();
    expect(screen.getByText(/JPL source labelled/i)).toBeInTheDocument();
  });
});
