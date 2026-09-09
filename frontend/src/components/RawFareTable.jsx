import React, { useState, useMemo } from 'react';
import { Table, Search, Filter } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { formatINR, formatDisplayDate } from '../utils/formatters';

export function RawFareTable({ fares, selectedRoute, latestTimestamp, tableRef }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sourceFilter, setSourceFilter] = useState('ALL');
  const [airlineFilter, setAirlineFilter] = useState('ALL');
  const [routeFilter, setRouteFilter] = useState('ALL');

  const uniqueAirlines = useMemo(() => {
    const set = new Set();
    (fares || []).forEach((f) => {
      if (f.airline) set.add(f.airline);
    });
    return Array.from(set).sort();
  }, [fares]);

  const uniqueRoutes = useMemo(() => {
    const set = new Set();
    (fares || []).forEach((f) => {
      if (f.route) set.add(f.route);
    });
    return Array.from(set).sort();
  }, [fares]);

  const uniqueSources = useMemo(() => {
    const set = new Set();
    (fares || []).forEach((f) => {
      const src = f.provenance || f.source;
      if (src) set.add(src);
    });
    return Array.from(set).sort();
  }, [fares]);

  const filteredFares = useMemo(() => {
    return (fares || []).filter((fare) => {
      // Search
      const searchStr = `${fare.route} ${fare.airline} ${fare.departure_time} ${fare.arrival_time} ${fare.travel_date} ${fare.observation_date || ''}`.toLowerCase();
      if (searchTerm && !searchStr.includes(searchTerm.toLowerCase())) {
        return false;
      }

      // Route filter (if not ALL)
      if (routeFilter !== 'ALL' && fare.route !== routeFilter) {
        return false;
      }

      // Airline filter
      if (airlineFilter !== 'ALL' && fare.airline !== airlineFilter) {
        return false;
      }

      // Source filter
      if (sourceFilter !== 'ALL') {
        const src = fare.provenance || fare.source;
        if (src !== sourceFilter) return false;
      }

      return true;
    });
  }, [fares, searchTerm, routeFilter, airlineFilter, sourceFilter]);

  const routeLabel = selectedRoute ? selectedRoute.replace('-', ' → ') : 'All Tracked Routes';

  return (
    <div ref={tableRef} id="raw-observations-table" className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-xs scroll-mt-6">
      {/* Header and Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-4 mb-4 border-b border-slate-100 gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2 m-0">
            <Table className="w-4 h-4 text-teal-700" />
            Underlying Fare Observations
          </h3>
          <p className="text-xs text-slate-500 m-0 mt-0.5 font-sans">
            Individual fare observations recorded for {routeLabel}
            {latestTimestamp && ` (Latest Collection: ${latestTimestamp})`}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search observations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-white border border-slate-300 rounded-xl pl-8 pr-3 py-1.5 text-slate-800 placeholder-slate-400 focus:outline-none focus:border-teal-700 text-xs w-44 sm:w-48 shadow-2xs"
            />
          </div>

          {/* Route Filter (when multiple routes available) */}
          {uniqueRoutes.length > 1 && (
            <select
              value={routeFilter}
              onChange={(e) => setRouteFilter(e.target.value)}
              className="bg-white border border-slate-300 rounded-xl px-2.5 py-1.5 text-slate-700 focus:outline-none focus:border-teal-700 cursor-pointer text-xs font-mono shadow-2xs"
            >
              <option value="ALL">All City-Pairs</option>
              {uniqueRoutes.map((r) => (
                <option key={r} value={r}>
                  {r.replace('-', ' → ')}
                </option>
              ))}
            </select>
          )}

          {/* Airline Filter */}
          <select
            value={airlineFilter}
            onChange={(e) => setAirlineFilter(e.target.value)}
            className="bg-white border border-slate-300 rounded-xl px-2.5 py-1.5 text-slate-700 focus:outline-none focus:border-teal-700 cursor-pointer text-xs shadow-2xs"
          >
            <option value="ALL">All Airlines</option>
            {uniqueAirlines.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>

          {/* Source Filter */}
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="bg-white border border-slate-300 rounded-xl px-2.5 py-1.5 text-slate-700 focus:outline-none focus:border-teal-700 cursor-pointer text-xs shadow-2xs"
          >
            <option value="ALL">All Sources</option>
            {uniqueSources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          <span className="text-[11px] font-mono text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
            {filteredFares.length} of {fares.length}
          </span>
        </div>
      </div>

      {/* Observation Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-sans text-left">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 bg-slate-50/50">
              <th className="py-2.5 px-3 font-semibold">City-Pair</th>
              <th className="py-2.5 px-3 font-semibold">Airline</th>
              <th className="py-2.5 px-3 font-semibold">Price</th>
              <th className="py-2.5 px-3 font-semibold">Observation Date</th>
              <th className="py-2.5 px-3 font-semibold">Travel Date</th>
              <th className="py-2.5 px-3 font-semibold">Timing</th>
              <th className="py-2.5 px-3 font-semibold">Stops</th>
              <th className="py-2.5 px-3 font-semibold">Seats</th>
              <th className="py-2.5 px-3 font-semibold">Provenance</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono">
            {filteredFares.slice(0, 100).map((f, i) => {
              const obsDate = f.search_timestamp ? f.search_timestamp.split('T')[0] : (f.observation_date || '—');
              const travDate = f.travel_date || '—';

              return (
                <tr key={i} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-2 px-3 font-bold text-slate-900">
                    {f.route ? f.route.replace('-', ' → ') : `${f.origin} → ${f.destination}`}
                  </td>
                  <td className="py-2 px-3 font-sans font-medium text-slate-800">
                    {f.airline}
                  </td>
                  <td className="py-2 px-3 font-bold text-teal-850 text-sm">
                    {formatINR(f.price_inr)}
                  </td>
                  <td className="py-2 px-3 text-slate-600">
                    {obsDate}
                  </td>
                  <td className="py-2 px-3 text-slate-600">
                    {travDate}
                  </td>
                  <td className="py-2 px-3 text-slate-500 text-[11px]">
                    {f.departure_time || '—'} - {f.arrival_time || '—'}
                  </td>
                  <td className="py-2 px-3 text-slate-500">
                    {f.stops || 'Direct'}
                  </td>
                  <td className="py-2 px-3 text-slate-500">
                    {f.seats_left ? `${f.seats_left} left` : '—'}
                  </td>
                  <td className="py-2 px-3">
                    <StatusBadge status={f.provenance || f.source} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filteredFares.length === 0 && (
          <div className="text-center py-8 text-slate-400 font-sans text-xs">
            No fare observations match the selected search and filter criteria.
          </div>
        )}

        {filteredFares.length > 100 && (
          <div className="p-3 text-center text-xs text-slate-500 bg-slate-50/50 border-t border-slate-100 font-sans">
            Showing first 100 of {filteredFares.length} matching observations.
          </div>
        )}
      </div>

      {/* Footer Note */}
      <div className="mt-3 pt-2.5 border-t border-slate-100 text-[11px] text-slate-400 font-sans flex flex-col sm:flex-row sm:items-center justify-between gap-1">
        <span>Source and collection metadata recorded at ingestion.</span>
        <span>Observation Date: collection date | Travel Date: departure date</span>
      </div>
    </div>
  );
}
