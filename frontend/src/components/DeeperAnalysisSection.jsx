import React, { useState } from 'react';
import { AirlineBreakdown } from './AirlineBreakdown';
import { BookingCurveChart } from './BookingCurveChart';
import { RawFareTable } from './RawFareTable';
import { Users, Calendar, Table, BarChart3 } from 'lucide-react';

export function DeeperAnalysisSection({
  airlineData,
  bookingCurveData,
  latestFaresData,
  selectedRoute,
  routes,
  rawTableRef,
}) {
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'airlines' | 'booking' | 'raw'

  const targetRouteDisplay = selectedRoute ? selectedRoute.replace('-', ' → ') : 'National Market';

  return (
    <section id="analysis" className="space-y-6 pt-6 border-t border-slate-200">
      {/* Section Title & Exploration Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-teal-850 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded">
              Deep Dive
            </span>
            <h3 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-950 m-0">
              Deeper analysis
            </h3>
          </div>
          <p className="text-xs text-slate-500 font-sans mt-1 m-0">
            Granular airline dispersion, advance purchase lead-time curves, and underlying observation records for {targetRouteDisplay}.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200 text-xs font-semibold self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
              activeTab === 'all'
                ? 'bg-white text-slate-950 shadow-2xs ring-1 ring-slate-300/80 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('airlines')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
              activeTab === 'airlines'
                ? 'bg-white text-slate-950 shadow-2xs ring-1 ring-slate-300/80 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Airline Mix
          </button>
          <button
            onClick={() => setActiveTab('booking')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
              activeTab === 'booking'
                ? 'bg-white text-slate-950 shadow-2xs ring-1 ring-slate-300/80 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Booking Curve
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
              activeTab === 'raw'
                ? 'bg-white text-slate-950 shadow-2xs ring-1 ring-slate-300/80 font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Raw Data
          </button>
        </div>
      </div>

      {/* Analytics Panels */}
      {(activeTab === 'all' || activeTab === 'airlines' || activeTab === 'booking') && (
        <div className={`grid grid-cols-1 ${activeTab === 'all' ? 'lg:grid-cols-2' : 'grid-cols-1'} gap-6`}>
          {(activeTab === 'all' || activeTab === 'airlines') && (
            <AirlineBreakdown airlineData={airlineData} route={selectedRoute} />
          )}

          {(activeTab === 'all' || activeTab === 'booking') && (
            <BookingCurveChart bookingData={bookingCurveData} route={selectedRoute} />
          )}
        </div>
      )}

      {/* Raw Flight Observations Table */}
      {(activeTab === 'all' || activeTab === 'raw') && (
        <div className="pt-2">
          <RawFareTable
            fares={latestFaresData?.fares || []}
            selectedRoute={selectedRoute || (routes.length > 0 ? routes[0] : null)}
            latestTimestamp={latestFaresData?.latest_search_timestamp}
            tableRef={rawTableRef}
          />
        </div>
      )}
    </section>
  );
}
