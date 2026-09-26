import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';

interface ClydeContextMiniProps {
  headline: string;
  insight: string;
  suggestedPrompt: string;
  actionText?: string;
  onAction?: () => void;
}

export const ClydeContextMini: React.FC<ClydeContextMiniProps> = ({
  headline,
  insight,
  suggestedPrompt,
  actionText,
  onAction
}) => {
  const { openClydeWithPrompt } = usePortal();

  return (
    <div className="relative overflow-hidden rounded-2xl border border-teal-200/90 bg-gradient-to-r from-teal-50/60 via-white to-sky-50/40 p-5 shadow-xs">
      <div className="absolute top-0 right-0 w-32 h-32 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 relative z-10">
        <div className="flex items-start gap-4">
          <div className="shrink-0 p-2 rounded-xl bg-teal-50 border border-teal-200">
            <GiantIcon type="clyde" size="sm" glow={false} />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-teal-800 uppercase tracking-wider">
                Clyde Copilot Guidance
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
              <span className="text-xs text-slate-600 font-medium">{headline}</span>
            </div>
            <p className="mt-1 text-sm text-slate-700 leading-relaxed max-w-2xl">
              {insight}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto shrink-0">
          <button
            onClick={() => openClydeWithPrompt(suggestedPrompt)}
            className="flex-1 sm:flex-none px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold transition-all shadow-xs active:scale-95 cursor-pointer whitespace-nowrap"
          >
            Ask Clyde AI
          </button>
          {actionText && onAction && (
            <button
              onClick={onAction}
              className="flex-1 sm:flex-none px-4 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-semibold transition-all active:scale-95 cursor-pointer whitespace-nowrap shadow-xs"
            >
              {actionText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
