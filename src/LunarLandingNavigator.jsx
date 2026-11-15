import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { 
  Play, Radio, Sun, Moon, Compass, TrendingUp, AlertTriangle, MapPin,
  Activity, Info, CheckCircle2, Satellite, Wifi, Sliders, Calendar,
  Clock, Bookmark, X, GitCompare, ToggleLeft, ToggleRight, AlertCircle,
  Database, Download, ExternalLink, ShieldCheck, FileText, ChevronRight,
  Layers, BarChart3, Shield, Sparkles, Eye, Crosshair, Globe, Gauge
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';
import { API_BASE_URL } from './config';
import RealHorizonsPanel from './RealHorizonsPanel';
import RealArchiveDataPanel from './RealArchiveDataPanel';
import DecisionBriefPanel from './DecisionBriefPanel';
import ChallengeAlignmentPanel from './ChallengeAlignmentPanel';
import MissionDesignLabPanel from './MissionDesignLabPanel';
import ScientificValidationPanel from './ScientificValidationPanel';
import RealReferenceKpiPanel from './RealReferenceKpiPanel';
import VerificationSuitePanel from './VerificationSuitePanel';
import JudgeEvidencePanel from './JudgeEvidencePanel';
import HorizonAndOpsPanel from './HorizonAndOpsPanel';
import LandingRiskPanel from './LandingRiskPanel';

/**
 * ============================================================================
 * LUNAR LANDING SITE NAVIGATOR — REALISTIC MISSION CONTROL DASHBOARD
 * NASA Space Apps Challenge
 * ----------------------------------------------------------------------------
 * High-realism, aerospace flight operations interface designed with NASA JPL
 * telemetry visual language, shaded lunar polar topography, live mission
 * clocks, and tactical instrument panels.
 * ============================================================================
 */

export const PRESET_SITES = [
  { 
    id: 'shackleton', 
    name: 'Shackleton Crater Rim', 
    lat: -89.9, 
    lon: 0.0, 
    elevation_m: 4200,
    description: 'Illustrative simulator preset; not a source-derived archive-area center or suitability result.',
    tradeoff: 'High illumination near peak; steep crater walls require high antenna.',
    craterType: 'Impact Rim Peak',
    illumRating: '92% Peak'
  },
  { 
    id: 'malapert', 
    name: 'Malapert Massif Ridge', 
    lat: -85.9, 
    lon: -2.9, 
    elevation_m: 5000,
    description: 'Illustrative simulator preset; compare with the separate archive-derived regional summary below.',
    tradeoff: 'Elevated vantage point, excellent continuous Earth line-of-sight.',
    craterType: 'Mountain Plateau',
    illumRating: '88% Ridge'
  },
  { 
    id: 'connecting-ridge', 
    name: 'Connecting Ridge', 
    lat: -89.4, 
    lon: 222.0, 
    elevation_m: 3800,
    description: 'Illustrative simulator preset; no source-backed site ranking is implied.',
    tradeoff: 'Connecting ridge between Shackleton & de Gerlache; narrow solar corridors.',
    craterType: 'Ridge Saddle',
    illumRating: '84% Saddle'
  },
  { 
    id: 'de-gerlache', 
    name: 'de Gerlache Rim 1', 
    lat: -88.5, 
    lon: -88.3, 
    elevation_m: 3100,
    description: 'Illustrative simulator preset; not a time-resolved archive product.',
    tradeoff: 'Intermediate elevation rim; balanced thermal environment.',
    craterType: 'Crater Crest',
    illumRating: '79% Crest'
  },
  { 
    id: 'haworth', 
    name: 'Haworth Crater Rim', 
    lat: -87.4, 
    lon: -5.1, 
    elevation_m: 2400,
    description: 'Illustrative simulator preset; does not represent terrain-aware illumination or Earth visibility.',
    tradeoff: 'Deep cold trap vicinity with extensive permanently shadowed regions.',
    craterType: 'Cold-Trap Boundary',
    illumRating: '65% Basin'
  }
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildInputSnapshot(siteId, startTime, duration, step, antenna, margin, demo, customCoords = null) {
  return JSON.stringify({ siteId, startTime, duration, step, antenna, margin, demo, customCoords });
}

export function localInputToUtcIso(localValue) {
  if (!localValue) return null;
  const dt = new Date(localValue);
  if (isNaN(dt.getTime())) return null;
  return dt.toISOString();
}

function formatUtcDisplay(utcIso) {
  if (!utcIso) return '—';
  try {
    const dt = new Date(utcIso);
    if (isNaN(dt.getTime())) return '—';
    return dt.toISOString().replace('T', ' ').replace('.000Z', ' UTC');
  } catch { return utcIso; }
}

function getLocalTzAbbr() {
  try {
    return Intl.DateTimeFormat(undefined, { timeZoneName: 'short' })
      .formatToParts(new Date())
      .find(p => p.type === 'timeZoneName')?.value || 'local';
  } catch { return 'local'; }
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function LunarLandingNavigator() {
  // ---- Input state ----
  const [selectedSiteId, setSelectedSiteId] = useState('shackleton');
  const [startTime, setStartTime] = useState('2026-11-14T12:00');
  const [missionDuration, setMissionDuration] = useState(14);
  const [timeStep, setTimeStep] = useState(4);
  const [antennaHeight, setAntennaHeight] = useState(6.0);
  const [losMargin, setLosMargin] = useState(0.25);
  const [demoMode, setDemoMode] = useState(false);
  const [benchmarkThreshold, setBenchmarkThreshold] = useState(75.0);
  const [useCustomCoords, setUseCustomCoords] = useState(false);
  const [customLat, setCustomLat] = useState(-89.5);
  const [customLon, setCustomLon] = useState(15.0);

  // ---- Navigation Tab state ----
  const [activeTab, setActiveTab] = useState('telemetry');

  // ---- Live Clock state ----
  const [liveUtcString, setLiveUtcString] = useState('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const iso = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
      setLiveUtcString(iso);
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  // ---- API / execution state ----
  const [simulationStatus, setSimulationStatus] = useState('idle');
  const [errorMessage, setErrorMessage] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [backendHealth, setBackendHealth] = useState({ online: false, checking: true });

  // ---- Stale-result tracking ----
  const [lastRunSnapshot, setLastRunSnapshot] = useState(null);

  // ---- Scenario comparison ----
  const [savedBaseline, setSavedBaseline] = useState(null);
  const [showComparisonView, setShowComparisonView] = useState(false);

  // ---- Provenance & Methodology Modal ----
  const [showMethodologyModal, setShowMethodologyModal] = useState(false);
  const [provenanceData, setProvenanceData] = useState(null);

  // ---- Abort controller & announcement ----
  const abortRef = useRef(null);
  const requestIdRef = useRef(0);
  const statusAnnouncerRef = useRef(null);

  const currentSite = useMemo(() => PRESET_SITES.find(s => s.id === selectedSiteId) || PRESET_SITES[0], [selectedSiteId]);
  const localTz = useMemo(() => getLocalTzAbbr(), []);

  const customCoordKey = useCustomCoords ? `${Number(customLat)},${Number(customLon)}` : null;
  const currentSnapshot = useMemo(
    () => buildInputSnapshot(selectedSiteId, startTime, missionDuration, timeStep, antennaHeight, losMargin, demoMode, customCoordKey),
    [selectedSiteId, startTime, missionDuration, timeStep, antennaHeight, losMargin, demoMode, customCoordKey]
  );

  const resultsAreStale = simulationResult && lastRunSnapshot && currentSnapshot !== lastRunSnapshot;
  const hasCurrentResult = simulationResult && !resultsAreStale &&
    (simulationStatus === 'success' || simulationStatus === 'engine_pending');

  const apiConfigError = API_BASE_URL === null;

  // Backend health check on mount
  useEffect(() => {
    if (apiConfigError) {
      setBackendHealth({ online: false, checking: false });
      return;
    }
    if (typeof import.meta !== 'undefined' && import.meta.env?.MODE === 'test') {
      return;
    }
    let mounted = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/status`);
        if (res.ok && mounted) {
          const data = await res.json();
          setBackendHealth({ online: true, checking: false, details: data });
        } else if (mounted) {
          setBackendHealth({ online: false, checking: false });
        }
      } catch {
        if (mounted) setBackendHealth({ online: false, checking: false });
      }
    })();
    return () => { mounted = false; };
  }, [apiConfigError]);

  // Fetch initial provenance specifications
  const fetchProvenance = useCallback(async () => {
    if (apiConfigError || provenanceData) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/provenance`);
      if (res.ok) {
        const data = await res.json();
        setProvenanceData(data);
      }
    } catch {
      // Fallback specifications
    }
  }, [apiConfigError, provenanceData]);

  const announce = useCallback((msg) => {
    if (statusAnnouncerRef.current) statusAnnouncerRef.current.textContent = msg;
  }, []);

  // Run simulation handler
  const handleRunSimulation = useCallback(async () => {
    if (apiConfigError) {
      setSimulationStatus('error');
      setErrorMessage('API base URL is not configured. Set the VITE_API_BASE_URL environment variable for production builds.');
      announce('Simulation failed: API URL not configured.');
      return;
    }

    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = ++requestIdRef.current;

    setSimulationStatus('loading');
    setErrorMessage(null);
    announce('Simulation request in progress.');

    const utcIso = localInputToUtcIso(startTime);
    if (!utcIso) {
      setSimulationStatus('error');
      setErrorMessage('Invalid start date/time. Please select a valid date and time.');
      announce('Simulation failed: invalid start date.');
      return;
    }

    const evalLat = useCustomCoords ? Number(customLat) : currentSite.lat;
    const evalLon = useCustomCoords ? Number(customLon) : currentSite.lon;
    const payload = {
      site_id: selectedSiteId,
      lat: evalLat,
      lon: evalLon,
      start_time: utcIso,
      mission_duration_days: Number(missionDuration),
      timestep_hours: Number(timeStep),
      antenna_height_m: Number(antennaHeight),
      los_margin_deg: Number(losMargin),
      demo_mode: Boolean(demoMode)
    };

    const snapshot = buildInputSnapshot(selectedSiteId, startTime, missionDuration, timeStep, antennaHeight, losMargin, demoMode, useCustomCoords ? `${evalLat},${evalLon}` : null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/simulation/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (HTTP ${response.status})`);
      }

      const data = await response.json();
      if (requestId !== requestIdRef.current) return;

      if (data.provenance) {
        setProvenanceData(data.provenance);
      }

      if (data.status === 'engine_pending') {
        setSimulationStatus('engine_pending');
        setSimulationResult(data);
        setLastRunSnapshot(snapshot);
        announce('Simulation complete: calculation engine integration pending. No data fabricated.');
      } else {
        setSimulationStatus('success');
        setSimulationResult(data);
        setLastRunSnapshot(snapshot);
        announce(data.is_demo
          ? 'Simulation complete with prototype demo data. Values are not scientifically certified.'
          : 'Simulation complete with engine results.');
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (requestId !== requestIdRef.current) return;
      setSimulationStatus('error');
      setSimulationResult(null);
      setLastRunSnapshot(null);
      const msg = err.message.includes('Failed to fetch')
        ? `Unable to reach the backend at ${API_BASE_URL}. Verify the server is running.`
        : err.message;
      setErrorMessage(msg);
      announce(`Simulation failed: ${msg}`);
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }, [apiConfigError, selectedSiteId, startTime, missionDuration, timeStep, antennaHeight, losMargin, demoMode, currentSite, useCustomCoords, customLat, customLon, announce]);

  // Save baseline handler
  const handleSaveAsBaseline = useCallback(() => {
    if (!simulationResult || resultsAreStale) return;
    setSavedBaseline({
      id: Date.now(),
      savedAt: new Date().toLocaleTimeString(),
      inputs: { ...simulationResult.inputs_used },
      kpis: simulationResult.kpis,
      timeline: simulationResult.timeline,
      isDemo: simulationResult.is_demo,
      status: simulationResult.status,
      dataSource: simulationResult.data_source,
      totalSteps: simulationResult.total_time_steps
    });
    setShowComparisonView(true);
    announce('Current result saved as baseline scenario for comparison.');
  }, [simulationResult, resultsAreStale, announce]);

  const handleClearBaseline = useCallback(() => {
    setSavedBaseline(null);
    setShowComparisonView(false);
    announce('Baseline scenario cleared.');
  }, [announce]);

  // Export JSON handler
  const handleExportRunJson = useCallback(() => {
    if (!simulationResult) return;
    const exportPayload = {
      export_timestamp_utc: new Date().toISOString(),
      application: "Lunar Landing Site Navigator",
      version: "1.3.0",
      status: simulationResult.status,
      data_source: simulationResult.data_source,
      is_demo_model: simulationResult.is_demo,
      inputs_evaluated: simulationResult.inputs_used,
      kpis: simulationResult.kpis,
      timeline_samples_count: simulationResult.timeline?.length || 0,
      timeline: simulationResult.timeline,
      provenance_and_methodology: simulationResult.provenance || provenanceData
    };

    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lunar_simulation_${simulationResult.inputs_used?.site_id || 'run'}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    announce('Simulation run and provenance exported as JSON.');
  }, [simulationResult, provenanceData, announce]);

  // Comparison compatibility warnings
  const comparisonWarnings = useMemo(() => {
    if (!savedBaseline || !simulationResult || !showComparisonView) return [];
    const warns = [];
    const baseIn = savedBaseline.inputs || {};
    const curIn = simulationResult.inputs_used || {};

    if (savedBaseline.isDemo !== simulationResult.is_demo) {
      warns.push('Data sources differ: one scenario is prototype demo data and the other is not. These cannot be compared as directly equivalent.');
    }
    if (baseIn.timestep_hours !== curIn.timestep_hours) {
      warns.push(`Time step differs (baseline: ${baseIn.timestep_hours}h vs current: ${curIn.timestep_hours}h). Timeline points are aligned by index, not by absolute elapsed time.`);
    }
    if (baseIn.mission_duration_days !== curIn.mission_duration_days) {
      warns.push(`Mission duration differs (baseline: ${baseIn.mission_duration_days}d vs current: ${curIn.mission_duration_days}d). Overlapping samples are compared; excess steps are unaligned.`);
    }
    if (baseIn.start_time_utc !== curIn.start_time_utc) {
      warns.push('Mission start times differ. Chart lines represent relative mission progress, not identical astronomical times.');
    }
    return warns;
  }, [savedBaseline, simulationResult, showComparisonView]);

  // Chart data
  const displayChartData = useMemo(() => {
    if (!simulationResult?.timeline?.length) return [];
    const cur = simulationResult.timeline;

    if (!savedBaseline || !showComparisonView || !savedBaseline.timeline?.length) {
      return cur.map(pt => ({
        label: `${pt.elapsed_hours}h (Day ${pt.sol_day})`,
        timestamp: pt.timestamp,
        elapsed_hours: pt.elapsed_hours,
        illumination: pt.illumination_pct,
        dte: pt.dte_connection_pct,
        sun_el: pt.sun_elevation_deg,
        sun_az: pt.sun_azimuth_deg,
        earth_el: pt.earth_elevation_deg,
        earth_az: pt.earth_azimuth_deg,
        benchmark: benchmarkThreshold
      }));
    }

    const maxSteps = Math.max(cur.length, savedBaseline.timeline.length);
    const merged = [];
    for (let i = 0; i < maxSteps; i++) {
      const c = cur[i];
      const b = savedBaseline.timeline[i];
      merged.push({
        label: c ? `${c.elapsed_hours}h` : (b ? `${b.elapsed_hours}h` : `#${i+1}`),
        illumination: c ? c.illumination_pct : null,
        dte: c ? c.dte_connection_pct : null,
        sun_el: c?.sun_elevation_deg,
        sun_az: c?.sun_azimuth_deg,
        earth_el: c?.earth_elevation_deg,
        earth_az: c?.earth_azimuth_deg,
        base_illumination: b ? b.illumination_pct : null,
        base_dte: b ? b.dte_connection_pct : null,
        benchmark: benchmarkThreshold
      });
    }
    return merged;
  }, [simulationResult, savedBaseline, showComparisonView, benchmarkThreshold]);

  // Polar stereographic coordinates for map projection
  const polarSites = useMemo(() => {
    const cx = 150, cy = 150, maxR = 120;
    return PRESET_SITES.map(site => {
      const dist = Math.max(0, (90 - Math.abs(site.lat)) / 10);
      const r = dist * maxR;
      const rad = (site.lon - 90) * (Math.PI / 180);
      return { ...site, svgX: Math.round((cx + r * Math.cos(rad)) * 10) / 10, svgY: Math.round((cy + r * Math.sin(rad)) * 10) / 10 };
    });
  }, []);

  // Metric deltas
  const metricDeltas = useMemo(() => {
    if (!savedBaseline?.kpis || !simulationResult?.kpis || resultsAreStale) return null;
    const bk = savedBaseline.kpis;
    const ck = simulationResult.kpis;
    if (bk.avg_illumination_pct == null || ck.avg_illumination_pct == null) return null;
    return {
      illum: +(ck.avg_illumination_pct - bk.avg_illumination_pct).toFixed(1),
      dte: +(ck.dte_connection_pct - bk.dte_connection_pct).toFixed(1)
    };
  }, [savedBaseline, simulationResult, resultsAreStale]);

  const kpiSourceLabel = simulationResult?.kpis
    ? (simulationResult.is_demo ? 'Demo Model' : 'Engine Result')
    : 'Awaiting Run';

  const staleNotice = resultsAreStale
    ? 'Results shown are from a previous configuration. Run simulation to update.'
    : null;

  return (
    <div className="lunar-shell flex h-screen w-screen overflow-hidden bg-[#03060c] text-slate-100 font-sans select-none antialiased">
      
      {/* Live Region for Screen Readers */}
      <div ref={statusAnnouncerRef} role="status" aria-live="polite" aria-atomic="true"
        className="sr-only" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }} />

      {/* ================================================================== */}
      {/* REALISTIC AEROSPACE TACTICAL SIDEBAR                               */}
      {/* ================================================================== */}
      <aside className="w-[330px] flex-shrink-0 border-r border-sky-500/20 bg-[#070c18]/95 backdrop-blur-2xl flex flex-col justify-between z-20 shadow-[8px_0_35px_rgba(0,0,0,0.6)] overflow-hidden" role="form" aria-label="Simulation parameters">
        
        {/* Scrollable controls */}
        <div className="flex flex-col h-full overflow-y-auto custom-scrollbar p-5 space-y-4">

          {/* Insignia & Brand Header */}
          <div className="pb-4 border-b border-sky-500/20 relative">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-cyan-400/20 via-sky-500/30 to-blue-700/40 border border-cyan-400/50 flex items-center justify-center text-cyan-300 shadow-[0_0_24px_rgba(56,189,248,0.35)] relative overflow-hidden">
                <Satellite className="h-5 w-5 animate-pulse relative z-10" aria-hidden="true" />
                <div className="absolute inset-0 bg-cyan-400/10 animate-ping opacity-30" />
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <h1 className="text-sm font-black tracking-wider uppercase bg-gradient-to-r from-cyan-200 via-sky-100 to-white bg-clip-text text-transparent font-orbitron">
                    LUNAR NAVIGATOR
                  </h1>
                </div>
                <div className="flex items-center space-x-2 mt-0.5">
                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-700/60 font-bold">ARTEMIS OPS</span>
                  <p className="text-[10px] text-slate-400 font-mono tracking-tight font-medium">South Pole Telemetry</p>
                </div>
              </div>
            </div>

            {/* Prototype disclaimer with high-impact tactical badge */}
            <div className="mt-3 p-2.5 bg-amber-950/30 border border-amber-500/40 rounded-xl text-[10px] font-mono text-amber-200/90 flex items-start space-x-2 shadow-sm" role="note">
              <Info className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <span><strong>PROTOTYPE INTERFACE</strong> — Real LOLA DEM & JPL Horizons calculation workflow in progress.</span>
            </div>

            {/* Backend connection telemetry status */}
            <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono px-3 py-1.5 rounded-lg bg-[#030610] border border-slate-800 shadow-inner" role="status">
              {apiConfigError ? (
                <span className="flex items-center space-x-1.5">
                  <AlertCircle className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />
                  <span className="text-rose-400 font-bold text-[10px]">API URL NOT CONFIGURED</span>
                </span>
              ) : (
                <>
                  <span className="flex items-center space-x-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${backendHealth.online ? 'bg-emerald-400 shadow-[0_0_10px_#34d399]' : 'bg-rose-500 shadow-[0_0_10px_#f43f5e]'}`} aria-hidden="true" />
                    <span className={backendHealth.online ? 'text-emerald-400 font-bold text-[10px]' : 'text-rose-400 font-bold text-[10px]'}>
                      {backendHealth.checking ? 'TELEMETRY CHECKING...' : backendHealth.online ? 'BACKEND CONNECTED (PORT 8000)' : 'BACKEND OFFLINE'}
                    </span>
                  </span>
                  <span className="text-[9px] text-slate-500 truncate max-w-[80px]" title={API_BASE_URL || ''}>
                    {(API_BASE_URL || '').replace(/^https?:\/\//, '')}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Form Controls */}
          <div className="space-y-4 text-xs">

            {/* 1. Candidate Landing Site */}
            <div className="lunar-glow-box p-3 space-y-2.5 hud-corner-brackets">
              <label htmlFor="site-select" className="font-bold text-slate-200 flex items-center justify-between">
                <span className="flex items-center space-x-1.5">
                  <MapPin className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                  <span>1. Candidate Landing Site</span>
                </span>
                <span className="text-[9px] font-mono text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/60 font-semibold">PRESET TARGET</span>
              </label>

              <select 
                id="site-select" 
                value={selectedSiteId} 
                onChange={e => setSelectedSiteId(e.target.value)}
                className="w-full bg-[#050a16] border border-cyan-800/60 rounded-lg px-3 py-2 text-xs font-bold text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-400 transition cursor-pointer shadow-inner"
              >
                {PRESET_SITES.map(s => (
                  <option key={s.id} value={s.id}>{s.name} ({s.lat}°S, {s.lon}°E)</option>
                ))}
              </select>

              {/* Site Telemetry Badge */}
              <div className="flex items-center justify-between text-[10px] font-mono bg-[#050914] px-2.5 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Class: <span className="text-cyan-300 font-semibold">{currentSite.craterType || 'Rim'}</span></span>
                <span className="text-slate-400">Solar: <span className="text-amber-300 font-semibold">{currentSite.illumRating || 'Peak'}</span></span>
              </div>

              <p className="text-[10px] text-slate-400 leading-relaxed font-sans">{currentSite.description}</p>

              {/* Custom Coordinates Override Button */}
              <div className="pt-2 border-t border-slate-800/80">
                <button
                  type="button"
                  aria-pressed={useCustomCoords}
                  onClick={() => setUseCustomCoords(v => !v)}
                  className={`w-full px-2.5 py-1.5 rounded-lg border text-[11px] font-mono flex items-center justify-between transition ${
                    useCustomCoords
                      ? 'bg-cyan-950/90 border-cyan-400 text-cyan-200 font-bold shadow-[0_0_14px_rgba(56,189,248,0.25)]'
                      : 'bg-[#050814] border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <span className="truncate pr-1 flex items-center space-x-1">
                    <Crosshair className="h-3 w-3 text-cyan-400" />
                    <span>Custom Lunar Coordinates Override</span>
                  </span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] ${useCustomCoords ? 'bg-cyan-500 text-black font-bold' : 'bg-slate-800 text-slate-400'}`}>
                    {useCustomCoords ? 'ACTIVE' : 'OFF'}
                  </span>
                </button>

                {useCustomCoords && (
                  <div className="mt-2.5 grid grid-cols-2 gap-2 text-[10px] font-mono animate-in fade-in duration-200">
                    <div className="bg-[#03060f] p-2 rounded-lg border border-cyan-800/50">
                      <label htmlFor="custom-lat-input" className="block text-slate-400 text-[9px] mb-1 font-sans">Lat (°S: -90..-80)</label>
                      <input
                        id="custom-lat-input"
                        type="number"
                        step="0.1"
                        min="-90"
                        max="-80"
                        aria-label="Custom lunar latitude"
                        value={customLat}
                        onChange={e => setCustomLat(e.target.value)}
                        className="w-full bg-[#080e1e] border border-cyan-700/60 rounded px-2 py-1 text-slate-100 font-mono text-xs focus:ring-1 focus:ring-cyan-400"
                      />
                    </div>
                    <div className="bg-[#03060f] p-2 rounded-lg border border-cyan-800/50">
                      <label htmlFor="custom-lon-input" className="block text-slate-400 text-[9px] mb-1 font-sans">Lon (°E: -180..360)</label>
                      <input
                        id="custom-lon-input"
                        type="number"
                        step="0.1"
                        min="-180"
                        max="360"
                        aria-label="Custom lunar longitude"
                        value={customLon}
                        onChange={e => setCustomLon(e.target.value)}
                        className="w-full bg-[#080e1e] border border-cyan-700/60 rounded px-2 py-1 text-slate-100 font-mono text-xs focus:ring-1 focus:ring-cyan-400"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 2. Mission Start Time */}
            <div className="lunar-glow-box p-3 space-y-2">
              <label htmlFor="start-time" className="font-bold text-slate-200 flex items-center justify-between">
                <span className="flex items-center space-x-1.5">
                  <Calendar className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
                  <span>2. Mission Start ({localTz})</span>
                </span>
                <span className="text-[9px] font-mono text-sky-400">EPOCH</span>
              </label>
              <input 
                id="start-time" 
                type="datetime-local" 
                value={startTime} 
                onChange={e => setStartTime(e.target.value)}
                aria-describedby="start-time-utc-display"
                className="w-full bg-[#050a16] border border-slate-700/90 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-400 shadow-inner"
              />
              <p id="start-time-utc-display" className="text-[10px] text-slate-400 font-mono flex items-center justify-between bg-[#04060f] px-2 py-1 rounded">
                <span>CONVERTED UTC:</span>
                <span className="text-sky-300 font-bold">{formatUtcDisplay(localInputToUtcIso(startTime))}</span>
              </p>
            </div>

            {/* 3. Duration & Step */}
            <div className="lunar-glow-box p-3 space-y-3">
              <div className="flex items-center justify-between">
                <label htmlFor="duration-slider" className="font-bold text-slate-200 flex items-center space-x-1.5">
                  <Clock className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
                  <span>3. Duration</span>
                </label>
                <output htmlFor="duration-slider" className="font-mono font-bold text-sky-300 bg-sky-950/90 px-2.5 py-0.5 rounded-lg border border-sky-600/60 text-xs shadow-sm">
                  {missionDuration} Days
                </output>
              </div>

              <input 
                id="duration-slider" 
                type="range" 
                min="1" 
                max="60" 
                step="1" 
                value={missionDuration}
                onChange={e => setMissionDuration(Number(e.target.value))}
                aria-valuemin={1} 
                aria-valuemax={60} 
                aria-valuenow={missionDuration} 
                aria-label="Mission duration in days"
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-400"
              />

              <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
                <button type="button" onClick={() => setMissionDuration(7)} className="hover:text-sky-300 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">7d</button>
                <button type="button" onClick={() => setMissionDuration(14)} className="hover:text-sky-300 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">14d</button>
                <button type="button" onClick={() => setMissionDuration(29)} className="hover:text-sky-300 px-1.5 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800 font-bold">29.5d Sol</button>
                <button type="button" onClick={() => setMissionDuration(60)} className="hover:text-sky-300 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">60d</button>
              </div>

              {/* Step Resolution Selector */}
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-[11px] text-slate-400" id="step-label">Step Resolution:</span>
                <div className="flex items-center space-x-1" role="radiogroup" aria-labelledby="step-label">
                  {[1, 2, 4, 6, 12].map(step => (
                    <button 
                      key={step} 
                      type="button" 
                      role="radio" 
                      aria-checked={timeStep === step}
                      onClick={() => setTimeStep(step)}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded transition ${
                        timeStep === step 
                          ? 'bg-cyan-500 text-black font-extrabold shadow-[0_0_10px_rgba(6,182,212,0.5)]' 
                          : 'bg-[#040712] text-slate-400 hover:text-slate-200 border border-slate-800'
                      }`}
                    >
                      {step}h
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* 4. Antenna Mast Height */}
            <div className="lunar-glow-box p-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <label htmlFor="antenna-slider" className="font-bold text-slate-200 flex items-center space-x-1.5">
                  <Radio className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                  <span>4. Antenna Mast Height</span>
                </label>
                <output htmlFor="antenna-slider" className="font-mono font-bold text-emerald-300 bg-emerald-950/90 px-2.5 py-0.5 rounded-lg border border-emerald-600/60 text-xs shadow-sm">
                  {antennaHeight.toFixed(1)} m
                </output>
              </div>

              <input 
                id="antenna-slider" 
                type="range" 
                min="0" 
                max="20" 
                step="0.5" 
                value={antennaHeight}
                onChange={e => setAntennaHeight(Number(e.target.value))}
                aria-valuemin={0} 
                aria-valuemax={20} 
                aria-valuenow={antennaHeight} 
                aria-label="Antenna mast height in meters"
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-400"
              />

              <div className="flex justify-between text-[10px] font-mono text-slate-500">
                <span>0 m (Surface)</span>
                <span>10 m (Mast)</span>
                <span>20 m (Tower)</span>
              </div>
            </div>

            {/* 5. Earth LOS Margin */}
            <div className="lunar-glow-box p-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <label htmlFor="los-slider" className="font-bold text-slate-200 flex items-center space-x-1.5">
                  <Sliders className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                  <span>5. Earth LOS Margin</span>
                </label>
                <output htmlFor="los-slider" className="font-mono font-bold text-amber-300 bg-amber-950/90 px-2.5 py-0.5 rounded-lg border border-amber-600/60 text-xs shadow-sm">
                  {losMargin.toFixed(2)}°
                </output>
              </div>

              <input 
                id="los-slider" 
                type="range" 
                min="0" 
                max="1" 
                step="0.05" 
                value={losMargin}
                onChange={e => setLosMargin(Number(e.target.value))}
                aria-valuemin={0} 
                aria-valuemax={1} 
                aria-valuenow={losMargin} 
                aria-label="Earth line-of-sight margin in degrees"
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
              />

              <div className="flex justify-between text-[10px] font-mono text-slate-500">
                <span>0.0° (Grazing)</span>
                <span>0.5° (Nominal)</span>
                <span>1.0° (Strict)</span>
              </div>
            </div>

            {/* 6. Demo Mode Toggle */}
            <div className="lunar-glow-box p-3 space-y-2 border-purple-500/30">
              <div className="flex items-center justify-between">
                <label htmlFor="demo-toggle" className="font-bold text-slate-200 flex items-center space-x-1.5 cursor-pointer">
                  <Activity className="h-3.5 w-3.5 text-purple-400" aria-hidden="true" />
                  <span>Enable Demo Mode</span>
                </label>
                <button 
                  id="demo-toggle" 
                  type="button" 
                  role="switch" 
                  aria-checked={demoMode}
                  onClick={() => setDemoMode(!demoMode)}
                  title="Toggle between strict engine connection and prototype demo mode"
                  aria-label={demoMode ? 'Demo mode is enabled. Click to disable.' : 'Demo mode is disabled. Click to enable.'}
                  className="focus:outline-none focus:ring-2 focus:ring-purple-400 rounded-lg transition"
                >
                  {demoMode ? (
                    <ToggleRight className="h-7 w-7 text-purple-400 filter drop-shadow-[0_0_8px_rgba(192,132,252,0.6)]" />
                  ) : (
                    <ToggleLeft className="h-7 w-7 text-slate-600 hover:text-slate-500" />
                  )}
                </button>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">
                {demoMode
                  ? 'Active: Returns transparently labelled synthetic data for workflow evaluation.'
                  : 'Disabled (Default): Queries real engine; returns Pending state until real engine is integrated.'}
              </p>
            </div>
          </div>

          {/* Run Simulation Master Action */}
          <div className="pt-2">
            <button 
              type="button" 
              onClick={handleRunSimulation}
              disabled={simulationStatus === 'loading' || apiConfigError}
              aria-label={simulationStatus === 'loading' ? 'Simulation in progress, please wait' : 'Run simulation with current parameters'}
              className={`w-full py-3.5 px-4 rounded-xl font-black text-xs uppercase tracking-wider flex items-center justify-center space-x-2 transition-all duration-200 shadow-2xl focus:outline-none focus:ring-2 focus:ring-cyan-300 font-orbitron ${
                simulationStatus === 'loading'
                  ? 'bg-cyan-950 border border-cyan-700/60 text-cyan-300 cursor-wait'
                  : apiConfigError
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 shadow-[0_4px_28px_rgba(56,189,248,0.45)] active:scale-[0.98]'
              }`}
            >
              {simulationStatus === 'loading' ? (
                <>
                  <div className="h-4 w-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" aria-hidden="true" />
                  <span>Processing Engine…</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" aria-hidden="true" />
                  <span>Run Simulation</span>
                </>
              )}
            </button>
            {apiConfigError && (
              <p className="mt-1.5 text-center text-[10px] text-rose-400 font-mono">Set VITE_API_BASE_URL for production.</p>
            )}
          </div>
        </div>

        {/* Tactical Footer */}
        <div className="border-t border-sky-500/15 p-3 bg-[#03060f] text-[10px] font-mono text-slate-500 flex justify-between items-center">
          <span className="truncate">COORDS: {currentSite.lat}°, {currentSite.lon}°</span>
          <span className="text-cyan-400 font-bold">NASA GSFC LOLA</span>
        </div>
      </aside>

      {/* ================================================================== */}
      {/* MAIN MISSION CONTROL FLIGHT DECK                                   */}
      {/* ================================================================== */}
      <main className="lunar-main flex-1 flex flex-col min-w-0 overflow-hidden bg-transparent" role="main" aria-label="Mission control dashboard">

        {/* Top Aerospace Telemetry Bar */}
        <header className="lunar-topbar flex items-center justify-between px-6 z-10 flex-shrink-0">
          
          {/* Target Site & Coordinates Display */}
          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center px-3 py-1 rounded-xl text-xs font-mono font-bold bg-cyan-950/90 text-cyan-300 border border-cyan-600/70 shadow-[0_0_16px_rgba(6,182,212,0.3)]">
              <Crosshair className="h-3.5 w-3.5 mr-1.5 text-cyan-400 animate-spin-slow" />
              TARGET: {currentSite.name.toUpperCase()}
            </span>
            <span className="text-xs text-slate-400 font-mono hidden md:inline">
              {currentSite.lat}°S, {currentSite.lon}°E • {currentSite.elevation_m} m elev
            </span>
          </div>

          {/* Live Mission Control Clock & Telemetry Badges */}
          <div className="hidden xl:flex items-center space-x-3 font-mono text-xs">
            <div className="px-3 py-1 rounded-lg bg-[#040816] border border-cyan-800/40 text-cyan-400 flex items-center space-x-2">
              <Clock className="h-3 w-3 text-cyan-400" />
              <span className="font-bold tracking-wider">{liveUtcString || '2026-11-15 11:00:00 UTC'}</span>
            </div>
            <div className="px-2.5 py-1 rounded-lg bg-[#040816] border border-slate-800 text-slate-400 text-[11px]">
              DATUM: <span className="text-slate-200 font-bold">MOON 2000 IAU</span>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center space-x-2.5">
            {/* Data Sources and Methodology Button */}
            <button
              type="button"
              onClick={() => {
                setShowMethodologyModal(true);
                fetchProvenance();
              }}
              aria-label="View official data sources and methodology"
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#091326] hover:bg-[#102042] border border-cyan-800/60 text-cyan-300 text-xs font-mono font-medium transition focus:outline-none focus:ring-2 focus:ring-cyan-400 shadow-sm"
            >
              <Database className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              <span className="hidden sm:inline">Data Sources & Provenance</span>
              <span className="sm:hidden">Sources</span>
            </button>

            {/* Export JSON Button */}
            {simulationResult && (
              <button
                type="button"
                onClick={handleExportRunJson}
                aria-label="Export simulation run and provenance as JSON"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#071324] hover:bg-[#0c2242] border border-slate-700 text-slate-200 text-xs font-mono font-medium transition focus:outline-none focus:ring-2 focus:ring-cyan-400 shadow-sm"
              >
                <Download className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                <span className="hidden sm:inline">Export Run JSON</span>
                <span className="sm:hidden">Export</span>
              </button>
            )}

            {/* Save Baseline Button */}
            {hasCurrentResult && simulationResult?.kpis && (
              <button 
                type="button" 
                onClick={handleSaveAsBaseline}
                aria-label="Save Baseline"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#0c1a32] hover:bg-[#132a52] border border-cyan-600/60 text-cyan-300 text-xs font-mono font-medium transition focus:outline-none focus:ring-2 focus:ring-cyan-400 shadow-sm"
              >
                <Bookmark className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                <span>Save Baseline</span>
              </button>
            )}

            {/* Scenario Compare Toggle */}
            {savedBaseline && (
              <button 
                type="button" 
                onClick={() => setShowComparisonView(!showComparisonView)}
                aria-label={showComparisonView ? 'Hide comparison view' : 'Show comparison with saved baseline'}
                aria-pressed={showComparisonView}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-medium transition focus:outline-none focus:ring-2 focus:ring-purple-400 ${
                  showComparisonView 
                    ? 'bg-purple-950/90 border border-purple-500 text-purple-200 shadow-[0_0_14px_rgba(192,132,252,0.3)]' 
                    : 'bg-slate-800/80 text-slate-300 hover:text-white border border-slate-700'
                }`}
              >
                <GitCompare className="h-3.5 w-3.5 text-purple-400" aria-hidden="true" />
                <span>{showComparisonView ? 'Comparing' : 'Compare'}</span>
              </button>
            )}

            {/* Benchmark Input */}
            <div className="hidden lg:flex items-center space-x-1.5 text-xs font-mono text-slate-400 bg-[#040714] px-3 py-1.5 rounded-xl border border-slate-800">
              <label htmlFor="benchmark-input" className="sr-only">Display benchmark percentage</label>
              <span aria-hidden="true">Bench:</span>
              <input 
                id="benchmark-input" 
                type="number" 
                min="0" 
                max="100" 
                value={benchmarkThreshold}
                onChange={e => setBenchmarkThreshold(Number(e.target.value))}
                aria-label="Display benchmark percentage"
                className="w-12 bg-transparent text-rose-400 font-bold focus:outline-none focus:ring-1 focus:ring-rose-400 rounded" 
              />
              <span aria-hidden="true">%</span>
            </div>
          </div>
        </header>

        {/* Clean Modern Navigation Tabs Bar */}
        <div className="px-6 py-2.5 bg-[#050914] border-b border-sky-500/15 flex items-center justify-between gap-3 overflow-x-auto custom-scrollbar flex-shrink-0">
          <div className="flex items-center space-x-2">
            {[
              { id: 'telemetry', label: 'المحاكاة والاستكشاف', sub: 'Telemetry & Orbit', icon: Satellite },
              { id: 'hazards', label: 'التضاريس والمخاطر', sub: 'Terrain & Hazards', icon: Shield },
              { id: 'lab', label: 'مختبر المهمة والقرارات', sub: 'Mission Design Lab', icon: BarChart3 },
              { id: 'archive', label: 'الأرشيف الفلكي', sub: 'Archive & Horizons', icon: Database },
              { id: 'validation', label: 'التحقق والتحكيم', sub: 'Validation & Judges', icon: CheckCircle2 },
              { id: 'all', label: 'عرض شامل', sub: 'All Modules', icon: Layers }
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={`tab-button ${isActive ? 'active' : ''}`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} aria-hidden="true" />
                  <span className="font-semibold">{tab.label}</span>
                  <span className="text-[10px] font-mono opacity-60 hidden xl:inline">({tab.sub})</span>
                </button>
              );
            })}
          </div>

          <div className="hidden md:flex items-center space-x-2 text-[11px] font-mono text-slate-400">
            <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#38bdf8]" />
            <span>Lunar South Pole • 80°S–90°S Raytracing Grid</span>
          </div>
        </div>

        {/* Dashboard Body Content */}
        <div className="lunar-content flex-1 flex flex-col p-6 overflow-y-auto space-y-6 custom-scrollbar">

          {/* ============================================================== */}
          {/* TAB 1: TELEMETRY & CORE DASHBOARD                              */}
          {/* ============================================================== */}
          <div className={activeTab === 'telemetry' || activeTab === 'all' ? 'space-y-6' : 'hidden'}>

            {/* Decision-first mission overview hero */}
            <section className="mission-overview" aria-labelledby="mission-overview-title">
              <div className="mission-overview__copy">
                <div className="eyebrow">
                  <span className="eyebrow__dot" /> Lunar south-pole screening workspace
                </div>
                <h2 id="mission-overview-title">Plan the next landing window with confidence.</h2>
                <p>
                  Start with a candidate site, adjust only the mission variables you need, then run one transparent simulation. Results are labelled by source and limitation so your team can act without guessing.
                </p>
                <div className="mission-overview__meta">
                  <span><MapPin className="h-3.5 w-3.5 text-cyan-400" /> {currentSite.name}</span>
                  <span><Clock className="h-3.5 w-3.5 text-sky-400" /> {missionDuration} day mission</span>
                  <span className={backendHealth.online ? 'is-online' : 'is-offline'}>
                    <span className="status-dot" /> {backendHealth.checking ? 'Checking engine' : backendHealth.online ? 'Engine connected' : 'Exploratory mode'}
                  </span>
                </div>
              </div>
              <div className="mission-overview__action">
                <div className="mission-overview__status">
                  <span className="status-kicker">Current run</span>
                  <strong>{simulationStatus === 'success' ? (simulationResult?.is_demo ? 'Demo result ready' : 'Simulation complete') : simulationStatus === 'loading' ? 'Running simulation…' : simulationStatus === 'engine_pending' ? 'Engine pending' : 'Ready to run'}</strong>
                  <span>{hasCurrentResult ? 'Inputs and evidence are in sync.' : 'No current result yet.'}</span>
                </div>
                <button 
                  type="button" 
                  aria-label="Run current mission configuration" 
                  onClick={handleRunSimulation} 
                  disabled={simulationStatus === 'loading' || apiConfigError} 
                  className="overview-run-button"
                >
                  {simulationStatus === 'loading' ? (
                    <div className="h-4 w-4 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Play className="h-4 w-4 fill-current" />
                  )}
                  <span>{simulationStatus === 'loading' ? 'Running…' : 'Run simulation'}</span>
                </button>
              </div>
            </section>

            {/* Stale result warning */}
            {staleNotice && (
              <div className="bg-amber-950/30 border border-amber-600/50 rounded-xl p-3.5 flex items-center space-x-2.5 text-xs text-amber-200 shadow-md" role="alert">
                <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0" aria-hidden="true" />
                <span><strong>Settings changed:</strong> {staleNotice}</span>
              </div>
            )}

            {/* Custom coordinate override mismatch notice */}
            {simulationResult?.coordinate_mismatch && !resultsAreStale && (
              <div className="bg-cyan-950/30 border border-cyan-600/50 rounded-xl p-3.5 flex items-center space-x-2.5 text-xs text-cyan-200 shadow-md" role="status" data-testid="coordinate-override-notice">
                <MapPin className="h-4 w-4 text-cyan-400 flex-shrink-0" aria-hidden="true" />
                <span><strong>Custom Coordinates Precedence:</strong> {simulationResult.coordinate_mismatch}</span>
              </div>
            )}

            {/* Error banner */}
            {simulationStatus === 'error' && (
              <div className="bg-rose-950/40 border border-rose-600/70 rounded-xl p-4 flex items-start space-x-3 text-rose-200 shadow-xl" role="alert">
                <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div className="flex-1 text-xs">
                  <h4 className="font-bold uppercase tracking-wider text-rose-300">Simulation Request Failed</h4>
                  <p className="mt-1 text-slate-300">{errorMessage}</p>
                </div>
              </div>
            )}

            {/* Engine pending banner */}
            {simulationStatus === 'engine_pending' && simulationResult && !resultsAreStale && (
              <div className="bg-amber-950/40 border border-amber-600/70 rounded-xl p-4 flex items-start space-x-3 text-amber-200 shadow-xl" role="status">
                <Info className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div className="flex-1 text-xs">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h4 className="font-bold uppercase tracking-wider text-amber-300">Calculation Engine — Integration Pending</h4>
                    <span className="text-[10px] font-mono px-2 py-0.5 bg-amber-900/60 rounded border border-amber-700/60 text-amber-200 font-bold">STATUS: ENGINE PENDING</span>
                  </div>
                  <p className="mt-1.5 text-slate-300 leading-relaxed">{simulationResult.status_message}</p>
                  <div className="mt-2.5 p-2.5 bg-black/40 rounded-lg border border-amber-900/50 text-[11px] font-mono text-slate-300 flex items-center justify-between flex-wrap gap-2">
                    <span>Toggle <strong>"Enable Demo Mode"</strong> in the sidebar to explore the workflow with labelled synthetic data.</span>
                    <button 
                      type="button"
                      onClick={() => { setDemoMode(true); setTimeout(handleRunSimulation, 50); }}
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-black font-bold rounded-lg text-[10px] uppercase tracking-wider transition whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-amber-300 shadow"
                      aria-label="Enable demo mode and re-run simulation"
                    >
                      Enable Demo & Run
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Demo mode active banner */}
            {simulationResult?.is_demo && !resultsAreStale && (
              <div className="bg-purple-950/30 border border-purple-500/50 rounded-xl p-3.5 flex items-center justify-between text-xs text-purple-200 flex-wrap gap-2 shadow-md" role="status">
                <div className="flex items-center space-x-2.5">
                  <Activity className="h-4 w-4 text-purple-400" aria-hidden="true" />
                  <span>{simulationResult.status === 'terrain_benchmark'
                    ? <><strong>SYNTHETIC TERRAIN BENCHMARK:</strong> real JPL Horizons angles combined with a synthetic test DEM. Demonstrates the engine, not a real site.</>
                    : <><strong>PROTOTYPE DEMO MODE:</strong> Synthetic approximations for workflow evaluation. Not scientifically certified.</>}</span>
                </div>
                <span className="text-[10px] font-mono text-purple-300 bg-purple-900/40 px-2 py-0.5 rounded border border-purple-700">
                  {simulationResult.status === 'terrain_benchmark' ? 'SYNTHETIC_TERRAIN_BENCHMARK' : 'SYNTHETIC_DEMO'}
                </span>
              </div>
            )}

            {/* Scenario Comparison Panel */}
            {savedBaseline && showComparisonView && (
              <div className="bg-[#0c1426] border border-purple-500/50 rounded-xl p-4 shadow-xl">
                <div className="flex items-center justify-between pb-3 border-b border-purple-900/40 flex-wrap gap-2">
                  <div className="flex items-center space-x-2">
                    <GitCompare className="h-4 w-4 text-purple-400" aria-hidden="true" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-purple-300">Scenario Comparison</h3>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono text-purple-400">Baseline saved {savedBaseline.savedAt}</span>
                    <button 
                      type="button" 
                      onClick={handleSaveAsBaseline} 
                      disabled={!hasCurrentResult || !simulationResult?.kpis}
                      aria-label="Replace baseline with current result"
                      className="text-[10px] font-mono px-2.5 py-1 rounded-lg bg-purple-900/40 text-purple-300 hover:bg-purple-800/50 transition disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-purple-400"
                    >
                      Replace
                    </button>
                    <button 
                      type="button" 
                      onClick={handleClearBaseline} 
                      aria-label="Remove saved baseline"
                      className="p-1 text-slate-400 hover:text-rose-400 rounded transition focus:outline-none focus:ring-2 focus:ring-rose-400"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Comparison warnings */}
                {comparisonWarnings.length > 0 && (
                  <div className="mt-2.5 space-y-1">
                    {comparisonWarnings.map((w, i) => (
                      <div key={i} className="text-[10px] font-mono text-amber-300 bg-amber-950/30 px-2.5 py-1 rounded border border-amber-900/40 flex items-start space-x-1.5" role="note">
                        <AlertTriangle className="h-3 w-3 text-amber-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                        <span>{w}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-3.5 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                  {/* Baseline A */}
                  <div className="bg-[#060b18] p-3.5 rounded-xl border border-purple-900/40 space-y-1.5 text-slate-300">
                    <div className="text-purple-300 font-bold flex items-center justify-between">
                      <span>[A] BASELINE</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-purple-900/30 border border-purple-800/40">
                        {savedBaseline.isDemo ? 'Demo' : savedBaseline.status === 'engine_pending' ? 'Pending' : 'Engine'}
                      </span>
                    </div>
                    <div>Site: {savedBaseline.inputs?.site_name || savedBaseline.inputs?.site_id}</div>
                    <div>Start: {formatUtcDisplay(savedBaseline.inputs?.start_time_utc)}</div>
                    <div>Duration: {savedBaseline.inputs?.mission_duration_days}d | Step: {savedBaseline.inputs?.timestep_hours}h</div>
                    <div>Antenna: {savedBaseline.inputs?.antenna_height_m}m | Margin: {savedBaseline.inputs?.los_margin_deg}°</div>
                    {savedBaseline.kpis ? (
                      <div className="pt-2 border-t border-slate-800 text-purple-400 font-bold flex justify-between">
                        <span>Illum: {savedBaseline.kpis.avg_illumination_pct}%</span>
                        <span>DTE: {savedBaseline.kpis.dte_connection_pct}%</span>
                      </div>
                    ) : <div className="text-slate-500 italic">No KPI data</div>}
                  </div>

                  {/* Current B */}
                  <div className="bg-[#060b18] p-3.5 rounded-xl border border-cyan-900/40 space-y-1.5 text-slate-300">
                    <div className="text-cyan-300 font-bold flex items-center justify-between">
                      <span>[B] CURRENT {resultsAreStale ? '(STALE)' : ''}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-900/30 border border-cyan-800/40">
                        {!simulationResult ? 'Not run' : simulationResult.is_demo ? 'Demo' : simulationResult.status === 'engine_pending' ? 'Pending' : 'Engine'}
                      </span>
                    </div>
                    <div>Site: {simulationResult?.inputs_used?.site_name || currentSite.name}</div>
                    <div>Start: {formatUtcDisplay(simulationResult?.inputs_used?.start_time_utc)}</div>
                    <div>Duration: {simulationResult?.inputs_used?.mission_duration_days ?? missionDuration}d | Step: {simulationResult?.inputs_used?.timestep_hours ?? timeStep}h</div>
                    <div>Antenna: {simulationResult?.inputs_used?.antenna_height_m ?? antennaHeight}m | Margin: {simulationResult?.inputs_used?.los_margin_deg ?? losMargin}°</div>
                    {simulationResult?.kpis && !resultsAreStale ? (
                      <div className="pt-2 border-t border-slate-800 text-cyan-400 font-bold flex justify-between">
                        <span>Illum: {simulationResult.kpis.avg_illumination_pct}%</span>
                        <span>DTE: {simulationResult.kpis.dte_connection_pct}%</span>
                      </div>
                    ) : <div className="text-slate-500 italic">{resultsAreStale ? 'Settings changed — run again' : 'Run simulation to evaluate'}</div>}

                    {/* Deltas */}
                    {metricDeltas && showComparisonView && !resultsAreStale && (
                      <div className="pt-1.5 border-t border-slate-800 flex justify-between text-[11px]">
                        <span className={metricDeltas.illum >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                          ΔIllum: {metricDeltas.illum > 0 ? '+' : ''}{metricDeltas.illum}%
                        </span>
                        <span className={metricDeltas.dte >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                          ΔDTE: {metricDeltas.dte > 0 ? '+' : ''}{metricDeltas.dte}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Official Challenge Specification Notice */}
            <div className="bg-[#080e1e] border border-cyan-800/40 rounded-xl p-3.5 shadow-md flex flex-col lg:flex-row lg:items-center justify-between gap-3 text-xs font-mono">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2.5 py-0.5 rounded-lg bg-cyan-950 text-cyan-300 border border-cyan-700/60 font-bold text-[11px]">
                    NASA Space Apps Challenge: Lunar Landing Site Navigator
                  </span>
                  <a
                    href="https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyan-400 hover:underline inline-flex items-center gap-1 text-[11px]"
                  >
                    <span>Official Challenge Specification</span>
                    <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </a>
                </div>
                <p className="text-[11px] text-amber-200/90 leading-relaxed font-sans">
                  <strong>حدود دقة البيانات (80 m/px Regional Screening — Not Final Pad Certification):</strong> بكسل LOLA DEM الواحد (80م×80م = 6,400 م²) يعادل 28.4 ضعف مساحة منصة الهبوط (15م×15م = 225 م²). النتائج أدناه مخصصة للفرز الهندسي الإقليمي ومقارنة النوافذ الزمنية، ولا تغني عن مسح LROC NAC بدقة 0.5 م/بكسل لاعتماد الهبوط النهائي.
                </p>
              </div>
            </div>

            {/* 4 Core Aerospace KPI Gauges */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" role="region" aria-label="Key Performance Indicators">
              {[
                {
                  label: 'Avg Illumination',
                  value: simulationResult?.kpis?.avg_illumination_pct,
                  unit: '%',
                  icon: Sun,
                  colorHex: '#fbbf24',
                  glowHex: 'rgba(251, 191, 36, 0.4)',
                  extra: 'Solar Photons',
                  srcBadge: simulationResult?.status === 'terrain_aware' ? 'المصدر: DEM فعلي 80m + JPL Horizons' : 'المصدر: بانتظار محاكاة مغطاة',
                  limBadge: 'الحد: أفق إقليمي ≥80م (قرص الشمس 0.26°)'
                },
                {
                  label: 'Geometric Earth LOS',
                  value: simulationResult?.kpis?.dte_connection_pct,
                  unit: '%',
                  icon: Wifi,
                  colorHex: '#34d399',
                  glowHex: 'rgba(52, 211, 153, 0.4)',
                  extra: simulationResult?.inputs_used ? `Mast: ${simulationResult.inputs_used.antenna_height_m}m (LOS)` : 'Geometric visibility',
                  srcBadge: simulationResult?.status === 'terrain_aware' ? 'المصدر: DEM فعلي 80m + JPL Horizons' : 'المصدر: بانتظار محاكاة مغطاة',
                  limBadge: 'الحد: خط رؤية هندسي (ميزانية RF بالأسفل)'
                },
                {
                  label: 'Max AMSI',
                  value: simulationResult?.kpis?.max_amsi?.split(' ')[0],
                  unit: '',
                  icon: Moon,
                  colorHex: '#38bdf8',
                  glowHex: 'rgba(56, 189, 248, 0.4)',
                  extra: simulationResult?.kpis?.max_amsi?.split(' ').slice(1).join(' '),
                  srcBadge: 'المصدر: ملف مرجعي تمهيدي (Preset Reference)',
                  limBadge: 'الحد: مؤشر ظل مرجعي للفرز الأولي فقط'
                },
                {
                  label: 'Avg ASIA',
                  value: simulationResult?.kpis?.avg_asia_hours,
                  unit: 'h',
                  icon: Activity,
                  colorHex: '#c084fc',
                  glowHex: 'rgba(192, 132, 252, 0.4)',
                  extra: 'Continuous Sunlight',
                  srcBadge: 'المصدر: ملف مرجعي تمهيدي (Preset Reference)',
                  limBadge: 'الحد: تقدير مرجعي غير معتمد للهبوط'
                }
              ].map((kpi, i) => {
                const Icon = kpi.icon;
                const hasVal = kpi.value != null && !resultsAreStale;
                const numericPct = hasVal && !isNaN(Number(kpi.value)) ? Math.min(Number(kpi.value), 100) : 0;
                const activeSegments = Math.round((numericPct / 100) * 12);
                
                return (
                  <div key={i} className="lunar-glow-box p-4 relative overflow-hidden hud-corner-brackets" role="group" aria-label={kpi.label}>
                    <div className="flex items-center justify-between text-slate-400 mb-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                        <Icon className="h-4 w-4" style={{ color: kpi.colorHex }} aria-hidden="true" />
                        <span>{kpi.label}</span>
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#030610] text-slate-400 border border-slate-800">
                        {hasVal ? 'ACTIVE' : 'STANDBY'}
                      </span>
                    </div>

                    <div className="flex items-baseline space-x-2 my-2">
                      <span className="text-3xl font-black font-orbitron text-white tracking-tight" style={{ textShadow: hasVal ? `0 0 16px ${kpi.glowHex}` : 'none' }}>
                        {hasVal ? `${kpi.value}${kpi.unit}` : '—'}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        {resultsAreStale ? 'Stale' : kpi.extra || kpiSourceLabel}
                      </span>
                    </div>

                    {/* Segmented LED style level indicator */}
                    <div className="my-2.5 flex items-center space-x-1" role="presentation">
                      {Array.from({ length: 12 }).map((_, segIdx) => (
                        <div
                          key={segIdx}
                          className="h-2 flex-1 rounded-sm transition-all duration-300"
                          style={{
                            backgroundColor: segIdx < activeSegments ? kpi.colorHex : 'rgba(30, 41, 59, 0.6)',
                            boxShadow: segIdx < activeSegments ? `0 0 6px ${kpi.glowHex}` : 'none'
                          }}
                        />
                      ))}
                    </div>

                    {/* Hidden standard meter for accessibility tests */}
                    <div className="sr-only" role="meter" aria-label={`${kpi.label} progress`}
                      aria-valuemin={0} aria-valuemax={100} aria-valuenow={numericPct} />

                    <div className="mt-2 space-y-1 text-[9px] font-mono">
                      <div className="px-2 py-0.5 rounded bg-slate-900/90 text-cyan-300 border border-slate-800 truncate" title={kpi.srcBadge}>
                        {kpi.srcBadge}
                      </div>
                      <div className="px-2 py-0.5 rounded bg-amber-950/40 text-amber-300/90 border border-amber-900/40 truncate" title={kpi.limBadge}>
                        {kpi.limBadge}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Interactive Polar Map & Candidate Sites Presets */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-[400px]">
              
              {/* Realistic Polar Stereographic Radar Map with Lunar Topography Shading */}
              <div className="lg:col-span-2 lunar-glow-box p-4 flex flex-col relative overflow-hidden shadow-2xl hud-corner-brackets">
                <div className="flex items-center justify-between mb-3 z-10 flex-wrap gap-2">
                  <div className="flex items-center space-x-2">
                    <Compass className="h-4 w-4 text-cyan-400" aria-hidden="true" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                      Illustrative View — South Pole Stereographic (Schematic)
                    </h3>
                  </div>
                  <div className="flex items-center space-x-2 text-[11px] font-mono">
                    <span className="px-2.5 py-0.5 rounded-lg border bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold shadow-[0_0_10px_rgba(56,189,248,0.2)]">
                      Schematic & Sites
                    </span>
                    <button 
                      type="button" 
                      disabled 
                      aria-disabled="true"
                      title="LOLA DEM raster layer requires real GeoTIFF ingestion into backend/data/dem/ (under development)"
                      className="px-2.5 py-0.5 rounded-lg border border-slate-800 text-slate-600 cursor-not-allowed"
                    >
                      LOLA DEM (80m Active)
                    </button>
                  </div>
                </div>

                <div className="relative flex-1 rounded-xl border border-sky-500/20 bg-[#02040a] overflow-hidden flex items-center justify-center min-h-[330px]" role="img" aria-label="Schematic polar stereographic map showing candidate landing sites positioned by their registered coordinates">
                  
                  {/* Radar rotating sweep beam */}
                  <div className="radar-beam" />

                  <svg className="w-full h-full max-w-[480px] max-h-[370px]" viewBox="0 0 300 300" role="presentation" aria-hidden="true">
                    <defs>
                      {/* Deep lunar space gradient */}
                      <radialGradient id="lunarSurfaceGrad" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#14223d" stopOpacity="0.95" />
                        <stop offset="35%" stopColor="#0d172c" stopOpacity="0.9" />
                        <stop offset="70%" stopColor="#060c18" stopOpacity="0.95" />
                        <stop offset="100%" stopColor="#010307" stopOpacity="0.98" />
                      </radialGradient>

                      {/* Shackleton Crater Deep Shadow */}
                      <radialGradient id="shackletonCraterShadow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#020408" stopOpacity="1" />
                        <stop offset="60%" stopColor="#060a14" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.4" />
                      </radialGradient>

                      {/* Malapert Massif Elevation Gradient */}
                      <radialGradient id="malapertGrad" cx="45%" cy="45%" r="60%">
                        <stop offset="0%" stopColor="#7dd3fc" stopOpacity="0.5" />
                        <stop offset="60%" stopColor="#0c4a6e" stopOpacity="0.25" />
                        <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                      </radialGradient>
                    </defs>

                    {/* Lunar South Pole Background Sphere */}
                    <rect x="0" y="0" width="300" height="300" fill="url(#lunarSurfaceGrad)" />

                    {/* Realistic Shaded Lunar Topography (Simulated Impact Basins & Ridges) */}
                    <circle cx="150" cy="150" r="118" fill="none" stroke="#0f1f3a" strokeWidth="1" />
                    
                    {/* Simulated Major Craters Relief (Shoemaker, Faustini, Haworth, Amundsen) */}
                    <ellipse cx="120" cy="165" rx="22" ry="18" fill="#030712" stroke="#1e293b" strokeWidth="0.8" opacity="0.6" />
                    <text x="120" y="167" textAnchor="middle" fill="#475569" fontSize="5.5" fontFamily="monospace">Shoemaker</text>

                    <ellipse cx="178" cy="168" rx="24" ry="19" fill="#030712" stroke="#1e293b" strokeWidth="0.8" opacity="0.6" />
                    <text x="178" y="170" textAnchor="middle" fill="#475569" fontSize="5.5" fontFamily="monospace">Faustini</text>

                    <ellipse cx="130" cy="115" rx="26" ry="20" fill="#030712" stroke="#1e293b" strokeWidth="0.8" opacity="0.6" />
                    <text x="130" y="117" textAnchor="middle" fill="#475569" fontSize="5.5" fontFamily="monospace">Haworth Basin</text>

                    {/* Malapert Massif Shaded Elevation Hill */}
                    <ellipse cx="145" cy="98" rx="28" ry="18" fill="url(#malapertGrad)" stroke="#38bdf8" strokeWidth="0.8" strokeDasharray="2 3" opacity="0.8" />
                    <text x="145" y="94" textAnchor="middle" fill="#38bdf8" fontSize="6" fontFamily="monospace" fontWeight="bold">MALAPERT MASSIF</text>

                    {/* Concentric Polar Range Circles (82°S, 84°S, 86°S, 88°S) */}
                    {[24, 48, 72, 96, 120].map(r => (
                      <circle key={r} cx="150" cy="150" r={r} fill="none" stroke="#1e3a5f" strokeDasharray="3 3" strokeWidth="0.75" />
                    ))}

                    {/* Radar Crosshairs */}
                    <line x1="150" y1="15" x2="150" y2="285" stroke="#1e3a5f" strokeWidth="0.8" />
                    <line x1="15" y1="150" x2="285" y2="150" stroke="#1e3a5f" strokeWidth="0.8" />

                    {/* Azimuth Angle Compass Ticks */}
                    <text x="150" y="12" textAnchor="middle" fill="#38bdf8" fontSize="7" fontFamily="monospace" fontWeight="bold">000° (Earth-Facing Prime)</text>
                    <text x="290" y="153" textAnchor="end" fill="#64748b" fontSize="6.5" fontFamily="monospace">090°E</text>
                    <text x="150" y="295" textAnchor="middle" fill="#64748b" fontSize="6.5" fontFamily="monospace">180°</text>
                    <text x="10" y="153" textAnchor="start" fill="#64748b" fontSize="6.5" fontFamily="monospace">270°E</text>

                    {/* South Pole Center: Shackleton Crater Rim */}
                    <circle cx="150" cy="150" r="11" fill="url(#shackletonCraterShadow)" stroke="#38bdf8" strokeWidth="1.5" />
                    <circle cx="150" cy="150" r="4" fill="#020408" stroke="#f59e0b" strokeWidth="1" />
                    <text x="150" y="146" textAnchor="middle" fill="#7dd3fc" fontSize="6.5" fontFamily="monospace" fontWeight="bold">90°S Pole</text>

                    {/* Candidate Landing Site Nodes */}
                    {polarSites.map(site => {
                      const isSel = site.id === selectedSiteId;
                      return (
                        <g 
                          key={site.id} 
                          tabIndex={0} 
                          role="button" 
                          aria-label={`Select ${site.name}`}
                          onClick={() => setSelectedSiteId(site.id)}
                          onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedSiteId(site.id); }}}
                          className="cursor-pointer focus:outline-none transition" 
                          style={{ outline: 'none' }}
                        >
                          {/* Animated Target Acquisition Bracket */}
                          {isSel && (
                            <g className="target-lock-reticle">
                              <circle cx={site.svgX} cy={site.svgY} r="13" fill="none" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3 3" />
                              <circle cx={site.svgX} cy={site.svgY} r="17" fill="none" stroke="#38bdf8" strokeWidth="1.5" className="animate-ping" opacity="0.5" />
                              {/* Corner Brackets */}
                              <path d={`M ${site.svgX - 9} ${site.svgY - 5} L ${site.svgX - 9} ${site.svgY - 9} L ${site.svgX - 5} ${site.svgY - 9}`} fill="none" stroke="#38bdf8" strokeWidth="1.5" />
                              <path d={`M ${site.svgX + 9} ${site.svgY - 5} L ${site.svgX + 9} ${site.svgY - 9} L ${site.svgX + 5} ${site.svgY - 9}`} fill="none" stroke="#38bdf8" strokeWidth="1.5" />
                              <path d={`M ${site.svgX - 9} ${site.svgY + 5} L ${site.svgX - 9} ${site.svgY + 9} L ${site.svgX - 5} ${site.svgY + 9}`} fill="none" stroke="#38bdf8" strokeWidth="1.5" />
                              <path d={`M ${site.svgX + 9} ${site.svgY + 5} L ${site.svgX + 9} ${site.svgY + 9} L ${site.svgX + 5} ${site.svgY + 9}`} fill="none" stroke="#38bdf8" strokeWidth="1.5" />
                            </g>
                          )}

                          {/* Site Node Pin */}
                          <circle cx={site.svgX} cy={site.svgY} r={isSel ? 5.5 : 3.8} fill={isSel ? '#38bdf8' : '#f59e0b'} stroke="#02040a" strokeWidth="1.5" />
                          <circle cx={site.svgX} cy={site.svgY} r={isSel ? 2 : 1.5} fill="#ffffff" />
                          
                          {/* Site Label with background badge */}
                          <text 
                            x={site.svgX + 8} 
                            y={site.svgY + 3.5} 
                            fill={isSel ? '#38bdf8' : '#e2e8f0'} 
                            fontSize="8" 
                            fontFamily="JetBrains Mono, monospace" 
                            fontWeight={isSel ? 'bold' : 'normal'}
                          >
                            {site.name.split(' ')[0]}
                          </text>
                        </g>
                      );
                    })}
                  </svg>

                  {/* Active Site Real-time Telemetry HUD Box */}
                  <div className="absolute bottom-3 left-3 bg-[#050b18]/95 backdrop-blur-md border border-cyan-800/60 rounded-xl p-3 text-[10px] font-mono text-slate-300 shadow-2xl">
                    <div className="flex items-center space-x-1.5 text-cyan-400 font-extrabold tracking-wider border-b border-slate-800 pb-1 mb-1">
                      <Crosshair className="h-3 w-3 text-cyan-400" />
                      <span>{currentSite.name.toUpperCase()}</span>
                    </div>
                    <div className="text-slate-200 font-bold">{currentSite.lat}°S, {currentSite.lon}°E • {currentSite.elevation_m}m elev</div>
                    <div className="text-slate-500 text-[9px] mt-0.5">Stereographic Projection: 80°S–90°S IAU Lunar Grid</div>
                  </div>

                  <div className="absolute top-3 right-3 bg-black/80 backdrop-blur px-3 py-1 rounded-lg border border-amber-500/40 text-[10px] font-mono text-amber-300 font-bold tracking-wider">
                    POLAR RADAR TELEMETRY
                  </div>
                </div>
              </div>

              {/* Site Presets Tactical Selector */}
              <div className="lunar-glow-box p-4 flex flex-col shadow-xl hud-corner-brackets">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-2">
                  <div className="flex items-center space-x-2">
                    <TrendingUp className="h-4 w-4 text-emerald-400" aria-hidden="true" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">Schematic Mission Presets</h3>
                  </div>
                </div>

                <div className="mb-3 p-2 bg-[#040712] border border-slate-800/90 rounded-lg text-[10px] font-mono text-slate-400">
                  <span className="text-amber-400 font-bold">Scope:</span> Fixed coordinates support simulator controls and schematic only. Landing safety, slopes, boulders, and plume interactions require dedicated screening.
                </div>

                <div className="space-y-2.5 overflow-y-auto flex-1 pr-1 custom-scrollbar" role="listbox" aria-label="Illustrative simulator site presets">
                  {PRESET_SITES.map((site) => {
                    const isSel = site.id === selectedSiteId;
                    return (
                      <div 
                        key={site.id} 
                        role="option" 
                        aria-selected={isSel} 
                        tabIndex={0}
                        onClick={() => setSelectedSiteId(site.id)}
                        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedSiteId(site.id); }}}
                        className={`p-3 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col focus:outline-none focus:ring-2 focus:ring-cyan-400 ${
                          isSel 
                            ? 'bg-cyan-950/70 border-cyan-400 shadow-[0_0_16px_rgba(6,182,212,0.35)]' 
                            : 'bg-[#050916] border-slate-800/80 hover:bg-[#0c162c] hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1 flex-wrap">
                          <span className={`text-xs font-bold ${isSel ? 'text-cyan-200' : 'text-slate-200'}`}>{site.name}</span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[8px] font-mono uppercase px-1.5 py-0.5 rounded bg-amber-950/70 text-amber-300 border border-amber-700/50">
                              Illustrative Preset
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">{site.lat}°S, {site.lon}°E</span>
                          </div>
                        </div>
                        <p className="mt-1 text-[10px] text-slate-400 font-sans leading-relaxed">{site.description}</p>
                        {site.tradeoff && (
                          <div className="mt-1.5 text-[9px] font-mono text-cyan-300 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-900/50 flex items-center justify-between">
                            <span>Trade-off: {site.tradeoff}</span>
                            <span className="text-amber-400 font-bold ml-1">{site.elevation_m}m</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Mission Timeline Chart */}
            <div className="lunar-glow-box p-5 shadow-2xl flex flex-col hud-corner-brackets">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800/80 mb-4 gap-2">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center space-x-2">
                    <Activity className="h-4 w-4 text-cyan-400" aria-hidden="true" />
                    <span>Mission Timeline: Illumination vs DTE</span>
                    {simulationResult?.is_demo && !resultsAreStale && (
                      <span className="text-[10px] font-normal text-purple-400 ml-2">(Synthetic Demo Data)</span>
                    )}
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {displayChartData.length > 0
                      ? `${displayChartData.length} telemetry steps | Source: ${simulationResult?.data_source || 'unknown'}${resultsAreStale ? ' (stale — settings changed)' : ''}`
                      : 'Run a simulation to populate the timeline.'}
                  </p>
                </div>

                <div className="flex items-center space-x-4 text-xs font-mono flex-wrap gap-y-1">
                  <span className="flex items-center space-x-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-400 shadow-[0_0_6px_#fbbf24]" />
                    <span className="text-slate-300">Illumination</span>
                  </span>
                  <span className="flex items-center space-x-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399]" />
                    <span className="text-slate-300">DTE</span>
                  </span>
                  {savedBaseline && showComparisonView && (
                    <>
                      <span className="flex items-center space-x-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-amber-300/40 border border-amber-300" />
                        <span className="text-slate-400">[Base] Illum</span>
                      </span>
                      <span className="flex items-center space-x-1.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-emerald-300/40 border border-emerald-300" />
                        <span className="text-slate-400">[Base] DTE</span>
                      </span>
                    </>
                  )}
                  <span className="flex items-center space-x-1.5">
                    <span className="h-0.5 w-4 bg-rose-400/60 border-t border-dashed border-rose-400" />
                    <span className="text-slate-400">Bench ({benchmarkThreshold}%)</span>
                  </span>
                </div>
              </div>

              <div className="w-full h-64" style={{ minWidth: 320, minHeight: 256 }} role="img" aria-label={displayChartData.length > 0 ? 'Timeline chart showing illumination and DTE over mission duration' : 'Empty chart area'}>
                {displayChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%" minWidth={320} minHeight={240} initialDimension={{ width: 800, height: 256 }}>
                    <AreaChart data={displayChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="gIllum" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.45} />
                          <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="gDTE" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.45} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.6} />
                      <XAxis dataKey="label" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 9, fontFamily: 'monospace' }} interval="preserveStartEnd" />
                      <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'monospace' }} unit="%" />
                      <Tooltip
                        content={({ active, payload, label }) => {
                          if (active && payload && payload.length) {
                            const dataPoint = payload[0].payload;
                            return (
                              <div className="bg-[#050916] border border-cyan-800/80 rounded-xl p-3 font-mono text-[11px] text-[#F8FAFC] shadow-2xl space-y-1">
                                <div className="text-cyan-400 font-bold border-b border-slate-800 pb-1">
                                  {label} {dataPoint.timestamp ? `(${dataPoint.timestamp})` : ''}
                                </div>
                                {payload.map((entry, idx) => (
                                  <div key={idx} className="flex justify-between space-x-3">
                                    <span style={{ color: entry.color }}>{entry.name}:</span>
                                    <span className="font-bold">{entry.value != null ? `${entry.value}%` : '—'}</span>
                                  </div>
                                ))}
                                {dataPoint.sun_el != null && (
                                  <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-800/60">
                                    Sun: {dataPoint.sun_el}° el, {dataPoint.sun_az}° az
                                  </div>
                                )}
                                {dataPoint.earth_el != null && (
                                  <div className="text-[10px] text-slate-400">
                                    Earth: {dataPoint.earth_el}° el, {dataPoint.earth_az}° az
                                  </div>
                                )}
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Area type="monotone" dataKey="benchmark" stroke="#f43f5e" strokeDasharray="4 4" strokeWidth={1} fill="none" name="Benchmark" connectNulls={false} />
                      {savedBaseline && showComparisonView && (
                        <>
                          <Area type="monotone" dataKey="base_illumination" stroke="#d97706" strokeDasharray="3 3" strokeWidth={1.5} fill="none" name="[Base] Illum" connectNulls={false} />
                          <Area type="monotone" dataKey="base_dte" stroke="#059669" strokeDasharray="3 3" strokeWidth={1.5} fill="none" name="[Base] DTE" connectNulls={false} />
                        </>
                      )}
                      <Area type="monotone" dataKey="illumination" stroke="#f59e0b" strokeWidth={2.5} fillOpacity={1} fill="url(#gIllum)" name="Illumination (%)" connectNulls={false} />
                      <Area type="monotone" dataKey="dte" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#gDTE)" name="DTE (%)" connectNulls={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full w-full flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-xl text-slate-500 font-mono text-xs space-y-2">
                    <Activity className="h-8 w-8 text-slate-700" aria-hidden="true" />
                    <span>No timeline data to display.</span>
                    <span className="text-[11px] text-slate-600">
                      {simulationStatus === 'engine_pending' ? 'Engine pending. Enable Demo Mode to preview the chart.' : 'Configure parameters and click "Run Simulation".'}
                    </span>
                  </div>
                )}
              </div>

              {/* Status bar */}
              <div className="mt-3 bg-[#030610] border border-slate-800/90 rounded-xl p-3 flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400 gap-2 shadow-inner" role="status">
                <div className="flex items-center space-x-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${
                    simulationStatus === 'success' ? 'bg-cyan-400 shadow-[0_0_8px_#38bdf8]' :
                    simulationStatus === 'loading' ? 'bg-amber-400 animate-pulse' :
                    simulationStatus === 'error' ? 'bg-rose-500 shadow-[0_0_8px_#f43f5e]' :
                    simulationStatus === 'engine_pending' ? 'bg-amber-500' : 'bg-slate-600'
                  }`} aria-hidden="true" />
                  <span className="font-bold text-slate-200">
                    {simulationStatus === 'idle' && 'IDLE'}
                    {simulationStatus === 'loading' && 'LOADING'}
                    {simulationStatus === 'engine_pending' && 'ENGINE PENDING'}
                    {simulationStatus === 'success' && (simulationResult?.is_demo ? 'DEMO COMPLETE' : 'COMPLETE')}
                    {simulationStatus === 'error' && 'ERROR'}
                  </span>
                  <span>
                    {simulationStatus === 'idle' && '— Ready for input.'}
                    {simulationStatus === 'loading' && '— Awaiting server response…'}
                    {simulationStatus === 'engine_pending' && '— Real engine integration pending.'}
                    {simulationStatus === 'success' && (resultsAreStale ? '— Settings changed since last run.' : '— Results displayed.')}
                    {simulationStatus === 'error' && '— See error details above.'}
                  </span>
                </div>
                <span>BENCHMARK: {benchmarkThreshold}% (adjustable display metric)</span>
              </div>
            </div>

          </div>

          {/* ============================================================== */}
          {/* TAB 2: TERRAIN & LANDING HAZARDS                               */}
          {/* ============================================================== */}
          <div className={activeTab === 'hazards' || activeTab === 'all' ? 'space-y-6' : 'hidden'}>
            <HorizonAndOpsPanel embedded />
            <LandingRiskPanel
              embedded
              siteId={selectedSiteId}
              lat={useCustomCoords ? Number(customLat) : currentSite.lat}
              lon={useCustomCoords ? Number(customLon) : currentSite.lon}
              riskData={simulationResult?.landing_risk_assessment}
            />
          </div>

          {/* ============================================================== */}
          {/* TAB 3: MISSION DESIGN LAB & STRATEGY                           */}
          {/* ============================================================== */}
          <div className={activeTab === 'lab' || activeTab === 'all' ? 'space-y-6' : 'hidden'}>
            <DecisionBriefPanel embedded />
            <MissionDesignLabPanel embedded />
          </div>

          {/* ============================================================== */}
          {/* TAB 4: SCIENTIFIC ARCHIVE & EPHEMERIS                          */}
          {/* ============================================================== */}
          <div className={activeTab === 'archive' || activeTab === 'all' ? 'space-y-6' : 'hidden'}>
            <RealReferenceKpiPanel reference={simulationResult?.reference_kpis} terrainInfo={simulationResult?.terrain_info} stale={resultsAreStale} />
            <RealArchiveDataPanel embedded />
            <RealHorizonsPanel ephemeris={simulationResult?.ephemeris_check} stale={resultsAreStale} />
          </div>

          {/* ============================================================== */}
          {/* TAB 5: VALIDATION & JUDGE EVIDENCE                             */}
          {/* ============================================================== */}
          <div className={activeTab === 'validation' || activeTab === 'all' ? 'space-y-6' : 'hidden'}>
            <JudgeEvidencePanel embedded />
            <ScientificValidationPanel report={simulationResult?.validation_report} stale={resultsAreStale} />
            <VerificationSuitePanel embedded />
            <ChallengeAlignmentPanel embedded />
          </div>

        </div>
      </main>

      {/* ================================================================== */}
      {/* DATA SOURCES & METHODOLOGY MODAL                                   */}
      {/* ================================================================== */}
      {showMethodologyModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#0b101f] border border-cyan-700/60 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-[0_20px_60px_rgba(0,0,0,0.7)] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-cyan-900/40 bg-[#050813]">
              <div className="flex items-center space-x-2.5">
                <Database className="h-5 w-5 text-cyan-400" aria-hidden="true" />
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-slate-100">Official Data Sources & Methodology</h2>
                  <p className="text-[10px] font-mono text-cyan-400">Provenance Audit & Scientific Transparency</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowMethodologyModal(false)}
                aria-label="Close methodology modal"
                className="p-1 rounded-lg text-slate-400 hover:text-white transition focus:outline-none focus:ring-2 focus:ring-cyan-400"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar text-xs">
              
              {/* Scientific Engine Status Notice */}
              <div className="p-3.5 rounded-xl border bg-amber-950/20 border-amber-800/40 text-amber-200 space-y-1">
                <div className="font-bold flex items-center space-x-1.5 text-amber-300">
                  <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                  <span>Scientific Integration Status</span>
                </div>
                <p className="text-[11px] leading-relaxed text-slate-300">
                  This system architecture is decoupled into production-ready service clients for JPL Horizons, SPICE kernels, and LOLA DEM rasters.
                  Currently, when running simulations with <strong>Demo Mode OFF</strong>, the system reports <code className="text-amber-300">engine_pending</code> and does not fabricate unverified results.
                </p>
              </div>

              {/* Official Sources List */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">External NASA / JPL / USGS Technical References</h3>
                
                <div className="space-y-2.5">
                  {[
                    {
                      name: "JPL Solar System Dynamics (Horizons API)",
                      url: "https://ssd.jpl.nasa.gov/api/horizons.api",
                      docUrl: "https://ssd-api.jpl.nasa.gov/doc/horizons.html",
                      role: "Provides apparent topocentric vectors for the Sun ('10') and Earth ('399') from lunar surface geodetic coordinates (coord@301) with down-leg light-time corrected positions.",
                      statusBadge: "Live API Verified & Offline Fixture Ready"
                    },
                    {
                      name: "USGS Astrogeology PDS Geosciences Node (Orbital Data Explorer - ODE)",
                      url: "https://ode.rsl.wustl.edu/",
                      docUrl: "https://science.nasa.gov/mission/lro/lola/",
                      role: "Official repository for LRO LOLA Gridded Data Records (LDEM_80S_100M and LDEM_80S_80MPP_ADJ). 32-bit floating point elevation relative to 1737.4 km lunar sphere in Polar Stereographic projection.",
                      statusBadge: "Active & Verified: LDEM_80S_80MPP_ADJ.TIF (80 m/px)"
                    },
                    {
                      name: "NAIF SPICE Toolkit & Lunar Kernels",
                      url: "https://naif.jpl.nasa.gov/naif/data.html",
                      docUrl: "https://naif.jpl.nasa.gov/naif/toolkit.html",
                      role: "Transformations across reference frames: ICRF (inertial) -> MOON_ME (IAU lunar body-fixed) -> Topocentric ENU (local tangent plane). Kernels: naif0012.tls, pck00010.tpc, de430.bsp.",
                      statusBadge: "Mathematical Frame Basis Verified"
                    },
                    {
                      name: "NASA Moon Trek Visualization Portal",
                      url: "https://trek.nasa.gov/moon/",
                      docUrl: "https://trek.nasa.gov/moon/",
                      role: "Interactive visual portal. Note: Moon Trek tiles provide 8-bit visual rendering (RGB/PNG), not 32-bit floating point elevation DEMs for raytracing. Used for visual verification only.",
                      statusBadge: "Visual Reference Only (Non-numerical)"
                    }
                  ].map((src, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-[#070b18] border border-slate-800 space-y-1.5 font-mono">
                      <div className="flex items-center justify-between flex-wrap gap-1">
                        <span className="font-bold text-slate-200">{src.name}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-lg bg-cyan-950/60 border border-cyan-800/40 text-cyan-300">
                          {src.statusBadge}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-sans leading-relaxed">{src.role}</p>
                      <div className="flex items-center space-x-3 text-[10px] text-cyan-400 pt-0.5">
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className="flex items-center space-x-1 hover:underline">
                          <span>Primary Link</span>
                          <ExternalLink className="h-3 w-3" aria-hidden="true" />
                        </a>
                        <a href={src.docUrl} target="_blank" rel="noopener noreferrer" className="flex items-center space-x-1 hover:underline text-slate-400">
                          <span>Documentation</span>
                          <ExternalLink className="h-3 w-3" aria-hidden="true" />
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Team-Supplied GIS Archive */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">Team-Supplied GIS Archive — Catalog v2</h3>
                <div className="p-3.5 rounded-xl bg-[#070b18] border border-amber-900/50 text-[11px] space-y-2 text-slate-300">
                  <p>Immediate archive references: <code>Illumination_Modeling/READ_ME.txt</code> and its Midsummer GeoTIFFs; <code>PSR_Volatile_Estimates/PSR_volatile_abundance_final.shp</code> and companion files; and the legacy <code>LandingSites</code> point bundle. The derived JSON is <code>lunar_catalog_v2.json</code>, rebuilt by <code>build_catalog_v2.py</code>.</p>
                  <p>Catalog v2 contains 336 regional rasters (21 areas, years 2025–2032, two source fields) and 141 PSR polygons. The supplied README defines raster counts as consecutive 12-hour increments; displayed days are raster values divided by 2. Primary upstream provenance and some field definitions are unverified; these user-supplied GIS archives are not attributed to NASA here. The rasters are not an elevation DEM.</p>
                  <p className="text-amber-200">“Sun+Earth” is the source-field label only; its definition is unverified and it is not a DTE or ground-station connection percentage. PSR assignment by centroid within rectangular area extents is approximate.</p>
                </div>
              </div>

              {/* Physical Assumptions & Raytracing */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-300">Methodology & Physical Raytracing</h3>
                <div className="p-3.5 rounded-xl bg-[#070b18] border border-slate-800 text-[11px] space-y-2 font-mono text-slate-300">
                  <div><strong>1. Lunar Curvature Drop:</strong> Δz_curv = r² / (2 · R_Moon) where R_Moon = 1,737.4 km. Accounts for horizon depression over terrain distance.</div>
                  <div><strong>2. Finite Celestial Discs:</strong> Modeled with apparent solar angular radius R_⊙ ≈ 0.260° (15.6 arcmin) and Earth angular radius R_⊕ ≈ 0.900° (54.0 arcmin). Accounts for solar penumbra and Earth disc occlusion.</div>
                  <div><strong>3. Antenna Vantage Elevation:</strong> Vantage height z_obs = z_ground + h_antenna elevates line of sight over local crater rims.</div>
                  <div><strong>4. Coordinate Precedence:</strong> When custom coordinates are submitted, they take precedence over predefined site presets.</div>
                </div>
              </div>

              {/* RF Communications vs Geometric Line-of-Sight Disclaimer */}
              <div className="p-3.5 rounded-xl bg-[#070b18] border border-emerald-900/40 text-[11px] space-y-1.5 font-mono text-emerald-200">
                <div className="font-bold text-emerald-300 uppercase tracking-wider">Geometric Earth Visibility vs. Operational RF Comms</div>
                <p className="text-[10px] leading-relaxed text-slate-300 font-sans">
                  The intended Direct-to-Earth metric is <strong>geometric line-of-sight</strong> between the site and Earth center/limb, not an operational RF link budget. The real terrain-aware calculation is not yet connected; current Demo Mode DTE percentages are synthetic, and the archive's Sun+Earth field is not a DTE measure. A future operational RF assessment would also require carrier frequency, transmitter power, antenna gain, receiver G/T, coding, attenuation, and DSN scheduling.
                </p>
              </div>

              {/* Landing Safety Boundaries */}
              <div className="p-3.5 rounded-xl bg-[#070b18] border border-amber-900/40 text-[11px] space-y-1.5 font-mono text-amber-200">
                <div className="font-bold text-amber-300 uppercase tracking-wider">Landing Safety & Hazard Boundaries</div>
                <p className="text-[10px] leading-relaxed text-slate-300 font-sans">
                  The planned site assessment concerns <strong>illumination and Earth line-of-sight geometry</strong>, but a terrain-aware real-data pipeline is still pending and Demo Mode remains synthetic. This tool does <em>not</em> evaluate or certify landing safety. Critical hazards—including slope stability, boulders, bearing strength, plume-surface interactions, and thermal conditions—require separate dedicated assessment.
                </p>
              </div>

              {/* Composite Ranking Disclaimer */}
              <div className="p-3.5 rounded-xl bg-[#070b18] border border-purple-900/40 text-[11px] space-y-1 font-mono text-purple-200">
                <div className="font-bold text-purple-300 uppercase tracking-wider">Composite Scoring Weighting (Design Metric)</div>
                <p className="text-[10px] leading-relaxed text-slate-300 font-sans">
                  The archive explorer does not calculate a composite suitability ranking. Any rating returned by the prototype Demo Mode is a <strong>synthetic project design index</strong>, not an archive-derived result, and is <strong>NOT an official NASA score or ranking</strong>. No measured slope layer is currently connected.
                </p>
              </div>

            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-cyan-900/40 bg-[#050813] flex items-center justify-between flex-wrap gap-2 text-xs">
              <span className="text-[10px] font-mono text-slate-500">
                Audit Version: 1.3.0 • Reference Datum: Moon 2000 IAU
              </span>
              <div className="flex items-center space-x-2">
                {simulationResult && (
                  <button
                    type="button"
                    onClick={handleExportRunJson}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs uppercase tracking-wider transition shadow"
                  >
                    <Download className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>Export Run & Provenance (JSON)</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowMethodologyModal(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
                >
                  Close
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
