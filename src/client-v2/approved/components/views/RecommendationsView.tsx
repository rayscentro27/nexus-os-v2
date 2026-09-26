import React, { useState } from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';
import radarEmptyStateImg from '../../assets/images/radar_empty_state_1790436758127.jpg';

export const RecommendationsView: React.FC = () => {
  const { recommendations, setActiveTab, openClydeWithPrompt, profile } = usePortal();
  const [filter, setFilter] = useState<string>('ALL');

  const filtered = filter === 'ALL'
    ? recommendations
    : filter === 'COMPLETED'
    ? [] // Currently all recommendations are in active queue, triggering empty state
    : recommendations.filter((r) => r.priority === filter);

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-teal-50 border border-teal-200 shrink-0 text-teal-600">
            <GiantIcon type="compass" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-teal-700 font-bold">
              <span>Personalized Capital Opportunities</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">Prioritized by ROI & Speed</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Strategic Recommendations · {recommendations.length} High-Leverage Initiatives
            </h1>
          </div>
        </div>

        {/* Priority Filter Controls */}
        <div className="flex items-center gap-1 p-0.5 bg-slate-100 border border-slate-200 rounded-lg">
          {['ALL', 'HIGH IMPACT', 'QUICK WIN', 'COMPLETED'].map((p) => {
            const count = p === 'ALL'
              ? recommendations.length
              : p === 'COMPLETED'
              ? 0
              : recommendations.filter((r) => r.priority === p).length;

            return (
              <button
                key={p}
                onClick={() => setFilter(p)}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                  filter === p
                    ? 'bg-white text-slate-900 font-bold shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {p === 'ALL' ? 'All' : p === 'HIGH IMPACT' ? 'High Impact' : p === 'QUICK WIN' ? 'Quick Win' : 'Completed'} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Recommendations Content or Branded Empty-State Illustration */}
      {filtered.length === 0 ? (
        <div className="flex-1 min-h-0 rounded-xl border border-slate-200/90 bg-white p-6 shadow-xs flex flex-col items-center justify-center text-center overflow-y-auto animate-fade-in">
          <div className="relative w-44 h-32 sm:w-56 sm:h-40 rounded-2xl overflow-hidden shadow-xs border border-slate-200 bg-slate-50 shrink-0 group">
            <img
              src={radarEmptyStateImg}
              alt="Opportunity Radar Scanned"
              referrerPolicy="no-referrer"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950/40 via-transparent to-transparent" />
            <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded text-[9px] font-bold font-mono bg-white/95 text-teal-800 border border-teal-300 shadow-xs">
              RADAR ACTIVE
            </span>
          </div>

          <div className="max-w-lg mt-4">
            <h3 className="text-base font-bold text-slate-900">
              {filter === 'COMPLETED'
                ? 'All Recommended Initiatives Are Currently Active'
                : 'No Opportunities Found in this Queue'}
            </h3>
            <p className="mt-1 text-xs text-slate-600 leading-relaxed">
              {filter === 'COMPLETED'
                ? `${profile.companyName} has ${recommendations.length} active recommendation(s) returned by the live client-scoped query.`
                : 'GoClear Opportunity Radar has analyzed your file. All recommended strategic levers are currently categorized under High Impact and Quick Win.'}
            </p>

            {/* Guidance Card with Clear Steps */}
            <div className="mt-3.5 p-3 rounded-xl bg-slate-50 border border-slate-200 text-left text-xs space-y-2 shadow-xs">
              <span className="text-[10px] font-bold text-teal-700 uppercase tracking-wider block">
                Next Strategic Execution Steps:
              </span>
              <div className="flex items-start gap-2.5 text-slate-700">
                <span className="w-4 h-4 rounded-full bg-teal-100 border border-teal-300 text-teal-800 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">1</span>
                <span>Execute the <strong>Revolving Balance Paydown</strong> to drop personal utilization under 10% (+15 pts).</span>
              </div>
              <div className="flex items-start gap-2.5 text-slate-700">
                <span className="w-4 h-4 rounded-full bg-teal-100 border border-teal-300 text-teal-800 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">2</span>
                <span>Upload <strong>90-Day Bank Statements</strong> in the Vault to unlock the $250,000 prime commercial facility.</span>
              </div>
              <div className="flex items-start gap-2.5 text-slate-700">
                <span className="w-4 h-4 rounded-full bg-teal-100 border border-teal-300 text-teal-800 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">3</span>
                <span>Submit your certified underwriting dossier for formal Credit Committee assignment.</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2.5">
              <button
                onClick={() => setFilter('ALL')}
                className="px-3.5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs shadow-xs cursor-pointer active:scale-95 transition-all"
              >
                View All 4 Active Initiatives →
              </button>
              <button
                onClick={() => setActiveTab('request-review')}
                className="px-3.5 py-2 rounded-lg bg-white border border-slate-200 hover:border-slate-300 text-slate-700 font-semibold text-xs shadow-xs cursor-pointer active:scale-95 transition-all"
              >
                Request Committee Audit
              </button>
              <button
                onClick={() => openClydeWithPrompt("What other strategic initiatives can I execute to increase my business bankability to 90+?")}
                className="px-3 py-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-teal-800 font-bold text-xs shadow-xs cursor-pointer transition-colors"
              >
                Ask Clyde Next Strategies →
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Recommendations 2x2 Consolidated Grid (Fits without scrolling) */
        <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 gap-2.5 overflow-hidden">
          {filtered.map((rec) => {
            const isHighImpact = rec.priority === 'HIGH IMPACT';
            const isQuickWin = rec.priority === 'QUICK WIN';

            return (
              <div
                key={rec.id}
                className={`p-3 rounded-xl border flex flex-col justify-between transition-all shadow-xs ${
                  isHighImpact
                    ? 'border-teal-200 bg-white hover:border-teal-300 ring-1 ring-teal-500/10'
                    : isQuickWin
                    ? 'border-amber-200 bg-white hover:border-amber-300 ring-1 ring-amber-500/10'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="font-bold text-[10px] text-teal-700 uppercase tracking-wider">
                      {rec.category}
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`font-mono font-bold text-[9px] px-1.5 py-0.5 rounded uppercase ${
                          isHighImpact
                            ? 'text-teal-800 bg-teal-50 border border-teal-200'
                            : isQuickWin
                            ? 'text-amber-800 bg-amber-50 border border-amber-200'
                            : 'text-slate-700 bg-slate-100 border border-slate-200'
                        }`}
                      >
                        {rec.priority}
                      </span>
                      <span className="font-mono text-emerald-700 font-bold text-xs">
                        {rec.impactScore}
                      </span>
                    </div>
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 tracking-tight leading-snug">
                    {rec.title}
                  </h3>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed line-clamp-2">
                    {rec.reason}
                  </p>

                  {/* Clean Light Impact Highlight Card */}
                  <div className="mt-2 p-2 rounded-lg bg-teal-50/70 border border-teal-200/80 text-[11px] text-slate-700 shadow-xs flex items-center justify-between">
                    <div>
                      <span className="text-teal-900 font-bold">Institutional Impact:</span>{' '}
                      <span className="text-slate-900 font-mono font-semibold">{rec.impactScore}</span>
                    </div>
                    <span className="text-[10px] text-teal-700 font-mono font-semibold">Underwriting Boost</span>
                  </div>
                </div>

                <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={() => openClydeWithPrompt(`How do I execute: ${rec.title}?`)}
                    className="text-[11px] text-slate-500 hover:text-teal-700 font-medium cursor-pointer"
                  >
                    Ask Clyde Guide →
                  </button>

                  <button
                    onClick={() => setActiveTab(rec.tabTarget)}
                    className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
                  >
                    {rec.actionLabel} →
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
