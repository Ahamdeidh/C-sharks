import React, { useEffect, useMemo, useState } from 'react';
import { Compass, Clock, Play, Sun, Wifi, Globe, Sparkles, ExternalLink } from 'lucide-react';
import { API_BASE_URL } from './config';

export default function HorizonAndOpsPanel({ embedded = false }) {
  const [data, setData] = useState(null);
  const [state, setState] = useState('loading');
  const [stepIdx, setStepIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audienceMode, setAudienceMode] = useState('mission_planner');
  const [programFilter, setProgramFilter] = useState('ALL');

  useEffect(() => {
    if (embedded && typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') return undefined;
    const controller = new AbortController();
    if (!API_BASE_URL) {
      setState('error');
      return () => controller.abort();
    }
    fetch(`${API_BASE_URL}/api/v1/mission/horizon-ops?antenna_height_m=6.0&los_margin_deg=0.25&step_hours=2`, {
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) throw new Error('Horizon operational windows unavailable');
        return res.json();
      })
      .then((val) => {
        if (!Array.isArray(val?.horizon_dynamics?.skyplot_samples) || !Array.isArray(val?.programs)) {
          throw new Error('Invalid horizon ops payload');
        }
        setData(val);
        setState('ready');
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setState('error');
      });
    return () => controller.abort();
  }, []);

  const samples = data?.horizon_dynamics?.skyplot_samples || [];

  useEffect(() => {
    if (!isPlaying || samples.length === 0) return undefined;
    const timer = setInterval(() => {
      setStepIdx((prev) => (prev + 1) % samples.length);
    }, 900);
    return () => clearInterval(timer);
  }, [isPlaying, samples.length]);

  const activeSample = samples[Math.min(stepIdx, Math.max(0, samples.length - 1))] || null;
  const hd = data?.horizon_dynamics;
  const power = hd?.solar_array_power_assessment;
  const delays = data?.schedule_slip_sensitivity?.in_window_delays || [];
  const activeAudience = data?.audience_modes?.[audienceMode] || data?.audience_modes?.mission_planner;

  const filteredPrograms = useMemo(() => {
    const list = data?.programs || [];
    if (programFilter === 'ALL') return list;
    return list.filter((p) => p.program.toLowerCase().includes(programFilter.toLowerCase()) || p.agency.toLowerCase().includes(programFilter.toLowerCase()));
  }, [data, programFilter]);

  if (state === 'loading') {
    return (
      <section className="bg-[#0B101D] border border-cyan-900/30 rounded-xl p-5 text-sm text-slate-400" aria-label="Horizon panorama and operational windows">
        Loading 360° horizon panorama, countdown windows, and multi-program comparator…
      </section>
    );
  }

  if (state !== 'ready' || !data || !activeSample) {
    return (
      <section className="bg-[#0B101D] border border-amber-900/50 rounded-xl p-5 text-sm text-amber-200" role="status" aria-label="Horizon panorama and operational windows">
        Horizon panorama and multi-program comparator are unavailable; core simulation modules remain independently usable.
      </section>
    );
  }

  // Convert azimuth (0..360) and elevation (-8..+8 deg) into 360° panorama SVG coordinates (width 560, height 180)
  const panW = 560;
  const panH = 180;
  const azToX = (az) => Math.max(12, Math.min(panW - 12, ((Number(az) % 360) / 360) * panW));
  const elToY = (el) => {
    // Map [-6 deg, +6 deg] to [panH - 20, 20]
    const clamped = Math.max(-6, Math.min(6, Number(el)));
    return (panH / 2) - (clamped / 6) * (panH / 2 - 22);
  };

  const horizonDipY = elToY(data.site?.smooth_sphere_horizon_dip_deg || -0.107);
  const zeroY = elToY(0);

  return (
    <section className="bg-[#0B101D] border border-cyan-800/50 rounded-xl p-5 shadow-2xl space-y-5" aria-labelledby="horizon-ops-title" data-testid="horizon-ops-panel">
      {/* Header & Audience Skill-Level Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-300">
            <Compass className="h-4 w-4" aria-hidden="true" />
            <h2 id="horizon-ops-title" className="text-xs font-bold uppercase tracking-wider">
              360° Horizon Panorama, Sunset/Earthset Countdowns &amp; Multi-Program Comparator
            </h2>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            Real NASA JPL Horizons positions relative to the local horizon at Shackleton Rim ({hd.window_start_utc} to {hd.window_end_utc}), with vertical solar array geometry and launch-slip sensitivity.
          </p>
        </div>

        {/* Audience Mode Tabs */}
        <div className="flex items-center gap-1.5" role="tablist" aria-label="Audience skill level mode">
          <button
            type="button"
            role="tab"
            aria-selected={audienceMode === 'mission_planner'}
            onClick={() => setAudienceMode('mission_planner')}
            className={`px-3 py-1.5 rounded-lg border text-[10px] font-mono transition ${
              audienceMode === 'mission_planner'
                ? 'bg-cyan-950/80 border-cyan-400 text-cyan-200 font-bold'
                : 'bg-[#070B16] border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            Mission Planner Mode
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={audienceMode === 'educator_public'}
            onClick={() => setAudienceMode('educator_public')}
            className={`px-3 py-1.5 rounded-lg border text-[10px] font-mono transition ${
              audienceMode === 'educator_public'
                ? 'bg-amber-950/80 border-amber-400 text-amber-200 font-bold'
                : 'bg-[#070B16] border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            Educator &amp; Public Mode
          </button>
        </div>
      </div>

      {/* Audience Mode Callout */}
      {activeAudience && (
        <div className="rounded-lg border border-cyan-900/40 bg-[#070B16] p-3.5 text-xs space-y-2" data-testid="audience-callout">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="font-bold text-cyan-300 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-amber-300" aria-hidden="true" />
              {activeAudience.label}
            </span>
            <span className="text-[10px] font-mono text-slate-400">{activeAudience.focus}</span>
          </div>
          <ul className="space-y-1 text-[11px] text-slate-300 list-disc pl-4">
            {activeAudience.key_takeaways.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 360° Horizon Panorama + Temporal Animation Controls */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 rounded-lg border border-slate-800 bg-[#050811] p-3.5 flex flex-col justify-between">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-200">
              360° Local Horizon Panorama (Azimuth 0°–360° vs. Apparent Elevation -6° to +6°)
            </span>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setIsPlaying((p) => !p)}
                aria-label={isPlaying ? 'Pause horizon animation' : 'Animate horizon positions'}
                className="px-2.5 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-200 text-[10px] font-mono flex items-center gap-1"
              >
                <Play className="h-3 w-3" aria-hidden="true" />
                <span>{isPlaying ? 'Pause' : 'Animate 48h'}</span>
              </button>
              <button
                type="button"
                onClick={() => setStepIdx((i) => (i - 1 + samples.length) % samples.length)}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono"
              >
                Prev
              </button>
              <button
                type="button"
                onClick={() => setStepIdx((i) => (i + 1) % samples.length)}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono"
              >
                Next
              </button>
            </div>
          </div>

          <svg viewBox={`0 0 ${panW} ${panH}`} className="w-full h-44 rounded border border-slate-800/80 bg-[#03060C]" role="img" aria-label="360 degree lunar horizon panorama showing Sun and Earth positions">
            {/* Sky & Below-Horizon Ground Shading */}
            <rect x="0" y="0" width={panW} height={horizonDipY} fill="#060c1a" />
            <rect x="0" y={horizonDipY} width={panW} height={panH - horizonDipY} fill="#111827" opacity="0.85" />

            {/* Compass Azimuth Grid Lines */}
            {[
              { az: 0, label: '0° N (Prime Meridian)' },
              { az: 90, label: '90° E' },
              { az: 180, label: '180° S' },
              { az: 270, label: '270° W' },
              { az: 359.9, label: '360° N' },
            ].map((g) => {
              const x = azToX(g.az);
              return (
                <g key={g.label}>
                  <line x1={x} y1={10} x2={x} y2={panH - 15} stroke="#1e293b" strokeDasharray="2 2" />
                  <text x={x} y={panH - 4} textAnchor="middle" fill="#64748b" fontSize="8" fontFamily="monospace">
                    {g.label}
                  </text>
                </g>
              );
            })}

            {/* Local Horizontal (0 deg) and Smooth-Sphere Mast Horizon Dip */}
            <line x1="0" y1={zeroY} x2={panW} y2={zeroY} stroke="#f43f5e" strokeDasharray="4 3" strokeWidth="1" />
            <text x={panW - 8} y={zeroY - 4} textAnchor="end" fill="#f43f5e" fontSize="8" fontFamily="monospace">
              Local Horizontal (0.0°)
            </text>
            <line x1="0" y1={horizonDipY} x2={panW} y2={horizonDipY} stroke="#22d3ee" strokeWidth="1.2" opacity="0.8" />
            <text x="8" y={horizonDipY + 10} fill="#22d3ee" fontSize="8" fontFamily="monospace">
              Smooth-Sphere Horizon Dip ({data.site?.smooth_sphere_horizon_dip_deg}°)
            </text>

            {/* Full 48h Trajectory Dots for Sun and Earth */}
            {samples.map((s) => (
              <g key={s.step_index}>
                <circle cx={azToX(s.sun_azimuth_deg)} cy={elToY(s.sun_elevation_deg)} r="2" fill="#f59e0b" opacity="0.35" />
                <circle cx={azToX(s.earth_azimuth_deg)} cy={elToY(s.earth_elevation_deg)} r="2" fill="#38bdf8" opacity="0.35" />
              </g>
            ))}

            {/* Active Sun Disc */}
            <circle
              cx={azToX(activeSample.sun_azimuth_deg)}
              cy={elToY(activeSample.sun_elevation_deg)}
              r="7"
              fill="#f59e0b"
              stroke="#fef3c7"
              strokeWidth="1.5"
            />
            <text
              x={azToX(activeSample.sun_azimuth_deg)}
              y={elToY(activeSample.sun_elevation_deg) - 10}
              textAnchor="middle"
              fill="#fde68a"
              fontSize="8.5"
              fontFamily="monospace"
              fontWeight="bold"
            >
              SUN ({activeSample.sun_elevation_deg.toFixed(2)}° el, {activeSample.sun_azimuth_deg.toFixed(1)}° az)
            </text>

            {/* Active Earth Disc */}
            <circle
              cx={azToX(activeSample.earth_azimuth_deg)}
              cy={elToY(activeSample.earth_elevation_deg)}
              r="9"
              fill="#0284c7"
              stroke="#bae6fd"
              strokeWidth="1.5"
            />
            <text
              x={Math.min(panW - 85, azToX(activeSample.earth_azimuth_deg))}
              y={elToY(activeSample.earth_elevation_deg) - 12}
              textAnchor="middle"
              fill="#7dd3fc"
              fontSize="8.5"
              fontFamily="monospace"
              fontWeight="bold"
            >
              EARTH ({activeSample.earth_elevation_deg.toFixed(2)}° el)
            </text>
          </svg>

          {/* Step Selector Pills */}
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-400">
            <span>
              Step {activeSample.step_index}/{samples.length}: <strong className="text-cyan-300">T+{activeSample.elapsed_hours}h</strong> ({activeSample.timestamp})
            </span>
            <span>
              Sun clearance: <strong className="text-amber-300">+{activeSample.sun_horizon_clearance_deg}°</strong> · Earth clearance: <strong className="text-rose-300">{activeSample.earth_horizon_clearance_deg}°</strong>
            </span>
          </div>
        </div>

        {/* Operational Countdowns & Solar Array Geometry Cards */}
        <div className="space-y-2.5 text-xs">
          <div className="rounded-lg border border-amber-800/50 bg-[#070B16] p-3">
            <div className="flex items-center gap-1.5 text-amber-300 font-bold text-[11px] uppercase tracking-wider">
              <Sun className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Countdown to Sunset &amp; Solar Elevation</span>
            </div>
            <div className="mt-1.5 font-mono text-sm font-black text-white">
              {hd.sun_elevation_min_deg}° to +{hd.sun_elevation_max_deg}° <span className="text-[10px] text-emerald-300 font-normal">(100% Sunlit in 48h Window)</span>
            </div>
            <p className="mt-1 text-[10px] text-slate-400 leading-relaxed">{hd.sunset_status}</p>
          </div>

          <div className="rounded-lg border border-sky-800/50 bg-[#070B16] p-3">
            <div className="flex items-center gap-1.5 text-sky-300 font-bold text-[11px] uppercase tracking-wider">
              <Wifi className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Earthset / Earthrise Status &amp; Libration</span>
            </div>
            <div className="mt-1.5 font-mono text-sm font-black text-white">
              {hd.earth_elevation_min_deg}° to {hd.earth_elevation_max_deg}° <span className="text-[10px] text-rose-300 font-normal">(Below Horizon · +{hd.earth_elevation_rate_deg_per_hour}°/h)</span>
            </div>
            <p className="mt-1 text-[10px] text-slate-400 leading-relaxed">{hd.earth_visibility_status}</p>
          </div>

          {power && (
            <div className="rounded-lg border border-emerald-800/50 bg-[#070B16] p-3">
              <div className="flex items-center gap-1.5 text-emerald-300 font-bold text-[11px] uppercase tracking-wider">
                <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Polar Solar Array Power Multiplier</span>
              </div>
              <div className="mt-1.5 font-mono text-sm font-black text-emerald-300">
                {power.vertical_vs_horizontal_flux_multiplier}× Direct Flux Gain <span className="text-[10px] text-slate-300 font-normal">(Vertical vs. Horizontal)</span>
              </div>
              <p className="mt-1 text-[10px] text-slate-400 leading-relaxed">{power.engineering_explanation}</p>
            </div>
          )}
        </div>
      </div>

      {/* Schedule-Delay / Launch-Slip Sensitivity Table */}
      <div className="rounded-xl border border-cyan-800/40 bg-[#070d1e] p-4 shadow-lg space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            <span>Launch-Delay &amp; Schedule-Slip Sensitivity (Real JPL Horizons Window)</span>
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 font-semibold">
            {delays.length} EVALUATED SLIPS
          </span>
        </div>
        <div className="overflow-x-auto rounded-lg border border-slate-800 bg-[#040714]">
          <table className="w-full min-w-[740px] text-left text-xs border-collapse">
            <thead className="text-[10px] uppercase font-mono text-slate-300 bg-slate-900/90 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3.5 whitespace-nowrap">Schedule Slip</th>
                <th className="py-2.5 px-3.5 whitespace-nowrap">Delayed Start (UTC)</th>
                <th className="py-2.5 px-3.5 whitespace-nowrap">Sun Elevation</th>
                <th className="py-2.5 px-3.5 whitespace-nowrap">Earth Elevation</th>
                <th className="py-2.5 px-3.5 min-w-[260px]">Operational Impact on Power &amp; Comms</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300 text-xs">
              {delays.map((d) => (
                <tr key={d.delay_hours} className="hover:bg-slate-800/30 transition">
                  <td className="py-2 px-3.5 font-mono font-bold text-cyan-300 whitespace-nowrap">T+{d.delay_hours}h</td>
                  <td className="py-2 px-3.5 font-mono whitespace-nowrap text-slate-200">{d.start_timestamp_utc}</td>
                  <td className="py-2 px-3.5 font-mono font-bold text-amber-300 whitespace-nowrap">+{d.initial_sun_elevation_deg.toFixed(3)}°</td>
                  <td className="py-2 px-3.5 font-mono font-bold text-sky-300 whitespace-nowrap">{d.initial_earth_elevation_deg.toFixed(3)}°</td>
                  <td className="py-2 px-3.5 text-xs text-slate-300 leading-relaxed">{d.operational_impact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Curated Multi-Program Lunar Landing Sites Comparator */}
      <div className="rounded-lg border border-slate-800 bg-[#070B16] p-3.5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-purple-300 flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Multi-Program Lunar Landing Sites Comparator (Apollo, CLPS, CSA, ISRO, CNSA &amp; Artemis)</span>
            </h3>
            <p className="text-[10px] text-slate-400">
              Contrasts historical equatorial Apollo missions with commercial CLPS targets, international lunar programs, and Artemis South Pole sites.
            </p>
          </div>
          <div className="flex flex-wrap gap-1 text-[10px] font-mono">
            {['ALL', 'Artemis', 'CLPS', 'CSA', 'ISRO', 'CNSA', 'Apollo'].map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => setProgramFilter(tag)}
                className={`px-2 py-0.5 rounded border transition ${
                  programFilter === tag
                    ? 'bg-purple-900/60 border-purple-400 text-purple-200 font-bold'
                    : 'bg-[#090D18] border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2.5" role="list" aria-label="Curated multi-program lunar landing sites">
          {filteredPrograms.map((site) => (
            <article key={site.id} role="listitem" className="rounded-lg border border-slate-800/90 bg-[#0B101D] p-3 space-y-1.5 text-[11px]">
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-bold text-slate-100">{site.name}</h4>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/50 text-cyan-300 whitespace-nowrap">
                  {site.agency}
                </span>
              </div>
              <div className="text-[10px] font-mono text-purple-300">
                {site.program} · {site.lat_deg}°, {site.lon_deg}°E
              </div>
              <p className="text-[10px] text-slate-300">
                <strong className="text-amber-300">Solar:</strong> {site.solar_regime}
              </p>
              <p className="text-[10px] text-slate-300">
                <strong className="text-emerald-300">Comms:</strong> {site.earth_comms_regime}
              </p>
              <div className="pt-1 flex items-center justify-between text-[9px] font-mono text-slate-400 border-t border-slate-800/70">
                <span>{site.power_array_design}</span>
                <a href={site.reference_url} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline inline-flex items-center gap-0.5">
                  <span>Ref</span>
                  <ExternalLink className="h-2.5 w-2.5" aria-hidden="true" />
                </a>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
