import React, { useEffect, useState } from 'react';
import { ExternalLink, Link2, ShieldCheck } from 'lucide-react';
import { API_BASE_URL } from './config';

export default function ChallengeAlignmentPanel({ embedded = false }) {
  const [data, setData] = useState(null);
  const [state, setState] = useState('loading');

  useEffect(() => {
    if (embedded && typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') {
      return undefined;
    }
    let mounted = true;
    const controller = new AbortController();
    if (!API_BASE_URL) {
      setState('error');
      return () => {
        mounted = false;
        controller.abort();
      };
    }
    fetch(`${API_BASE_URL}/api/v1/challenge/alignment`, { signal: controller.signal })
      .then(response => {
        if (!response.ok) throw new Error('Alignment unavailable');
        return response.json();
      })
      .then(value => {
        if (!mounted) return;
        if (!Array.isArray(value?.criteria) || !value?.coverage) throw new Error('Invalid alignment response');
        setData(value);
        setState('ready');
      })
      .catch(error => {
        if (!mounted || error?.name === 'AbortError' || error?.message === 'Unknown url') return;
        setState('error');
      });
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [embedded]);

  if (state === 'loading' && embedded) return null;

  const official = data?.official_challenge || {
    event: '2026 NASA International Space Apps Challenge',
    challenge_number: 'Challenge #5 (CLPS Lunar Mission Browser / South Pole Site & Window Selection)',
    official_title: 'Lunar Landing Site Navigator',
    official_url: 'https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/',
    challenges_directory_url: 'https://www.spaceappschallenge.org/2026/challenges/',
  };

  return (
    <section className="bg-[#0B101D] border border-cyan-900/30 rounded-xl p-5 shadow-xl space-y-4" aria-labelledby="challenge-alignment-heading">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2 border-b border-slate-800 pb-4">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-cyan-300 flex items-center gap-1.5">
            <Link2 className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Relevance &amp; Official NASA Space Apps 2026 Traceability</span>
          </div>
          <h3 id="challenge-alignment-heading" className="text-sm font-bold text-white mt-1">
            Challenge Alignment Matrix — {official.official_title} — {official.challenge_number}
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Maps every official challenge objective (OBJ-01..OBJ-07) directly to its implemented feature, API route, data source tier, and spatial resolution boundary.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <a
            href={official.official_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] font-mono px-2.5 py-1 rounded bg-cyan-950/70 text-cyan-200 border border-cyan-700/60 hover:border-cyan-400 inline-flex items-center gap-1"
          >
            <span>Official Challenge Page</span>
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
          {data?.coverage && (
            <span className="text-[10px] font-mono px-2.5 py-1 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-700/50">
              {data.coverage.implementation_status}
            </span>
          )}
        </div>
      </div>

      <p className="text-xs text-amber-200 bg-amber-950/30 border border-amber-900/50 rounded p-2" data-testid="dem-coverage-disclosure">
        Spatial coverage limit: the bundled central DEM subset is 601 × 601 pixels (about 48 × 48 km at 80 m/px). Locations beyond this subset are outside DEM coverage; terrain-aware results are not available there.
      </p>
      {state === 'loading' && <p className="text-xs font-mono text-slate-400" role="status">Loading challenge alignment matrix...</p>}
      {state === 'error' && <p className="text-xs font-mono text-amber-300" role="alert">Challenge alignment matrix is unavailable.</p>}

      {state === 'ready' && data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.criteria.map(item => (
              <article key={item.id} className="p-3.5 rounded-lg bg-[#070B14] border border-slate-800 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-xs font-bold text-slate-100">{item.challenge_goal}</h4>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 shrink-0">
                    {item.status.replace(/_/g, ' ')}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{item.project_response}</p>
                <div className="text-[11px] text-slate-400"><strong className="text-slate-200">NASA/JPL &amp; archive role:</strong> {item.data_role}</div>
                <div className="text-[11px] text-amber-300/90"><strong className="text-amber-200">Remaining gap / limit:</strong> {item.gap}</div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {item.evidence.map(ev => (
                    <span key={ev} className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-700">
                      {ev}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>

          {Array.isArray(data.challenge_objectives_detail) && (
            <div className="p-3.5 rounded-lg bg-[#070B14] border border-cyan-900/40 space-y-2">
              <div className="text-xs font-bold text-cyan-300 uppercase tracking-wider">
                Direct Feature-to-Requirement Traceability Matrix (Official Objectives OBJ-01 to OBJ-07)
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {data.challenge_objectives_detail.map(obj => (
                  <div key={obj.objective} className="p-2.5 rounded bg-slate-950/70 border border-slate-800 text-[11px] space-y-1">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-bold text-slate-100">{obj.objective}</span>
                      {obj.requirement_id && (
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {obj.requirement_id}
                        </span>
                      )}
                    </div>
                    <div className="text-slate-300">{obj.implementation}</div>
                    {obj.code_and_endpoint && (
                      <div className="text-[10px] font-mono text-emerald-300">
                        Route/Module: {obj.code_and_endpoint}
                      </div>
                    )}
                    {obj.source_and_limit && (
                      <div className="text-[10px] font-mono text-amber-300/90">
                        Source &amp; Limit: {obj.source_and_limit}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(data.partner_resources) && (
            <div className="p-3.5 rounded-lg bg-[#070B14] border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-emerald-300 uppercase tracking-wider">
                Official Challenge, NASA &amp; Space Agency Partner Resources Integrated
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {data.partner_resources.map(res => (
                  <div key={res.name} className="p-2.5 rounded bg-slate-950/70 border border-slate-800 text-[11px]">
                    <a href={res.url} target="_blank" rel="noopener noreferrer" className="font-bold text-cyan-300 hover:underline inline-flex items-center gap-1">
                      <span>{res.name}</span>
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                    </a>
                    <p className="text-slate-400 mt-0.5">{res.integration}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-[11px] font-mono text-slate-300 flex items-start gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" aria-hidden="true" />
            <span>{data.honesty_note}</span>
          </div>
        </>
      )}
    </section>
  );
}
