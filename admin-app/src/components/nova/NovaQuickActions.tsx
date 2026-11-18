import React, { useState } from 'react';
import { Mic, ArrowUp, AlertTriangle } from 'lucide-react';
import { useNexus } from '../../context/NexusContext';

export const NovaQuickActions: React.FC = () => {
  const {
    quickActions,
    triggerQuickAction,
    sendMessage,
    novaState,
    setIsNeedsRayDrawerOpen,
    needsRayDecisions
  } = useNexus();
  const [inputText, setInputText] = useState('');

  const pendingDecisionsCount = needsRayDecisions.filter(d => d.status === 'PENDING').length;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    sendMessage(inputText);
    setInputText('');
  };

  return (
    <div className="pt-2 px-1 space-y-3">
      {/* Quick Action Chips */}
      <div className="flex flex-wrap items-center gap-1.5">
        {pendingDecisionsCount > 0 && (
          <button
            type="button"
            onClick={() => setIsNeedsRayDrawerOpen(true)}
            className="px-2.5 py-1 rounded-full text-xs font-bold text-amber-900 bg-amber-50 hover:bg-amber-100 border border-amber-300 shadow-2xs transition-all active:scale-95 whitespace-nowrap cursor-pointer flex items-center gap-1 animate-beacon-amber"
          >
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Review {pendingDecisionsCount} Gates</span>
          </button>
        )}
        {quickActions.map((action, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => triggerQuickAction(action)}
            className="px-2.5 py-1 rounded-full text-xs font-medium text-slate-700 bg-white hover:bg-blue-50 hover:text-blue-600 border border-slate-200/90 shadow-2xs transition-all active:scale-95 whitespace-nowrap cursor-pointer interactive-btn"
          >
            {action}
          </button>
        ))}
      </div>

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <div className="absolute left-3 text-slate-400">
          <Mic className="w-4 h-4" />
        </div>
        <input
          type="text"
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          placeholder={novaState === 'listening' ? 'Ask Nova anything by voice...' : 'Ask Nova anything...'}
          className="w-full pl-9 pr-10 py-2.5 bg-slate-50/90 hover:bg-white focus:bg-white text-xs text-slate-800 placeholder:text-slate-400 rounded-xl border border-slate-200/80 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all shadow-2xs"
        />
        <button
          type="submit"
          disabled={!inputText.trim()}
          className="absolute right-1.5 p-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600 text-white transition-colors cursor-pointer"
        >
          <ArrowUp className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
