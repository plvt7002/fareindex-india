import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Sparkles,
  Plane,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Minus,
  Info,
  ArrowRight,
  BarChart3,
  Layers,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { api } from '../api/client';
import { formatINR, formatPct, formatDisplayDate } from '../utils/formatters';

const AIRPORTS = [
  { code: 'HYD', name: 'Hyderabad (RGIA)' },
  { code: 'DEL', name: 'Delhi (IGIA)' },
  { code: 'GOI', name: 'Goa (Dabolim)' },
  { code: 'BOM', name: 'Mumbai (CSMIA)' },
  { code: 'BLR', name: 'Bengaluru (KIA)' },
  { code: 'MAA', name: 'Chennai (MAA)' },
  { code: 'CCU', name: 'Kolkata (CCU)' },
];

const PRESETS = [
  { origin: 'HYD', destination: 'DEL', outbound_date: '2026-09-29', label: 'HYD → DEL (29 Sep 2026)' },
  { origin: 'HYD', destination: 'GOI', outbound_date: '2026-09-29', label: 'HYD → GOI (29 Sep 2026)' },
];

function GoogleHistoryTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-900 text-white p-2.5 rounded-lg shadow-xl text-xs font-sans">
      <div className="text-slate-400 text-[11px] mb-1">{d.displayDate}</div>
      <div className="font-mono font-bold text-sm text-sky-300">
        {formatINR(d.price)}
      </div>
      <div className="text-[10px] text-slate-400 mt-0.5">Google recorded fare</div>
    </div>
  );
}

