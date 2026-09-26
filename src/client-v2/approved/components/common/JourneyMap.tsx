import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { TabType } from '../../types/portal';

export const JourneyMap: React.FC = () => {
  const { journeyNodes, activeTab, setActiveTab } = usePortal();

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div>
          <span className="text-xs uppercase tracking-wider text-teal-700 font-semibold">
            Institutional Roadmap
          </span>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            Financial Readiness Journey
          </h2>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-600">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-500 shadow-xs shadow-teal-500/50" />
            Verified
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500 animate-pulse" />
            In Progress
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-300" />
            Pending Review
          </span>
        </div>
      </div>

      {/* Connected Nodes Progression Track */}
      <div className="relative mt-6 pt-2 pb-2">
        {/* Desktop Connected Connecting Line */}
        <div className="hidden lg:block absolute top-[42px] left-8 right-8 h-1 bg-slate-200 -z-0">
          <div
            className="h-full bg-gradient-to-r from-teal-500 via-sky-500 to-amber-500 rounded-full transition-all duration-1000"
            style={{ width: '74%' }}
          />
        </div>

        {/* Nodes Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-4 relative z-10">
          {journeyNodes.map((node, index) => {
            const isCompleted = node.status === 'completed';
            const isInProgress = node.status === 'in-progress';
            const isActiveView = activeTab === node.tab;

            return (
              <button
                key={node.id}
                onClick={() => setActiveTab(node.tab as TabType)}
                className={`group flex flex-col items-center text-center p-3 rounded-xl transition-all duration-200 border text-left cursor-pointer ${
                  isActiveView
                    ? 'border-teal-500 bg-teal-50/60 shadow-xs ring-1 ring-teal-500/20'
                    : 'border-slate-200 bg-slate-50/70 hover:bg-white hover:border-slate-300 shadow-xs'
                }`}
              >
                {/* Node Milestone Circle */}
                <div
                  className={`w-11 h-11 rounded-full flex items-center justify-center font-mono font-bold text-xs transition-all ${
                    isCompleted
                      ? 'bg-teal-50 text-teal-700 border-2 border-teal-500 shadow-xs'
                      : isInProgress
                      ? 'bg-sky-50 text-sky-700 border-2 border-sky-500 ring-4 ring-sky-500/10'
                      : 'bg-white text-slate-500 border border-slate-300'
                  }`}
                >
                  {isCompleted ? (
                    <svg className="w-5 h-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <span>0{index + 1}</span>
                  )}
                </div>

                <div className="mt-3 w-full">
                  <div className="flex items-center justify-center gap-1">
                    <span className="text-xs font-semibold text-slate-800 group-hover:text-teal-700 transition-colors">
                      {node.label}
                    </span>
                  </div>

                  <div className="mt-1 flex items-center justify-center gap-1 text-[11px] font-mono tabular-nums text-slate-500">
                    <span className={isCompleted ? 'text-teal-700 font-bold' : isInProgress ? 'text-sky-700 font-bold' : 'text-slate-400'}>
                      {node.progress}%
                    </span>
                  </div>

                  <p className="mt-1 text-[10px] text-slate-500 line-clamp-1 hidden sm:block">
                    {node.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
