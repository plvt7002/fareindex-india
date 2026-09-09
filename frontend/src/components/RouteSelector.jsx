import React from 'react';
import { Globe, MapPin } from 'lucide-react';

export function RouteSelector({ routes, selectedRoute, onSelectRoute, routeSummaries }) {
  const summariesByRoute = (routeSummaries || []).reduce((acc, curr) => {
    acc[curr.route] = curr;
    return acc;
  }, {});

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-3">
      <span className="text-xs font-semibold text-slate-500 uppercase mr-1 flex items-center gap-1.5">
        <MapPin className="w-3.5 h-3.5 text-teal-700" />
        Market View:
      </span>

      {/* National Composite Tab */}
      <button
        onClick={() => onSelectRoute(null)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer border ${
          selectedRoute === null
            ? 'bg-teal-800 text-white border-teal-800 shadow-xs'
            : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
        }`}
      >
        <Globe className="w-3.5 h-3.5" />
        <span>National Composite</span>
      </button>

      {/* Individual Routes */}
      {routes.map((route) => {
        const summary = summariesByRoute[route];
        const isSelected = selectedRoute === route;
        const indexVal = summary?.latest_index;
        const hasIndex = indexVal !== undefined && indexVal !== null;
        const isElevated = hasIndex && indexVal >= 100.0;

        return (
          <button
            key={route}
            onClick={() => onSelectRoute(route)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer border ${
              isSelected
                ? 'bg-teal-800 text-white border-teal-800 shadow-xs'
                : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
            }`}
          >
            <span>{route.replace('-', ' → ')}</span>
            {hasIndex ? (
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-semibold ${
                  isSelected
                    ? 'bg-teal-900 text-teal-100'
                    : isElevated
                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                    : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}
              >
                {indexVal.toFixed(1)}
              </span>
            ) : (
              <span className={`text-[10px] ${isSelected ? 'text-teal-200' : 'text-slate-400'}`}>
                (Raw data)
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
