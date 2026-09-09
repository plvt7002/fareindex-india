import React from 'react';
import { Route as RouteIcon, ArrowRight, Table, AlertCircle } from 'lucide-react';

export function RouteSummaryTable({ summaries, selectedRoute, onSelectRoute, onViewRouteObservations }) {
  if (!summaries || summaries.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-4 border-b border-slate-200 gap-2">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 m-0">
            <RouteIcon className="w-4 h-4 text-teal-700" />
            Tracked Domestic Routes Summary
          </h3>
          <p className="text-xs text-slate-500 m-0 mt-0.5">
            Key market metrics and index status across tracked domestic city-pairs
          </p>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          Only indexed routes contribute to National Composite
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {summaries.map((s) => {
          const isSelected = selectedRoute === s.route;
          const indexVal = s.latest_index;
          const hasIndex = indexVal !== undefined && indexVal !== null;
          const isElevated = hasIndex && indexVal >= 100.0;
          const changePct = s.index_change_pct;

          return (
            <div
              key={s.route}
              className={`p-4 rounded-lg border transition-all ${
                isSelected
                  ? 'bg-teal-50/30 border-teal-600 shadow-xs'
                  : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
              }`}
            >
              {/* Header Row */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-base font-bold font-mono text-slate-900">
                    {s.route.replace('-', ' → ')}
                  </span>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                    {s.observation_count} obs ({s.observation_days_count} days)
                  </span>
                </div>

                {hasIndex ? (
                  <span
                    className={`font-mono font-bold text-xs px-2.5 py-1 rounded-md border ${
                      isElevated
                        ? 'text-rose-700 bg-rose-50 border-rose-200'
                        : 'text-emerald-700 bg-emerald-50 border-emerald-200'
                    }`}
                  >
                    Index: {indexVal.toFixed(2)}
                  </span>
                ) : (
                  <span className="text-xs text-amber-800 bg-amber-50 border border-amber-200 font-mono px-2 py-0.5 rounded flex items-center gap-1 font-medium">
                    <AlertCircle className="w-3 h-3 text-amber-600" />
                    Index unavailable
                  </span>
                )}
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-2 text-xs font-mono pt-3 border-t border-slate-100">
                <div>
                  <span className="text-[10px] text-slate-500 block font-sans">Latest Avg</span>
                  <span className="font-bold text-slate-900">
                    {s.latest_avg_fare ? `₹${s.latest_avg_fare.toLocaleString('en-IN')}` : '—'}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-slate-500 block font-sans">Baseline Fare</span>
                  <span className="text-slate-700">
                    {s.baseline_fare ? `₹${s.baseline_fare.toLocaleString('en-IN')}` : 'Awaiting baseline'}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-slate-500 block font-sans">Index Movement</span>
                  <span
                    className={`font-semibold ${
                      changePct > 0 ? 'text-rose-700' : changePct < 0 ? 'text-emerald-700' : 'text-slate-400'
                    }`}
                  >
                    {changePct !== null && changePct !== undefined ? `${changePct > 0 ? '+' : ''}${changePct.toFixed(1)}%` : '—'}
                  </span>
                </div>
              </div>

              {/* Sub-explanation for unindexed route */}
              {!hasIndex && (
                <div className="mt-2.5 p-2 bg-slate-50 rounded border border-slate-100 text-[11px] text-slate-600 font-sans">
                  <strong>Status:</strong> Awaiting multi-day baseline. Multiple observation dates are required to calculate a statistically robust baseline.
                </div>
              )}

              {/* Actions Row */}
              <div className="mt-3 pt-2.5 text-[11px] flex items-center justify-between border-t border-slate-100 font-sans">
                <span className="text-slate-500">
                  {s.airlines?.length > 0 ? `Carriers: ${s.airlines.join(', ')}` : 'No carriers recorded'}
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onSelectRoute(s.route)}
                    className="text-teal-700 hover:text-teal-900 font-medium flex items-center gap-1 cursor-pointer"
                  >
                    Analyze Chart <ArrowRight className="w-3 h-3" />
                  </button>

                  <button
                    onClick={() => onViewRouteObservations && onViewRouteObservations(s.route)}
                    className="text-slate-600 hover:text-slate-900 font-medium flex items-center gap-1 border-l border-slate-200 pl-2 cursor-pointer"
                  >
                    <Table className="w-3 h-3 text-slate-400" />
                    View observations
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
