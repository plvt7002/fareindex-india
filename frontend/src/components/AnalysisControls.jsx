import React from 'react';
import { Route, Calendar, SlidersHorizontal, RotateCcw } from 'lucide-react';

export function AnalysisControls({
  routes,
  selectedRoute,
  onSelectRoute,
  routeSummaries,
  availableDates,
  startDate,
  endDate,
  onDateChange,
  onResetDates,
  metricView,
  onMetricChange,
}) {
  const isCustomDateRange = Boolean(startDate || endDate);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        {/* Left: Route Selector Pills (Single Source of Truth) */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5 shrink-0">
            <Route className="w-3.5 h-3.5 text-teal-700" />
            Route Scope:
          </span>

          <div className="flex flex-wrap items-center gap-1.5 bg-slate-100/80 p-1 rounded-lg border border-slate-200/80">
            {/* National Composite */}
            <button
              onClick={() => onSelectRoute(null)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all cursor-pointer ${
                selectedRoute === null
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
              }`}
            >
              National Composite
            </button>

            {/* Tracked City Pairs */}
            {routes.map((r) => {
              const summary = routeSummaries.find((s) => s.route === r);
              const hasIndex = summary?.latest_index !== null && summary?.latest_index !== undefined;
              const isSelected = selectedRoute === r;

              return (
                <button
                  key={r}
                  onClick={() => onSelectRoute(r)}
                  className={`px-3 py-1 text-xs font-medium font-mono rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
                    isSelected
                      ? 'bg-teal-700 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                  }`}
                >
                  <span>{r.replace('-', ' → ')}</span>
                  {!hasIndex && (
                    <span className={`text-[10px] px-1 py-0.2 rounded font-sans ${
                      isSelected ? 'bg-teal-800 text-teal-100' : 'bg-slate-200 text-slate-500'
                    }`}>
                      No Index
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Date Range Filter & Metric Selector */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Observation Date Filter Controls */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg text-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <span className="text-slate-500 text-[11px] font-medium mr-1 hidden sm:inline">Obs Date:</span>
            
            {/* Start Date */}
            <select
              value={startDate || ''}
              onChange={(e) => onDateChange(e.target.value || null, endDate)}
              className="bg-white border border-slate-300 rounded px-1.5 py-0.5 text-xs text-slate-700 font-mono focus:outline-none focus:border-teal-700 cursor-pointer"
              title="Filter starting observation date"
            >
              <option value="">Start (All)</option>
              {availableDates.map((d) => (
                <option key={`start-${d}`} value={d}>
                  {d}
                </option>
              ))}
            </select>

            <span className="text-slate-400 font-mono text-[11px]">→</span>

            {/* End Date */}
            <select
              value={endDate || ''}
              onChange={(e) => onDateChange(startDate, e.target.value || null)}
              className="bg-white border border-slate-300 rounded px-1.5 py-0.5 text-xs text-slate-700 font-mono focus:outline-none focus:border-teal-700 cursor-pointer"
              title="Filter ending observation date"
            >
              <option value="">End (Latest)</option>
              {availableDates.map((d) => (
                <option key={`end-${d}`} value={d}>
                  {d}
                </option>
              ))}
            </select>

            {/* Reset / All Dates button */}
            {isCustomDateRange && (
              <button
                onClick={onResetDates}
                className="ml-1 px-1.5 py-0.5 text-[11px] text-teal-700 hover:text-teal-900 hover:bg-teal-50 rounded flex items-center gap-0.5 cursor-pointer font-medium"
                title="Reset to all available observation dates"
              >
                <RotateCcw className="w-3 h-3" />
                Reset
              </button>
            )}
          </div>

          {/* Metric Selector (Index vs Average Fare) */}
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-medium">
            <button
              onClick={() => onMetricChange('index')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                metricView === 'index'
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Index (Base 100)
            </button>
            <button
              onClick={() => onMetricChange('fare')}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                metricView === 'fare'
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Average Fare (₹)
            </button>
          </div>

        </div>

      </div>

      {/* Scope Caption */}
      <div className="mt-2.5 pt-2 border-t border-slate-100 text-[11px] text-slate-400 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
        <span>
          Scope: Date range &amp; metric filters apply to the analytical charts below. The top hero reflects the latest market snapshot.
        </span>
        {isCustomDateRange && (
          <span className="font-mono text-teal-800 font-medium bg-teal-50 px-2 py-0.5 rounded border border-teal-200 shrink-0">
            Active Filter: {startDate || 'Earliest'} to {endDate || 'Latest'}
          </span>
        )}
      </div>
    </div>
  );
}
