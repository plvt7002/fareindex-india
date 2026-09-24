import React from 'react';
import { X, BookOpen, Layers, ShieldCheck, Sparkles } from 'lucide-react';

export function MethodologyModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div 
        className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="methodology-title"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center text-slate-800">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h3 id="methodology-title" className="text-base font-bold text-slate-900 m-0">
                How is this calculated?
              </h3>
              <p className="text-xs text-slate-500 m-0 font-sans">
                Methodology for FareIndex India market observations
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-700 text-xs leading-relaxed">
          {/* Plain English Mission */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
            <div className="flex items-center gap-2 text-slate-900 font-bold text-xs mb-1">
              <span>Don&apos;t just find a fare. Understand what the fare means.</span>
            </div>
            <p className="m-0 text-slate-600 text-xs leading-relaxed">
              FareIndex India is not a booking engine. It adds an independent Indian-market reference frame to live airfare signals, allowing travelers to benchmark live prices against empirical domestic distributions.
            </p>
          </div>

          {/* 7 Simple Steps */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 mb-3 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-slate-700" />
              How It Works: The 7-Step Workflow
            </h4>
            
            <ol className="space-y-2.5 pl-0 list-none m-0">
              <li className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[11px] shrink-0 mt-0.5">1</span>
                <div>
                  <strong className="text-slate-900 block text-xs">Collect observed domestic one-way fares</strong>
                  <span className="text-slate-600">
                    Real domestic airfares for 1 adult in Economy are collected systematically across major domestic routes and advance booking horizons.
                  </span>
                </div>
              </li>

              <li className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[11px] shrink-0 mt-0.5">2</span>
                <div>
                  <strong className="text-slate-900 block text-xs">Validate and normalize observations</strong>
                  <span className="text-slate-600">
                    Itineraries with international transit stops or non-comparable cabin configurations are filtered out to ensure genuine domestic travel only.
                  </span>
                </div>
              </li>

              <li className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[11px] shrink-0 mt-0.5">3</span>
                <div>
                  <strong className="text-slate-900 block text-xs">Deduplicate repeated scraper runs</strong>
                  <span className="text-slate-600">
                    Repeated scraper queries for the same travel date on the same observation day are consolidated to prevent artificial statistical overweighting.
                  </span>
                </div>
              </li>

              <li className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[11px] shrink-0 mt-0.5">4</span>
                <div>
                  <strong className="text-slate-900 block text-xs">Build route-level distributions</strong>
                  <span className="text-slate-600">
                    Empirical quantiles (P25, Median, P75) are calibrated across verified canonical datasets to define normal market price ranges.
                  </span>
                </div>
              </li>

              <li className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[11px] shrink-0 mt-0.5">5</span>
                <div>
                  <strong className="text-slate-900 block text-xs">Retrieve live Google Flights signal via SerpApi</strong>
                  <span className="text-slate-600">
                    Real-time flight search results and Google&apos;s own typical search range are queried securely on demand.
                  </span>
                </div>
              </li>

              <li className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[11px] shrink-0 mt-0.5">6</span>
                <div>
                  <strong className="text-slate-900 block text-xs">Compare the live fare against both reference frames</strong>
                  <span className="text-slate-600">
                    The live fare is simultaneously evaluated against Google&apos;s typical search range and FareIndex&apos;s verified domestic distribution.
                  </span>
                </div>
              </li>

              <li className="flex items-start gap-3 p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                <span className="w-5 h-5 rounded-full bg-slate-900 text-white font-mono font-bold flex items-center justify-center text-[11px] shrink-0 mt-0.5">7</span>
                <div>
                  <strong className="text-slate-900 block text-xs">Explain agreement or divergence transparently</strong>
                  <span className="text-slate-600">
                    Deterministic comparison surfaces whether the signals agree or diverge, explaining the underlying difference in reference datasets.
                  </span>
                </div>
              </li>
            </ol>
          </div>

          {/* Purely Descriptive Reminder */}
          <div className="border border-slate-200 rounded-xl p-3 bg-slate-50">
            <div className="flex items-center gap-1.5 font-bold text-slate-900 mb-1">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-700" />
              <span>Descriptive Market Intelligence Only</span>
            </div>
            <p className="text-slate-500 text-[11px] m-0">
              Fare position (LOW / NORMAL / HIGH) is purely descriptive based on statistical percentiles. FareIndex India provides no buying advice, price predictions, or booking transactions.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

