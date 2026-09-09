import React from 'react';
import { Info } from 'lucide-react';

export function MetricCard({ title, value, subtext, change, changeType, icon: Icon, tooltip }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs hover:border-slate-300 transition-colors relative group">
      <div className="flex items-center justify-between text-slate-500 mb-1.5">
        <span className="text-xs font-medium text-slate-600 flex items-center gap-1.5">
          {Icon && <Icon className="w-3.5 h-3.5 text-teal-700" />}
          {title}
        </span>
        {tooltip && (
          <div className="relative group/tooltip cursor-help">
            <Info className="w-3.5 h-3.5 text-slate-400 hover:text-slate-600" />
            <div className="absolute right-0 bottom-full mb-2 hidden group-hover/tooltip:block w-52 p-2 bg-slate-900 text-slate-100 text-xs rounded shadow-lg z-20 font-normal">
              {tooltip}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-baseline justify-between mt-1">
        <div className="text-2xl font-bold font-mono text-slate-900 tracking-tight">
          {value ?? '—'}
        </div>
        {change !== undefined && change !== null && (
          <div
            className={`text-xs font-medium font-mono px-2 py-0.5 rounded border ${
              changeType === 'increase'
                ? 'text-rose-700 bg-rose-50 border-rose-200'
                : changeType === 'decrease'
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                : 'text-slate-600 bg-slate-50 border-slate-200'
            }`}
          >
            {changeType === 'increase' ? '↑' : changeType === 'decrease' ? '↓' : ''} {change}
          </div>
        )}
      </div>

      {subtext && (
        <div className="text-xs text-slate-500 mt-1.5">
          {subtext}
        </div>
      )}
    </div>
  );
}
