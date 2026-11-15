import React, { useEffect, useState } from 'react';
import { ArrowRight, ClipboardCheck, Route, FileText } from 'lucide-react';
import { API_BASE_URL } from './config';

export default function JudgeEvidencePanel({ embedded = false }) {
  const [pack, setPack] = useState(null);
  const [state, setState] = useState('loading');

  useEffect(() => {
    if (embedded && typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') return undefined;
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/v1/judge/evidence-pack`, { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('Evidence pack unavailable'); return response.json(); })
      .then(value => { if (!Array.isArray(value?.walkthrough) || !value?.score_support) throw new Error('Invalid evidence pack'); setPack(value); setState('ready'); })
      .catch(error => { if (error.name !== 'AbortError') setState('error'); });
    return () => controller.abort();
  }, []);

  if (state === 'loading') return <section className="bg-[#0B101D] border border-orange-900/30 rounded-xl p-5" aria-label="Judge evidence pack">Loading judge evidence pack…</section>;
  if (state !== 'ready') return <section className="bg-[#0B101D] border border-amber-900/50 rounded-xl p-5 text-sm text-amber-200" role="status" aria-label="Judge evidence pack">Judge evidence pack is unavailable; all project modules remain independently usable.</section>;

  return (
    <section className="bg-[#0B101D] border border-orange-900/50 rounded-xl p-5 shadow-2xl" aria-labelledby="judge-pack-title">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div><div className="flex items-center gap-2 text-orange-300"><Route className="h-4 w-4" aria-hidden="true" /><h2 id="judge-pack-title" className="text-xs font-bold uppercase tracking-wider">Judge Evidence Pack</h2></div><p className="mt-1 text-[11px] text-slate-400 max-w-3xl">{pack.purpose}</p></div>
        <span className="text-[10px] font-mono px-2 py-1 rounded border border-orange-700/60 bg-orange-950/30 text-orange-300 whitespace-nowrap">5-STEP WALKTHROUGH</span>
      </div>
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3.5" role="list" aria-label="Judge evidence walkthrough">
        {pack.walkthrough.map(item => (
          <article key={item.step} role="listitem" className="rounded-xl border border-slate-800/80 bg-[#070e1c] p-4 flex flex-col justify-between shadow-md space-y-2">
            <div>
              <div className="flex items-center gap-2 text-orange-400 text-xs font-mono font-bold">
                <span className="px-1.5 py-0.5 rounded bg-orange-950/80 border border-orange-800/50">STEP 0{item.step}</span>
                <ArrowRight className="h-3.5 w-3.5 text-orange-400" aria-hidden="true" />
              </div>
              <h3 className="mt-2 text-xs font-bold text-slate-100">{item.title}</h3>
              <p className="mt-1 text-[11px] text-slate-400 italic">{item.question}</p>
              <p className="mt-2 text-[11px] leading-relaxed text-slate-200">{item.answer}</p>
            </div>
            <div className="mt-2 pt-2 border-t border-slate-800 text-[10px] font-mono text-cyan-300 break-words">
              {item.evidence.join(' · ')}
            </div>
          </article>
        ))}
      </div>
      <div className="mt-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3.5" aria-label="Criterion evidence summary">
        {Object.entries(pack.score_support).map(([criterion, evidence]) => (
          <div key={criterion} className="rounded-xl border border-slate-800/80 bg-[#070e1c] p-4 shadow-md space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-200 border-b border-slate-800 pb-2">
              <ClipboardCheck className="h-4 w-4 text-emerald-400" aria-hidden="true" />
              <span>{criterion}</span>
            </div>
            <div className="text-[11px] text-slate-300 leading-relaxed space-y-1">
              {evidence.map((ev, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <span className="text-cyan-400 font-bold">•</span>
                  <span>{ev}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {pack.presentation_storytelling?.pitch_arc && (
        <div className="mt-4 pt-3 border-t border-slate-800/80">
          <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-orange-300 mb-2">
            <FileText className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{pack.presentation_storytelling.headline} (Presentation Rubric Support)</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2 text-[10px]">
            {pack.presentation_storytelling.pitch_arc.map(item => (
              <div key={item.minute} className="rounded-lg border border-slate-800 bg-[#070B16] p-2.5">
                <div className="font-mono text-orange-300 font-bold">{item.minute} · {item.stage}</div>
                <p className="mt-1 text-slate-400 leading-relaxed">{item.script}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="mt-3 text-[10px] text-slate-500">This pack organizes evidence for review; it does not manufacture an official score. Known scientific limitations remain visible.</p>
    </section>
  );
}
