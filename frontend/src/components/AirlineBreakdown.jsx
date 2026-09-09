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
import { Users } from 'lucide-react';
import { formatINR } from '../utils/formatters';

function CustomAirlineTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;

  return (
    <div className="bg-white border border-slate-300 p-3 rounded-xl shadow-md text-xs font-sans text-slate-800 max-w-xs ring-1 ring-black/5">
      <div className="font-semibold text-slate-900 pb-1 mb-1 border-b border-slate-100 flex items-center justify-between">
        <span>Airline</span>
        <span className="font-mono text-teal-850 font-bold">{d.airline}</span>
      </div>
      <div className="space-y-1 font-mono mt-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-slate-500 font-sans">Average Fare:</span>
          <span className="font-bold text-slate-900">{formatINR(d.avg_fare)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-500 font-sans">Price Range:</span>
          <span className="text-slate-600">{formatINR(d.min_fare)} - {formatINR(d.max_fare)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-500 font-sans">Price Spread:</span>
          <span className="text-amber-700 font-semibold">{formatINR(d.spread)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-slate-500 font-sans">Observations:</span>
          <span className="text-slate-600">{d.observation_count} observations ({d.market_share_pct}%)</span>
        </div>
      </div>
    </div>
  );
}

export function AirlineBreakdown({ airlineData, route }) {
  const airlines = airlineData?.airlines || [];

  if (airlines.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs">
        <div className="flex items-center gap-2 pb-3 mb-3 border-b border-slate-200">
          <Users className="w-4 h-4 text-teal-700" />
          <h3 className="text-base font-bold text-slate-900 m-0">Average Fare by Airline</h3>
        </div>
        <div className="p-6 text-center text-slate-500 font-sans text-xs">
          No airline price distribution data available.
        </div>
      </div>
    );
  }

  const routeLabel = route ? route.replace('-', ' → ') : 'Tracked Market';

  return (
    <div className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3.5 border-b border-slate-100 gap-2">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 m-0">
            <Users className="w-4 h-4 text-teal-700" />
            Average Fare by Airline
          </h3>
          <p className="text-xs text-slate-500 m-0 mt-0.5 font-sans">
            Observed fare levels and price dispersion across {routeLabel}.
          </p>
        </div>

        <div className="text-xs font-sans text-slate-600 self-start sm:self-auto bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
          Lowest Avg: <strong className="text-emerald-750 font-bold">{airlineData?.lowest_avg_carrier || '—'}</strong>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
        {/* Horizontal Bar Chart */}
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={airlines} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis
                type="number"
                stroke="#cbd5e1"
                tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'monospace' }}
                tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
              />
              <YAxis
                dataKey="airline"
                type="category"
                stroke="#cbd5e1"
                tick={{ fill: '#1e293b', fontSize: 11, fontFamily: 'sans-serif', fontWeight: 500 }}
                width={85}
              />
              <Tooltip content={<CustomAirlineTooltip />} />
              <Bar dataKey="avg_fare" radius={[0, 4, 4, 0]}>
                {airlines.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.airline === airlineData?.lowest_avg_carrier ? '#0f766e' : '#64748b'}
                    opacity={0.9}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Breakdown Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left font-sans">
                <th className="pb-2 font-medium">Airline</th>
                <th className="pb-2 font-medium text-right">Avg Fare</th>
                <th className="pb-2 font-medium text-right">Spread</th>
                <th className="pb-2 font-medium text-right">Observations</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {airlines.map((a) => (
                <tr key={a.airline} className="hover:bg-slate-50/50">
                  <td className="py-2 text-slate-900 font-sans font-medium flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-700" />
                    {a.airline}
                  </td>
                  <td className="py-2 text-right font-bold text-slate-900">
                    {formatINR(a.avg_fare)}
                  </td>
                  <td className="py-2 text-right text-slate-600">
                    {formatINR(a.spread)}
                  </td>
                  <td className="py-2 text-right text-slate-500">
                    {a.observation_count} <span className="text-[10px] text-slate-400 font-sans">({a.market_share_pct}%)</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
