import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, Info, AlertCircle, RotateCcw, ArrowDown } from 'lucide-react';

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0].payload;
  const indexVal = data.index_value ?? data.national_index;
  const avgFare = data.avg_fare ?? data.national_avg_fare;
  const isElevated = indexVal >= 100;
  const diffPct = (indexVal - 100).toFixed(2);

  return (
    <div className="bg-white border border-slate-300 p-3 rounded-lg shadow-md text-xs font-sans max-w-xs text-slate-800">
      <div className="font-semibold text-slate-900 pb-1.5 mb-1.5 border-b border-slate-200 flex justify-between items-center">
        <span>Observation Date</span>
        <span className="font-mono text-slate-600">{data.observation_date}</span>
      </div>

      <div className="space-y-1 font-mono text-xs">
        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">Airfare Index:</span>
          <span className="font-bold text-slate-900">
            {indexVal !== undefined ? indexVal.toFixed(2) : '—'}
          </span>
        </div>

        <div className="flex justify-between items-center gap-4">
          <span className="text-slate-500 font-sans">vs Baseline:</span>
          <span className={`font-semibold ${isElevated ? 'text-rose-700' : 'text-emerald-700'}`}>
            {isElevated ? `+${diffPct}% above base` : `${diffPct}% below base`}
          </span>
        </div>

        {avgFare && (
          <div className="flex justify-between items-center gap-4 pt-1 border-t border-slate-100">
            <span className="text-slate-500 font-sans">Day Avg Fare:</span>
            <span className="font-semibold text-teal-800">
              ₹{avgFare.toLocaleString('en-IN')}
            </span>
          </div>
        )}

        {data.route_contributions && (
          <div className="pt-1.5 text-[11px] text-slate-500 border-t border-slate-100 font-sans">
            Contributing routes: {data.route_contributions.map(r => r.route).join(', ')}
          </div>
        )}
      </div>

      <div className="mt-2 pt-1.5 border-t border-slate-100 text-[10px] text-slate-400 font-sans italic">
        Base = 100 establishes the reference period benchmark.
      </div>
    </div>
  );
}

