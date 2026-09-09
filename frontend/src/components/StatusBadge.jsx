import React from 'react';

export function StatusBadge({ status, source, provenance }) {
  const label = status || provenance || source || 'Unknown';
  const labelLower = label.toLowerCase();

  if (labelLower.includes('demo') || labelLower.includes('not live')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
        DEMO - NOT LIVE
      </span>
    );
  }

  if (labelLower.includes('playwright')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
        Playwright Scraper
      </span>
    );
  }

  if (labelLower.includes('amadeus')) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-800 border border-sky-200">
        <span className="w-1.5 h-1.5 rounded-full bg-sky-600"></span>
        Amadeus API
      </span>
    );
  }

  if (labelLower.includes('recovered') || labelLower.includes('google flights') || labelLower === 'unknown') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-800 border border-blue-200">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
        Recovered Data
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
      <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
      {label}
    </span>
  );
}
