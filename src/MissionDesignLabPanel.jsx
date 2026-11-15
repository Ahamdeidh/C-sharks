import React, { useEffect, useMemo, useState } from 'react';
import { FlaskConical, Lightbulb, Sparkles } from 'lucide-react';
import { API_BASE_URL } from './config';

export default function MissionDesignLabPanel({ embedded = false }) {
  const [lab, setLab] = useState(null);
  const [mode, setMode] = useState('balanced');
  const [state, setState] = useState('loading');

  useEffect(() => {
    if (embedded && typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') return undefined;
    const controller = new AbortController();
    if (!API_BASE_URL) { setState('error'); return () => controller.abort(); }
    fetch(`${API_BASE_URL}/api/v1/mission/design-lab`, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error('Design lab unavailable'); return r.json(); })
      .then(value => { if (!Array.isArray(value?.scenarios)) throw new Error('Invalid lab response'); setLab(value); setState('ready'); })
      .catch(error => { if (error.name !== 'AbortError') setState('error'); });
    return () => controller.abort();
  }, []);

  const selected = useMemo(() => lab?.scenarios?.find(item => item.mode_id === mode) || lab?.scenarios?.[0], [lab, mode]);

  if (state === 'loading') return <section className="bg-[#0B101D] border border-purple-900/30 rounded-xl p-5" aria-label="Mission design lab">Loading mission design lab…</section>;
  if (state !== 'ready' || !selected) return <section className="bg-[#0B101D] border border-amber-900/50 rounded-xl p-5 text-sm text-amber-200" role="status" aria-label="Mission design lab">Mission design lab is unavailable; the core navigator remains usable.</section>;

  return (
    <section className="bg-[#0B101D] border border-purple-900/50 rounded-xl p-5 shadow-2xl" aria-labelledby="design-lab-title">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2 text-purple-300"><FlaskConical className="h-4 w-4" aria-hidden="true" /><h2 id="design-lab-title" className="text-xs font-bold uppercase tracking-wider">Mission Design Lab</h2><Sparkles className="h-3.5 w-3.5 text-amber-300" aria-hidden="true" /></div>
          <p className="mt-1 text-[11px] text-slate-400 max-w-3xl">{lab.concept}</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded border border-purple-700/60 bg-purple-950/30 text-purple-300 whitespace-nowrap">COUNTERFACTUAL EXPLORATION</span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="Mission priority modes">
        {lab.scenarios.map(scenario => <button key={scenario.mode_id} type="button" role="tab" aria-selected={scenario.mode_id === selected.mode_id} onClick={() => setMode(scenario.mode_id)} className={`px-3 py-2 rounded-lg border text-[10px] font-mono transition focus:outline-none focus:ring-2 focus:ring-purple-400 ${scenario.mode_id === selected.mode_id ? 'bg-purple-900/50 border-purple-400 text-purple-200' : 'bg-[#070B16] border-slate-800 text-slate-400 hover:border-purple-800'}`}>{scenario.label}</button>)}
      </div>
      <div className="mt-3 p-3 rounded-lg bg-purple-950/20 border border-purple-900/50 text-[11px] text-slate-300"><span className="text-purple-300 font-bold">{selected.description}</span><span className="block mt-1 text-slate-500">{selected.creative_question}</span></div>
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3" role="list" aria-label={`${selected.label} ranked regions`}>
        {selected.ranked_regions.map(region => (
          <article key={region.area_id} role="listitem" className="rounded-xl border border-slate-800/80 bg-[#070e1c] p-3.5 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-mono text-purple-300 font-bold px-1.5 py-0.5 rounded bg-purple-950/80 border border-purple-800/50">#{region.rank}</span>
                <span className="text-sm font-black font-mono text-white">{region.score}</span>
              </div>
              <h3 className="mt-2 text-xs font-bold text-slate-200">{region.name}</h3>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-800 space-y-1 text-[10px] font-mono text-slate-400">
              <div className="flex justify-between"><span>Solar:</span> <span className="text-amber-300 font-semibold">{region.contribution.solar}</span></div>
              <div className="flex justify-between"><span>Comms:</span> <span className="text-emerald-300 font-semibold">{region.contribution.communications}</span></div>
              <div className="flex justify-between"><span>Science:</span> <span className="text-cyan-300 font-semibold">{region.contribution.science}</span></div>
            </div>
          </article>
        ))}
      </div>
      {lab.sensitivity && (
        <div className="mt-4 rounded-xl border border-slate-800/80 bg-[#070e1c] p-4 shadow-md" aria-label="Weight sensitivity analysis">
          <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">Weight sensitivity — how robust is the shortlist?</h3>
          <p className="mt-1 text-[11px] text-slate-400">{lab.sensitivity.interpretation}</p>
          <div className="mt-3 space-y-2" role="list" aria-label="Share of random weightings in which each region ranks first">
            {lab.sensitivity.regions.map(row => (
              <div key={row.area_id} role="listitem" className="flex items-center gap-3 text-[10px] font-mono text-slate-300">
                <span className="w-40 truncate font-semibold text-slate-200">{row.name}</span>
                <div className="flex-1 h-2 rounded bg-slate-800 overflow-hidden"><div className="h-full rounded bg-cyan-400 shadow-[0_0_8px_rgba(56,189,248,0.5)]" style={{ width: `${row.top_rank_share_pct}%` }} /></div>
                <span className="min-w-[140px] text-right whitespace-nowrap text-cyan-300 font-bold">{row.top_rank_share_pct}% first · rank {row.best_rank}–{row.worst_rank}</span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] text-slate-500 font-mono">{lab.sensitivity.draws.toLocaleString()} random weightings, fixed seed {lab.sensitivity.seed}.</p>
        </div>
      )}
      <div className="mt-4 flex items-start gap-2 text-[10px] text-slate-500"><Lightbulb className="h-3.5 w-3.5 text-amber-300 mt-0.5" aria-hidden="true" /><span>{lab.novelty.join(' ')}</span></div>
    </section>
  );
}
