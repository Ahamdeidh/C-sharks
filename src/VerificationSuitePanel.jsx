import React, { useEffect, useState } from 'react';
import { BadgeCheck, XCircle } from 'lucide-react';
import { API_BASE_URL } from './config';

export default function VerificationSuitePanel({ embedded = false }) {
  const [suite, setSuite] = useState(null);
  const [state, setState] = useState('loading');

  useEffect(() => {
    if (embedded && typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') return undefined;
    const controller = new AbortController();
    if (!API_BASE_URL) { setState('error'); return () => controller.abort(); }
    fetch(`${API_BASE_URL}/api/v1/validation/benchmarks`, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error('Benchmarks unavailable'); return r.json(); })
      .then(value => { if (!Array.isArray(value?.results)) throw new Error('Invalid benchmark response'); setSuite(value); setState('ready'); })
      .catch(error => { if (error.name !== 'AbortError') setState('error'); });
    return () => controller.abort();
  }, []);

  if (state === 'loading') return <section className="bg-[#0B101D] border border-emerald-900/30 rounded-xl p-5 text-sm text-slate-400" aria-label="Verification suite">Running verification suite…</section>;
  if (state !== 'ready') return <section className="bg-[#0B101D] border border-amber-900/50 rounded-xl p-5 text-sm text-amber-200" role="status" aria-label="Verification suite">Verification suite is unavailable; the core navigator remains usable.</section>;

  return (
    <section className="bg-[#0B101D] border border-emerald-900/50 rounded-xl p-5 shadow-xl" aria-labelledby="verification-suite-title">
      <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div>
          <h2 id="verification-suite-title" className="text-xs font-bold uppercase tracking-wider text-emerald-300">Independent Verification Suite</h2>
          <p className="mt-1 text-[11px] text-slate-400">{suite.meaning}</p>
        </div>
        <span className={`text-[10px] font-mono px-2 py-1 rounded border whitespace-nowrap ${suite.all_passed ? 'border-emerald-700/60 bg-emerald-950/30 text-emerald-300' : 'border-rose-700/60 bg-rose-950/30 text-rose-300'}`}>{suite.passed}/{suite.total} PASSED</span>
      </div>
      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2" role="list" aria-label="Benchmark results">
        {suite.results.map(item => {
          const Icon = item.passed ? BadgeCheck : XCircle;
          return (
            <div key={item.id} role="listitem" className="flex items-start gap-2 p-2 rounded border border-slate-800 bg-[#070B16] text-[10px]">
              <Icon className={`h-3.5 w-3.5 mt-0.5 ${item.passed ? 'text-emerald-400' : 'text-rose-400'}`} aria-hidden="true" />
              <span><strong className="text-slate-200">{item.title}</strong><span className="block text-slate-500 mt-0.5 font-mono">{item.reference}</span></span>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-[10px] text-slate-500">Not covered: {suite.not_covered.join(' ')}</p>
    </section>
  );
}
