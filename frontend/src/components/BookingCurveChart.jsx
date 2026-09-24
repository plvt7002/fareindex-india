import React, { useState } from 'react';
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
import { Info, ShieldCheck } from 'lucide-react';
import { formatINR } from '../utils/formatters';

const HORIZONS = [
  { id: '7D', label: 'Near-term', desc: '1–10 days ahead' },
  { id: '14D', label: '14D', desc: '11–17 days ahead' },
  { id: '21D', label: '21D', desc: '18–25 days ahead' },
  { id: '30D', label: '30D', desc: '26–45 days ahead' },
  { id: '60D', label: '60D', desc: '46+ days ahead' },
];

function CustomBookingTooltip({ active, payload, viewMetric }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;

  return (
    <div className="bg-white border border-slate-300 p-3 rounded-xl shadow-lg text-xs font-sans text-slate-800 max-w-xs">
      <div className="font-bold text-slate-900 pb-1.5 mb-1.5 border-b border-slate-100 flex items-center justify-between gap-3">
        <span className="text-slate-500 font-normal">Booking Horizon:</span>
        <span className="font-mono text-slate-950 font-bold px-1.5 py-0.2 rounded bg-slate-100 border border-slate-200">
          {d.lead_time_label || `${d.lead_time_days}d ahead`}
        </span>
      </div>

      <div className="space-y-1.5 font-mono text-xs">
        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">Typical Fare (Median):</span>
          <span className="font-bold text-slate-950 text-sm">{formatINR(d.typical_fare ?? d.median_fare)}</span>
        </div>
        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">Average Fare (Mean):</span>
          <span className="font-semibold text-slate-800">{formatINR(d.average_fare ?? d.avg_fare)}</span>
        </div>
        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">Observed Range:</span>
          <span className="text-slate-600">{formatINR(d.min_fare)} – {formatINR(d.max_fare)}</span>
        </div>
        <div className="flex justify-between items-center gap-4 pt-1 border-t border-slate-100 text-[11px]">
          <span className="text-slate-500 font-sans">Observed sample:</span>
          <span className="font-semibold text-slate-700">{d.observation_count} flights (n = {d.observation_count})</span>
        </div>
      </div>
    </div>
  );
}

export function BookingCurveChart({ bookingData, route, selectedBucket = '7D', onSelectBucket }) {
  const [metricView, setMetricView] = useState('median'); // 'median' [Default] | 'average'
  const [activeHorizon, setActiveHorizon] = useState('7D');

  const series = bookingData?.series || bookingData?.curve || [];

  if (!series || series.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-3">
        <h2 className="text-xl font-bold text-slate-950 m-0 tracking-tight">
          Booking Behaviour
        </h2>
        <div className="py-8 text-center text-slate-500 text-xs">
          No booking behaviour observations available.
        </div>
      </div>
    );
  }

  const routeTitle = route ? route.replace('-', ' → ') : 'Tracked Market';
  const currentSelectedBucket = selectedBucket || activeHorizon;

  const nearTermEntry = series.find((s) => s.bucket === '7D') || series[0];
  const nearTermVal = nearTermEntry ? (nearTermEntry.typical_fare ?? nearTermEntry.median_fare) : null;

  let bookingInsight = 'Observed fares vary by booking horizon across advance departure dates.';
  if (nearTermVal) {
    bookingInsight = `Observed fares vary by booking horizon, with the near-term window currently at ${formatINR(nearTermVal)}.`;
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-5 shadow-sm">
      {/* Header with Title and Subtitle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-950 m-0 tracking-tight">
            How fares vary with booking time
          </h2>
          <p className="text-xs text-slate-500 m-0 mt-1">
            How observed fares differ depending on how far ahead the flight is booked ({routeTitle}).
          </p>
        </div>

        {/* Controls: Horizon Selector + Typical/Average Toggle */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Horizon Selector */}
          <div className="inline-flex items-center p-1 rounded-xl bg-slate-100 border border-slate-200 text-xs">
            {HORIZONS.map((h) => {
              const isSelected = currentSelectedBucket === h.id;
              return (
                <button
                  key={h.id}
                  onClick={() => {
                    setActiveHorizon(h.id);
                    if (onSelectBucket) onSelectBucket(h.id);
                  }}
                  className={`px-2.5 py-1 rounded-lg font-mono font-semibold transition-all cursor-pointer ${isSelected
                      ? 'bg-teal-700 text-white font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                    }`}
                  title={`${h.id}: ${h.desc}`}
                >
                  {h.label}
                </button>
              );
            })}
          </div>

          {/* Toggle: Typical vs Average */}
          <div className="inline-flex items-center p-1 rounded-xl bg-slate-100 border border-slate-200 text-xs">
            <button
              onClick={() => setMetricView('median')}
              className={`px-3 py-1 rounded-lg font-semibold transition-all cursor-pointer ${metricView === 'median'
                  ? 'bg-teal-700 text-white font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              Typical
            </button>
            <button
              onClick={() => setMetricView('average')}
              className={`px-3 py-1 rounded-lg font-semibold transition-all cursor-pointer ${metricView === 'average'
                  ? 'bg-teal-700 text-white font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              Average
            </button>
          </div>
        </div>
      </div>

      {/* ONE concise, data-derived takeaway ABOVE chart */}
      <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs sm:text-sm text-slate-800 font-medium leading-relaxed flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-teal-700 shrink-0" />
        <span>{bookingInsight}</span>
      </div>

      {/* Horizon Guide Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
        {HORIZONS.map((h) => {
          const isSelected = currentSelectedBucket === h.id;
          const entry = series.find((s) => s.bucket === h.id);
          const obsCount = entry?.observation_count;
          return (
            <div
              key={h.id}
              className={`p-2.5 rounded-xl border transition-all ${isSelected
                  ? 'bg-teal-50 border-teal-200 text-teal-950 font-medium shadow-2xs'
                  : 'bg-slate-50/60 border-slate-200/70 text-slate-600'
                }`}
            >
              <div className="font-mono font-bold text-xs text-slate-900 flex items-center justify-between">
                <span>{h.label}</span>
                {obsCount !== undefined && (
                  <span className="text-[10px] text-slate-500 font-normal font-mono">n = {obsCount}</span>
                )}
              </div>
              <div className="text-[11px] text-slate-500 leading-tight mt-0.5">{h.desc}</div>
            </div>
          );
        })}
      </div>

      {/* Booking Curve Bar Chart */}
      <div className="h-64 sm:h-72 w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={series} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis
              dataKey="lead_time_label"
              stroke="#CBD5E1"
              tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace', fontWeight: 500 }}
            />
            <YAxis
              stroke="#CBD5E1"
              tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip
              content={<CustomBookingTooltip viewMetric={metricView} />}
              cursor={false}
              isAnimationActive={false}
            />
            <Bar
              dataKey={metricView === 'median' ? 'typical_fare' : 'average_fare'}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            >
              {series.map((entry, index) => {
                const isHighlighted = entry.bucket === currentSelectedBucket;
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={isHighlighted ? '#0F766E' : '#CBD5E1'}
                    opacity={1.0}
                  />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Booking Curve Explanatory Footnote */}
      <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-400 gap-2">
        <div className="flex items-center gap-1.5 text-[11px]">
          <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>Lead time is the advance interval in days between observation date and flight travel date.</span>
        </div>
        <div className="text-[11px] font-mono shrink-0">
          Advance booking curve
        </div>
      </div>
    </div>
  );
}


