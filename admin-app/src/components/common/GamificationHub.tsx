import React, { useState } from 'react';
import {
  Trophy,
  CheckCircle2,
  Sparkles,
  Flame,
  Award,
  ChevronRight,
  Zap,
  ArrowUpRight
} from 'lucide-react';
import { useNexus } from '../../context/NexusContext';

interface Quest {
  id: string;
  title: string;
  category: string;
  xpReward: number;
  progress: number;
  maxProgress: number;
  pageTarget: string;
}

const DAILY_QUESTS: Quest[] = [
  {
    id: 'quest-approvals',
    title: 'Review 3 Pending Approvals',
    category: 'Approvals',
    xpReward: 150,
    progress: 2,
    maxProgress: 3,
    pageTarget: 'approvals'
  },
  {
    id: 'quest-research',
    title: 'Inspect New FinTech Research Brief',
    category: 'Research',
    xpReward: 100,
    progress: 0,
    maxProgress: 1,
    pageTarget: 'research'
  },
  {
    id: 'quest-nova',
    title: 'Ask Nova a Voice or Strategy Question',
    category: 'Nova AI',
    xpReward: 80,
    progress: 1,
    maxProgress: 1,
    pageTarget: 'command-center'
  }
];

export const GamificationHub: React.FC = () => {
  const { xp, level, streakDays, completedQuests, completeQuest, setCurrentPage } = useNexus();
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const handleClaimQuest = (quest: Quest, e: React.MouseEvent) => {
    e.stopPropagation();
    if (completedQuests.includes(quest.id)) return;
    completeQuest(quest.id, quest.xpReward);
    setToastMessage(`+${quest.xpReward} XP Earned! "${quest.title}" Completed!`);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Next level threshold calculation
  const currentLevelFloor = (level - 1) * 400;
  const nextLevelCeil = level * 400;
  const progressPercent = Math.min(100, Math.max(0, Math.round(((xp - currentLevelFloor) / 400) * 100)));

  return (
    <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-600 rounded-3xl p-5 sm:p-6 text-white shadow-[0_10px_30px_rgba(37,99,235,0.18)] relative overflow-hidden my-6">
      {/* Background decorative glows */}
      <div className="absolute -right-16 -top-16 w-64 h-64 bg-cyan-400/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -left-16 -bottom-16 w-64 h-64 bg-indigo-400/20 rounded-full blur-3xl pointer-events-none" />

      {/* Toast popup */}
      {toastMessage && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 bg-white text-slate-900 px-4 py-2 rounded-2xl shadow-xl flex items-center gap-2 text-xs font-bold animate-pop border border-blue-200">
          <Sparkles className="w-4 h-4 text-amber-500 fill-amber-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-6">
        {/* Left: Operator Level, Avatar Rank & XP Gauge */}
        <div className="flex items-center gap-4.5 sm:gap-5">
          {/* Big Gamified Level Crest */}
          <div className="relative shrink-0">
            <div className="w-16 h-16 sm:w-18 sm:h-18 rounded-2xl bg-white/10 backdrop-blur-md border border-white/30 flex flex-col items-center justify-center shadow-lg relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <Award className="w-6 h-6 text-amber-300 drop-shadow-sm stroke-[2.2]" />
              <span className="text-[12px] sm:text-xs font-black tracking-tight text-white mt-0.5">
                LVL {level}
              </span>
            </div>
            {/* Streak flame badge */}
            <div className="absolute -bottom-1.5 -right-1.5 px-2 py-0.5 rounded-full bg-gradient-to-r from-amber-400 to-orange-500 text-white font-black text-[10px] flex items-center gap-0.5 shadow-sm border border-amber-300">
              <Flame className="w-3 h-3 fill-white" />
              <span>{streakDays}d</span>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-extrabold uppercase tracking-wider text-cyan-200 bg-white/15 px-2.5 py-0.5 rounded-full border border-white/20">
                Nexus Commander
              </span>
              <span className="text-xs text-white/80 font-medium">Rank Tier 2</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight mt-1 flex items-center gap-2">
              Daily Operational Quests
              <Sparkles className="w-5 h-5 text-amber-300" />
            </h2>
            {/* XP Bar */}
            <div className="mt-2.5 flex items-center gap-3">
              <div className="w-40 sm:w-56 h-2.5 bg-white/20 rounded-full overflow-hidden backdrop-blur-xs p-0.5">
                <div
                  className="h-full bg-gradient-to-r from-cyan-300 to-emerald-300 rounded-full transition-all duration-500 shadow-sm"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <span className="text-xs font-bold text-white/95 tabular-nums">
                {xp} <span className="text-white/60 font-medium">/ {nextLevelCeil} XP</span>
              </span>
            </div>
          </div>
        </div>

        {/* Right: Quest Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 flex-1 max-w-3xl">
          {DAILY_QUESTS.map(quest => {
            const isCompleted = completedQuests.includes(quest.id);
            const isReady = quest.progress >= quest.maxProgress;

            return (
              <div
                key={quest.id}
                onClick={() => !isCompleted && setCurrentPage(quest.pageTarget as any)}
                className={`p-3 rounded-2xl border transition-all cursor-pointer backdrop-blur-md relative flex flex-col justify-between ${
                  isCompleted
                    ? 'bg-white/10 border-white/20 opacity-80'
                    : isReady
                    ? 'bg-white/20 border-cyan-300/80 shadow-md hover:bg-white/25 hover:scale-[1.02]'
                    : 'bg-white/15 border-white/25 hover:bg-white/20 hover:border-white/40'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-cyan-200">
                      {quest.category}
                    </span>
                    <span className="text-[11px] font-black text-amber-300 bg-amber-400/20 px-2 py-0.5 rounded-full border border-amber-300/30 flex items-center gap-1">
                      <Zap className="w-2.5 h-2.5 fill-amber-300" />
                      +{quest.xpReward} XP
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-white leading-snug">
                    {quest.title}
                  </h4>
                </div>

                <div className="mt-3 flex items-center justify-between pt-2 border-t border-white/15">
                  <span className="text-[10px] font-semibold text-white/80">
                    {isCompleted ? 'Completed' : `${quest.progress} / ${quest.maxProgress}`}
                  </span>

                  {isCompleted ? (
                    <span className="text-[10px] font-bold text-emerald-300 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Done
                    </span>
                  ) : isReady ? (
                    <button
                      type="button"
                      onClick={(e) => handleClaimQuest(quest, e)}
                      className="px-2.5 py-1 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 text-white font-black text-[10px] shadow-sm hover:scale-105 active:scale-95 transition-all cursor-pointer animate-pop"
                    >
                      Claim XP!
                    </button>
                  ) : (
                    <span className="text-[10px] font-semibold text-white/70 flex items-center gap-0.5 hover:text-white">
                      Go <ArrowUpRight className="w-3 h-3" />
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
