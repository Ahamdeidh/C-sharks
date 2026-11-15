import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import LandingRiskPanel from './LandingRiskPanel';

const SAMPLE_RISK = {
  service: 'landing_site_risk_and_rf_assessment',
  mode: 'evaluated_engineering_model',
  status: 'evaluated',
  blocked_components: 0,
  site_id: 'shackleton',
  site_name: 'Shackleton Crater Rim',
  lat_deg: -89.9,
  lon_deg: 0.0,
  pad_scale_topography: {
    source: 'real_lola_dem_bidirectional_gradient',
    slope_east_west_deg: 3.12,
    slope_north_south_deg: -4.45,
    slope_total_deg: 5.43,
    pad_scale_effective_slope_deg: 8.25,
    downslope_aspect_true_az_deg: 145.0,
    tilt_margin_deg: 3.75,
    status: 'pass',
  },
  components: {
    boulder_hazard: {
      status: 'pass',
      source_model: 'LRO Diviner Rock Abundance',
      rock_abundance_fraction: 0.009,
      boulder_d99_diameter_m: 0.42,
      boulder_h99_height_m: 0.218,
      under_deck_clearance_margin_m: 0.282,
      clean_25m_pad_probability_pct: 87.6,
    },
    regolith_bearing: {
      status: 'pass',
      source_model: 'Lunar Sourcebook Terzaghi Model',
      cohesion_kpa: 0.85,
      internal_friction_angle_deg: 39.0,
      ultimate_bearing_capacity_kpa: 92.4,
      dynamic_touchdown_contact_pressure_kpa: 8.42,
      bearing_safety_factor: 10.97,
      estimated_footpad_sinkage_cm: 2.0,
    },
    plume_surface_interaction: {
      status: 'pass',
      source_model: 'Roberts-Continuum Plume Scour Model',
      descent_thrust_n: 15000.0,
      nozzle_cutoff_height_m: 2.0,
      impingement_wall_shear_pa: 83.6,
      critical_regolith_erosion_shear_pa: 25.0,
      predicted_scour_depth_cm: 6.18,
      transient_dust_optical_depth: 0.09,
    },
    rf_link_budget: {
      status: 'caution',
      source_model: 'NASA DSN 34m BWG X-Band Link Budget',
      free_space_path_loss_db: 222.65,
      eirp_dbw: 41.78,
      data_rate_mbps: 2.0,
      rf_link_margin_when_los_clear_db: 9.22,
      relay_recommendation: 'Direct-to-Earth X-band link closes with +9.2 dB margin whenever Earth is above the terrain horizon.',
    },
  },
};

describe('LandingRiskPanel', () => {
  it('renders bidirectional DEM pad-scale slope, boulder clearance, regolith bearing, PSI, and RF link budget', () => {
    render(<LandingRiskPanel riskData={SAMPLE_RISK} />);
    expect(screen.getByText(/5\/5 DOMAINS EVALUATED/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Boulder Clearance/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Regolith Bearing/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Plume Interaction/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. DSN X-Band RF Link/i)).toBeInTheDocument();
    expect(screen.getByText(/\+9\.22 dB/i)).toBeInTheDocument();
  });
});
