import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { ShieldCheck } from 'lucide-react';
import { formatDisplayDate, formatShortDate, formatINR, formatPct } from '../utils/formatters';

function MovementChartTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;

  const d = payload[0].payload;
  const dateStr = formatDisplayDate(d.observation_date);
  const fare = d.fare ?? 0;
  const isVerified = d.source_class === 'verified_current';
  const obsCount = d.observation_count ?? 0;
  const changeInr = d.change_inr;
  const changePct = d.change_pct;

  return (
    <div className="bg-white border border-slate-300 p-3 rounded-xl shadow-lg text-xs font-sans max-w-xs text-slate-800">
      <div className="font-bold text-slate-900 pb-1.5 mb-1.5 border-b border-slate-100 flex items-center justify-between gap-2">
        <span className="font-mono text-xs font-bold text-slate-900">{dateStr}</span>
      </div>

      <div className="space-y-1.5 font-mono text-xs">
        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">
            Typical market fare:
          </span>
          <span className="font-bold text-slate-950 text-sm">
            {formatINR(fare)}
          </span>
        </div>

        {isVerified && changePct !== null && changePct !== undefined && (
          <div className="flex justify-between items-center gap-4">
            <span className="text-slate-500 font-sans">Change vs previous:</span>
            <span className={`font-bold ${changePct > 0 ? 'text-rose-700' : changePct < 0 ? 'text-emerald-700' : 'text-slate-700'}`}>
              {changePct > 0 ? '↑ ' : changePct < 0 ? '↓ ' : ''}{formatINR(Math.abs(changeInr))} ({formatPct(changePct)})
            </span>
          </div>
        )}

        <div className="flex justify-between items-center gap-4 pt-1 border-t border-slate-100 text-[11px]">
          <span className="text-slate-500 font-sans">Observed sample:</span>
          <span className="font-semibold text-slate-800">
            {obsCount} flights
          </span>
        </div>
      </div>
    </div>
  );
}

function CustomizedMovementDot(props) {
  const { cx, cy, payload } = props;
  if (!cx || !cy) return null;

  if (payload.source_class === 'verified_current') {
    return (
      <g>
        <circle cx={cx} cy={cy} r={9} fill="#0F766E" fillOpacity={0.18} />
        <circle cx={cx} cy={cy} r={5.5} fill="#0F766E" stroke="#ffffff" strokeWidth={2} />
      </g>
    );
  }

  // Historical reference dot
  return (
    <g>
      <circle cx={cx} cy={cy} r={4} fill="#ffffff" stroke="#94A3B8" strokeWidth={2} />
    </g>
  );
}

export function FareMovementChart({
  movementData,
  selectedRoute,
  isNational,
}) {
  const isBuilding = movementData?.status === 'BUILDING_BASELINE';
  const series = movementData?.series || [];
  const routeTitle = selectedRoute ? selectedRoute.replace('-', ' → ') : 'Tracked market';
  const latestMovement = movementData?.latest_point;

  // Single dynamic sentence summarizing the movement
  let insightSentence = 'Market movement is currently tracking within a stable range across observed dates.';
  if (latestMovement?.change_pct !== null && latestMovement?.change_pct !== undefined) {
    const absChg = formatINR(Math.abs(latestMovement.change_inr));
    const pctStr = formatPct(Math.abs(latestMovement.change_pct));
    if (latestMovement.direction === 'RISING') {
      insightSentence = `Typical fare rose ${absChg} (+${pctStr}) from the previous verified observation.`;
    } else if (latestMovement.direction === 'FALLING') {
      insightSentence = `Typical fare fell ${absChg} (-${pctStr}) from the previous verified observation.`;
    } else {
      insightSentence = `Typical fare remained stable compared with the previous verified observation.`;
    }
  }

  // Building State (e.g. HYD-GOI with only 1 observation point)
  if (isBuilding) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-slate-950 m-0 tracking-tight">
                Fare Movement
              </h2>
              <span
                className="text-xs font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-medium cursor-help"
                title="Current fares are verified. More observation dates are being collected to build a stronger historical trend."
              >
                Building history
              </span>
            </div>
            <p className="text-xs text-slate-500 m-0 mt-1">
              How the typical fare has changed across observation dates.
            </p>
          </div>
        </div>

        <div className="py-10 text-center text-slate-600 text-xs max-w-md mx-auto space-y-2">
          <p className="font-semibold text-slate-900 text-sm m-0">
            Observation history is accumulating for {routeTitle}.
          </p>
          <p className="text-slate-500 m-0 leading-relaxed">
            Multi-day movement trends will display as daily observation dates are recorded.
          </p>
        </div>

        <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-1.5 text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            <span>Actual observation timestamps only. No synthetic dates.</span>
          </div>
          <span className="font-mono text-[11px]">Verified observations</span>
        </div>
      </div>
    );
  }

  // Active Multi-Day Movement Series
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-950 m-0 tracking-tight">
            Fare Movement
          </h2>
          <p className="text-xs text-slate-500 mt-1 m-0">
            How the typical fare has changed across observation dates.
          </p>
        </div>
      </div>

      {/* ONE concise, data-derived takeaway ABOVE chart */}
      <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs sm:text-sm text-slate-800 font-medium leading-relaxed flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-teal-700 shrink-0" />
        <span>{insightSentence}</span>
      </div>

      {/* Main Movement Chart */}
      <div className="h-80 sm:h-90 w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series} margin={{ top: 15, right: 20, left: 10, bottom: 5 }}>
            <defs>
              <linearGradient id="movementAreaGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0F766E" stopOpacity={0.12} />
                <stop offset="95%" stopColor="#0F766E" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis
              dataKey="observation_date"
              stroke="#CBD5E1"
              tickFormatter={formatShortDate}
              tick={{ fill: '#64748B', fontSize: 12, fontFamily: 'monospace', fontWeight: 600 }}
            />
            <YAxis
              stroke="#CBD5E1"
              tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'monospace' }}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(1)}k`}
              domain={['dataMin - 400', 'dataMax + 400']}
            />
            <Tooltip
              content={<MovementChartTooltip />}
              isAnimationActive={false}
              cursor={{ stroke: '#94A3B8', strokeWidth: 1, strokeDasharray: '3 3' }}
            />
            <Area
              type="monotone"
              dataKey="fare"
              stroke="#0F766E"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#movementAreaGradient)"
              isAnimationActive={false}
              dot={<CustomizedMovementDot />}
              activeDot={{ r: 7, fill: '#0F766E', stroke: '#ffffff', strokeWidth: 2.5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Minimal Footer Note */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-1.5 text-[11px]">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>Verified domestic one-way observations.</span>
        </div>
        <span className="font-mono text-[11px]">Fare Movement</span>
      </div>
    </div>
  );
}