export function IndexChart({
  data,
  selectedRoute,
  isNational,
  startDate,
  endDate,
  onResetDates,
  onViewRawObservations,
  metricView = 'index',
  routeSummary,
  contributingRoutesCount,
  totalRoutesCount,
}) {
  const rawData = data || [];

  // 1. Check if route has NO index data at all (e.g. HYD-GOI awaiting baseline)
  if (rawData.length === 0) {
    const obsCount = routeSummary?.observation_count ?? 0;
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-xs text-center">
        <div className="max-w-md mx-auto space-y-3">
          <div className="w-10 h-10 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 mx-auto">
            <AlertCircle className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900 m-0">
            Index not yet available
          </h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            {obsCount > 0
              ? `${obsCount} observations are recorded for ${selectedRoute?.replace('-', ' → ')}, but a multi-day baseline has not yet been established.`
              : `No observations or baseline recorded for ${selectedRoute?.replace('-', ' → ')}.`}
          </p>
          <div className="pt-2">
            <button
              onClick={() => onViewRawObservations && onViewRawObservations(selectedRoute)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-50 hover:bg-teal-100 text-teal-850 border border-teal-300 rounded-lg text-xs font-semibold cursor-pointer transition-colors"
            >
              <ArrowDown className="w-3.5 h-3.5" />
              View raw observations
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 2. Filter data by date range
  const filteredData = rawData.filter((d) => {
    if (startDate && d.observation_date < startDate) return false;
    if (endDate && d.observation_date > endDate) return false;
    return true;
  });

  // 3. Check if date filter emptied the data
  if (filteredData.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-xs text-center">
        <div className="max-w-md mx-auto space-y-3">
          <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 mx-auto">
            <AlertCircle className="w-5 h-5" />
          </div>
          <h3 className="text-base font-bold text-slate-900 m-0">
            No indexed observations in this period
          </h3>
          <p className="text-xs text-slate-600">
            No recorded index points exist between <span className="font-mono text-slate-800 font-medium">{startDate}</span> and <span className="font-mono text-slate-800 font-medium">{endDate}</span>.
          </p>
          <div className="pt-2">
            <button
              onClick={onResetDates}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-teal-700 hover:bg-teal-800 text-white rounded-lg text-xs font-medium cursor-pointer transition-colors shadow-xs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset / All Available Dates
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Calculate domains
  const indexValues = filteredData.map((d) => d.index_value ?? d.national_index ?? 100);
  const minIndex = Math.floor(Math.min(...indexValues, 95) - 5);
  const maxIndex = Math.ceil(Math.max(...indexValues, 105) + 5);

  const fareValues = filteredData.map((d) => d.avg_fare ?? d.national_avg_fare ?? 0).filter((v) => v > 0);
  const minFare = fareValues.length ? Math.floor(Math.min(...fareValues) * 0.9) : 0;
  const maxFare = fareValues.length ? Math.ceil(Math.max(...fareValues) * 1.1) : 25000;

  // Active period display string
  const firstDate = filteredData[0]?.observation_date;
  const lastDate = filteredData[filteredData.length - 1]?.observation_date;
  const periodLabel = firstDate === lastDate ? firstDate : `${firstDate} to ${lastDate}`;

  // Subtitle note
  const subtitleNote = isNational
    ? `${contributingRoutesCount ?? 1} / ${totalRoutesCount ?? 2} indexed routes currently contributing to composite`
    : `Tracking observed daily average vs baseline (₹${routeSummary?.baseline_fare?.toLocaleString('en-IN') ?? '—'})`;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
      {/* Chart Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3.5 mb-3.5 border-b border-slate-200 gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 m-0">
            <TrendingUp className="w-4 h-4 text-teal-700" />
            {isNational ? 'National Composite Airfare Index' : `${selectedRoute?.replace('-', ' → ')} Airfare Index`}
          </h3>
          <p className="text-xs text-slate-500 m-0 mt-0.5">
            {subtitleNote}
          </p>
        </div>

        {/* Selected Period Badge */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="text-[11px] font-mono text-slate-600 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200">
            Period: <span className="font-semibold text-slate-800">{periodLabel}</span> ({filteredData.length} pts)
          </div>
        </div>
      </div>

      {/* Recharts Canvas */}
      <div className="h-72 sm:h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={filteredData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="lightIndexGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0f766e" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#0f766e" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="lightFareGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0284c7" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />

            <XAxis
              dataKey="observation_date"
              stroke="#94a3b8"
              tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'monospace' }}
              tickLine={{ stroke: '#e2e8f0' }}
            />

            <YAxis
              domain={metricView === 'index' ? [minIndex, maxIndex] : [minFare, maxFare]}
              stroke="#94a3b8"
              tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'monospace' }}
              tickFormatter={(v) => (metricView === 'index' ? `${v}` : `₹${(v / 1000).toFixed(1)}k`)}
              tickLine={{ stroke: '#e2e8f0' }}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Crucial Baseline Line = 100 */}
            {metricView === 'index' && (
              <ReferenceLine
                y={100}
                stroke="#d97706"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: 'BASELINE = 100',
                  position: 'right',
                  fill: '#b45309',
                  fontSize: 10,
                  fontFamily: 'monospace',
                  fontWeight: 'bold',
                }}
              />
            )}

            <Area
              type="monotone"
              dataKey={metricView === 'index' ? (d) => d.index_value ?? d.national_index : (d) => d.avg_fare ?? d.national_avg_fare}
              stroke={metricView === 'index' ? '#0f766e' : '#0284c7'}
              strokeWidth={2}
              fillOpacity={1}
              fill={metricView === 'index' ? 'url(#lightIndexGradient)' : 'url(#lightFareGradient)'}
              dot={{ r: 4, fill: metricView === 'index' ? '#0f766e' : '#0284c7', stroke: '#ffffff', strokeWidth: 2 }}
              activeDot={{ r: 6, fill: metricView === 'index' ? '#0f766e' : '#0284c7', stroke: '#ffffff', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Baseline Footnote */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 font-sans gap-2">
        <div className="flex items-center gap-2">
          <span className="w-3 h-0.5 bg-amber-500 border-b border-amber-500 border-dashed inline-block" />
          <span>Baseline (100.0) = Mean of initial observation period daily route averages</span>
        </div>
        <div className="flex items-center gap-1">
          <Info className="w-3 h-3 text-slate-400" />
          <span>Only routes with a valid index contribute to the national composite</span>
        </div>
      </div>
    </div>
  );
}
