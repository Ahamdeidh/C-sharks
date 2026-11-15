import React, { useEffect, useState } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2, Target } from 'lucide-react';
import { API_BASE_URL } from './config';

export default function DecisionBriefPanel({ embedded = false }) {
  const [brief, setBrief] = useState(null);
  const [state, setState] = useState('loading');

  useEffect(() => {
    if (embedded && typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') return undefined;
    const controller = new AbortController();
    if (!API_BASE_URL) {
      setState('unavailable');
      return () => controller.abort();
    }
    fetch(`${API_BASE_URL}/api/v1/mission/decision-brief`, { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error('Decision brief unavailable');
        return response.json();
      })
      .then(data => {
        if (!Array.isArray(data?.ranked_regions) || !Array.isArray(data?.recommended_work_packages) || !data?.provenance?.ranking_formula) {
          throw new Error('Decision brief response has an invalid shape');
        }
        setBrief(data);
        setState('ready');
      })
      .catch(error => {
        if (error.name !== 'AbortError') setState('error');
      });
    return () => controller.abort();
  }, []);

  if (state === 'loading') {
    return <section className="bg-[#0B101D] border border-cyan-900/30 rounded-xl p-5" aria-label="Mission decision brief">Loading mission decision brief…</section>;
  }
  if (state !== 'ready' || !brief) {
    return <section className="bg-[#0B101D] border border-amber-900/50 rounded-xl p-5 text-sm text-amber-200" role="status" aria-label="Mission decision brief">Decision brief is unavailable. The exploratory simulator remains usable.</section>;
  }

  return (
    <section className="bg-[#0B101D] border border-cyan-900/40 rounded-xl p-5 shadow-2xl" aria-labelledby="decision-brief-title">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-300">
            <Target className="h-4 w-4" aria-hidden="true" />
            <h2 id="decision-brief-title" className="text-xs font-bold uppercase tracking-wider">Mission Decision Brief</h2>
          </div>
          <p className="mt-1 text-[11px] text-slate-400 max-w-3xl">A ranked triage shortlist that turns archive evidence into the next research actions. It is not a landing certificate.</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded border border-amber-700/60 bg-amber-950/30 text-amber-300 whitespace-nowrap">REFERENCE TRIAGE ONLY</span>
      </div>

      <div className="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div>
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-300 mb-2">Priority regions</h3>
          <div className="space-y-2" role="list" aria-label="Ranked priority regions">
            {brief.ranked_regions.map(region => (
              <article key={region.area_id} className="rounded-lg border border-slate-800 bg-[#070B16] p-3" role="listitem">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800 text-[11px] font-mono flex items-center justify-center">{region.rank}</span>
                    <h4 className="text-xs font-semibold text-slate-100">{region.name}</h4>
                  </div>
                  <span className="text-xs font-mono font-bold text-cyan-300">{region.triage_index}/100</span>
                </div>
                <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono bg-[#030610] p-2 rounded-lg border border-slate-800/80">
                  <span>Sun: <strong className="text-amber-300 font-bold">{region.sun_only_mean_days.toFixed(2)}d</strong></span>
                  <span>Source field: <strong className="text-emerald-300 font-bold">{region.sun_plus_earth_mean_days.toFixed(2)}d</strong></span>
                  <span>Approx PSR: <strong className="text-purple-300 font-bold">{region.approx_psr_polygons}</strong></span>
                </div>
                <p className="mt-2 text-[10px] text-slate-500">{region.recommended_next_action}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-3">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-amber-300 flex items-center gap-2"><AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" /> Evidence blockers</h3>
            <ul className="mt-2 space-y-1.5 text-[10px] text-slate-300 list-disc pl-4">
              {brief.ranked_regions[0]?.blockers.map(blocker => <li key={blocker}>{blocker}</li>)}
            </ul>
          </div>
          <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/10 p-3">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Recommended work packages</h3>
            <ol className="mt-2 space-y-2 text-[10px] text-slate-300">
              {brief.recommended_work_packages.map(item => <li key={item.priority} className="flex gap-2"><span className="font-mono text-cyan-400">{item.priority}.</span><span>{item.action} <span className="text-slate-500">Unlocks: {item.unlocks}</span></span></li>)}
            </ol>
          </div>
          <div className="text-[10px] text-slate-500 flex items-start gap-1.5"><ArrowRight className="h-3 w-3 mt-0.5 text-cyan-500" aria-hidden="true" /> Ranking formula: {brief.provenance.ranking_formula}</div>
        </div>
      </div>
    </section>
  );
}
