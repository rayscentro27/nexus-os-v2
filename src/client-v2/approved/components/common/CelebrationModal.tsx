import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from './GiantIcon';

export const CelebrationModal: React.FC = () => {
  const { activeCelebration, dismissCelebration } = usePortal();

  if (!activeCelebration) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-teal-300 bg-white p-8 text-center shadow-2xl">
        {/* Glow */}
        <div className="absolute -top-20 -left-20 w-52 h-52 bg-teal-500/15 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -right-20 w-52 h-52 bg-amber-500/15 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center">
          <div className="w-20 h-20 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mb-4">
            <GiantIcon type="rocket" size="lg" glow={false} />
          </div>

          <span className="text-xs font-bold uppercase tracking-wider text-teal-700">
            Readiness Acceleration
          </span>

          <h3 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
            {activeCelebration.title}
          </h3>

          <div className="my-4 px-4 py-2 rounded-xl bg-teal-50 border border-teal-300 font-mono text-xl font-extrabold text-teal-800">
            +{activeCelebration.points} READINESS POINTS
          </div>

          <p className="text-sm text-slate-600 leading-relaxed max-w-xs">
            {activeCelebration.subtitle}
          </p>

          <button
            onClick={dismissCelebration}
            className="mt-6 w-full py-3 px-6 rounded-xl bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white font-bold text-sm transition-all shadow-md active:scale-95 cursor-pointer"
          >
            Claim & Continue Journey
          </button>
        </div>
      </div>
    </div>
  );
};
