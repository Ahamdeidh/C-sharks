import React, { useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from './config';

const YEARS = Array.from({ length: 8 }, (_, index) => 2025 + index);
const FEATURED_AREAS = new Set([
  'PeakNearShackleton',
  'MalapertMassif',
  'ConnectingRidge',
  'deGerlacheRim',
  'Haworth',
]);
const AREA_LABELS = {
  PeakNearShackleton: 'Peak near Shackleton',
  MalapertMassif: 'Malapert Massif',
  ConnectingRidge: 'Connecting Ridge',
  deGerlacheRim: 'de Gerlache Rim',
  Haworth: 'Haworth',
  deGerlacheRim2: 'de Gerlache Rim 2',
};

function formatAreaName(key) {
  return AREA_LABELS[key] || key.replace(/([a-z])([A-Z0-9])/g, '$1 $2');
}

function numberOrDash(value, digits = 2) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
}

export default function RealArchiveDataPanel({ embedded = false }) {
  const [catalog, setCatalog] = useState(null);
  const [error, setError] = useState('');
  const [year, setYear] = useState(2025);
  const [query, setQuery] = useState('');
  const [showRasterStats, setShowRasterStats] = useState(false);

  useEffect(() => {
    if (embedded && typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') return undefined;
    if (!API_BASE_URL) {
      setError('API base URL is not configured.');
      return undefined;
    }
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/v1/reference/catalog-v2`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Reference catalog request failed (${response.status})`);
        return response.json();
      })
      .then(setCatalog)
      .catch((err) => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, []);

  const areas = useMemo(() => {
    const q = query.trim().toLowerCase();
    return Object.entries(catalog?.areas || {})
      .filter(([key]) => !q || `${key} ${formatAreaName(key)}`.toLowerCase().includes(q))
      .sort(([a], [b]) => {
        const aFeatured = FEATURED_AREAS.has(a);
        const bFeatured = FEATURED_AREAS.has(b);
        return Number(bFeatured) - Number(aFeatured) || formatAreaName(a).localeCompare(formatAreaName(b));
      });
  }, [catalog, query]);

  const rasterProducts = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (catalog?.raster_products || []).filter((product) =>
      product.year === year && (!q || `${product.area} ${formatAreaName(product.area)}`.toLowerCase().includes(q))
    );
  }, [catalog, query, year]);
  const exceedance = catalog?.sun_plus_earth_vs_sun_only;
  const exceedancePercent = Number(exceedance?.mean_fraction_pixels_where_sun_plus_earth_exceeds_sun_only || 0) * 100;

  return (
    <section className="bg-[#0B101D] border border-cyan-900/30 rounded-xl p-5 shadow-xl" aria-labelledby="archive-data-title">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-3 mb-4">
        <div>
          <h3 id="archive-data-title" className="text-sm font-bold uppercase tracking-wider text-slate-100">Lunar Archive Catalog v2</h3>
          <p className="mt-1 text-[11px] text-slate-400">Regional raster summaries and PSR polygons · reference data, not simulation outputs</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <label htmlFor="archive-year" className="text-slate-400">Raster year</label>
          <select id="archive-year" value={year} onChange={(event) => setYear(Number(event.target.value))} className="bg-[#090D18] border border-slate-700 rounded px-2 py-1 text-slate-200">
            {YEARS.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
          <label className="sr-only" htmlFor="archive-area-search">Search archive regions</label>
          <input id="archive-area-search" aria-label="Search archive regions" placeholder="Search regions…" value={query} onChange={(event) => setQuery(event.target.value)} className="w-40 bg-[#090D18] border border-slate-700 rounded px-2 py-1 text-slate-200" />
        </div>
      </div>

      {error ? <p role="alert" className="text-sm text-rose-300">Unable to load archive data: {error}</p> : !catalog ?
        <p className="text-sm text-slate-400">Loading archive data…</p> : <>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-slate-400 mb-4">
            <span><strong className="text-cyan-300">{catalog.counts?.rasters ?? '—'}</strong> regional rasters</span>
            <span><strong className="text-cyan-300">{catalog.counts?.areas ?? '—'}</strong> areas</span>
            <span><strong className="text-cyan-300">{catalog.counts?.psr_polygons ?? '—'}</strong> PSR polygons in source layer</span>
            <span>Moon 2000 south-polar stereographic · pixel size in metres</span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-[#040714] shadow-inner">
            <table className="w-full min-w-[920px] text-left text-xs border-collapse">
              <caption className="sr-only">Archive-derived mean consecutive illumination days by lunar region</caption>
              <thead className="text-[10px] uppercase font-mono tracking-wider text-slate-300 bg-slate-900/90 border-b border-slate-800">
                <tr>
                  <th scope="col" className="py-3 px-4 min-w-[220px]">Archive area</th>
                  <th scope="col" className="py-3 px-4 min-w-[240px]">Sun-only consecutive illumination days<br /><span className="normal-case text-slate-400 font-normal">{year} / 2025–2032 mean</span></th>
                  <th scope="col" className="py-3 px-4 min-w-[240px]">Sun+Earth source field<br /><span className="normal-case text-amber-300/80 font-normal">definition unverified · days*</span></th>
                  <th scope="col" className="py-3 px-4 min-w-[150px]">PSR polygons<br /><span className="normal-case text-slate-400 font-normal">centroid in extent†</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {areas.map(([key, area]) => {
                  const sunOnly = area.series?.sun_only;
                  const sunEarth = area.series?.sun_plus_earth;
                  const yearIndex = sunOnly?.years?.indexOf(year) ?? -1;
                  const sunYear = yearIndex >= 0 ? sunOnly.mean_days_by_year[yearIndex] : null;
                  const earthIndex = sunEarth?.years?.indexOf(year) ?? -1;
                  const earthYear = earthIndex >= 0 ? sunEarth.mean_days_by_year[earthIndex] : null;
                  const center = area.center_lat_lon || [];
                  const featured = FEATURED_AREAS.has(key);
                  return (
                    <tr key={key} className={`transition hover:bg-slate-800/30 ${featured ? 'bg-cyan-950/20 text-slate-200' : 'text-slate-300'}`}>
                      <th scope="row" className="py-2.5 px-4 font-medium text-left align-top">
                        <span className="block font-semibold text-slate-100">{formatAreaName(key)}</span>
                        <span className="block mt-0.5 text-[10px] font-mono text-cyan-400/80">{numberOrDash(center[0], 3)}°, {numberOrDash(center[1], 3)}°</span>
                      </th>
                      <td className="py-2.5 px-4 font-mono align-top text-amber-300 font-semibold">{numberOrDash(sunYear)} <span className="text-slate-500 font-normal">/</span> {numberOrDash(sunOnly?.mean_days_all_years)}</td>
                      <td className="py-2.5 px-4 font-mono align-top text-sky-300 font-semibold">{numberOrDash(earthYear)} <span className="text-slate-500 font-normal">/</span> {numberOrDash(sunEarth?.mean_days_all_years)}</td>
                      <td className="py-2.5 px-4 font-mono align-top text-purple-300 font-semibold">{area.psr_polygons_in_extent ?? '—'}</td>
                    </tr>
                  );
                })}
                {areas.length === 0 && <tr><td colSpan="4" className="p-6 text-center text-slate-500 font-mono">No matching areas found.</td></tr>}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[10px] text-slate-400 font-mono leading-relaxed">For both columns: the first number is the selected-year mean of regional raster values; the second is the mean of the eight yearly regional means (2025–2032), not a percentage or forecast. Coordinates are area centers.</p>

          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            <div className="p-3.5 rounded-xl border border-slate-800 bg-[#070b18] text-[11px] leading-relaxed text-slate-300 shadow-md">
              <h4 className="font-semibold text-cyan-200 mb-1 text-xs">Units and interpretation</h4>
              <p>{catalog.units_note}. The archive README describes raster samples as consecutive 12-hour increments; division by 2 expresses days. These are regional, year-labelled maximum-consecutive-duration products, not time-resolved illumination or Earth-visibility predictions.</p>
              <p className="mt-2 text-amber-200/90">* “Sun+Earth” is the supplied source-field label only. Its definition is unverified; it is not a ground-station connection, DTE availability, or a percentage. In the source validation, this field exceeds Sun-only for a mean {exceedancePercent.toFixed(2)}% of pixels across {exceedance?.pairs ?? '—'} area-year pairs, so it is not a logical intersection.</p>
            </div>
            <div className="p-3.5 rounded-xl border border-slate-800 bg-[#070b18] text-[11px] leading-relaxed text-slate-300 shadow-md">
              <h4 className="font-semibold text-cyan-200 mb-1 text-xs">Validation and spatial limits</h4>
              <p>Point-attribute values equal the sampled raster pixel in {catalog.validation_vs_site_point_attributes?.sun_only?.attr_equals_pixel_pct ?? '—'}% of Sun-only checks and {catalog.validation_vs_site_point_attributes?.sun_plus_earth?.attr_equals_pixel_pct ?? '—'}% of Sun+Earth checks. Mean absolute differences from the sampled pixel are {numberOrDash(catalog.validation_vs_site_point_attributes?.sun_only?.mean_abs_diff_vs_pixel)} and {numberOrDash(catalog.validation_vs_site_point_attributes?.sun_plus_earth?.mean_abs_diff_vs_pixel)} days, respectively; these checks do not establish a universal error bound.</p>
              <p className="mt-2 text-amber-200/90">† PSR counts are approximate: a polygon is assigned to each area whose rectangular extent contains its centroid. A displayed zero is not evidence that no PSR exists; Haworth and Malapert both show zero in this approximate assignment and warrant source-geometry review.</p>
            </div>
          </div>

          <details className="mt-4 rounded-xl border border-slate-800 bg-[#070b18] overflow-hidden shadow-md">
            <summary className="cursor-pointer px-4 py-3 text-xs font-semibold text-cyan-200 hover:text-cyan-100 transition">Explore per-raster statistics for {year} ({rasterProducts.length} products)</summary>
            <div className="overflow-x-auto border-t border-slate-800 bg-[#040714]">
              <table className="w-full min-w-[880px] text-left text-xs border-collapse">
                <thead className="text-slate-300 uppercase font-mono text-[10px] bg-slate-900/90 border-b border-slate-800"><tr>
                  <th className="py-2.5 px-3.5 min-w-[160px]">Area</th>
                  <th className="py-2.5 px-3.5 min-w-[240px]">Source measure</th>
                  <th className="py-2.5 px-3.5 whitespace-nowrap">Mean d</th>
                  <th className="py-2.5 px-3.5 whitespace-nowrap">Median d</th>
                  <th className="py-2.5 px-3.5 whitespace-nowrap">P90 d</th>
                  <th className="py-2.5 px-3.5 whitespace-nowrap">Max d</th>
                  <th className="py-2.5 px-3.5 whitespace-nowrap">Pixels &gt; 0</th>
                  <th className="py-2.5 px-3.5 whitespace-nowrap">Pixel size</th>
                </tr></thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {rasterProducts.map((product) => <tr key={product.file} className="hover:bg-slate-800/30 transition">
                    <td className="py-2 px-3.5 font-medium text-slate-200 whitespace-nowrap">{formatAreaName(product.area)}</td>
                    <td className="py-2 px-3.5 text-xs text-slate-300">{product.measure === 'sun_only' ? 'Sun-only consecutive illumination days' : 'Sun+Earth source field (definition unverified)'}</td>
                    <td className="py-2 px-3.5 font-mono text-amber-300 font-semibold">{numberOrDash(product.days?.mean, 3)}</td>
                    <td className="py-2 px-3.5 font-mono text-slate-300">{numberOrDash(product.days?.median, 3)}</td>
                    <td className="py-2 px-3.5 font-mono text-slate-300">{numberOrDash(product.days?.p90, 3)}</td>
                    <td className="py-2 px-3.5 font-mono text-sky-300 font-semibold">{numberOrDash(product.days?.max, 3)}</td>
                    <td className="py-2 px-3.5 font-mono text-slate-300">{Number.isFinite(Number(product.days?.frac_pixels_gt0)) ? `${(Number(product.days.frac_pixels_gt0) * 100).toFixed(2)}%` : '—'}</td>
                    <td className="py-2 px-3.5 font-mono text-cyan-300 whitespace-nowrap">{product.pixel_size_m ?? '—'} m</td>
                  </tr>)}
                </tbody>
              </table>
            </div>
          </details>

          <details className="mt-3 rounded border border-slate-800 bg-slate-950/30">
            <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-cyan-200">Catalog sources and provenance warning</summary>
            <div className="px-3 pb-3 text-[11px] leading-relaxed text-amber-200/90">
              <p>{catalog.provenance_warning} The app does not claim NASA authorship, and the supplied raster bundle does not include a verified elevation DEM.</p>
              <p className="mt-2 text-slate-400">Immediate project references: Illumination_Modeling/READ_ME.txt and its Midsummer GeoTIFFs; PSR_Volatile_Estimates/PSR_volatile_abundance_final.shp and companion files; and the legacy LandingSites point bundle used for validation.</p>
            </div>
          </details>
        </>}
    </section>
  );
}
