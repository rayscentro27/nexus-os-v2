import React, { useState, useRef, useEffect } from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';
import { TabType } from '../../types/portal';

export const ClydeWorkspace: React.FC = () => {
  const {
    isClydeOpen,
    setIsClydeOpen,
    clydeMessages,
    isClydeThinking,
    sendClydeQuery,
    profile,
    setActiveTab
  } = usePortal();

  const [inputQuery, setInputQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isClydeOpen) {
      scrollToBottom();
    }
  }, [clydeMessages, isClydeOpen, isClydeThinking]);

  if (!isClydeOpen) return null;

  const quickPrompts = [
    'What is blocking my funding readiness?',
    'What should I do next?',
    'Explain my credit utilization',
    'How can I improve business bankability?',
    'What documents am I missing?',
    'Help me prepare for underwriter review'
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isClydeThinking) return;
    const query = inputQuery;
    setInputQuery('');
    sendClydeQuery(query);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/40 backdrop-blur-sm animate-fade-in">
      {/* Main Clyde Modal / Full Workspace */}
      <div className="relative flex flex-col w-full max-w-4xl h-[90vh] max-h-[880px] rounded-3xl border border-teal-200/90 bg-white shadow-2xl overflow-hidden">
        {/* Glow Accents */}
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Premium Header */}
        <div className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-slate-200/80 bg-slate-50">
          <div className="flex items-center gap-3.5">
            <div className="p-2 rounded-xl bg-teal-50 border border-teal-200 shrink-0">
              <GiantIcon type="clyde" size="sm" glow={false} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                  Clyde AI Copilot
                </h3>
                <span className="text-[10px] font-bold text-teal-800 border border-teal-300 bg-teal-50 rounded px-1.5 py-0.2 uppercase">
                  Institutional Intelligence
                </span>
              </div>
              <p className="text-xs text-slate-600">
                Grounded in {profile.companyName} portfolio & approved commercial readiness context
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-xs text-slate-600 font-mono">
              Score: <strong className="text-teal-700 font-semibold">{profile.readinessPoints} pts</strong>
            </span>
            <button
              onClick={() => setIsClydeOpen(false)}
              className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200/60 transition-colors cursor-pointer"
              title="Close Clyde Copilot"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Suggested Prompt Chips */}
        <div className="relative z-10 px-6 py-2.5 bg-white border-b border-slate-200/80 overflow-x-auto flex items-center gap-2 no-scrollbar">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider shrink-0 mr-1">
            Suggested:
          </span>
          {quickPrompts.map((prompt, i) => (
            <button
              key={i}
              onClick={() => sendClydeQuery(prompt)}
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-teal-50 border border-slate-200 hover:border-teal-300 text-slate-700 hover:text-teal-800 transition-all shrink-0 cursor-pointer active:scale-95"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Message Stream */}
        <div className="relative z-10 flex-1 overflow-y-auto px-6 py-6 space-y-6 bg-slate-50/50">
          {clydeMessages.map((msg) => {
            const isUser = msg.sender === 'user';

            return (
              <div
                key={msg.id}
                className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {!isUser && (
                  <div className="w-9 h-9 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center shrink-0 mt-1">
                    <GiantIcon type="clyde" size="sm" glow={false} />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-2xl p-4.5 text-sm leading-relaxed ${
                    isUser
                      ? 'bg-gradient-to-r from-teal-600 to-sky-600 text-white font-medium shadow-sm'
                      : 'border border-slate-200 bg-white text-slate-800 shadow-sm'
                  }`}
                >
                  <div className="whitespace-pre-line">{msg.text}</div>

                  {/* Rich Contextual Card Inside Chat */}
                  {msg.card && (
                    <div className="mt-4 pt-3 border-t border-slate-200">
                      <div className="rounded-xl border border-teal-200 bg-teal-50/50 p-3.5">
                        <div className="flex items-center gap-2 text-xs font-bold text-teal-800 uppercase tracking-wider">
                          <span className="w-2 h-2 rounded-full bg-teal-500" />
                          <span>{msg.card.title}</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-700 leading-normal">
                          {msg.card.description}
                        </p>
                        {msg.card.actionTab && (
                          <button
                            onClick={() => {
                              setIsClydeOpen(false);
                              if (msg.card?.actionTab) {
                                setActiveTab(msg.card.actionTab as TabType);
                              }
                            }}
                            className="mt-3 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs transition-all shadow-sm active:scale-95 cursor-pointer"
                          >
                            {msg.card.actionText} →
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  <div className={`mt-2 text-[10px] text-right ${isUser ? 'text-teal-100' : 'text-slate-400'}`}>
                    {msg.timestamp}
                  </div>
                </div>

                {isUser && (
                  <div className="w-9 h-9 rounded-xl overflow-hidden ring-2 ring-teal-500/40 shrink-0 mt-1">
                    <img
                      src={profile.avatarUrl}
                      alt={profile.name}
                      referrerPolicy="no-referrer"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
              </div>
            );
          })}

          {/* Thinking / Analyzing Indicator */}
          {isClydeThinking && (
            <div className="flex gap-3.5 items-center text-xs text-teal-700">
              <div className="w-8 h-8 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center shrink-0">
                <GiantIcon type="clyde" size="sm" glow={false} />
              </div>
              <div className="flex items-center gap-2 p-3 rounded-xl bg-white border border-slate-200 text-slate-700 shadow-xs">
                <span className="w-2 h-2 rounded-full bg-teal-500 animate-ping" />
                <span>Clyde is synthesizing underwriting criteria...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form
          onSubmit={handleSubmit}
          className="relative z-10 p-4 border-t border-slate-200/80 bg-white flex items-center gap-3"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask Clyde anything about your readiness, underwriting rules, or next steps..."
            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-teal-500 focus:bg-white focus:ring-1 focus:ring-teal-500 transition-all"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || isClydeThinking}
            className="px-5 py-3 rounded-xl bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 disabled:opacity-50 text-white font-bold text-xs sm:text-sm transition-all shadow-md active:scale-95 cursor-pointer whitespace-nowrap"
          >
            Send Inquiry
          </button>
        </form>
      </div>
    </div>
  );
};
