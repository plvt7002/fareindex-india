import React from 'react';
import { CheckCircle2, Clock } from 'lucide-react';
import { formatINR } from '../utils/formatters';
import { ROUTE_CATALOG, COMING_SOON_ROUTES } from '../config/routes';

export function TrackedRoutesSection({
  summaries,
  selectedRoute,
  onSelectRoute,
}) {
  const activeRoutes = summaries || [];


  return (
    <section id="routes" className="space-y-4 pt-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-950 m-0">
            Tracked routes
          </h3>
          <p className="text-xs text-slate-500 font-sans mt-0.5 m-0">
            Select a city-pair to explore its fare distribution, advance booking curve, and verified observations.
          </p>
        </div>
        <div className="text-xs font-mono text-slate-600 font-semibold self-start sm:self-auto bg-slate-100 px-3 py-1 rounded-lg border border-slate-200/80">
          {activeRoutes.length} active routes tracked
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Tracked Routes */}
        {activeRoutes.map((s) => {
          const isSelected = selectedRoute === s.route;
          const cityInfo = CITY_NAMES[s.route] || {
            origin: s.route.split('-')[0],
            dest: s.route.split('-')[1],
            airportOrigin: s.route.split('-')[0],
            airportDest: s.route.split('-')[1],
          };

          const typical7d = s.lead_time_7d_typical_fare ?? s.current_typical_fare ?? s.latest_avg_fare;
          const average7d = s.lead_time_7d_average_fare ?? s.current_average_fare ?? s.latest_avg_fare;

          return (
            <div
              key={s.route}
              onClick={() => onSelectRoute(s.route)}
              className={`bg-white border rounded-3xl p-5 shadow-xs transition-all cursor-pointer relative overflow-hidden flex flex-col justify-between space-y-4 hover:border-teal-500/80 hover:shadow-md ${
                isSelected
                  ? 'border-teal-600 ring-2 ring-teal-500/30 bg-teal-50/10'
                  : 'border-slate-200/90'
              }`}
            >
              {/* Active Selection Badge */}
              {isSelected && (
                <div className="absolute top-3.5 right-3.5 flex items-center gap-1 text-[10px] font-bold text-teal-850 bg-teal-100/90 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-3 h-3 text-teal-700" />
                  <span>Active View</span>
                </div>
              )}

              {/* Route Header */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-base font-extrabold text-slate-950 font-mono tracking-tight">
                    {cityInfo.airportOrigin} → {cityInfo.airportDest}
                  </span>
                </div>
                <div className="text-xs text-slate-500 font-sans font-medium">
                  {cityInfo.origin} to {cityInfo.dest}
                </div>
              </div>

              {/* Typical & Average 7D Fare */}
              <div className="space-y-1.5">
                <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 block font-sans">
                  Typical Fare (Near-term 1–10D)
                </span>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-2xl font-extrabold text-slate-950 font-mono">
                    {formatINR(typical7d)}
                  </span>
                  <span className="text-xs font-mono text-slate-500">
                    avg {formatINR(average7d)}
                  </span>
                </div>
              </div>

              {/* Card Footer: Metadata */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>{s.observation_count} flights</span>
                <span className="text-teal-800 font-semibold">1 obs day</span>
              </div>
            </div>
          );
        })}

        {/* Planned / Coming Soon Routes */}
        {COMING_SOON_ROUTES.map((p) => (
          <div
            key={p.code}
            className="bg-slate-50/70 border border-dashed border-slate-300/80 rounded-3xl p-5 shadow-2xs flex flex-col justify-between space-y-4"
          >
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-base font-extrabold text-slate-500 font-mono tracking-tight">
                  {p.originCode} → {p.destCode}
                </span>
                <span className="inline-flex items-center gap-1 text-[9px] font-mono font-bold uppercase tracking-wider text-slate-500 bg-slate-200/70 px-2 py-0.5 rounded">
                  COMING SOON
                </span>
              </div>
              <div className="text-xs text-slate-400 font-sans font-medium">
                {p.originName} to {p.destName}
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 block font-sans">
                Status
              </span>
              <div className="text-xs font-semibold text-slate-500 italic font-sans flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>Scheduled for observation</span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200/70 text-[11px] text-slate-400 font-sans">
              {p.description}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
