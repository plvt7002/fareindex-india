import React, { useState } from 'react';
import { CheckCircle2, Clock, Sparkles, X, Info } from 'lucide-react';
import { TRACKED_ROUTES, COMING_SOON_ROUTES, ROUTE_CATALOG } from '../config/routes';

export function RouteCoverageSection({
  selectedRoute,
  onSelectRoute,
  routeSummaries = [],
}) {
  const [comingSoonNotice, setComingSoonNotice] = useState(null);

  const handleComingSoonClick = (routeObj) => {
    setComingSoonNotice({
      route: routeObj.code,
      title: `${routeObj.originName} (${routeObj.originCode}) → ${routeObj.destName} (${routeObj.destCode})`,
      message: `FareIndex India is expanding coverage. Scrapers for ${routeObj.originName} to ${routeObj.destName} are scheduled for automated daily observations. Verified index metrics will be activated once sufficient observation history is accumulated.`,
    });
  };

  return (
    <div className="space-y-3">
      {/* Route Expansion Notification Modal/Banner if Coming Soon clicked */}
      {comingSoonNotice && (
        <div className="p-3.5 rounded-2xl bg-teal-50/90 border border-teal-200/80 text-teal-950 text-xs shadow-xs flex items-start justify-between gap-3 animate-fadeIn">
          <div className="flex items-start gap-2.5">
            <div className="p-1 rounded-lg bg-teal-600 text-white shrink-0 mt-0.5">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <div className="space-y-0.5">
              <div className="font-bold flex items-center gap-2">
                <span>{comingSoonNotice.title}</span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.2 rounded bg-teal-200/80 text-teal-900 font-semibold">
                  Coverage Coming Soon
                </span>
              </div>
              <p className="text-teal-800 text-[11px] leading-relaxed m-0 font-sans">
                {comingSoonNotice.message}
              </p>
            </div>
          </div>
          <button
            onClick={() => setComingSoonNotice(null)}
            className="p-1 rounded-lg hover:bg-teal-200/60 text-teal-700 transition-colors cursor-pointer shrink-0"
            title="Dismiss notice"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Route Coverage Grid */}
      <div className="space-y-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Tracked Routes */}
          {TRACKED_ROUTES.map((routeObj) => {
            const isSelected = selectedRoute === routeObj.code;
            const summary = routeSummaries.find((s) => s.route === routeObj.code);
            const isGoi = routeObj.code === 'HYD-GOI';

            return (
              <div
                key={routeObj.code}
                onClick={() => onSelectRoute(routeObj.code)}
                className={`group relative rounded-2xl p-3.5 transition-all cursor-pointer border flex flex-col justify-between gap-2.5 ${
                  isSelected
                    ? 'bg-teal-900/5 border-teal-600 ring-2 ring-teal-500/20 shadow-xs'
                    : 'bg-white border-slate-200/90 hover:border-teal-400 hover:shadow-xs'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-extrabold font-mono text-slate-950 tracking-tight">
                        {routeObj.originCode} → {routeObj.destCode}
                      </span>
                      {isSelected && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-teal-700 shrink-0" />
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500 font-medium font-sans">
                      {routeObj.originName} to {routeObj.destName}
                    </div>
                  </div>

                  <span
                    className={`text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full cursor-help ${
                      isGoi
                        ? 'bg-teal-100 text-teal-900 border border-teal-200'
                        : 'bg-teal-100 text-teal-900 border border-teal-200'
                    }`}
                    title="Active tracked route with verified observations."
                  >
                    Tracked
                  </span>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500 font-sans">
                  <span className="font-medium">
                    {summary ? `${summary.observation_count} canonical observations · all horizons` : 'Active tracking'}
                  </span>
                  <span className="text-teal-800 font-semibold font-mono">
                    {isSelected ? 'Active View' : 'Select route →'}
                  </span>
                </div>
              </div>
            );
          })}

          {/* Coming Soon Routes */}
          {COMING_SOON_ROUTES.map((routeObj) => (
            <div
              key={routeObj.code}
              onClick={() => handleComingSoonClick(routeObj)}
              className="group relative rounded-2xl p-3.5 border border-dashed border-slate-300 bg-slate-50/70 hover:bg-slate-100/80 hover:border-slate-400 transition-all cursor-pointer flex flex-col justify-between gap-2.5"
              title="Click for coverage expansion details"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-bold font-mono text-slate-600 tracking-tight">
                      {routeObj.originCode} → {routeObj.destCode}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-medium font-sans">
                    {routeObj.originName} to {routeObj.destName}
                  </div>
                </div>

                <span className="text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-200/80 text-slate-600 border border-slate-300/80 flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5 text-slate-500" />
                  <span>Coming soon</span>
                </span>
              </div>

              <div className="pt-2 border-t border-slate-200/70 flex items-center justify-between text-[10px] text-slate-400 font-sans">
                <span className="truncate max-w-[170px]">Scheduled for observation</span>
                <span className="text-slate-500 font-semibold group-hover:text-teal-800 transition-colors">
                  Details →
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
