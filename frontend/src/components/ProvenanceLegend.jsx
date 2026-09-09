import React from 'react';
import { ShieldCheck } from 'lucide-react';

export function ProvenanceLegend() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
      <div className="flex items-center gap-2 pb-2.5 mb-3 border-b border-slate-200">
        <ShieldCheck className="w-4 h-4 text-teal-700" />
        <h3 className="text-xs font-semibold text-slate-800 uppercase tracking-wider font-sans m-0">
          Data Provenance &amp; Integrity Policy
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-sans">
          <thead>
            <tr className="text-slate-500 border-b border-slate-100 bg-slate-50/50">
              <th className="py-2 px-3 font-medium w-48">Source Category</th>
              <th className="py-2 px-3 font-medium">Description &amp; Verification Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            <tr>
              <td className="py-2.5 px-3">
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                  Playwright Scraper
                </span>
              </td>
              <td className="py-2.5 px-3 text-slate-600 text-xs">
                Live automated headless browser collection from Google Flights with stealth execution and structured DOM parsing.
              </td>
            </tr>
            <tr>
              <td className="py-2.5 px-3">
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-600" />
                  Recovered Data
                </span>
              </td>
              <td className="py-2.5 px-3 text-slate-600 text-xs">
                Historical fare records recovered from earlier observation runs across August and September 2026.
              </td>
            </tr>
            <tr>
              <td className="py-2.5 px-3">
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  DEMO - NOT LIVE
                </span>
              </td>
              <td className="py-2.5 px-3 text-slate-600 text-xs">
                Synthetic verification records generated strictly for offline testing. Explicitly segregated and never described as live market observations.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
