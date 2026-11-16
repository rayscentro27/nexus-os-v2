import React from 'react';
import { Sparkles } from 'lucide-react';
import { useNexus, PAGE_NOVA_GREETINGS } from '../../context/NexusContext';
import { UserAvatar } from '../common/UserAvatar';

export const NovaConversation: React.FC = () => {
  const { currentPage, messages, novaState } = useNexus();
  const greetingData = PAGE_NOVA_GREETINGS[currentPage] || PAGE_NOVA_GREETINGS['command-center'];

  // Heights for audio waveform bars
  const waveformHeights = [
    6, 12, 18, 10, 16, 24, 30, 22, 14, 28, 36, 26, 18, 32, 28, 20, 15, 24, 30, 18, 12, 8
  ];

  return (
    <div className="flex flex-col gap-3 px-1">
      {/* Speech bubble / greeting from Nova */}
      <div className="p-3.5 bg-blue-50/70 border border-blue-100/80 rounded-2xl text-xs text-slate-700 leading-relaxed shadow-xs">
        <div className="font-semibold text-slate-800 text-[13px] mb-1">
          {greetingData.greeting.split('\n')[0]}
        </div>
        <div className="text-slate-600">
          {greetingData.greeting.split('\n')[1] || greetingData.greeting}
        </div>
      </div>

      {/* Live Audio Waveform */}
      <div className="flex items-center justify-center gap-[3px] py-1 px-2 h-10 bg-slate-50/60 rounded-xl">
        {waveformHeights.map((h, i) => (
          <span
            key={i}
            className={`w-[2.5px] rounded-full bg-blue-500/80 transition-all duration-300 ${
              novaState === 'speaking' || novaState === 'listening' ? 'animate-wave' : 'opacity-40'
            }`}
            style={{
              height: novaState === 'speaking' || novaState === 'listening' ? `${h}px` : '4px',
              animationDelay: `${(i % 5) * 0.15}s`
            }}
          />
        ))}
      </div>

      {/* Message Feed */}
      <div className="space-y-3 max-h-48 overflow-y-auto custom-scrollbar pr-1">
        {messages.map(msg => (
          <div key={msg.id} className="text-xs">
            {msg.sender === 'user' ? (
              <div className="flex items-start gap-2">
                <UserAvatar name="Ray Davis" size="xs" />
                <div className="flex-1">
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-0.5">
                    <span className="font-medium text-slate-700">You</span>
                    <span>({msg.timestamp})</span>
                  </div>
                  <div className="text-slate-800 bg-slate-100/90 rounded-xl p-2.5 leading-relaxed">
                    {msg.text}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles className="w-3 h-3" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-0.5">
                    <span className="font-semibold text-blue-600">Nova</span>
                    <span className="text-[10px] text-slate-400">({novaState})</span>
                  </div>
                  <div className="text-slate-800 bg-blue-50/90 border border-blue-100/70 rounded-xl p-2.5 leading-relaxed flex items-start justify-between gap-2">
                    <p>{msg.text}</p>
                    {/* Mini animated wave indicator */}
                    <div className="flex items-center gap-0.5 shrink-0 mt-1">
                      <span className="w-0.5 h-3 bg-blue-500 rounded-full animate-wave" />
                      <span className="w-0.5 h-4 bg-blue-600 rounded-full animate-wave" style={{ animationDelay: '0.2s' }} />
                      <span className="w-0.5 h-2 bg-blue-400 rounded-full animate-wave" style={{ animationDelay: '0.4s' }} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
