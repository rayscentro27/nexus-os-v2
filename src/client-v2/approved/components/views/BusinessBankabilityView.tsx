import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

export const BusinessBankabilityView: React.FC = () => {
  const { bankabilityPillars, setActiveTab, openClydeWithPrompt, profile, facts } = usePortal();

  // Composite Bankability Score
  const averageScore = Math.round(
    bankabilityPillars.length ? bankabilityPillars.reduce((acc, curr) => acc + curr.score, 0) / bankabilityPillars.length : facts.bankabilityScore
  );

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-teal-50 border border-teal-200 shrink-0 text-teal-600">
            <GiantIcon type="bank-column" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-teal-700 font-bold">
              <span>Institutional Bank Rating & Trust Strength</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">6 Underwriting Pillars</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Business Bankability Score · <span className="text-teal-700 font-mono">{averageScore} / 100</span> (Target: 85+)
            </h1>
          </div>
        </div>

        <button
          onClick={() => setActiveTab('funding-readiness')}
          className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
        >
          View Matched Funding Facilities →
        </button>
      </div>

      {/* 2-Column Consolidated Cockpit (Fits without scrolling) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 overflow-hidden">
        {/* Left: Score Dial & Clyde Insight (Clean Light Card - 4 cols) */}
        <div className="lg:col-span-4 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs text-slate-900">
          <div>
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
              <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider">
                Composite Bankability
              </span>
              <span className="text-[10px] font-mono text-amber-700 font-semibold">
                7 Pts to Prime Target
              </span>
            </div>

            <div className="flex flex-col items-center justify-center my-3 text-center">
              <div className="relative w-28 h-28 rounded-full border-4 border-teal-400/50 bg-teal-50/60 flex flex-col items-center justify-center">
                <span className="text-4xl font-black text-slate-900 tabular-nums tracking-tight">
                  {averageScore}
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700">
                  / 100 Score
                </span>
              </div>
              <h3 className="text-xs font-bold text-slate-900 mt-2">
                Underwriting Grade: Strong Prime-Minus
              </h3>
              <p className="text-[11px] text-slate-600 mt-1 max-w-xs leading-snug">
                {profile.companyName} foundations reflect the live requirements returned for this client. Remaining gaps are shown in the pillars.
              </p>
            </div>
          </div>

          {/* Clyde Bankability Advice */}
          <div className="p-2.5 rounded-lg border border-teal-200/70 bg-teal-50/40 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-teal-800 uppercase">⚡ Pillar Weight</span>
              <button
                onClick={() => openClydeWithPrompt("Which bankability pillar matters most for an unsecured business line of credit?")}
                className="text-[10px] text-teal-700 font-bold hover:underline cursor-pointer"
              >
                Ask Clyde →
              </button>
            </div>
            <p className="text-[11px] text-slate-600 mt-1 leading-snug">
              Banking & Cash Flow carries 25% weight. Uploading 90-day statements lifts this pillar to 92%, delivering an instant +5 point leap.
            </p>
          </div>
        </div>

        {/* Right: 6 Bankability Pillars Grid (Clean White Surface - 8 cols) */}
        <div className="lg:col-span-8 rounded-xl border border-slate-200/90 bg-white p-3 flex flex-col justify-between shadow-xs overflow-hidden">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 shrink-0">
            <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider">
              Underwriting Trust Pillars
            </span>
            <span className="text-[10px] font-mono text-slate-400">Weighted Commercial Rubric</span>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 pr-1 scrollbar-thin">
            {bankabilityPillars.map((pillar) => (
              <div
                key={pillar.id}
                className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/80 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between text-xs">
                    <h4 className="font-bold text-slate-900 text-xs">{pillar.name}</h4>
                    <span className="font-mono font-bold text-teal-700 text-xs">
                      {pillar.score}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden mt-1.5">
                    <div
                      className={`h-full rounded-full ${
                        pillar.score >= 80 ? 'bg-teal-500' : pillar.score >= 70 ? 'bg-sky-500' : 'bg-amber-500'
                      }`}
                      style={{ width: `${pillar.score}%` }}
                    />
                  </div>
                </div>

                <p className="text-[11px] text-slate-600 mt-1.5 pt-1 border-t border-slate-200/80 line-clamp-2">
                  {pillar.details}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
