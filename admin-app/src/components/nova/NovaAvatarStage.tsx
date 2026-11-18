import React, { useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX, RotateCcw } from 'lucide-react';
import { ASSETS } from '../../data/assets';
import { NovaState } from '../../types';
import { useNexus } from '../../context/NexusContext';
import { NovaVideo } from './NovaVideo';

interface NovaAvatarStageProps {
  state: NovaState;
  compact?: boolean;
}

export const NovaAvatarStage: React.FC<NovaAvatarStageProps> = ({ state, compact = false }) => {
  const { isSpeakerOn } = useNexus();
  const videoRef = useRef<HTMLVideoElement>(null);
  // Autoplay requires starting muted until the user explicitly enables audio
  const [isAudioUnmuted, setIsAudioUnmuted] = useState(false);

  // Normalize visible states to: READY | LISTENING | THINKING | SPEAKING
  const visibleState: 'READY' | 'LISTENING' | 'THINKING' | 'SPEAKING' =
    state === 'listening'
      ? 'LISTENING'
      : state === 'thinking'
      ? 'THINKING'
      : state === 'speaking'
      ? 'SPEAKING'
      : 'READY';

  useEffect(() => {
    const videoEl = videoRef.current;
    if (!videoEl) return;

    const effectiveMuted = !isAudioUnmuted || !isSpeakerOn;
    videoEl.muted = effectiveMuted;

    if (videoEl.paused) {
      videoEl.play().catch(() => {
        // Fallback to muted playback if browser blocks unmuted autoplay
        videoEl.muted = true;
        setIsAudioUnmuted(false);
        videoEl.play().catch(() => undefined);
      });
    }
  }, [isAudioUnmuted, isSpeakerOn, visibleState]);

  const handleToggleAudio = () => {
    const videoEl = videoRef.current;
    if (!videoEl) return;

    const next = !isAudioUnmuted;
    setIsAudioUnmuted(next);
    videoEl.muted = !next || !isSpeakerOn;
    if (next) {
      videoEl.currentTime = 0;
      videoEl.play().catch(() => undefined);
    }
  };

  const handleReplayGreeting = () => {
    const videoEl = videoRef.current;
    if (!videoEl) return;

    videoEl.currentTime = 0;
    if (isSpeakerOn) {
      setIsAudioUnmuted(true);
      videoEl.muted = false;
    }
    videoEl.play().catch(() => undefined);
  };

  return (
    <div className="flex flex-col items-center justify-center pt-1 pb-1 relative select-none">
      {/* Concentric soundwaves / ambient rings container */}
      <div className={`relative ${compact ? 'w-40 h-48' : 'w-44 h-52'} flex items-center justify-center`}>
        {/* Subtle Outer ambient wave rings */}
        <div
          className={`absolute inset-0 rounded-2xl border border-sky-300/40 pointer-events-none transition-all duration-700 ${
            visibleState === 'SPEAKING'
              ? 'scale-105 opacity-60 animate-pulse'
              : visibleState === 'LISTENING'
              ? 'scale-102 opacity-70 border-cyan-400/50'
              : visibleState === 'THINKING'
              ? 'scale-100 opacity-40 border-indigo-300/50 animate-pulse'
              : 'opacity-25'
          }`}
        />
        <div
          className={`absolute inset-2.5 rounded-xl border border-blue-400/30 pointer-events-none transition-all duration-700 ${
            visibleState === 'SPEAKING'
              ? 'scale-102 opacity-75'
              : visibleState === 'LISTENING'
              ? 'opacity-60 border-cyan-300/40'
              : 'opacity-20'
          }`}
        />

        {/* Soft radial ambient glow */}
        <div
          className={`absolute inset-4 rounded-full blur-md pointer-events-none transition-all duration-500 ${
            visibleState === 'SPEAKING'
              ? 'bg-gradient-to-tr from-blue-200/50 via-cyan-100/40 to-indigo-200/50'
              : visibleState === 'THINKING'
              ? 'bg-gradient-to-tr from-indigo-200/50 via-purple-100/30 to-blue-200/40'
              : visibleState === 'LISTENING'
              ? 'bg-gradient-to-tr from-cyan-200/60 via-sky-100/40 to-blue-200/50'
              : 'bg-gradient-to-tr from-blue-100/30 via-slate-100/30 to-indigo-100/30'
          }`}
        />

        {/* Vertical subtle acoustic wave bars on left & right */}
        <div className="absolute left-1.5 flex items-center gap-1 h-16 opacity-75">
          <span
            className={`w-0.5 rounded-full bg-sky-400/80 transition-all duration-300 ${
              visibleState === 'SPEAKING' ? 'h-8' : visibleState === 'LISTENING' ? 'h-5' : 'h-3'
            }`}
          />
          <span
            className={`w-0.5 rounded-full bg-blue-500/70 transition-all duration-300 ${
              visibleState === 'SPEAKING' ? 'h-11' : visibleState === 'LISTENING' ? 'h-7' : 'h-4'
            }`}
          />
          <span
            className={`w-0.5 rounded-full bg-cyan-400/80 transition-all duration-300 ${
              visibleState === 'SPEAKING' ? 'h-14' : visibleState === 'LISTENING' ? 'h-9' : 'h-6'
            }`}
          />
        </div>

        <div className="absolute right-1.5 flex items-center gap-1 h-16 opacity-75">
          <span
            className={`w-0.5 rounded-full bg-cyan-400/80 transition-all duration-300 ${
              visibleState === 'SPEAKING' ? 'h-14' : visibleState === 'LISTENING' ? 'h-9' : 'h-6'
            }`}
          />
          <span
            className={`w-0.5 rounded-full bg-blue-500/70 transition-all duration-300 ${
              visibleState === 'SPEAKING' ? 'h-11' : visibleState === 'LISTENING' ? 'h-7' : 'h-4'
            }`}
          />
          <span
            className={`w-0.5 rounded-full bg-sky-400/80 transition-all duration-300 ${
              visibleState === 'SPEAKING' ? 'h-8' : visibleState === 'LISTENING' ? 'h-5' : 'h-3'
            }`}
          />
        </div>

        {/* Circular Video Avatar Frame */}
        <div
          className={`relative ${
            compact ? 'w-32 h-40' : 'w-36 h-44'
          } rounded-2xl overflow-hidden p-0.5 bg-gradient-to-b from-blue-400 via-cyan-300 to-indigo-400 shadow-[0_4px_18px_rgba(37,99,235,0.18)]`}
        >
          <div className="w-full h-full rounded-full overflow-hidden bg-slate-900">
            <NovaVideo
              ref={videoRef}
              muted={!isAudioUnmuted || !isSpeakerOn}
              aria-label="Nova Executive AI Avatar"
              className={`w-full h-full object-cover object-[50%_28%] transition-transform duration-500 ${
                visibleState === 'SPEAKING'
                  ? 'scale-103'
                  : visibleState === 'LISTENING'
                  ? 'scale-102'
                  : 'scale-100 hover:scale-102'
              }`}
            />
          </div>

          {/* Thinking overlay badge */}
          {visibleState === 'THINKING' && (
            <div className="absolute inset-0 bg-blue-900/25 backdrop-blur-[1px] flex items-center justify-center pointer-events-none">
              <span className="w-2.5 h-2.5 rounded-full bg-white animate-ping" />
            </div>
          )}
        </div>
      </div>

      {/* State Badge & Video Audio Controls */}
      <div className="mt-1 flex items-center gap-1.5">
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white border border-slate-200/90 shadow-2xs text-[11px] font-semibold text-slate-700">
          <span className="relative flex h-2 w-2">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                visibleState === 'SPEAKING'
                  ? 'bg-blue-400'
                  : visibleState === 'LISTENING'
                  ? 'bg-cyan-400'
                  : visibleState === 'THINKING'
                  ? 'bg-indigo-400'
                  : 'bg-emerald-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                visibleState === 'SPEAKING'
                  ? 'bg-blue-600'
                  : visibleState === 'LISTENING'
                  ? 'bg-cyan-500'
                  : visibleState === 'THINKING'
                  ? 'bg-indigo-600'
                  : 'bg-emerald-500'
              }`}
            />
          </span>
          <span className="font-bold text-slate-800">
            STATE: {visibleState}
          </span>
        </div>

        <button
          type="button"
          onClick={handleToggleAudio}
          title={isAudioUnmuted && isSpeakerOn ? 'Mute avatar voice' : 'Unmute avatar voice'}
          className={`p-1.5 rounded-full border text-xs transition-colors cursor-pointer ${
            isAudioUnmuted && isSpeakerOn
              ? 'bg-blue-50 border-blue-200 text-blue-600'
              : 'bg-white border-slate-200 text-slate-500 hover:text-slate-700 hover:bg-slate-50'
          }`}
        >
          {isAudioUnmuted && isSpeakerOn ? (
            <Volume2 className="w-3.5 h-3.5" />
          ) : (
            <VolumeX className="w-3.5 h-3.5" />
          )}
        </button>

        <button
          type="button"
          onClick={handleReplayGreeting}
          title="Replay Nova greeting"
          className="p-1.5 rounded-full border border-slate-200 bg-white text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Operating Authority Subtitle */}
      <div className="text-[10px] text-slate-400 font-semibold mt-1">
        Analyst &amp; Recommender · Authority: Ray
      </div>
    </div>
  );
};
