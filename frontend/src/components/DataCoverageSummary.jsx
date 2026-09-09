import React from 'react';
import { Database, CalendarCheck, Route, FileSpreadsheet } from 'lucide-react';

export function DataCoverageSummary({
  lastObservationDate,
  contributingRoutesCount,
  totalRoutesCount,
  totalObservations,
  usableTravelDatesCount,
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
      <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-100">
        <span className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-teal-700" />
          Market Data Ingestion Coverage
        </span>
        <span className="text-[11px] font-mono text-slate-500">
          Current Ingestion Snapshot
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* 1. Last Observation Date */}
        <div className="bg-slate-50/70 border border-slate-200/80 rounded-lg p-2.5">
          <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1">
            <CalendarCheck className="w-3 h-3 text-teal-700" />
            Last Observation
          </div>
          <div className="text-sm font-bold font-mono text-slate-900 mt-1">
            {lastObservationDate || '—'}
          </div>
        </div>

        {/* 2. Indexed Routes Contributing */}
        <div className="bg-slate-50/70 border border-slate-200/80 rounded-lg p-2.5">
          <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1">
            <Route className="w-3 h-3 text-teal-700" />
            Indexed Routes
          </div>
          <div className="text-sm font-bold font-mono text-slate-900 mt-1">
            {contributingRoutesCount ?? 0} / {totalRoutesCount ?? 0}
          </div>
        </div>

        {/* 3. Total Observations */}
        <div className="bg-slate-50/70 border border-slate-200/80 rounded-lg p-2.5">
          <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1">
            <FileSpreadsheet className="w-3 h-3 text-teal-700" />
            Total Observations
          </div>
          <div className="text-sm font-bold font-mono text-slate-900 mt-1">
            {totalObservations?.toLocaleString('en-IN') ?? '0'}
          </div>
        </div>

        {/* 4. Travel Dates Records */}
        <div className="bg-slate-50/70 border border-slate-200/80 rounded-lg p-2.5">
          <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1">
            <CalendarCheck className="w-3 h-3 text-teal-700" />
            Travel Dates Available
          </div>
          <div className="text-sm font-bold font-mono text-slate-900 mt-1">
            {usableTravelDatesCount ?? 0} / {totalObservations ?? 0}
          </div>
        </div>
      </div>
    </div>
  );
}
