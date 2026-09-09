import React, { useState } from 'react';
import {
  ShieldCheck,
  HelpCircle,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { formatDisplayDate, formatINR, formatPct } from '../utils/formatters';
import { RouteCoverageSection } from './RouteCoverageSection';

/**
 * Descriptive fare position based on percentiles.
 * Strictly descriptive — no buying/booking advice.
 */
function getFarePosition(p25, median, p75, count) {
  if (!count || count < 5 || !p25 || !p75) {
    return {
      label: 'LIMITED HISTORY',
      status: 'LIMITED',
      desc: 'Limited observation history for stable percentile range.',
      badgeClass: 'text-amber-800 bg-amber-50 border-amber-200',
    };
  }

  if (median <= p25) {
    return {
      label: 'LOW',
      status: 'LOW',
      desc: `Typical fare is near the lower end of the observed market range (below P25: ${formatINR(p25)}).`,
      badgeClass: 'text-emerald-800 bg-emerald-50 border-emerald-200',
    };
  }

  if (median >= p75) {
    return {
      label: 'HIGH',
      status: 'HIGH',
      desc: `Typical fare is near the upper end of the observed market range (above P75: ${formatINR(p75)}).`,
      badgeClass: 'text-rose-800 bg-rose-50 border-rose-200',
    };
  }

  const isNearLower = (median - p25) < (p75 - p25) * 0.35;
  return {
    label: 'NORMAL',
    status: 'NORMAL',
    desc: isNearLower
      ? `Typical fare is near the lower end of the normal observed range.`
      : `Typical fare sits comfortably within the normal observed range.`,
    badgeClass: 'text-slate-800 bg-slate-100 border-slate-200',
  };
}

export function MarketHero({
  routes,
  selectedRoute,
  onSelectRoute,
  routeSummaries,
  nationalData,
  nearTermTrendData,
  currentRouteTrendData,
  movementData,
  onOpenMethodology,
}) {
  const [showMethodologyTooltip, setShowMethodologyTooltip] = useState(false);
  const isNational = selectedRoute === null;
  const currentSummary = routeSummaries?.find((s) => s.route === selectedRoute);

  // Use fixed near-term (1–10D) trend data for hero benchmark
  const nearTerm = nearTermTrendData || currentRouteTrendData;

  // PRIMARY HERO METRIC: Latest Daily Market Level (Median across canonical all-horizon snapshot)
  let latestMarketLevel = movementData?.daily_median_fare ?? movementData?.latest_point?.fare ?? currentSummary?.daily_median_fare ?? currentSummary?.latest_median_fare ?? 0;
  let latestMarketAverage = movementData?.daily_mean_fare ?? movementData?.latest_point?.daily_mean_fare ?? currentSummary?.daily_mean_fare ?? currentSummary?.latest_avg_fare ?? 0;

  // SECONDARY BENCHMARK: Typical Near-Term Fare (Median of 1-10D near-term bucket)
  let typicalNearTermFare = currentSummary?.near_term_median ?? nearTerm?.current_typical_fare ?? currentSummary?.current_typical_fare ?? 0;
  let averageNearTermFare = currentSummary?.near_term_mean ?? nearTerm?.current_average_fare ?? currentSummary?.current_average_fare ?? 0;
  let nearTermP25 = nearTerm?.p25_fare;
  let nearTermP75 = nearTerm?.p75_fare;
  let nearTermCount = nearTerm?.observation_count ?? currentSummary?.observation_count ?? 0;

  let rawObsDate = currentSummary?.latest_observation_date || nationalData?.latest_value?.observation_date || null;
  let routeDisplayName = selectedRoute ? selectedRoute.replace('-', ' → ') : 'Tracked-route composite';

  if (isNational) {
    const latestNat = nationalData?.latest_value;
    latestMarketLevel = latestNat?.national_median_fare || latestNat?.national_avg_fare || 0;
    latestMarketAverage = latestNat?.national_avg_fare || 0;
    typicalNearTermFare = latestNat?.national_median_fare || latestNat?.national_avg_fare || 0;
    nearTermCount = (routeSummaries || []).reduce((acc, curr) => acc + (curr.observation_count || 0), 0);
    rawObsDate = latestNat?.observation_date || null;
    routeDisplayName = 'Tracked-route composite';
  }

  const formattedDate = formatDisplayDate(rawObsDate, '9 Sep 2026');

  // Movement details from Movement API
  const latestMovement = movementData?.latest_point;
  const changeInr = latestMovement?.change_inr;
  const changePct = latestMovement?.change_pct;
  const direction = latestMovement?.direction || 'STABLE';
  const hasMovement = changeInr !== null && changeInr !== undefined;

  // Plain English movement statement
  let movementStatement = 'Observed market fares are stable compared with the previous available market level.';
  if (direction === 'RISING') {
    movementStatement = 'Observed market level is higher than the previous available observation date.';
  } else if (direction === 'FALLING') {
    movementStatement = 'Observed market level is lower than the previous available observation date.';
  }

  const position = getFarePosition(
    nearTermP25,
    typicalNearTermFare,
    nearTermP75,
    nearTermCount
  );

  return (
    <section id="overview" className="space-y-6 pt-1">
      {/* 1. CONSUMER ROUTE SELECTOR ROW & ROUTE COVERAGE */}
      <div className="space-y-3 pb-4 border-b border-slate-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Route:
            </span>
            <div className="inline-flex items-center p-1 rounded-xl bg-slate-100 border border-slate-200 gap-1">
              {routes.map((r) => {
                const isSelected = selectedRoute === r;
                return (
                  <button
                    key={r}
                    onClick={() => onSelectRoute(r)}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${isSelected
                        ? 'bg-teal-700 text-white shadow-xs'
                        : 'text-slate-700 hover:text-slate-950 hover:bg-slate-200/50'
                      }`}
                  >
                    <span>{r.replace('-', ' → ')}</span>
                  </button>
                );
              })}

              {/* Tracked Route Composite */}
              <button
                onClick={() => onSelectRoute(null)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer flex items-center gap-1 ${isNational
                    ? 'bg-teal-700 text-white font-bold shadow-xs'
                    : 'text-slate-500 hover:text-slate-800'
                  }`}
                title="Tracked-route composite"
              >
                <span>Composite</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-sans">
            <span className="w-2 h-2 rounded-full bg-teal-600" />
            <span>Latest observation · <strong className="font-mono text-slate-900 font-semibold">{formattedDate}</strong></span>
          </div>
        </div>

        {/* Route Coverage & Coming Soon Cards */}
        <RouteCoverageSection
          selectedRoute={selectedRoute}
          onSelectRoute={onSelectRoute}
          routeSummaries={routeSummaries}
        />
      </div>

      {/* 2. HERO: MARKET LEVEL & MOVEMENT */}
      <div className="space-y-4">
        {/* Route and Label */}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-950 m-0 font-sans">
              {routeDisplayName}
            </h1>
            {isNational && (
              <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200 font-medium">
                Composite view
              </span>
            )}
          </div>
          <div className="space-y-0.5 pt-0.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 font-sans">
                Typical Market Fare
              </span>
              <button
                onClick={() => setShowMethodologyTooltip(!showMethodologyTooltip)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
                title="How typical fare is calculated"
              >
                <HelpCircle className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-xs text-slate-500 font-normal m-0">
              All current eligible observations
            </p>
          </div>
        </div>

        {/* Methodology Tooltip Callout */}
        {showMethodologyTooltip && (
          <div className="p-4 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-700 leading-relaxed max-w-2xl space-y-1.5">
            <div className="font-bold text-slate-900">How market metrics are calculated:</div>
            <div className="space-y-1 text-slate-600">
              <div>• <strong>Typical Market Fare ({formatINR(latestMarketLevel)}):</strong> Typical fare is the median of eligible observed domestic one-way fares across all booking horizons.</div>
              <div>• <strong>Average Observed Fare ({formatINR(latestMarketAverage)}):</strong> Arithmetic mean of all eligible market observations.</div>
              <div>• <strong>Typical Near-Term Fare ({formatINR(typicalNearTermFare)}):</strong> Median for departures within 1–10 days ahead.</div>
              <div>• <strong>Typical Fare Range ({nearTermP25 && nearTermP75 ? `${formatINR(nearTermP25)} – ${formatINR(nearTermP75)}` : '—'}):</strong> Middle 50% of observed fares (25th–75th percentile).</div>
            </div>
          </div>
        )}

        {/* Big Dominant Number */}
        <div>
          <div className="text-6xl sm:text-7xl lg:text-8xl font-black tracking-tight text-slate-950 font-mono leading-none">
            {formatINR(latestMarketLevel)}
          </div>
        </div>

        {/* Movement Metric & Plain English Statement */}
        <div className="space-y-1.5 pt-1">
          {hasMovement ? (
            <div className="flex flex-wrap items-center gap-2.5">
              <span className={`text-base sm:text-lg font-bold font-mono flex items-center gap-1 ${direction === 'RISING' ? 'text-rose-700' :
                  direction === 'FALLING' ? 'text-emerald-700' : 'text-slate-700'
                }`}>
                {direction === 'RISING' ? <TrendingUp className="w-5 h-5" /> : direction === 'FALLING' ? <TrendingDown className="w-5 h-5" /> : <Minus className="w-5 h-5" />}
                {direction === 'RISING' ? '↑ ' : direction === 'FALLING' ? '↓ ' : ''}
                {formatINR(Math.abs(changeInr))} ({formatPct(changePct)})
              </span>
              <span className="text-xs text-slate-500 font-medium">
                vs previous observation
              </span>
              <span className={`text-[11px] font-mono px-2 py-0.5 rounded font-bold uppercase ${direction === 'RISING' ? 'bg-rose-50 text-rose-800 border border-rose-200' :
                  direction === 'FALLING' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                    'bg-slate-100 text-slate-700 border border-slate-200'
                }`}>
                {direction}
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200 font-medium">
                {latestMovement?.movement_type === 'VERIFIED_DAY_OVER_DAY' || movementData?.status === 'VERIFIED_DAY_OVER_DAY'
                  ? 'VERIFIED DAY-OVER-DAY'
                  : 'Provisional'}
              </span>
            </div>
          ) : (
            <div className="text-xs text-slate-500 font-mono">
              Observation history is accumulating for this route.
            </div>
          )}

          <p className="text-sm text-slate-700 font-medium m-0">
            {movementStatement}
          </p>
        </div>

        {/* 3. COMPACT INLINE SECONDARY METRICS STRIP */}
        <div className="pt-4 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          {/* Item 1: Typical Near-Term Fare */}
          <div className="space-y-0.5">
            <span className="text-slate-500 font-medium block">
              Typical near-term fare:
            </span>
            <div className="font-mono text-lg font-bold text-slate-900">
              {formatINR(typicalNearTermFare)}
            </div>
            <span className="text-[11px] text-slate-500 block leading-tight">
              Flights departing in 1–10 days
            </span>
          </div>

          {/* Item 2: Average Observed Fare */}
          <div className="space-y-0.5">
            <span className="text-slate-500 font-medium block">
              Average observed fare:
            </span>
            <div className="font-mono text-lg font-bold text-slate-900">
              {formatINR(latestMarketAverage)}
            </div>
            <span className="text-[11px] text-slate-500 block leading-tight">
              Arithmetic mean across all market observations.
            </span>
          </div>

          {/* Item 3: Typical Fare Range */}
          <div className="space-y-0.5">
            <span className="text-slate-500 font-medium block">
              Typical Fare Range:
            </span>
            <div className="font-mono text-lg font-bold text-slate-900">
              {nearTermP25 && nearTermP75 ? `${formatINR(nearTermP25)} – ${formatINR(nearTermP75)}` : '—'}
            </div>
            <span className="text-[11px] text-slate-500 block leading-tight">
              Middle 50% of observed fares (25th–75th percentile).
            </span>
          </div>

          {/* Item 4: Fare Position */}
          <div className="space-y-0.5">
            <span className="text-slate-500 font-medium block">
              Fare Position:
            </span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`px-2 py-0.5 rounded font-mono text-xs font-bold border ${position.badgeClass}`}>
                {position.label}
              </span>
            </div>
            <span className="text-[11px] text-slate-500 block leading-tight pt-0.5">
              {position.desc}
            </span>
          </div>
        </div>

        {/* Short Contextual Note */}
        <div className="pt-2 text-xs text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-t border-slate-100">
          <p className="m-0">
            <strong>{routeDisplayName}</strong> typical market fare is <strong>{formatINR(latestMarketLevel)}</strong>, with an average observed fare of <strong>{formatINR(latestMarketAverage)}</strong>.
          </p>
          <div className="flex items-center gap-1.5 shrink-0 text-slate-400 text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            <span>Domestic · One-way · Economy · 1 adult · INR</span>
          </div>
        </div>
      </div>
    </section>
  );
}
