import React from 'react';
import { CheckCircle2, ShieldAlert, XCircle } from 'lucide-react';

export default function ScientificValidationPanel({ report, stale = false }) {
  if (!report || stale) return null;
  const iconFor = status => status === 'pass' ? CheckCircle2 : status === 'blocked' ? XCircle : ShieldAlert;
  const colorFor = status => status === 'pass' ? 'text-emerald-400' : status === 'blocked' ? 'text-rose-400' : 'text-amber-300';
  return (
    <section className="bg-[#0B101D] border border-amber-900/50 rounded-xl p-5 shadow-xl" aria-labelledby="scientific-validation-title">
      <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div><h2 id="scientific-validation-title" className="text-xs font-bold uppercase tracking-wider text-amber-300">Scientific Integrity Gate</h2><p className="mt-1 text-[11px] text-slate-400">{report.meaning}</p></div>
        <span className="text-[10px] font-mono px-2 py-1 rounded border border-amber-700/60 bg-amber-950/30 text-amber-300">{report.status.replaceAll('_', ' ')}</span>
      </div>
      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2" role="list" aria-label="Scientific validation checks">
        {report.checks.map(check => { const Icon = iconFor(check.status); return <div key={check.id} role="listitem" className="flex items-start gap-2 p-2 rounded border border-slate-800 bg-[#070B16] text-[10px]"><Icon className={`h-3.5 w-3.5 mt-0.5 ${colorFor(check.status)}`} aria-hidden="true" /><span><strong className={colorFor(check.status)}>{check.id.replaceAll('_', ' ')}</strong><span className="block text-slate-400 mt-0.5">{check.message}</span></span></div>; })}
      </div>
      <p className="mt-3 text-[10px] text-slate-500">Scope: {report.real_data_scope}</p>
    </section>
  );
}
