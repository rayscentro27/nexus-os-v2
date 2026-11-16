import React from 'react';
import { Sparkles, ArrowUpRight, X } from 'lucide-react';
import { useNexus, PAGE_NOVA_GREETINGS } from '../../context/NexusContext';
import { NovaAvatarStage } from '../nova/NovaAvatarStage';
import { NovaVoiceControls } from '../nova/NovaVoiceControls';
import { NovaConversation } from '../nova/NovaConversation';
import { NovaQuickActions } from '../nova/NovaQuickActions';

export const NovaPanel: React.FC<{ className?: string }> = ({ className = '' }) => {
  const {
    currentPage,
    novaState,
    setCurrentPage,
    setIsNovaDrawerOpen,
    setIsMobileNovaOpen,
  } = useNexus();

  const greetingData =
    PAGE_NOVA_GREETINGS[currentPage] || PAGE_NOVA_GREETINGS['command-center'];

  const handleOpenConsole = () => {
    setCurrentPage('nova');
    setIsNovaDrawerOpen(false);
    setIsMobileNovaOpen(false);
  };

  return (
    <aside
      className={`w-80 shrink-0 bg-white border-l border-slate-200/80 p-4 flex flex-col justify-between overflow-y-auto custom-scrollbar select-none shadow-[-2px_0_12px_rgba(0,0,0,0.015)] ${className}`}
    >
      <div className="space-y-3">
        {/* Top Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
              <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                Nova Operator
              </h2>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5 leading-snug">
              {greetingData.subtitle}
            </p>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={handleOpenConsole}
              className="px-2 py-1 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-[11px] font-semibold text-slate-700 flex items-center gap-1 cursor-pointer"
              title="Open full Nova Console"
            >
              <span>Console</span>
              <ArrowUpRight className="w-3 h-3 text-slate-500" />
            </button>
            <button
              type="button"
              onClick={() => {
                setIsNovaDrawerOpen(false);
                setIsMobileNovaOpen(false);
              }}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"
              aria-label="Close Nova drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Avatar Stage */}
        <NovaAvatarStage state={novaState} />

        {/* Conversation Feed & Waveform */}
        <NovaConversation />

        {/* Voice Controls Bar */}
        <NovaVoiceControls />
      </div>

      {/* Quick Actions & Input at bottom */}
      <div className="mt-2">
        <NovaQuickActions />
      </div>
    </aside>
  );
};
