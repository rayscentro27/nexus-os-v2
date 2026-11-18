import React from 'react';
import { Volume2, VolumeX, Mic, MicOff, PhoneOff } from 'lucide-react';
import { useNexus } from '../../context/NexusContext';

export const NovaVoiceControls: React.FC = () => {
  const {
    novaState,
    setNovaState,
    isMuted,
    setIsMuted,
    isSpeakerOn,
    setIsSpeakerOn
  } = useNexus();

  const toggleMic = () => {
    if (novaState === 'listening') {
      setNovaState('idle');
    } else {
      setNovaState('listening');
    }
  };

  return (
    <div className="flex items-center justify-between px-2 pt-2 pb-1">
      {/* Speaker Toggle */}
      <button
        type="button"
        onClick={() => setIsSpeakerOn(prev => !prev)}
        title={isSpeakerOn ? 'Mute speaker' : 'Unmute speaker'}
        className={`w-11 h-11 rounded-2xl flex flex-col items-center justify-center transition-all cursor-pointer shadow-2xs hover:scale-105 active:scale-95 ${
          isSpeakerOn ? 'bg-slate-100/90 hover:bg-slate-200/90 text-slate-700' : 'bg-rose-50 text-rose-600 border border-rose-200'
        }`}
      >
        {isSpeakerOn ? <Volume2 className="w-5 h-5 stroke-[2.2]" /> : <VolumeX className="w-5 h-5 stroke-[2.2]" />}
        <span className="text-[9px] text-slate-600 font-bold -mt-0.5">Speaker</span>
      </button>

      {/* Mute Mic Toggle */}
      <button
        type="button"
        onClick={() => setIsMuted(prev => !prev)}
        title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
        className={`w-11 h-11 rounded-2xl flex flex-col items-center justify-center transition-all cursor-pointer shadow-2xs hover:scale-105 active:scale-95 ${
          isMuted ? 'bg-amber-50 text-amber-600 border border-amber-200' : 'bg-slate-100/90 hover:bg-slate-200/90 text-slate-700'
        }`}
      >
        {isMuted ? <MicOff className="w-5 h-5 stroke-[2.2]" /> : <Mic className="w-5 h-5 stroke-[2.2]" />}
        <span className="text-[9px] text-slate-600 font-bold -mt-0.5">Mute</span>
      </button>

      {/* Big Blue Primary Microphone Button */}
      <div className="flex flex-col items-center">
        <button
          type="button"
          onClick={toggleMic}
          className={`relative w-14 h-14 rounded-2xl flex items-center justify-center text-white shadow-lg transition-all duration-300 cursor-pointer active:scale-90 ${
            novaState === 'listening'
              ? 'bg-blue-600 ring-4 ring-blue-100 hover:bg-blue-700 scale-108 animate-pulse'
              : 'bg-gradient-to-tr from-blue-600 to-indigo-500 hover:from-blue-700 hover:to-indigo-600 hover:scale-105 shadow-blue-500/25'
          }`}
        >
          <Mic className="w-6 h-6 stroke-[2.3] text-white" />
          {novaState === 'listening' && (
            <span className="absolute -inset-1.5 rounded-2xl border-2 border-blue-400 animate-ping opacity-35" />
          )}
        </button>
        <span className="text-[11px] font-bold text-blue-600 mt-1">
          {novaState === 'listening' ? 'Listening...' : 'Tap to speak'}
        </span>
      </div>

      {/* End Conversation Button */}
      <button
        type="button"
        onClick={() => setNovaState('idle')}
        title="End voice conversation"
        className="w-11 h-11 rounded-2xl bg-rose-500 hover:bg-rose-600 active:scale-95 text-white flex flex-col items-center justify-center transition-all shadow-2xs cursor-pointer hover:scale-105"
      >
        <PhoneOff className="w-5 h-5 stroke-[2.2]" />
        <span className="text-[9px] text-rose-100 font-bold -mt-0.5">End</span>
      </button>
    </div>
  );
};
