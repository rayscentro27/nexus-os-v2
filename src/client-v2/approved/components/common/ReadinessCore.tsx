import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { Tooltip } from './Tooltip';
import { StatusBadge } from './StatusBadge';

interface ReadinessCoreProps {
  onContinueJourney?: () => void;
  compact?: boolean;
}

export const ReadinessCore: React.FC<ReadinessCoreProps> = ({
  onContinueJourney,
  compact = false
}) => {
  const { profile, currentLevel, nextLevel, missions, setActiveTab } = usePortal();

  const percentage = Math.round((profile.readinessPoints / profile.readinessTarget) * 100);
  const nextMission = missions.find((m) => !m.completed) || missions[0];

  // SVG circular geometry
  const radius = compact ? 65 : 108;
  const strokeWidth = compact ? 8 : 12;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (circumference * percentage) / 100;

  // Milestone tick angles around perimeter
  const milestoneAngles = [0, 45, 90, 135, 180, 225, 270, 315];

  return (
    <div className={`relative overflow-hidden rounded-2xl border border-teal-200/90 bg-gradient-to-br from-white via-teal-50/20 to-sky-50/30 p-6 lg:p-8 ${compact ? '' : 'shadow-md'}`}>
      {/* Background ambient glow */}
      <div className="absolute -top-24 -left-24 w-80 h-80 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-80 h-80 rounded-full bg-sky-500/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-8 lg:gap-12">
        {/* Giant Circular Readiness Core */}
        <Tooltip
          title="Composite Funding Readiness Index"
          tag={`${percentage}% BANKABLE`}
          tagType="teal"
          position="right"
          content="Multi-pillar institutional underwriting model evaluating tri-bureau guarantor profile (35%), entity legitimacy (30%), cash-flow velocity (20%), and document vault completeness (15%)."
        >
          <div className="relative flex items-center justify-center shrink-0 cursor-help">
          {/* Outer Orbital Rotating Ring */}
          <div className="absolute inset-0 -m-5 lg:-m-7 rounded-full border border-teal-500/30 border-dashed animate-orbital-slow pointer-events-none" />
          <div className="absolute inset-0 -m-10 lg:-m-12 rounded-full border border-sky-500/25 animate-orbital-reverse pointer-events-none hidden sm:block" />

          {/* SVG Multi-Layer Rings */}
          <div className="relative">
            <svg
              className={`${compact ? 'w-44 h-44' : 'w-64 h-64 sm:w-72 sm:h-72'} -rotate-90 transform`}
              viewBox="0 0 260 260"
            >
              <defs>
                <linearGradient id="readinessGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#00D2B4" />
                  <stop offset="60%" stopColor="#0EA5E9" />
                  <stop offset="100%" stopColor="#38BDF8" />
                </linearGradient>
                <filter id="glowFilter" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="6" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Perimeter Milestones Ticks */}
              {milestoneAngles.map((angle, idx) => {
                const rad = (angle * Math.PI) / 180;
                const cx = 130 + 124 * Math.cos(rad);
                const cy = 130 + 124 * Math.sin(rad);
                const isPassed = (angle / 360) * 100 <= percentage;
                return (
                  <circle
                    key={idx}
                    cx={cx}
                    cy={cy}
                    r={isPassed ? 3.5 : 2}
                    fill={isPassed ? '#00D2B4' : '#CBD5E1'}
                    opacity={isPassed ? 1 : 0.8}
                  />
                );
              })}

              {/* Inactive Track Ring */}
              <circle
                cx="130"
                cy="130"
                r={radius}
                className="stroke-slate-200"
                strokeWidth={strokeWidth}
                fill="none"
              />

              {/* Active Animated Progress Arc */}
              <circle
                cx="130"
                cy="130"
                r={radius}
                stroke="url(#readinessGradient)"
                strokeWidth={strokeWidth}
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="none"
                style={{
                  transition: 'stroke-dashoffset 1.4s cubic-bezier(0.16, 1, 0.3, 1)'
                }}
                filter="url(#glowFilter)"
              />

              {/* Inner Decorative Ring */}
              <circle
                cx="130"
                cy="130"
                r={radius - 18}
                stroke="#E2E8F0"
                strokeWidth="1.5"
                strokeDasharray="4 6"
                fill="none"
              />
            </svg>

            {/* Core Center Display */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4">
              <span className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 tabular-nums">
                {percentage}%
              </span>
              <span className="mt-1 text-[11px] sm:text-xs font-bold tracking-wider text-teal-700 uppercase">
                Funding Readiness
              </span>
              <div className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-600">
                <span className="font-mono tabular-nums text-slate-900 font-semibold">{profile.readinessPoints}</span>
                <span>/</span>
                <span className="font-mono tabular-nums text-slate-500">{profile.readinessTarget} pts</span>
              </div>
            </div>
          </div>
        </div>
      </Tooltip>

        {/* Hero Mission Control & Progression Details */}
        <div className="flex-1 w-full flex flex-col justify-between">
          <div>
            {/* Header info without cheap badges */}
            <div className="flex items-center gap-2 text-xs text-slate-500 tracking-wide uppercase">
              <span className="text-teal-700 font-bold">GoClear Sovereign Velocity</span>
              <span aria-hidden="true">·</span>
              <span>14-Day Active Progression</span>
              <span aria-hidden="true">·</span>
              <span className="text-slate-700 font-medium">Target $250k Facility</span>
            </div>

            <h1 className="mt-2 text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-slate-900">
              Institutional Funding Readiness
            </h1>
            <p className="mt-2 text-sm sm:text-base text-slate-600 max-w-xl leading-relaxed">
              {profile.companyName} is currently tracking in the{' '}
              <strong className="text-teal-700 font-semibold">{currentLevel.name}</strong> tier. Your legal entity and personal credit are certified; clearing 90-day cash flow verification will advance your file into the Tier-1 Bankable category.
            </p>
          </div>

          {/* Next Mission Spotlight Card */}
          <Tooltip
            title="Strategic Capital Directive"
            tag={`+${nextMission.points} PTS`}
            tagType="amber"
            position="top"
            content={`Algorithmic recommendation: ${nextMission.description} Resolving this requirement clears the top institutional underwriting blocker.`}
            className="w-full mt-6"
          >
            <div className="w-full rounded-xl border border-teal-200/90 bg-white/95 p-4 sm:p-5 shadow-xs hover:border-teal-400/80 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-xs font-semibold text-amber-800">
                    <StatusBadge
                      status={nextMission.status || (nextMission.completed ? 'Completed' : 'In Progress')}
                      variant="light"
                      size="sm"
                    />
                    <span>NEXT MISSION</span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono tabular-nums">+{nextMission.points} READINESS POINTS</span>
                    <span aria-hidden="true">·</span>
                    <span className="text-slate-500">{nextMission.timeEstimate}</span>
                  </div>
                  <h4 className="mt-1 text-base sm:text-lg font-semibold text-slate-900 truncate">
                    {nextMission.title}
                  </h4>
                  <p className="mt-1 text-xs sm:text-sm text-slate-600 line-clamp-2">
                    {nextMission.description}
                  </p>
                </div>

                <button
                  onClick={() => {
                    if (onContinueJourney) {
                      onContinueJourney();
                    } else {
                      setActiveTab(nextMission.targetTab);
                    }
                  }}
                  className="shrink-0 px-4 py-2.5 bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white font-bold text-xs sm:text-sm rounded-lg transition-all shadow-md hover:shadow-teal-500/20 active:scale-95 whitespace-nowrap cursor-pointer"
                >
                  CONTINUE JOURNEY →
                </button>
              </div>
            </div>
          </Tooltip>

          {/* Current Level vs Next Level Stepper */}
          <div className="mt-6 pt-5 border-t border-slate-200/90 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
            <div>
              <span className="text-slate-500 uppercase tracking-wider text-[10px]">CURRENT LEVEL</span>
              <div className="mt-0.5 text-sm sm:text-base font-bold text-teal-700">
                {currentLevel.name}
              </div>
            </div>

            <div className="hidden sm:flex items-center gap-2 text-slate-400">
              <div className="w-16 h-0.5 bg-gradient-to-r from-teal-400/50 to-sky-400/50" />
              <span>→</span>
            </div>

            <div>
              <span className="text-slate-500 uppercase tracking-wider text-[10px]">NEXT TIER UNLOCK</span>
              <div className="mt-0.5 text-sm sm:text-base font-bold text-slate-900">
                {nextLevel ? nextLevel.name : 'Apex Ready'}
              </div>
            </div>

            <div className="text-right">
              <span className="text-slate-500 uppercase tracking-wider text-[10px]">POINTS TO NEXT TIER</span>
              <div className="mt-0.5 font-mono tabular-nums text-sm sm:text-base font-bold text-amber-700">
                {nextLevel ? `${nextLevel.minPoints - profile.readinessPoints} pts needed` : 'Max Tier'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
