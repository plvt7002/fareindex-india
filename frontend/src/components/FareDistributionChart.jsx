import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import { ShieldCheck } from 'lucide-react';
import { formatINR } from '../utils/formatters';

const BUCKET_METADATA = {
  '7D': { label: 'Near-term', range: '1–10 days ahead' },
  '14D': { label: '14D', range: '11–17 days ahead' },
  '21D': { label: '21D', range: '18–25 days ahead' },
  '30D': { label: '30D', range: '26–45 days ahead' },
  '60D': { label: '60D', range: '46+ days ahead' },
};

function CustomDistributionTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;

  return (
    <div className="bg-white border border-slate-300 p-3 rounded-xl shadow-lg text-xs font-sans text-slate-800 max-w-xs">
      <div className="font-bold text-slate-900 pb-1.5 mb-1.5 border-b border-slate-100 flex items-center justify-between gap-2">
        <span className="text-slate-500 font-normal">Fare Bracket:</span>
        <span className="font-mono text-slate-950 font-bold px-1.5 py-0.2 rounded bg-slate-100 border border-slate-200">
          {d.bin_label}
        </span>
      </div>

      <div className="space-y-1.5 font-mono text-xs">
        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">Observations:</span>
          <span className="font-bold text-slate-950 text-sm">
            {d.count} flights
          </span>
        </div>
        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">Share:</span>
          <span className="font-semibold text-slate-700">
            {d.percentage}%
          </span>
        </div>

        {d.has_median && (
          <div className="mt-1.5 pt-1.5 border-t border-slate-100 flex items-center gap-1.5 text-[11px] font-sans text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-700 shrink-0" />
            <span>Contains <strong>Typical Fare</strong></span>
          </div>
        )}

        {d.has_mean && (
          <div className="mt-1 flex items-center gap-1.5 text-[11px] font-sans text-slate-700 bg-slate-50 px-2 py-0.5 rounded">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500 shrink-0" />
            <span>Contains <strong>Average Fare</strong></span>
          </div>
        )}
      </div>
    </div>
  );
}

export function FareDistributionChart({
  distributionData,
  route,
  leadTimeLabel = 'Near-term · 1–10 days ahead',
  leadTimeBucket = '7D',
}) {
  const bins = distributionData?.bins || [];
  const medianFare = distributionData?.median_fare;
  const averageFare = distributionData?.average_fare;
  const p10Fare = distributionData?.p10_fare;
  const p25Fare = distributionData?.p25_fare;
  const p75Fare = distributionData?.p75_fare;
  const p90Fare = distributionData?.p90_fare;
  const totalObservations = distributionData?.total_observations || 0;
  const minFare = distributionData?.min_fare;
  const maxFare = distributionData?.max_fare;

  const routeDisplayName = route ? route.replace('-', ' → ') : 'Selected Route';
  const horizonInfo = BUCKET_METADATA[leadTimeBucket] || {
    label: leadTimeLabel || 'Near-term',
    range: '1–10 days ahead',
  };
  const horizonHeading = `${horizonInfo.label} · ${horizonInfo.range}`;

  const horizonName = horizonInfo.label || 'near-term';
  let distributionInsight = `Observed fares for ${horizonName.toLowerCase()} departures show typical market pricing at ${medianFare ? formatINR(medianFare) : '—'}.`;
  if (p25Fare && p75Fare) {
    distributionInsight = `Most ${horizonName.toLowerCase()} fares are concentrated between ${formatINR(p25Fare)} and ${formatINR(p75Fare)}.`;
  }

  if (!bins || bins.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-3 shadow-sm">
        <h2 className="text-xl font-bold text-slate-950 m-0 tracking-tight">
          Where fares are clustering
        </h2>
        <div className="py-8 text-center text-slate-500 text-xs">
          No verified fare observations available for this travel window.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-xl font-bold text-slate-950 m-0 tracking-tight">
              Where fares are clustering
            </h2>
            <span className="text-xs font-mono px-2.5 py-0.5 rounded-md bg-teal-50 text-teal-900 border border-teal-200 font-bold">
              {horizonHeading}
            </span>
          </div>
          <p className="text-xs text-slate-500 m-0 mt-1">
            Where observed fares cluster for flights departing {horizonInfo.range} on {routeDisplayName}.
          </p>
        </div>

        <div className="text-xs font-mono text-slate-600 flex items-center gap-3">
          <span>Observed: <strong>{totalObservations} flights</strong></span>
          <span className="text-slate-300">•</span>
          <span
            className="cursor-help"
            title={p10Fare && p90Fare ? `P10–P90: ${formatINR(p10Fare)} – ${formatINR(p90Fare)}` : undefined}
          >
            Span: <strong>{formatINR(minFare)} – {formatINR(maxFare)}</strong>
          </span>
        </div>
      </div>

      {/* ONE concise, data-derived takeaway ABOVE chart */}
      <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs sm:text-sm text-slate-800 font-medium leading-relaxed flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-teal-700 shrink-0" />
        <span>{distributionInsight}</span>
      </div>

      {/* Main Consumer Stat Row (Typical · Average · Typical Fare Range) */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200/90 text-xs font-sans">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-900 font-bold">Typical:</span>
          <span className="font-mono font-bold text-slate-950">{medianFare ? formatINR(medianFare) : '—'}</span>
        </div>
        <div className="text-slate-300">•</div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-medium">Average:</span>
          <span className="font-mono font-semibold text-slate-800">{averageFare ? formatINR(averageFare) : '—'}</span>
        </div>
        <div className="text-slate-300">•</div>
        <div className="flex items-center gap-1.5">
          <span className="text-slate-500 font-medium">Typical Fare Range:</span>
          <span
            className="font-mono font-bold text-slate-900 cursor-help"
            title={p10Fare && p90Fare ? `Middle 50% (P25–P75). 80% range (P10–P90): ${formatINR(p10Fare)} – ${formatINR(p90Fare)}` : 'Middle 50% of observed fares'}
          >
            {p25Fare && p75Fare ? `${formatINR(p25Fare)} – ${formatINR(p75Fare)}` : '—'}
          </span>
        </div>
      </div>

      {/* Clean Distribution Histogram Chart */}
      <div className="h-64 sm:h-72 w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bins} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis
              dataKey="bin_label"
              stroke="#CBD5E1"
              tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace', fontWeight: 500 }}
            />
            <YAxis
              stroke="#CBD5E1"
              tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
              tickFormatter={(v) => `${v}`}
              allowDecimals={false}
            />
            <Tooltip
              content={<CustomDistributionTooltip />}
              cursor={false}
              isAnimationActive={false}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {bins.map((entry, index) => {
                const isMedianBin = entry.has_median;
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={isMedianBin ? '#0F766E' : '#CBD5E1'}
                    opacity={1.0}
                  />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Footer */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-1.5 text-[11px]">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>Verified domestic one-way observations for selected travel horizon.</span>
        </div>
      </div>
    </div>
  );
}

