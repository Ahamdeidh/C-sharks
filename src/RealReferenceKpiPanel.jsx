import React from 'react';
import { Satellite } from 'lucide-react';

const Metric = ({ label, value, unit, tone }) => (
  <div className="rounded-lg border border-slate-800 bg-[#070B16] p-3">
    <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
    <div className={`mt-1 text-xl font-black font-mono ${tone}`}>{value}<span className="text-[10px] text-slate-500 ml-1">{unit}</span></div>
  </div>
);

export default function RealReferenceKpiPanel({ reference, terrainInfo, stale = false }) {
  if (!reference || stale) return null;
  const terrainRan = Boolean(terrainInfo?.dem_product);
  return (
    <section className="bg-[#0B101D] border border-cyan-900/50 rounded-xl p-5 shadow-xl" aria-labelledby="real-reference-title">
      <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div>
          <div className="flex items-center gap-2 text-cyan-300"><Satellite className="h-4 w-4" aria-hidden="true" /><h2 id="real-reference-title" className="text-xs font-bold uppercase tracking-wider">Real-Data Reference KPIs</h2></div>
          <p className="mt-1 text-[11px] text-slate-400">{reference.label}. {reference.steps_evaluated} of {reference.steps_requested} requested steps are covered by real NASA JPL Horizons angles.</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded border border-cyan-700/60 bg-cyan-950/30 text-cyan-300 whitespace-nowrap">{terrainRan ? 'TERRAIN APPLIED' : 'NO TERRAIN'}</span>
      </div>
      <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2">
        <Metric label="Illumination" value={reference.avg_illumination_pct} unit="%" tone="text-amber-300" />
        <Metric label="Earth visibility" value={reference.geometric_dte_visibility_pct} unit="%" tone="text-emerald-300" />
        <Metric label="Longest darkness" value={reference.longest_continuous_darkness_hours} unit="h" tone="text-slate-200" />
        <Metric label="Longest Earth blackout" value={reference.longest_earth_blackout_hours} unit="h" tone="text-rose-300" />
      </div>
      {reference.vertical_array_cosine_factor != null && (
        <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 text-[10px] font-mono">
          <div className="rounded border border-slate-800 bg-[#070B16] p-2 text-slate-300">
            Vertical Solar Array Factor (cos θ): <strong className="text-emerald-300">{(reference.vertical_array_cosine_factor * 100).toFixed(2)}%</strong> vs Flat (sin θ): <strong className="text-amber-300">{(reference.horizontal_surface_sine_factor * 100).toFixed(2)}%</strong>
          </div>
          <div className="rounded border border-slate-800 bg-[#070B16] p-2 text-slate-300">
            Sunset status: <strong className="text-amber-200">{reference.sunset_countdown_status}</strong>
          </div>
          <div className="rounded border border-slate-800 bg-[#070B16] p-2 text-slate-300">
            Earthset status: <strong className="text-sky-200">{reference.earthset_countdown_status}</strong>
          </div>
        </div>
      )}
      <ul className="mt-3 space-y-1 text-[10px] text-slate-500 list-disc pl-4">
        {reference.assumptions.map(item => <li key={item}>{item}</li>)}
      </ul>
      <p className="mt-2 text-[10px] text-amber-300/80">{reference.interpretation_limit}</p>
    </section>
  );
}
