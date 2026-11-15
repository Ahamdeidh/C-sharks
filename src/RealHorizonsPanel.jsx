import React, { useMemo } from 'react';
import { Satellite, ShieldCheck, AlertTriangle } from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine
} from 'recharts';

const SOURCE_LABELS = {
  jpl_horizons_live: { text: 'LIVE JPL HORIZONS', cls: 'bg-emerald-950/70 text-emerald-300 border-emerald-700/60' },
  jpl_horizons_recorded_fixture: { text: 'RECORDED JPL HORIZONS FIXTURE', cls: 'bg-cyan-950/70 text-cyan-300 border-cyan-700/60' }
};

export default function RealHorizonsPanel({ ephemeris, stale }) {
  const data = useMemo(() => {
    if (!ephemeris?.samples?.length) return [];
    return ephemeris.samples.map((s) => ({
      step: s.step_index,
      label: s.timestamp ? s.timestamp.slice(5, 16).replace('T', ' ') : `#${s.step_index}`,
      sun_el: s.sun_elevation_deg,
      earth_el: s.earth_elevation_deg,
      sun_az: s.sun_azimuth_deg,
      earth_az: s.earth_azimuth_deg
    }));
  }, [ephemeris]);

  if (!ephemeris) {
    return (
      <section
        aria-label="Real NASA JPL Horizons ephemeris check"
        className="bg-[#0B101D] border border-slate-800/80 rounded-xl p-4 text-xs font-mono text-slate-400 flex items-start space-x-2.5"
      >
        <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <span className="text-slate-200 font-bold">Real NASA Ephemeris Check: </span>
          No real NASA ephemeris covers this request: no recorded Horizons fixture covers this requested site or date. Recorded files include a Shackleton 48-hour series and five site-specific fixtures covering 2026-11-14 through 2026-11-20; each is limited to its recorded site/window. The original fixture covers the
          Shackleton Rim preset (<code className="text-cyan-300">-89.9°, 0.0°</code>) from{' '}
          <code className="text-cyan-300">2026-11-14 12:00 UTC</code> to{' '}
          <code className="text-cyan-300">2026-11-16 12:00 UTC</code>. Set{' '}
          <code className="text-cyan-300">ENABLE_LIVE_HORIZONS=1</code> on the backend to query JPL Horizons live, subject to network access.
        </div>
      </section>
    );
  }

  const badge = SOURCE_LABELS[ephemeris.source] || { text: ephemeris.source, cls: 'bg-slate-900 text-slate-300 border-slate-700' };
  const { coverage, summary } = ephemeris;

  return (
    <section
      aria-label="Real NASA JPL Horizons ephemeris check"
      className={`bg-[#0B101D] border border-cyan-900/40 rounded-xl p-5 shadow-xl transition-opacity ${stale ? 'opacity-50' : 'opacity-100'}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
        <div className="flex items-center space-x-2">
          <Satellite className="h-4 w-4 text-cyan-400" aria-hidden="true" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100">
            Real NASA Data — JPL Horizons Apparent Sun &amp; Earth Elevation
          </h3>
        </div>
        <div className="flex items-center space-x-2 text-[10px] font-mono">
          <span className={`px-2 py-0.5 rounded border font-bold ${badge.cls}`}>{badge.text}</span>
          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
            {coverage.steps_with_real_ephemeris}/{coverage.steps_requested} steps covered
          </span>
        </div>
      </div>

      {data.length > 0 && (
        <>
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-[11px] font-mono">
            <div className="p-2.5 rounded bg-[#070B14] border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Sun Elevation Range</div>
              <div className="text-amber-300 font-bold mt-0.5">
                {Number(summary.sun_elevation_min_deg ?? Math.min(...data.map((d) => d.sun_el))).toFixed(3)}° to {Number(summary.sun_elevation_max_deg ?? Math.max(...data.map((d) => d.sun_el))).toFixed(3)}°
              </div>
              <div className="text-[9px] text-emerald-400 mt-0.5">Source: JPL Horizons DE440</div>
            </div>
            <div className="p-2.5 rounded bg-[#070B14] border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Earth Elevation Range</div>
              <div className="text-sky-300 font-bold mt-0.5">
                {Number(summary.earth_elevation_min_deg ?? Math.min(...data.map((d) => d.earth_el))).toFixed(3)}° to {Number(summary.earth_elevation_max_deg ?? Math.max(...data.map((d) => d.earth_el))).toFixed(3)}°
              </div>
              <div className="text-[9px] text-emerald-400 mt-0.5">Source: JPL Horizons DE440</div>
            </div>
            <div className="p-2.5 rounded bg-[#070B14] border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Sun &gt; 0° (Local Horizontal)</div>
              <div className="text-slate-100 font-bold mt-0.5">{summary.sun_above_local_horizontal_pct}%</div>
              <div className="text-[9px] text-amber-300 mt-0.5">Limit: Smooth Horizontal (0°)</div>
            </div>
            <div className="p-2.5 rounded bg-[#070B14] border border-slate-800/80">
              <div className="text-slate-400 text-[10px]">Earth &gt; 0° (Local Horizontal)</div>
              <div className="text-slate-100 font-bold mt-0.5">{summary.earth_above_local_horizontal_pct}%</div>
              <div className="text-[9px] text-amber-300 mt-0.5">Limit: Smooth Horizontal (0°)</div>
            </div>
          </div>

          <div
            className="mt-4 w-full h-48"
            style={{ minWidth: 320, minHeight: 192 }}
            role="img"
            aria-label="Line chart of NASA Horizons apparent elevation of the Sun and Earth over time"
          >
            <ResponsiveContainer width="100%" height="100%" minWidth={320} minHeight={180} initialDimension={{ width: 800, height: 192 }}>
              <LineChart data={data} margin={{ top: 10, right: 12, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
                <XAxis dataKey="label" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 9, fontFamily: 'monospace' }} interval="preserveStartEnd" />
                <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }} domain={['auto', 'auto']} unit="°" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0B101D', borderColor: '#1e293b', borderRadius: '8px', fontSize: '11px', fontFamily: 'monospace' }}
                  formatter={(v, name) => [`${Number(v).toFixed(3)}°`, name]}
                />
                <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" label={{ value: 'Local horizontal 0°', position: 'insideTopRight', fill: '#94a3b8', fontSize: 9 }} />
                <Line type="monotone" dataKey="sun_el" name="Sun elevation" stroke="#f59e0b" strokeWidth={2} dot={{ r: 2 }} />
                <Line type="monotone" dataKey="earth_el" name="Earth elevation" stroke="#38bdf8" strokeWidth={2} dot={{ r: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 grid sm:grid-cols-3 gap-2 text-[11px] font-mono">
            {Number(summary.earth_elevation_max_deg ?? Math.max(...data.map((d) => d.earth_el))) < 0 && (
              <div data-testid="earth-below-finding" className="sm:col-span-3 p-2.5 rounded bg-amber-950/30 border border-amber-800/60 text-amber-200">
                <strong>Real-data finding:</strong> Earth apparent elevation is negative ({Number(summary.earth_elevation_min_deg ?? Math.min(...data.map((d) => d.earth_el))).toFixed(2)}° to{' '}
                {Number(summary.earth_elevation_max_deg ?? Math.max(...data.map((d) => d.earth_el))).toFixed(2)}°) across all {coverage.steps_with_real_ephemeris} covered steps — from a flat horizontal
                at this site and date, Earth is below the horizon.
              </div>
            )}
          </div>
        </>
      )}

      <div className="mt-3 p-2.5 rounded bg-[#070B14] border border-slate-800 text-[10px] font-mono text-slate-400 flex items-start space-x-2">
        <ShieldCheck className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <span>
          <strong className="text-slate-200">Provenance &amp; scope:</strong> Recorded NASA JPL Horizons response (observer{' '}
          <code>coord@301</code>, targets <code>10</code> Sun and <code>399</code> Earth, airless apparent az/el). Linearly interpolated
          between recorded samples; never extrapolated beyond the recorded window. LOLA terrain masks and Sun/Earth discs are not applied
          in this raw-angle panel. Terrain-aware simulation is limited to the bundled central 601 × 601 DEM subset (about 48 × 48 km); locations outside it are not covered.
        </span>
      </div>
    </section>
  );
}
