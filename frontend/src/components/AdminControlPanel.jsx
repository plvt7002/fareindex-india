import React, { useState } from 'react';
import { Play, Calculator, Cpu, AlertTriangle, CheckCircle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../api/client';

export function AdminControlPanel({ scrapeStatus, onActionComplete }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleScrapeNow = async () => {
    setIsScraping(true);
    setErrorMsg(null);
    try {
      await api.scrapeNow();
      if (onActionComplete) onActionComplete();
    } catch (err) {
      setErrorMsg(err.message || 'Scrape execution failed');
    } finally {
      setIsScraping(false);
    }
  };

  const handleRebuildIndex = async () => {
    setIsRebuilding(true);
    setErrorMsg(null);
    try {
      await api.rebuildIndex();
      if (onActionComplete) onActionComplete();
    } catch (err) {
      setErrorMsg(err.message || 'Index rebuild failed');
    } finally {
      setIsRebuilding(false);
    }
  };

  const status = scrapeStatus?.status || 'never_run';

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-slate-500" />
          <div>
            <h3 className="text-xs font-semibold text-slate-800 uppercase tracking-wider font-sans m-0">
              Data Operations &amp; Backend Controls
            </h3>
            <p className="text-[11px] text-slate-500 m-0">
              Manual pipeline execution for demonstration and index recalculation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900 px-2.5 py-1 rounded bg-slate-100 border border-slate-200 cursor-pointer"
          >
            <span>{isOpen ? 'Hide Controls' : 'Show Controls'}</span>
            {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="mt-4 pt-4 border-t border-slate-200 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleScrapeNow}
              disabled={isScraping || isRebuilding}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-teal-800 hover:bg-teal-700 text-white font-medium text-xs shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
            >
              {isScraping ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Collecting Fares...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Trigger Scrape Now</span>
                </>
              )}
            </button>

            <button
              onClick={handleRebuildIndex}
              disabled={isScraping || isRebuilding}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs border border-slate-300 shadow-xs transition-colors disabled:opacity-50 cursor-pointer"
            >
              {isRebuilding ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-teal-700" />
                  <span>Recalculating...</span>
                </>
              ) : (
                <>
                  <Calculator className="w-3.5 h-3.5 text-teal-700" />
                  <span>Rebuild Index Values</span>
                </>
              )}
            </button>
          </div>

          {/* Diagnostics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div className="bg-slate-50 p-2.5 rounded-md border border-slate-200">
              <span className="text-slate-500 text-[10px] uppercase block mb-0.5 font-sans">
                Last Job Status
              </span>
              <div className="font-semibold text-slate-800">
                {status === 'ok' ? (
                  <span className="text-emerald-700 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> Successful
                  </span>
                ) : status === 'error' ? (
                  <span className="text-rose-700 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Error
                  </span>
                ) : (
                  <span className="text-slate-500">Ready</span>
                )}
              </div>
            </div>

            <div className="bg-slate-50 p-2.5 rounded-md border border-slate-200">
              <span className="text-slate-500 text-[10px] uppercase block mb-0.5 font-sans">
                Active Provider
              </span>
              <span className="font-semibold text-slate-800">
                {scrapeStatus?.provider || 'Configured in .env'}
              </span>
            </div>

            <div className="bg-slate-50 p-2.5 rounded-md border border-slate-200">
              <span className="text-slate-500 text-[10px] uppercase block mb-0.5 font-sans">
                Rows Ingested (Last Run)
              </span>
              <span className="font-semibold text-teal-800">
                {scrapeStatus?.inserted ?? 0} observations
              </span>
            </div>

            <div className="bg-slate-50 p-2.5 rounded-md border border-slate-200">
              <span className="text-slate-500 text-[10px] uppercase block mb-0.5 font-sans">
                Completed Timestamp
              </span>
              <span className="text-slate-700 truncate block text-[11px]">
                {scrapeStatus?.finished_at ? new Date(scrapeStatus.finished_at).toLocaleTimeString() : '—'}
              </span>
            </div>
          </div>

          {/* Error Banner */}
          {(errorMsg || scrapeStatus?.error) && (
            <div className="p-3 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-xs font-mono flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Diagnostic:</span> {errorMsg || scrapeStatus?.error}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