export function SecondOpinionSection({ onExploreAnalytics }) {
  const [origin, setOrigin] = useState('HYD');
  const [destination, setDestination] = useState('DEL');
  const [outboundDate, setOutboundDate] = useState('2026-09-29');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [isDetailedExplanationOpen, setIsDetailedExplanationOpen] = useState(false);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);

  // Fetch comparison dynamically from backend API
  const handleCheckFare = useCallback(async (customOrigin, customDest, customDate) => {
    const o = (customOrigin || origin).trim().toUpperCase();
    const d = (customDest || destination).trim().toUpperCase();
    const dt = (customDate || outboundDate).trim();

    if (!o || !d || !dt) {
      setError('Please select valid origin, destination, and outbound date.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.getSecondOpinion(o, d, dt);
      setResult(data);
    } catch (err) {
      console.error('Second Opinion API Error:', err);
      setError(err.message || 'Failed to retrieve Second Opinion from backend service.');
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  }, [origin, destination, outboundDate]);

  // Load default query on mount
  useEffect(() => {
    handleCheckFare('HYD', 'DEL', '2026-09-29');
  }, [handleCheckFare]);

  // Transform Google price history if available
  const historySeries = useMemo(() => {
    if (!result?.google?.price_history || !Array.isArray(result.google.price_history)) {
      return [];
    }
    return result.google.price_history.map(([timestamp, price]) => {
      const d = new Date(timestamp * 1000);
      return {
        timestamp,
        date: d.toISOString().split('T')[0],
        displayDate: d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
        price: Number(price),
      };
    });
  }, [result]);

  const comparisonStatus = result?.comparison?.status || 'INSUFFICIENT_DATA';
  const signalGap = result?.comparison?.signal_gap;

  // Midpoint & deviations for visual context
  const googleRange = result?.google?.typical_price_range;
  const googleMidpoint = googleRange && googleRange.low && googleRange.high
    ? (googleRange.low + googleRange.high) / 2
    : null;
  const googlePct = googleMidpoint && result?.live_price
    ? ((result.live_price - googleMidpoint) / googleMidpoint) * 100
    : null;

  const fareindexMedian = result?.fareindex?.median;
  const fareindexPct = fareindexMedian && result?.live_price
    ? ((result.live_price - fareindexMedian) / fareindexMedian) * 100
    : null;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* 1. PRIMARY PRODUCT STORY & SEARCH */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 text-white rounded-3xl p-6 sm:p-8 shadow-xl border border-slate-800 relative overflow-hidden">
        {/* Decorative blur accents */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-72 h-72 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-20 w-72 h-72 rounded-full bg-sky-500/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/15 border border-teal-400/30 text-teal-300 text-xs font-semibold mb-3 tracking-wide">
            <Sparkles className="w-3.5 h-3.5 text-teal-400" />
            <span>FAREINDEX SECOND OPINION</span>
          </div>

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white font-sans leading-tight">
            What does your airfare actually mean?
          </h1>

          <p className="mt-2 text-sm sm:text-base text-slate-300 max-w-2xl leading-relaxed">
            See how Google Flights and FareIndex interpret the same fare using different reference frames.
          </p>
        </div>

        {/* 2. SEARCH CONTROLS */}
        <div className="mt-6 pt-6 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          {/* Origin */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Plane className="w-3.5 h-3.5 text-teal-400 -rotate-45" />
              <span>From (Origin)</span>
            </label>
            <select
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="w-full bg-slate-800/90 border border-slate-700 text-white rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:ring-2 focus:ring-teal-500 focus:border-teal-500 cursor-pointer transition-all"
            >
              {AIRPORTS.map((a) => (
                <option key={a.code} value={a.code} className="bg-slate-900 text-white">
                  {a.code} — {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Destination */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Plane className="w-3.5 h-3.5 text-teal-400 rotate-45" />
              <span>To (Destination)</span>
            </label>
            <select
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full bg-slate-800/90 border border-slate-700 text-white rounded-xl px-3.5 py-2.5 text-sm font-semibold focus:ring-2 focus:ring-teal-500 focus:border-teal-500 cursor-pointer transition-all"
            >
              {AIRPORTS.map((a) => (
                <option key={a.code} value={a.code} className="bg-slate-900 text-white">
                  {a.code} — {a.name}
                </option>
              ))}
            </select>
          </div>

          {/* Date */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-teal-400" />
              <span>Outbound Date</span>
            </label>
            <input
              type="date"
              value={outboundDate}
              onChange={(e) => setOutboundDate(e.target.value)}
              className="w-full bg-slate-800/90 border border-slate-700 text-white rounded-xl px-3.5 py-2 text-sm font-semibold focus:ring-2 focus:ring-teal-500 focus:border-teal-500 cursor-pointer transition-all [color-scheme:dark]"
            />
          </div>

          {/* Submit Button */}
          <div>
            <button
              onClick={() => handleCheckFare()}
              disabled={isLoading}
              className="w-full bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold px-4 py-2.5 rounded-xl transition-all shadow-md active:scale-95 disabled:opacity-60 cursor-pointer flex items-center justify-center gap-2 text-sm"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-slate-950" />
                  <span>Checking Live Fares...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 text-slate-950" />
                  <span>Check Fare</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Presets */}
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium">Quick Routes:</span>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => {
                setOrigin(p.origin);
                setDestination(p.destination);
                setOutboundDate(p.outbound_date);
                handleCheckFare(p.origin, p.destination, p.outbound_date);
              }}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/80 transition-colors font-medium cursor-pointer"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-sans flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
            <div>
              <div className="font-bold text-rose-900">Query Failed</div>
              <div className="text-rose-700 mt-0.5">{error}</div>
            </div>
          </div>
          <button
            onClick={() => handleCheckFare()}
            className="px-3 py-1.5 bg-rose-100 hover:bg-rose-200 text-rose-900 rounded-lg border border-rose-300 font-semibold cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && !result && (
        <div className="space-y-6 animate-pulse">
          <div className="h-32 bg-slate-200 rounded-2xl border border-slate-300/80" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-48 bg-slate-200 rounded-2xl border border-slate-300/80" />
            <div className="h-48 bg-slate-200 rounded-2xl border border-slate-300/80" />
          </div>
        </div>
      )}

      {/* 3. RESULT HERO (ONE CENTRAL LIVE FARE) */}
      {result && (
        <div className="space-y-8">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 text-center shadow-xs relative overflow-hidden">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold mb-3">
              <span className="font-bold text-slate-900">{result.origin} → {result.destination}</span>
              <span className="text-slate-300">·</span>
              <span className="font-mono text-slate-600">{formatDisplayDate(result.outbound_date)}</span>
            </div>

            <div className="text-xs font-bold uppercase tracking-widest text-slate-400 font-mono">
              YOUR LIVE FARE
            </div>

            <div className="text-4xl sm:text-5xl lg:text-6xl font-black font-mono text-slate-950 tracking-tight my-2">
              {formatINR(result.live_price)}
            </div>

            <div className="text-xs text-slate-500 flex items-center justify-center gap-2">
              <span className="font-semibold text-slate-700">
                {result.google?.flight_result_count ?? 0} verified domestic flights found
              </span>
              <span className="text-slate-300">·</span>
              <span>Lowest verified one-way itinerary</span>
            </div>
          </div>

          {/* 4. SIGNAL COMPARISON (PROMOTED CORE RESULT VISUAL CENTER) */}
          <div
            className={`rounded-3xl p-6 sm:p-8 border shadow-sm transition-all ${
              comparisonStatus === 'FULL_DIVERGENCE'
                ? 'bg-amber-50/80 border-amber-300 text-amber-950'
                : comparisonStatus === 'PARTIAL_DIVERGENCE'
                ? 'bg-sky-50/80 border-sky-300 text-sky-950'
                : comparisonStatus === 'AGREEMENT'
                ? 'bg-emerald-50/80 border-emerald-300 text-emerald-950'
                : 'bg-slate-100 border-slate-300 text-slate-900'
            }`}
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
                <span>SIGNAL COMPARISON</span>
                <span className="text-[11px] font-sans font-medium text-slate-600">Dual Reference Frame Benchmark</span>
              </div>

              {/* Prominent Side-by-Side Diagram */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 rounded-2xl bg-white/90 border border-slate-200 shadow-xs">
                {/* Google Box */}
                <div className="text-center sm:text-left flex flex-col gap-1">
                  <span className="text-[11px] font-bold text-slate-500 font-mono uppercase">GOOGLE FLIGHTS</span>
                  <span className={`px-4 py-1.5 rounded-xl text-sm font-black uppercase font-mono border inline-flex items-center justify-center gap-1.5 ${
                    result.google?.price_level === 'high' ? 'bg-rose-50 text-rose-800 border-rose-200' :
                    result.google?.price_level === 'low' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                    'bg-sky-50 text-sky-800 border-sky-200'
                  }`}>
                    {result.google?.price_level === 'high' && <TrendingUp className="w-4 h-4" />}
                    {result.google?.price_level === 'low' && <TrendingDown className="w-4 h-4" />}
                    {(result.google?.price_level === 'typical' || !result.google?.price_level) && <Minus className="w-4 h-4" />}
                    <span>{result.google?.price_level || 'TYPICAL'}</span>
                  </span>
                </div>

                {/* Relationship Badge in Middle */}
                <div className="flex flex-col items-center gap-1">
                  {comparisonStatus === 'FULL_DIVERGENCE' && (
                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-black bg-amber-200 text-amber-950 border border-amber-400 shadow-2xs tracking-wide">
                      <AlertTriangle className="w-4 h-4 text-amber-900" />
                      <span>CLEAR DISAGREEMENT</span>
                    </span>
                  )}
                  {comparisonStatus === 'PARTIAL_DIVERGENCE' && (
                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-black bg-sky-200 text-sky-950 border border-sky-400 shadow-2xs tracking-wide">
                      <Sparkles className="w-4 h-4 text-sky-900" />
                      <span>SAME TIER, DIFFERENT REFERENCE</span>
                    </span>
                  )}
                  {comparisonStatus === 'AGREEMENT' && (
                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-black bg-emerald-200 text-emerald-950 border border-emerald-400 shadow-2xs tracking-wide">
                      <CheckCircle2 className="w-4 h-4 text-emerald-900" />
                      <span>SIGNALS ALIGN</span>
                    </span>
                  )}
                  {comparisonStatus === 'INSUFFICIENT_DATA' && (
                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold bg-slate-200 text-slate-800 border border-slate-300">
                      <HelpCircle className="w-4 h-4 text-slate-700" />
                      <span>NOT ENOUGH DATA</span>
                    </span>
                  )}
                  <span className="text-[11px] font-sans font-medium text-slate-500">
                    Two reference frames interpret the same live fare differently.
                  </span>
                </div>

                {/* FareIndex Box */}
                <div className="text-center sm:text-right flex flex-col gap-1">
                  <span className="text-[11px] font-bold text-slate-500 font-mono uppercase">FAREINDEX</span>
                  <span className={`px-4 py-1.5 rounded-xl text-sm font-black uppercase font-mono border inline-flex items-center justify-center gap-1.5 ${
                    result.fareindex?.tier === 'LOW' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                    result.fareindex?.tier === 'HIGH' ? 'bg-rose-50 text-rose-800 border-rose-200' :
                    'bg-sky-50 text-sky-800 border-sky-200'
                  }`}>
                    {result.fareindex?.tier === 'LOW' && <TrendingDown className="w-4 h-4" />}
                    {result.fareindex?.tier === 'HIGH' && <TrendingUp className="w-4 h-4" />}
                    {(result.fareindex?.tier === 'TYPICAL' || !result.fareindex?.tier) && <Minus className="w-4 h-4" />}
                    <span>{result.fareindex?.tier || 'TYPICAL'}</span>
                  </span>
                </div>
              </div>

              {/* Plain Language Interpretation Statement */}
              <div className="text-sm sm:text-base font-bold text-slate-900 leading-snug">
                {comparisonStatus === 'FULL_DIVERGENCE' && (
                  <span>
                    The same {formatINR(result.live_price)} fare is <strong className="uppercase text-rose-800">{result.google?.price_level || 'HIGH'}</strong> relative to Google&apos;s typical search range, but <strong className="uppercase text-emerald-800">{result.fareindex?.tier || 'LOW'}</strong> relative to FareIndex&apos;s verified domestic distribution.
                  </span>
                )}
                {comparisonStatus === 'PARTIAL_DIVERGENCE' && (
                  <span>
                    Both reference frames classify {formatINR(result.live_price)} as <strong className="uppercase text-sky-800">{result.fareindex?.tier || 'TYPICAL'}</strong>, but their underlying reference levels differ ({formatINR(googleMidpoint)} Google midpoint vs {formatINR(fareindexMedian)} FareIndex median).
                  </span>
                )}
                {comparisonStatus === 'AGREEMENT' && (
                  <span>
                    Both reference signals align on the relative fare tier for this departure date.
                  </span>
                )}
                {comparisonStatus === 'INSUFFICIENT_DATA' && (
                  <span>
                    Comparison inconclusive due to missing reference data.
                  </span>
                )}
              </div>

              {/* Reference-Frame Gap Strip */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-200/80 text-xs">
                <div className="text-slate-600 text-[11px] leading-relaxed">
                  <strong>Reference-frame gap:</strong> Difference between FareIndex deviation ({fareindexPct !== null ? formatPct(fareindexPct) : '—'}) and Google midpoint deviation ({googlePct !== null ? formatPct(googlePct) : '—'}).
                </div>
                <div className="flex items-center gap-2 font-mono self-end sm:self-auto shrink-0">
                  <span className="text-slate-500 font-sans text-[11px]">Experimental reference-frame gap:</span>
                  <span className="font-bold text-slate-900 bg-white/90 px-2.5 py-0.5 rounded-lg border border-slate-200">
                    {signalGap !== null && signalGap !== undefined ? formatPct(signalGap) : '—'}
                  </span>
                </div>
              </div>
            </div>

            {/* WHY DO THE SIGNALS DIFFER? */}
            <div className="mt-5 pt-5 border-t border-slate-200/80 space-y-2.5">
              <div className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Info className="w-3.5 h-3.5 text-slate-600" />
                <span>WHY DO THE SIGNALS DIFFER?</span>
              </div>

              <div className="text-xs sm:text-sm text-slate-700 leading-relaxed font-sans space-y-1">
                <p className="m-0">
                  Google Flights and FareIndex use different reference frames. Google provides a live search-window interpretation, while FareIndex compares the fare with an independently observed domestic one-way distribution.
                </p>
                <p className="font-semibold text-slate-900 m-0">
                  Same live fare. Different reference frame.
                </p>
              </div>

              {result.explanation && (
                <div className="pt-1">
                  <button
                    onClick={() => setIsDetailedExplanationOpen(!isDetailedExplanationOpen)}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-teal-800 hover:text-teal-950 underline underline-offset-2 cursor-pointer transition-colors"
                  >
                    <span>{isDetailedExplanationOpen ? 'Hide statistical breakdown' : 'View statistical breakdown'}</span>
                    {isDetailedExplanationOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {isDetailedExplanationOpen && (
                    <div className="mt-2.5 p-4 rounded-xl bg-white/80 border border-slate-200 text-xs text-slate-700 leading-relaxed font-sans shadow-2xs">
                      {result.explanation}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 5. TWO WAYS TO INTERPRET THIS FARE (DETAILED EVIDENCE CARDS) */}
          <div className="space-y-4">
            <div className="text-center sm:text-left">
              <h2 className="text-lg sm:text-xl font-bold text-slate-950 tracking-tight leading-snug">
                Detailed Evidence: Two Reference Frames
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                How each independent framework evaluates this flight itinerary:
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* LEFT PANEL: GOOGLE FLIGHTS REFERENCE FRAME */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs flex flex-col justify-between relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-sky-50 rounded-bl-full pointer-events-none" />

                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-sky-600" />
                      <span className="text-sm font-bold text-slate-900 font-sans">
                        Google Flights
                      </span>
                    </div>
                    <span className="text-[11px] font-semibold text-sky-800 bg-sky-50 px-2.5 py-0.5 rounded-full border border-sky-200 shrink-0">
                      Search Reference
                    </span>
                  </div>

                  {/* Google Tier / Level */}
                  <div className="space-y-1.5 my-4">
                    <div className="text-xs text-slate-500 font-medium">Google&apos;s interpretation:</div>
                    <div>
                      <span
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-2xl text-lg font-black uppercase tracking-wider border shadow-2xs ${
                          result.google?.price_level === 'high'
                            ? 'bg-rose-50 text-rose-800 border-rose-200'
                            : result.google?.price_level === 'low'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : 'bg-sky-50 text-sky-800 border-sky-200'
                        }`}
                      >
                        {result.google?.price_level === 'high' && <TrendingUp className="w-5 h-5" />}
                        {result.google?.price_level === 'low' && <TrendingDown className="w-5 h-5" />}
                        {(result.google?.price_level === 'typical' || !result.google?.price_level) && <Minus className="w-5 h-5" />}
                        <span>{result.google?.price_level || 'TYPICAL'}</span>
                      </span>
                    </div>
                  </div>

                  {/* Typical Price Range */}
                  <div className="pt-4 border-t border-slate-100 space-y-2.5">
                    <div className="flex justify-between items-baseline text-xs">
                      <span className="text-slate-500">Typical search range:</span>
                      <span className="font-mono font-bold text-slate-900 text-sm">
                        {result.google?.typical_price_range
                          ? `${formatINR(result.google.typical_price_range.low)} — ${formatINR(result.google.typical_price_range.high)}`
                          : 'Not available'}
                      </span>
                    </div>

                    {googlePct !== null && (
                      <div className="text-[11px] font-mono text-slate-500 flex justify-between">
                        <span>Relative to midpoint ({formatINR(googleMidpoint)}):</span>
                        <span className={`font-bold ${googlePct > 0 ? 'text-rose-700' : googlePct < 0 ? 'text-emerald-700' : 'text-slate-700'}`}>
                          {formatPct(googlePct)}
                        </span>
                      </div>
                    )}

                    {/* Range Visualizer */}
                    {result.google?.typical_price_range && (
                      <div className="pt-1">
                        <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden flex">
                          <div className="h-full bg-sky-500 rounded-full w-full" />
                        </div>
                        <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
                          <span>Low: {formatINR(result.google.typical_price_range.low)}</span>
                          <span>High: {formatINR(result.google.typical_price_range.high)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 text-[11px] text-slate-400 flex justify-between items-center">
                  <span>Source: SerpApi / Google Flights</span>
                  <span className="font-medium text-slate-600">{result.google?.airlines?.slice(0, 3).join(', ')}</span>
                </div>
              </div>

              {/* RIGHT PANEL: FAREINDEX REFERENCE FRAME */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs flex flex-col justify-between relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-teal-50 rounded-bl-full pointer-events-none" />

                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-teal-600" />
                      <span className="text-sm font-bold text-slate-900 font-sans">
                        FareIndex reference distribution
                      </span>
                    </div>
                    <span className="text-[11px] font-semibold text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded-full border border-teal-200 shrink-0">
                      Observed Distribution
                    </span>
                  </div>

                  {/* FareIndex Tier */}
                  <div className="space-y-1.5 my-4">
                    <div className="text-xs text-slate-500 font-medium">FareIndex&apos;s interpretation:</div>
                    <div>
                      <span
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-2xl text-lg font-black uppercase tracking-wider border shadow-2xs ${
                          result.fareindex?.tier === 'LOW'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : result.fareindex?.tier === 'HIGH'
                            ? 'bg-rose-50 text-rose-800 border-rose-200'
                            : 'bg-sky-50 text-sky-800 border-sky-200'
                        }`}
                      >
                        {result.fareindex?.tier === 'LOW' && <TrendingDown className="w-5 h-5" />}
                        {result.fareindex?.tier === 'HIGH' && <TrendingUp className="w-5 h-5" />}
                        {(result.fareindex?.tier === 'TYPICAL' || !result.fareindex?.tier) && <Minus className="w-5 h-5" />}
                        <span>{result.fareindex?.tier || 'TYPICAL'}</span>
                      </span>
                    </div>
                  </div>

                  {/* Quantile Distribution Breakdown */}
                  <div className="pt-4 border-t border-slate-100 space-y-2.5">
                    <div className="text-xs text-slate-500 font-medium">Verified domestic distribution:</div>
                    <div className="grid grid-cols-3 gap-2 bg-slate-50 p-2.5 rounded-xl border border-slate-200/80 text-center font-mono text-xs">
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase font-sans">P25</div>
                        <div className="font-bold text-slate-900 mt-0.5">{formatINR(result.fareindex?.p25)}</div>
                      </div>
                      <div className="border-x border-slate-200 px-1">
                        <div className="text-[10px] text-teal-800 uppercase font-sans font-bold">Median</div>
                        <div className="font-black text-teal-900 mt-0.5">{formatINR(result.fareindex?.median)}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase font-sans">P75</div>
                        <div className="font-bold text-slate-900 mt-0.5">{formatINR(result.fareindex?.p75)}</div>
                      </div>
                    </div>

                    {fareindexPct !== null && (
                      <div className="text-[11px] font-mono text-slate-500 flex justify-between pt-0.5">
                        <span>Relative to median ({formatINR(fareindexMedian)}):</span>
                        <span className={`font-bold ${fareindexPct > 0 ? 'text-rose-700' : fareindexPct < 0 ? 'text-emerald-700' : 'text-slate-700'}`}>
                          {formatPct(fareindexPct)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-100 space-y-1 text-[11px]">
                  <div className="flex justify-between items-center text-slate-400">
                    <span>Source: FareIndex India · canonical domestic one-way observations</span>
                    <span className="font-semibold text-slate-700">
                      {result.fareindex?.observation_count ?? 0} canonical observations · Sep 8–9 · all horizons
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 leading-tight">
                    Reference distribution: {result.fareindex?.observation_count ?? 0} canonical domestic one-way observations across Sep 8–9 and all lead-time horizons.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 6. SUPPORTING EVIDENCE: GOOGLE FLIGHTS PRICE HISTORY */}
          {historySeries.length > 0 ? (
            <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-base font-bold text-slate-950 flex items-center gap-2">
                    <span>Google Flights price history</span>
                    <span className="text-xs font-normal text-slate-500 font-mono">
                      ({historySeries.length} recorded price points)
                    </span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Price history recorded by Google Flights for this specific departure date.
                  </p>
                </div>
                <span className="text-xs font-mono font-bold text-sky-800 bg-sky-50 px-2.5 py-1 rounded-lg border border-sky-200 self-start sm:self-auto">
                  Latest recorded: {formatINR(historySeries[historySeries.length - 1]?.price)}
                </span>
              </div>

              <div className="h-44 sm:h-52 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historySeries} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="googleHistoryGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0284c7" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis
                      dataKey="displayDate"
                      tickLine={false}
                      axisLine={{ stroke: '#CBD5E1' }}
                      tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                      dy={6}
                    />
                    <YAxis
                      domain={['auto', 'auto']}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `₹${(v / 1000).toFixed(1)}k`}
                      tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
                      width={50}
                    />
                    <Tooltip content={<GoogleHistoryTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="price"
                      stroke="#0284c7"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#googleHistoryGradient)"
                      dot={{ r: 2, fill: '#0284c7', stroke: '#ffffff', strokeWidth: 1.5 }}
                      activeDot={{ r: 4.5, fill: '#0369a1', stroke: '#ffffff', strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-center text-xs text-slate-500 font-mono">
              Google Flights price history data is not available for this specific date query.
            </div>
          )}

          {/* 8. METHODOLOGY & PROVENANCE DETAILS */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs">
            <button
              onClick={() => setIsMethodologyOpen(!isMethodologyOpen)}
              className="w-full flex items-center justify-between text-left cursor-pointer group"
            >
              <div className="flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-teal-700" />
                <span className="text-sm font-bold text-slate-900 group-hover:text-teal-900 transition-colors">
                  How this comparison works & Reference Frameworks
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                <span>{isMethodologyOpen ? 'Hide details' : 'Show details'}</span>
                {isMethodologyOpen ? (
                  <ChevronUp className="w-4 h-4 text-slate-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                )}
              </div>
            </button>

            {isMethodologyOpen && (
              <div className="mt-4 pt-4 border-t border-slate-100 text-xs text-slate-600 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/70">
                    <div className="font-bold text-slate-900 mb-1 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-sky-500" />
                      <span>Google Flights Signal</span>
                    </div>
                    <p className="text-slate-600 leading-relaxed text-[11px]">
                      SerpApi queries Google Flights and extracts live flight pricing, carrier availability, and Google’s own computed typical search price range.
                    </p>
                  </div>

                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/70">
                    <div className="font-bold text-slate-900 mb-1 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-teal-600" />
                      <span>FareIndex Signal</span>
                    </div>
                    <p className="text-slate-600 leading-relaxed text-[11px]">
                      FareIndex evaluates the live fare against verified domestic one-way distributions in the canonical dataset (P25, Median, P75), filtering out foreign transit routes.
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-[11px]">
                  <div>
                    <div className="text-slate-400 uppercase font-sans text-[10px]">FareIndex Basis</div>
                    <div className="font-bold text-slate-800">{result.methodology?.fareindex_basis || 'Observed domestic distribution'}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 uppercase font-sans text-[10px]">Comparison Type</div>
                    <div className="font-bold text-slate-800">{result.methodology?.comparison_type || 'Experimental heuristic'}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 uppercase font-sans text-[10px]">Live Source</div>
                    <div className="font-bold text-slate-800">{result.provenance?.live_source || 'SerpApi / Google Flights'}</div>
                  </div>
                  <div>
                    <div className="text-slate-400 uppercase font-sans text-[10px]">Baseline Source</div>
                    <div className="font-bold text-slate-800">{result.provenance?.historical_source || 'FareIndex India'}</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 9. EXPLORE ANALYTICS TRANSITION CALLOUT */}
          {onExploreAnalytics && (
            <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-3xl p-6 sm:p-7 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
              <div>
                <div className="text-xs font-bold text-teal-400 uppercase tracking-wider font-mono mb-1 flex items-center gap-1.5">
                  <BarChart3 className="w-3.5 h-3.5" />
                  <span>FareIndex Market Analytics</span>
                </div>
                <div className="text-base font-bold text-white">
                  Want to explore airfare market trends and route distributions?
                </div>
                <p className="text-xs text-slate-300 mt-0.5">
                  Inspect multi-day fare movements, booking lead-time curves, and underlying market observations.
                </p>
              </div>

              <button
                onClick={() => onExploreAnalytics('overview')}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs tracking-wide transition-all shrink-0 cursor-pointer flex items-center gap-2 shadow-md active:scale-95"
              >
                <span>View Analytics Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
