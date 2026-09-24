import React from 'react';
import { Plane, RefreshCw, BookOpen } from 'lucide-react';
import { formatDisplayDate } from '../utils/formatters';

const NAV_ITEMS = [
  { id: 'second-opinion', label: '⚡ Second Opinion', isSpecial: true },
  { id: 'overview', label: 'Overview' },
  { id: 'movement', label: 'Fare Movement' },
  { id: 'distribution', label: 'Distribution' },
  { id: 'booking', label: 'Booking Behaviour' },
  { id: 'observed-fares', label: 'Observed Fares' },
];

export function Header({
  lastObservationDate,
  onRefresh,
  isRefreshing,
  onOpenMethodology,
  activeSection = 'overview',
  onNavigate,
}) {
  const handleNavClick = (e, id) => {
    e.preventDefault();
    if (onNavigate) {
      onNavigate(id);
    } else {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        window.history.replaceState(null, '', `#${id}`);
      }
    }
  };

  const formattedSnapshotDate = formatDisplayDate(lastObservationDate, 'Latest');

  return (
    <header className="border-b border-slate-200/90 bg-white/95 backdrop-blur-md sticky top-0 z-40 px-4 sm:px-8 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col gap-2.5">
        {/* Top Row: Brand + Controls */}
        <div className="flex items-center justify-between gap-4">
          {/* Brand Logo & Tagline */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center text-white shadow-xs">
              <Plane className="w-5 h-5 -rotate-45" />
            </div>
            <div>
              <a
                href="#overview"
                onClick={(e) => handleNavClick(e, 'overview')}
                className="text-2xl sm:text-[32px] font-black tracking-tight text-slate-950 hover:text-teal-900 transition-colors block leading-tight font-sans"
              >
                FareIndex <span className="font-extrabold text-teal-800">India</span>
              </a>
              <p className="text-xs text-slate-500 hidden sm:block font-medium tracking-normal mt-0.5">
                Understand what an airfare means
              </p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-1.5 text-xs font-semibold text-slate-600">
            {NAV_ITEMS.map((item) => {
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={(e) => handleNavClick(e, item.id)}
                  className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer font-medium ${isActive
                      ? 'bg-slate-100 text-slate-950 font-bold border border-slate-200 shadow-2xs'
                      : 'hover:text-slate-950 hover:bg-slate-50 text-slate-600'
                    }`}
                >
                  {item.label}
                </button>
              );
            })}
            <button
              onClick={onOpenMethodology}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-teal-850 hover:bg-teal-50 transition-colors cursor-pointer font-semibold ml-1"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>How it works</span>
            </button>
          </nav>

          {/* Right Side: Observation Date Indicator & Refresh */}
          <div className="flex items-center gap-2.5 text-xs">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-100/90 border border-slate-200/90 text-[11px] font-sans text-slate-700">
              <span className="w-2 h-2 rounded-full bg-teal-600" />
              <span className="font-medium text-slate-600">Market data through ·</span>
              <span className="font-mono font-semibold text-slate-900">{formattedSnapshotDate}</span>
            </div>

            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 shadow-2xs transition-all disabled:opacity-50 cursor-pointer font-semibold text-xs active:scale-95"
              title="Refresh market analytics dashboard"
              aria-label="Refresh market analytics"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-teal-700' : 'text-slate-500'}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Mobile / Tablet Horizontal Scroll Nav Strip */}
        <div className="lg:hidden flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 -mx-2 px-2 scrollbar-none text-xs font-medium text-slate-600 border-t border-slate-100">
          {NAV_ITEMS.map((item) => {
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={(e) => handleNavClick(e, item.id)}
                className={`px-2.5 py-1 rounded-lg shrink-0 transition-all text-[11px] ${isActive
                    ? 'bg-slate-900 text-white font-bold'
                    : 'bg-slate-100 text-slate-700'
                  }`}
              >
                {item.label}
              </button>
            );
          })}
          <button
            onClick={onOpenMethodology}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg shrink-0 text-teal-900 bg-teal-50 border border-teal-200 text-[11px] font-semibold"
          >
            <BookOpen className="w-3 h-3" />
            <span>How it works</span>
          </button>
        </div>
      </div>
    </header>
  );
}
