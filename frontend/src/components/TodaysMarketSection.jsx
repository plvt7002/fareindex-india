import React, { useState, useMemo, useEffect } from 'react';
import { ShieldCheck, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, ArrowUpDown, Filter, Loader2, Sparkles, ListFilter, ArrowRight } from 'lucide-react';
import { formatINR, formatDisplayDate, formatStops, mapObservedFare, getRepresentativeFares, calculatePercentiles } from '../utils/formatters';
import { api } from '../api/client';

const PAGE_SIZE = 20;

export function TodaysMarketSection({ latestFaresData, selectedRoute, typicalFare, selectedBucket = '7D' }) {
  const [viewMode, setViewMode] = useState('REPRESENTATIVE'); // 'REPRESENTATIVE' | 'ALL'

  const [airlineFilter, setAirlineFilter] = useState('ALL');
  const [windowFilter, setWindowFilter] = useState('ALL');
  const [stopsFilter, setStopsFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('CLOSEST_TYPICAL'); // CLOSEST_TYPICAL [Default] | PRICE_ASC | PRICE_DESC | TIME_ASC | TIME_DESC
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedRowId, setExpandedRowId] = useState(null);

  // Reset page and filters when route changes
  useEffect(() => {
    setCurrentPage(1);
    setAirlineFilter('ALL');
    setWindowFilter('ALL');
    setStopsFilter('ALL');
    setExpandedRowId(null);
    setViewMode('REPRESENTATIVE');
    setSortBy('CLOSEST_TYPICAL');
  }, [selectedRoute]);

  const rawRows = latestFaresData?.fares || [];
  const timestamp = latestFaresData?.latest_search_timestamp;
  const formattedCollectionDate = formatDisplayDate(timestamp, 'Latest verified observation');
  const formattedCollectionTime = formatDisplayDate(timestamp, 'Latest Collection');

  // Explicit mapping of each individual row to enforce price_inr binding
  const mappedFares = useMemo(() => {
    return rawRows
      .map(mapObservedFare)
      .filter((f) => f && f.price_inr > 0);
  }, [rawRows]);

  // Dynamic airline counts from active dataset
  const airlineStats = useMemo(() => {
    const counts = {};
    mappedFares.forEach((f) => {
      const air = f.airline || 'Unknown';
      counts[air] = (counts[air] || 0) + 1;
    });
    return counts;
  }, [mappedFares]);

  const uniqueAirlines = useMemo(() => {
    return Object.keys(airlineStats).sort();
  }, [airlineStats]);

  // Travel window bucket counts
  const windowStats = useMemo(() => {
    const counts = {};
    mappedFares.forEach((f) => {
      const b = f.leadTimeBucket || 'UNKNOWN';
      counts[b] = (counts[b] || 0) + 1;
    });
    return counts;
  }, [mappedFares]);

  // Reset page when filter or sort changes
  useEffect(() => {
    setCurrentPage(1);
  }, [airlineFilter, windowFilter, stopsFilter, sortBy, viewMode]);

  // Filter application across all mapped observations
  const filteredFares = useMemo(() => {
    return mappedFares.filter((f) => {
      if (airlineFilter !== 'ALL' && f.airline !== airlineFilter) return false;
      if (windowFilter !== 'ALL' && f.leadTimeBucket !== windowFilter) return false;
      if (stopsFilter !== 'ALL') {
        const isNonStop = f.stops === 'Nonstop';
        if (stopsFilter === 'NON_STOP' && !isNonStop) return false;
        if (stopsFilter === 'CONNECTING' && isNonStop) return false;
      }
      return true;
    });
  }, [mappedFares, airlineFilter, windowFilter, stopsFilter]);

  // Dynamic percentiles for current filtered population
  const percentiles = useMemo(() => {
    const prices = filteredFares.map((f) => Number(f.price_inr || 0)).filter((p) => p > 0);
    return calculatePercentiles(prices);
  }, [filteredFares]);

  // Representative fares (top 10 closest to median within P10-P90)
  const representativeFares = useMemo(() => {
    return getRepresentativeFares(filteredFares, 10);
  }, [filteredFares]);

  // Active list to sort and display depending on viewMode
  const activeList = useMemo(() => {
    if (viewMode === 'REPRESENTATIVE') {
      const list = [...representativeFares];
      if (sortBy === 'PRICE_ASC') {
        list.sort((a, b) => (a.price_inr || 0) - (b.price_inr || 0));
        return list;
      }
      if (sortBy === 'TIME_ASC') {
        list.sort((a, b) => String(a.departureTime || '').localeCompare(String(b.departureTime || '')));
        return list;
      }
      if (sortBy === 'TIME_DESC') {
        list.sort((a, b) => String(b.departureTime || '').localeCompare(String(a.departureTime || '')));
        return list;
      }
      return representativeFares;
    }

    // ALL view: sort complete filtered dataset
    const list = [...filteredFares];
    list.sort((a, b) => {
      if (sortBy === 'CLOSEST_TYPICAL') {
        const med = percentiles.median || typicalFare;
        const diffA = Math.abs((a.price_inr || 0) - med);
        const diffB = Math.abs((b.price_inr || 0) - med);
        if (Math.abs(diffA - diffB) > 0.01) return diffA - diffB;
        return (a.price_inr || 0) - (b.price_inr || 0);
      }
      if (sortBy === 'PRICE_ASC') return (a.price_inr || 0) - (b.price_inr || 0);
      if (sortBy === 'PRICE_DESC') return (b.price_inr || 0) - (a.price_inr || 0);
      if (sortBy === 'TIME_ASC') return String(a.departureTime || '').localeCompare(String(b.departureTime || ''));
      if (sortBy === 'TIME_DESC') return String(b.departureTime || '').localeCompare(String(a.departureTime || ''));
      return 0;
    });
    return list;
  }, [viewMode, representativeFares, filteredFares, sortBy, percentiles.median, typicalFare]);

  // Pagination calculation
  const totalCount = activeList.length;
  const isPaginated = viewMode === 'ALL';
  const totalPages = isPaginated ? Math.max(1, Math.ceil(totalCount / PAGE_SIZE)) : 1;
  const validPage = Math.min(currentPage, totalPages);
  const startIndex = isPaginated ? (validPage - 1) * PAGE_SIZE : 0;
  const endIndex = isPaginated ? Math.min(startIndex + PAGE_SIZE, totalCount) : totalCount;
  const displayedFares = activeList.slice(startIndex, endIndex);

  const routeDisplayName = selectedRoute ? selectedRoute.replace('-', ' → ') : 'HYD → DEL';

  const toggleExpand = (id) => {
    setExpandedRowId((prev) => (prev === id ? null : id));
  };

  return (
    <section id="observed-fares" className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-5 shadow-sm">
      {/* Section Header & View Mode Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-xl font-bold text-slate-950 m-0 tracking-tight font-sans">
              {viewMode === 'REPRESENTATIVE'
                ? 'Representative Domestic Fares'
                : 'All Verified Domestic Observations'}
            </h2>
            <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-800 border border-teal-200 font-semibold">
              {viewMode === 'REPRESENTATIVE' && sortBy === 'CLOSEST_TYPICAL'
                ? `${displayedFares.length} representative fares (from ${filteredFares.length} observed)`
                : `${filteredFares.length} verified observations · ${uniqueAirlines.length} airlines`}
            </span>
          </div>
          <p className="text-xs text-slate-500 m-0 mt-1 font-sans">
            {viewMode === 'REPRESENTATIVE'
              ? 'Current domestic fares that best represent the observed market range.'
              : `Complete set of verified domestic one-way observations for ${routeDisplayName}.`}
          </p>
          <div className="text-[11px] font-mono text-slate-400 mt-0.5">
            Observation date: 9 Sep 2026 · Collected {formattedCollectionDate}
          </div>
        </div>

        {/* View Mode Switcher & Dataset Badge */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Mode Selector: Representative vs All */}
          <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200">
            <button
              type="button"
              onClick={() => {
                setViewMode('REPRESENTATIVE');
                setSortBy('CLOSEST_TYPICAL');
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer inline-flex items-center gap-1.5 ${viewMode === 'REPRESENTATIVE'
                  ? 'bg-teal-700 text-white shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Representative</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setViewMode('ALL');
                if (sortBy === 'CLOSEST_TYPICAL') setSortBy('PRICE_ASC');
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer inline-flex items-center gap-1.5 ${viewMode === 'ALL'
                  ? 'bg-teal-700 text-white shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
                }`}
            >
              <ListFilter className="w-3.5 h-3.5" />
              <span>All Observations ({mappedFares.length})</span>
            </button>
          </div>

          {/* Domestic One-Way Indicator Badge */}
          <div className="inline-flex items-center px-3 py-1.5 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-xs font-mono font-semibold">
            <span>Domestic · One-Way</span>
          </div>
        </div>
      </div>

      {/* Customer Explanation Banner */}
      <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <div className="text-slate-600">
          {viewMode === 'REPRESENTATIVE' ? (
            <span>
              Showing fares closest to the typical market level (P10–P90: {formatINR(percentiles.p10)} – {formatINR(percentiles.p90)}). View all to explore every current observation.
            </span>
          ) : (
            <span>
              Some flights can be substantially higher because fares vary by availability, demand, travel date and itinerary.
            </span>
          )}
        </div>
        <div>
          {viewMode === 'REPRESENTATIVE' ? (
            <button
              type="button"
              onClick={() => {
                setViewMode('ALL');
                setSortBy('PRICE_ASC');
              }}
              className="text-teal-700 hover:text-teal-900 font-semibold cursor-pointer inline-flex items-center gap-1 shrink-0 text-xs"
            >
              <span>View all current observations</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                setViewMode('REPRESENTATIVE');
                setSortBy('CLOSEST_TYPICAL');
              }}
              className="text-teal-700 hover:text-teal-900 font-semibold cursor-pointer inline-flex items-center gap-1 shrink-0 text-xs"
            >
              <span>← Back to representative fares</span>
            </button>
          )}
        </div>
      </div>

      {/* Travel Window Filter Strip */}
      <div className="flex items-center gap-1.5 flex-wrap text-xs">
        <span className="text-[11px] font-semibold text-slate-500 mr-1">Travel Window:</span>
        <button
          onClick={() => setWindowFilter('ALL')}
          className={`px-2.5 py-1 rounded-lg text-[11px] font-sans transition-all cursor-pointer border ${windowFilter === 'ALL'
              ? 'bg-teal-700 text-white border-teal-700 font-semibold shadow-xs'
              : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-slate-300'
            }`}
        >
          All Dates ({mappedFares.length})
        </button>
        {['7D', '14D', '21D', '30D', '60D'].map((bucket) => {
          const count = windowStats[bucket] || 0;
          if (count === 0) return null;
          const labelMap = {
            '7D': 'Near-term (1–10D)',
            '14D': '14D',
            '21D': '21D',
            '30D': '30D',
            '60D': '60D+',
          };
          return (
            <button
              key={bucket}
              onClick={() => setWindowFilter(windowFilter === bucket ? 'ALL' : bucket)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-sans transition-all cursor-pointer border ${windowFilter === bucket
                  ? 'bg-teal-700 text-white border-teal-700 font-semibold shadow-xs'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-slate-300'
                }`}
            >
              <span>{labelMap[bucket] || bucket}</span>
              <span className="ml-1 opacity-80 font-mono text-[10px]">({count})</span>
            </button>
          );
        })}
      </div>

      {/* Filter and Sorting Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200/80 text-xs">
        {/* Left: Airline & Stops Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={airlineFilter}
              onChange={(e) => setAirlineFilter(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:outline-none focus:border-slate-400 cursor-pointer text-xs"
            >
              <option value="ALL">All Airlines ({mappedFares.length})</option>
              {uniqueAirlines.map((air) => (
                <option key={air} value={air}>
                  {air} ({airlineStats[air]})
                </option>
              ))}
            </select>
          </div>

          <select
            value={stopsFilter}
            onChange={(e) => setStopsFilter(e.target.value)}
            className="bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:outline-none focus:border-slate-400 cursor-pointer text-xs"
          >
            <option value="ALL">All Stops</option>
            <option value="NON_STOP">Nonstop only</option>
            <option value="CONNECTING">Connecting only</option>
          </select>
        </div>

        {/* Right: Sort Control & Record Count */}
        <div className="flex items-center gap-3 justify-between sm:justify-end">
          <span className="text-[11px] font-mono text-slate-500">
            {isPaginated
              ? `Showing ${totalCount === 0 ? '0' : `${startIndex + 1}–${endIndex}`} of ${totalCount}`
              : `${displayedFares.length} representative fares`}
          </span>

          <div className="flex items-center gap-1.5">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:outline-none focus:border-slate-400 cursor-pointer text-xs"
            >
              <option value="CLOSEST_TYPICAL">Closest to typical</option>
              <option value="PRICE_ASC">Lowest fare</option>
              {viewMode === 'ALL' && <option value="PRICE_DESC">Highest fare</option>}
              <option value="TIME_ASC">Earliest departure</option>
              <option value="TIME_DESC">Latest departure</option>
            </select>
          </div>
        </div>
      </div>

      {displayedFares.length === 0 ? (
        <div className="p-8 text-center text-slate-500 text-xs bg-slate-50 rounded-xl border border-slate-200">
          No observed flights match the selected filter criteria.
        </div>
      ) : (
        <div className="overflow-x-auto border border-slate-200/90 rounded-xl">
          <table className="w-full text-left text-xs border-collapse font-sans">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">Airline</th>
                <th className="py-3 px-4">Departure</th>
                <th className="py-3 px-4">Arrival</th>
                <th className="py-3 px-4">Travel Date</th>
                <th className="py-3 px-4">Stops</th>
                <th className="py-3 px-4 text-right">Observed Fare</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {displayedFares.map((flight) => {
                const isNonStop = flight.stops === 'Nonstop';
                const isExpanded = expandedRowId === flight.id;

                return (
                  <React.Fragment key={flight.id}>
                    <tr
                      onClick={() => toggleExpand(flight.id)}
                      className={`hover:bg-slate-50/80 transition-colors cursor-pointer ${isExpanded ? 'bg-slate-50' : ''
                        }`}
                    >
                      {/* Airline */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900">{flight.airline}</span>
                        </div>
                      </td>

                      {/* Departure */}
                      <td className="py-3 px-4 font-mono font-semibold text-slate-800">
                        {flight.departureTime}
                      </td>

                      {/* Arrival */}
                      <td className="py-3 px-4 font-mono text-slate-600">
                        {flight.arrivalTime}
                      </td>

                      {/* Travel Date */}
                      <td className="py-3 px-4 font-mono text-slate-700">
                        {flight.travelDate}
                      </td>

                      {/* Stops */}
                      <td className="py-3 px-4">
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded font-medium border ${isNonStop
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : 'bg-slate-100 text-slate-700 border-slate-200'
                            }`}
                        >
                          {flight.stops}
                        </span>
                      </td>

                      {/* Observed Fare - strictly flight.price_inr */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <span className="font-mono font-bold text-slate-950 text-sm">
                            {formatINR(flight.price_inr)}
                          </span>
                          {isExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Flight Detail Drawer */}
                    {isExpanded && (
                      <tr className="bg-slate-50/90 text-slate-600 text-xs">
                        <td colSpan={6} className="py-3 px-4 border-t border-slate-200/60">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                            <div>
                              <span className="text-slate-400 font-sans text-[10px] uppercase tracking-wider block">Flight Route</span>
                              <span className="font-semibold text-slate-800">{flight.origin} → {flight.destination}</span>
                            </div>
                            <div>
                              <span className="text-slate-400 font-sans text-[10px] uppercase tracking-wider block">Cabin & Seats</span>
                              <span className="text-slate-700">{flight.cabinClass} ({flight.seatsLeft})</span>
                            </div>
                            <div>
                              <span className="text-slate-400 font-sans text-[10px] uppercase tracking-wider block">Routing Details</span>
                              <span className="text-slate-700">{flight.stops}</span>
                            </div>
                            <div>
                              <span className="text-slate-400 font-sans text-[10px] uppercase tracking-wider block">Collected At</span>
                              <span className="text-slate-500 text-[11px]">{formattedCollectionTime}</span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer (when in ALL view or paginated) */}
      {isPaginated && totalPages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-100">
          <div className="text-xs font-mono text-slate-500">
            Page {validPage} of {totalPages} · {totalCount} eligible flights
          </div>

          <div className="flex items-center gap-1 self-center">
            {/* Previous Page */}
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={validPage === 1}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-all"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            {/* Page Number Buttons */}
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((page) => {
                return (
                  page === 1 ||
                  page === totalPages ||
                  Math.abs(page - validPage) <= 1
                );
              })
              .map((page, idx, arr) => {
                const prevPage = arr[idx - 1];
                const showEllipsis = prevPage && page - prevPage > 1;

                return (
                  <React.Fragment key={page}>
                    {showEllipsis && (
                      <span className="px-1 text-slate-400 font-mono text-xs">...</span>
                    )}
                    <button
                      onClick={() => setCurrentPage(page)}
                      className={`min-w-8 h-8 px-2 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${validPage === page
                          ? 'bg-teal-700 text-white shadow-xs font-bold'
                          : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                        }`}
                    >
                      {page}
                    </button>
                  </React.Fragment>
                );
              })}

            {/* Next Page */}
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={validPage === totalPages}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-all"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Footer Disclaimer */}
      <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-400 gap-2">
        <div className="flex items-center gap-1.5 text-[11px]">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>
            Verified domestic one-way observations collected during scheduled runs. Not an airline booking engine.
          </span>
        </div>
        <div className="text-[11px] font-mono shrink-0">
          {viewMode === 'REPRESENTATIVE' ? (
            <span>Showing fares closest to the typical market level · {totalCount} observations from 9 Sep 2026</span>
          ) : (
            <span>{totalCount} observations from 9 Sep 2026</span>
          )}
        </div>
      </div>
    </section>
  );
}




