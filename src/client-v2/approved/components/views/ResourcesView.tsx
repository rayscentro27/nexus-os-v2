import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

export const ResourcesView: React.FC = () => {
  const { resources, currentLevel, openClydeWithPrompt } = usePortal();

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* Consolidated Header Banner (Clean White Surface) */}
      <div className="flex items-center justify-between gap-3 p-3 rounded-xl border border-slate-200/90 bg-white shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-amber-50 border border-amber-200 shrink-0 text-amber-600">
            <GiantIcon type="library" size="sm" glow={false} />
          </div>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-amber-800 font-bold">
              <span>GoClear Capital Intelligence Academy</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500 font-medium">Proprietary Curriculum</span>
            </div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">
              Underwriting Knowledge & Playbooks · {currentLevel.name} Tier
            </h1>
          </div>
        </div>

        <button
          onClick={() => openClydeWithPrompt('Can you summarize the GoClear Institutional Capital Architecture guide for me?')}
          className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
        >
          Study with Clyde AI →
        </button>
      </div>

      {/* Main Consolidated Playbooks Grid (Fits on screen without scrolling) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-3 gap-2.5 overflow-hidden">
        {resources.map((res) => (
          <div
            key={res.id}
            className="rounded-xl border border-slate-200/90 bg-white overflow-hidden flex flex-col justify-between shadow-xs group hover:border-amber-400/60 hover:shadow-sm transition-all"
          >
            <div className="relative h-28 overflow-hidden bg-slate-100 shrink-0">
              <img
                src={res.imageThumbnail}
                alt={res.title}
                referrerPolicy="no-referrer"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 opacity-90"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 via-transparent to-transparent" />
              <div className="absolute top-2 left-2 flex items-center gap-1.5">
                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-white/95 text-amber-800 border border-amber-300 shadow-xs">
                  {res.type.toUpperCase()}
                </span>
              </div>
              <div className="absolute bottom-1.5 right-2 text-[10px] text-slate-300 font-mono">
                {res.duration}
              </div>
            </div>

            <div className="p-3 flex-1 flex flex-col justify-between min-h-0">
              <div>
                <h3 className="text-xs font-bold text-slate-900 tracking-tight group-hover:text-amber-700 transition-colors line-clamp-1">
                  {res.title}
                </h3>
                <p className="mt-1 text-[11px] text-slate-600 leading-snug line-clamp-2">
                  {res.summary}
                </p>
              </div>

              <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[10px] text-slate-400 font-mono">Verified Guide</span>
                <button
                  onClick={() => openClydeWithPrompt(`Explain key concepts from ${res.title}`)}
                  className="text-xs text-amber-700 hover:text-amber-800 font-bold hover:underline cursor-pointer"
                >
                  Read & Review →
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
