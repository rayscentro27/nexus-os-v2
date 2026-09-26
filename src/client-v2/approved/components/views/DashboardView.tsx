import React from 'react';
import { usePortal } from '../../context/PortalContext';
import { GiantIcon } from '../common/GiantIcon';
import { TabType, Mission } from '../../types/portal';
import { Tooltip } from '../common/Tooltip';
import { StatusBadge } from '../common/StatusBadge';

export const DashboardView: React.FC = () => {
  const {
    missions,
    completeMission,
    achievements,
    setActiveTab,
    profile,
    currentLevel,
    nextLevel,
    journeyNodes,
    openClydeWithPrompt,
    facts,
    liveMode
  } = usePortal();

  const percentage = Math.round((profile.readinessPoints / profile.readinessTarget) * 100);
  const nextMission = missions.find((m) => !m.completed) || missions[0];

  // Context-aware financial explanations for mission cards
  const getMissionTooltip = (mission: Mission) => {
    switch (mission.id) {
      case 'm1':
      case 'm-1':
        return {
          title: 'Cash-Flow Verification Audit',
          tag: '90-DAY STATEMENTS',
          tagType: 'amber' as const,
          content:
            'Tier 1 commercial lenders require trailing 90-day consecutive statements with zero NSFs to verify average daily balance exceeds $15,000 and ensure positive debt-service capacity.'
        };
      case 'm2':
      case 'm-2':
        return {
          title: 'Guarantor Credit Optimization',
          tag: 'UTILIZATION < 10%',
          tagType: 'teal' as const,
          content:
            `Revolving utilization is ${facts.utilizationPercent || 'not available'}%. The target is ${facts.utilizationTargetPercent}%; Nexus will show the client-scoped balance state when persisted.`
        };
      case 'm3':
      case 'm-3':
        return {
          title: 'Entity Public Records Match',
          tag: '411 & SOS REGISTRY',
          tagType: 'teal' as const,
          content:
            'Ensuring public directory matches across Dun & Bradstreet, Google Business, and Delaware Division of Corporations records prevents automated underwriting fraud rejections.'
        };
      case 'm4':
      case 'm-4':
        return {
          title: 'Corporate Entity Separation',
          tag: 'DELAWARE LLC',
          tagType: 'emerald' as const,
          content:
            'Good standing certificate and clean SOS registration confirm the corporate veil is legally airtight, shielding guarantor personal assets from corporate debt liability.'
        };
      default:
        return {
          title: `${mission.category} Directive`,
          tag: `+${mission.points} PTS`,
          tagType: 'teal' as const,
          content: `${mission.description} Directly advances underwriter scorecard metrics for institutional financing.`
        };
    }
  };

  // SVG Geometry for compact circular readiness core
  const radius = 48;
  const strokeWidth = 8;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (circumference * percentage) / 100;

  return (
    <div className="h-full flex flex-col gap-2.5 overflow-hidden animate-fade-in select-none">
      {/* 1. Consolidated Executive Command Header Ribbon (Clean Light Accent) */}
      <div className="relative overflow-hidden rounded-xl border border-teal-200/90 bg-gradient-to-r from-white via-teal-50/30 to-sky-50/20 p-3 shadow-sm shrink-0">
        <div className="absolute top-0 right-1/4 w-72 h-32 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col xl:flex-row items-center justify-between gap-3 relative z-10">
          {/* Left: Compact Circular Readiness Ring & Tier */}
          <div className="flex items-center gap-3.5 shrink-0">
            <Tooltip
              title="Composite Readiness Index"
              tag={`${percentage}% BANKABLE`}
              tagType="teal"
              position="bottom"
              content="Weighted institutional index combining Personal Credit (35%), Entity Legitimacy (30%), Cash-Flow Velocity (20%), and Document Vault Integrity (15%) against commercial lender underwriting models."
            >
              <div className="relative w-24 h-24 flex items-center justify-center shrink-0 cursor-help">
                <svg className="w-24 h-24 -rotate-90 transform" viewBox="0 0 120 120">
                  <defs>
                    <linearGradient id="readinessGradCompact" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#00D2B4" />
                      <stop offset="100%" stopColor="#38BDF8" />
                    </linearGradient>
                  </defs>
                  <circle
                    cx="60"
                    cy="60"
                    r={radius}
                    className="stroke-slate-200"
                    strokeWidth={strokeWidth}
                    fill="none"
                  />
                  <circle
                    cx="60"
                    cy="60"
                    r={radius}
                    stroke="url(#readinessGradCompact)"
                    strokeWidth={strokeWidth}
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    fill="none"
                    style={{ transition: 'stroke-dashoffset 1s ease' }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-xl font-black text-slate-900 tabular-nums leading-none">
                    {percentage}%
                  </span>
                  <span className="text-[9px] font-bold uppercase tracking-wider text-teal-700 mt-0.5 leading-none">
                    Readiness
                  </span>
                </div>
              </div>
            </Tooltip>

            <Tooltip
              title="Institutional Lending Tier"
              tag={currentLevel.name}
              tagType="teal"
              position="bottom"
              content={`${profile.companyName} is currently ranked in ${currentLevel.name} (${profile.readinessPoints} of ${profile.readinessTarget} points). Funding outcomes remain subject to review.`}
            >
              <div className="cursor-help">
                <div className="flex items-center gap-1.5 text-[10px] text-teal-700 font-bold uppercase tracking-wider">
                  <span>{currentLevel.name}</span>
                  <span className="text-slate-300">·</span>
                  <span className="font-mono text-slate-600">{profile.readinessPoints} / {profile.readinessTarget} Pts</span>
                </div>
                <h1 className="text-base font-bold text-slate-900 tracking-tight">
                  Funding Readiness Command
                </h1>
                <div className="mt-0.5 flex items-center gap-2 text-[11px] text-slate-600">
                  <span>Next Tier: <strong className="text-slate-900">{nextLevel ? nextLevel.name : 'Completed'}</strong></span>
                  <span className="text-amber-700 font-mono text-[10px] font-semibold">
                    {nextLevel ? `(${nextLevel.minPoints - profile.readinessPoints} pts needed)` : ''}
                  </span>
                </div>
              </div>
            </Tooltip>
          </div>

          {/* Center: Integrated 7-Step Financial Readiness Journey */}
          <div className="flex-1 w-full max-w-2xl px-2">
            <div className="flex items-center justify-between mb-1 text-[10px]">
              <span className="text-teal-300 font-bold uppercase tracking-wider">
                Financial Readiness Journey
              </span>
              <span className="text-slate-400 font-mono">
                {journeyNodes.filter((n) => n.status === 'completed').length} of {journeyNodes.length} Verified
              </span>
            </div>

            <div className="grid grid-cols-7 gap-1.5 relative">
              {journeyNodes.map((node, idx) => {
                const isCompleted = node.status === 'completed';
                const isInProgress = node.status === 'in-progress';
                return (
                  <Tooltip
                    key={node.id}
                    title={`Stage ${idx + 1}: ${node.label}`}
                    tag={isCompleted ? 'VERIFIED' : isInProgress ? 'IN PROGRESS' : 'PENDING'}
                    tagType={isCompleted ? 'emerald' : isInProgress ? 'teal' : 'amber'}
                    position="bottom"
                    content={
                      node.id === 'entity'
                        ? 'Validates registered Delaware LLC status, corporate veil, and clean SOS filing.'
                        : node.id === 'credit'
                        ? 'Guarantor FICO score benchmarked above 740 to qualify for prime interest brackets.'
                        : node.id === 'banking'
                        ? 'Dedicated commercial operating account with daily balances exceeding $15k.'
                        : node.id === 'financials'
                        ? 'Trailing 90-day cash flow verifying debt-service coverage ratio (DSCR > 1.25x).'
                        : node.id === 'compliance'
                        ? 'EIN, operating agreements, and clean commercial bureau profile verification.'
                        : node.id === 'underwriting'
                        ? 'Automated underwriting algorithm clearance against lender scorecard.'
                        : 'Final term sheet issuance and multi-facility capital disbursement.'
                    }
                  >
                    <button
                      onClick={() => setActiveTab(node.tab as TabType)}
                      className={`w-full group p-1 rounded-lg border text-center transition-all cursor-pointer flex flex-col items-center ${
                        isCompleted
                          ? 'border-teal-400 bg-teal-50 hover:bg-teal-100/70'
                          : isInProgress
                          ? 'border-sky-400 bg-sky-50 ring-1 ring-sky-300'
                          : 'border-slate-200 bg-white hover:bg-slate-50'
                      }`}
                    >
                      <div
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold ${
                          isCompleted
                            ? 'bg-teal-100 text-teal-800'
                            : isInProgress
                            ? 'bg-sky-100 text-sky-800 animate-pulse'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {isCompleted ? '✓' : `0${idx + 1}`}
                      </div>
                      <span className="text-[10px] font-semibold text-slate-700 truncate w-full mt-0.5 leading-tight group-hover:text-teal-700">
                        {node.label}
                      </span>
                    </button>
                  </Tooltip>
                );
              })}
            </div>
          </div>

          {/* Right: Next Mission Spotlight CTA */}
          <Tooltip
            title="Next Strategic Milestone"
            tag={`+${nextMission.points} PTS`}
            tagType="amber"
            position="bottom"
            content={`Priority underwriting directive: ${nextMission.description} Completing this action clears the top commercial loan blocker.`}
          >
            <div className="shrink-0 flex items-center gap-3 bg-white border border-teal-200/90 rounded-xl p-2.5 shadow-xs">
              <div className="text-left min-w-0">
                <div className="flex items-center gap-1.5 text-[9px] font-bold text-amber-800 uppercase tracking-wider mb-1">
                  <StatusBadge
                    status={nextMission.status || (nextMission.completed ? 'Completed' : 'In Progress')}
                    variant="light"
                    size="sm"
                  />
                  <span className="font-mono">+{nextMission.points} PTS</span>
                  <span className="text-slate-300">·</span>
                  <span className="text-[10px] text-slate-500 font-medium">{nextMission.timeEstimate}</span>
                </div>
                <div className="text-xs font-bold text-slate-900 truncate max-w-[170px]">
                  {nextMission.title}
                </div>
              </div>

              <button
                onClick={() => setActiveTab(nextMission.targetTab)}
                className="px-3 py-2 bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white font-bold text-xs rounded-lg transition-all shadow-sm active:scale-95 whitespace-nowrap cursor-pointer"
              >
                Continue →
              </button>
            </div>
          </Tooltip>
        </div>
      </div>

      {/* 2. Balanced Consolidated Cockpit Grid (Auto-filling & Fitted to Viewport without Scrolling) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-3 overflow-hidden">
        {/* Left Column (8 cols): Active Readiness Missions & Underwriting Blockers */}
        <div className="lg:col-span-8 flex flex-col gap-3 min-h-0 overflow-hidden">
          {/* Panel 1: Active Missions Queue (Auto-filling 2x2 Grid) */}
          <div className="flex flex-col rounded-xl border border-slate-200/90 bg-slate-50/80 p-3.5 shadow-xs overflow-hidden shrink-0">
            <div className="flex items-center justify-between pb-2.5 border-b border-slate-200/80 shrink-0">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-teal-500 shadow-xs shadow-teal-500/50" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Readiness Missions
                </h2>
                <span className="text-[10px] text-slate-500 font-medium hidden sm:inline">
                  · Hover cards for underwriter context & impact
                </span>
              </div>
              <span className="text-[11px] font-mono text-teal-800 font-bold bg-white px-2 py-0.5 rounded-md border border-slate-200 shadow-xs">
                {missions.filter((m) => m.completed).length} / {missions.length} Done
              </span>
            </div>

            {/* Auto-filling Missions Grid with Context-Aware Tooltips & Prominent Visual Indicator Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2.5">
              {missions.map((mission) => {
                const isCompleted = mission.completed;
                const isBlocked = mission.status === 'Blocked' && !isCompleted;
                const statusToDisplay = isCompleted ? 'Completed' : isBlocked ? 'Blocked' : 'In Progress';
                const tip = getMissionTooltip(mission);

                return (
                  <Tooltip
                    key={mission.id}
                    title={tip.title}
                    tag={tip.tag}
                    tagType={tip.tagType}
                    position="top"
                    content={tip.content}
                    className="flex flex-col"
                  >
                    <div
                      className={`p-2.5 rounded-xl border transition-all flex flex-col justify-between h-full ${
                        isCompleted
                          ? 'border-emerald-200/90 bg-emerald-50/20 text-slate-900 shadow-xs'
                          : isBlocked
                          ? 'border-rose-200/90 bg-rose-50/15 hover:border-rose-300 hover:shadow-xs text-slate-900 shadow-xs'
                          : 'border-slate-200 bg-white hover:border-teal-400 hover:shadow-xs text-slate-900 shadow-xs'
                      }`}
                    >
                      <div>
                        {/* Top Metadata Line with Status Indicator Badge */}
                        <div className="flex items-center justify-between gap-1.5 mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <StatusBadge status={statusToDisplay} size="sm" />
                            <span className="font-bold text-teal-800 uppercase bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200/70 font-mono text-[9px]">
                              {mission.category}
                            </span>
                          </div>
                          <span className="font-mono text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 font-bold text-[9px]">
                            +{mission.points} Pts
                          </span>
                        </div>

                        <div className="flex items-start gap-2 min-w-0">
                          <div
                            className={`p-1.5 rounded-lg border shrink-0 shadow-xs mt-0.5 ${
                              isCompleted
                                ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                                : isBlocked
                                ? 'bg-rose-50 border-rose-200 text-rose-600'
                                : 'bg-slate-50 border-slate-200 text-teal-600'
                            }`}
                          >
                            <GiantIcon
                              type={
                                mission.category === 'Credit'
                                  ? 'gauge'
                                  : mission.category === 'Documents'
                                  ? 'vault'
                                  : mission.category === 'Bankability'
                                  ? 'bank-column'
                                  : 'building'
                              }
                              size="sm"
                              glow={false}
                            />
                          </div>
                          <div className="min-w-0 flex-1">
                            <h3 className="text-xs font-bold text-slate-900 truncate leading-tight">
                              {mission.title}
                            </h3>
                            <p className="text-[11px] text-slate-600 line-clamp-1 mt-0.5 leading-snug">
                              {mission.description}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between gap-2">
                        <button
                          onClick={() => setActiveTab(mission.targetTab)}
                          className="text-[10px] text-slate-500 hover:text-teal-700 font-semibold cursor-pointer bg-slate-50 hover:bg-slate-100 px-2 py-0.5 rounded transition-colors"
                        >
                          Open View →
                        </button>

                        {isCompleted ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 font-mono bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            ✓ COMPLETED
                          </span>
                        ) : isBlocked ? (
                          <button
                            onClick={() => setActiveTab(mission.targetTab)}
                            className="px-2.5 py-0.5 rounded-md bg-rose-600 hover:bg-rose-700 text-white font-bold text-[10px] transition-all shadow-xs cursor-pointer whitespace-nowrap active:scale-95"
                          >
                            Resolve Prerequisite →
                          </button>
                        ) : (
                          <button
                            disabled={liveMode}
                            onClick={() => completeMission(mission.id)}
                            title={liveMode ? 'Completion is recorded through the governed client workflow.' : undefined}
                            className="px-2.5 py-0.5 rounded-md bg-teal-600 hover:bg-teal-700 text-white font-bold text-[10px] transition-all cursor-pointer whitespace-nowrap active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Complete (+{mission.points} Pts)
                          </button>
                        )}
                      </div>
                    </div>
                  </Tooltip>
                );
              })}
            </div>
          </div>

          {/* Panel 2: Underwriting Blockers & Health Alerts (Auto-filling 3-Column Cockpit) */}
          <div className="flex flex-col rounded-xl border border-slate-200/90 bg-slate-50/80 p-3.5 shadow-xs overflow-hidden flex-1 min-h-0">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200/80 shrink-0">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse shadow-xs shadow-rose-500/50" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Underwriting Blockers & Intelligence
                </h2>
              </div>
              <span className="text-[10px] font-mono text-rose-800 font-bold bg-white px-2 py-0.5 rounded-md border border-rose-200 shadow-xs">
                Action Required · 2 Signals
              </span>
            </div>

            {/* 3-Column Auto-filling Cards Layout with Context-Aware Tooltips */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-2.5 flex-1 min-h-0">
              {/* Blocker 1: Critical Cash Flow Hold */}
              <Tooltip
                title="Debt-Service Coverage Metric"
                tag="CRITICAL HOLD"
                tagType="rose"
                position="top"
                content="Commercial lenders require 90-day verified statements to confirm operating revenue covers proposed credit line servicing costs by at least 1.25x. Uploading statements releases this hold immediately."
                className="flex flex-col"
              >
                <div className="p-3 rounded-xl border border-rose-200/90 bg-white shadow-xs hover:border-rose-300 transition-all flex flex-col justify-between h-full">
                  <div>
                    <div className="flex items-center justify-between">
                      <StatusBadge status="Blocked" label="Blocked · Critical Hold" size="sm" />
                      <button
                        onClick={() => setActiveTab('documents')}
                        className="text-[10px] font-bold text-teal-700 hover:text-teal-800 hover:underline cursor-pointer bg-slate-50 hover:bg-slate-100 px-1.5 py-0.5 rounded transition-colors"
                      >
                        Vault →
                      </button>
                    </div>
                    <h3 className="text-xs font-bold text-slate-900 mt-1.5 leading-snug">
                      Unverified 90-Day Bank Statements
                    </h3>
                    <p className="text-[11px] text-slate-600 mt-1 leading-snug line-clamp-2">
                      Lenders require cash flow records before underwriting unsecured facilities.
                    </p>
                  </div>
                  <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-rose-700 font-medium">
                    <span>Priority 1 Blocker</span>
                    <span className="font-mono font-bold">+8 Pts on Upload</span>
                  </div>
                </div>
              </Tooltip>

              {/* Blocker 2: Revolving Utilization */}
              <Tooltip
                title="Revolving Utilization Threshold"
                tag="UNDERWRITING FLAG"
                tagType="amber"
                position="top"
                content="Revolving utilization above 10% signals debt dependence to Tier 1 credit scoring models. Reducing to under 10% removes secondary risk markups and preserves prime rates."
                className="flex flex-col"
              >
                <div className="p-3 rounded-xl border border-amber-200/90 bg-white shadow-xs hover:border-amber-300 transition-all flex flex-col justify-between h-full">
                  <div>
                    <div className="flex items-center justify-between">
                      <StatusBadge status="Blocked" label="Blocked · Flag" size="sm" />
                      <button
                        onClick={() => setActiveTab('credit-utilization')}
                        className="text-[10px] font-bold text-teal-700 hover:text-teal-800 hover:underline cursor-pointer bg-slate-50 hover:bg-slate-100 px-1.5 py-0.5 rounded transition-colors"
                      >
                        Sim →
                      </button>
                    </div>
                    <h3 className="text-xs font-bold text-slate-900 mt-1.5 leading-snug">
                      Revolving Utilization at {facts.utilizationPercent ? `${facts.utilizationPercent}%` : 'Not available'}
                    </h3>
                    <p className="text-[11px] text-slate-600 mt-1 leading-snug line-clamp-2">
                      {facts.utilizationPercent ? `Target utilization is below ${facts.utilizationTargetPercent}%.` : 'No live utilization balance was returned.'}
                    </p>
                  </div>
                  <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-amber-700 font-medium">
                    <span>Target: &lt;10%</span>
                    <span className="font-mono font-bold">+$4,050 Paydown</span>
                  </div>
                </div>
              </Tooltip>

              {/* Blocker 3: Clyde Copilot Insight (Clean Light Accent) */}
              <Tooltip
                title="Predictive Risk Scorecard"
                tag="AI UNDERWRITING"
                tagType="teal"
                position="top"
                content="Automated lender simulation projects an immediate upgrade from Tier 3 to Tier 4 Prime once 90-day statements and revolving paydown are finalized."
                className="flex flex-col"
              >
                <div className="p-3 rounded-xl border border-teal-200/80 bg-gradient-to-br from-teal-50/50 to-white shadow-xs text-slate-900 flex flex-col justify-between h-full">
                  <div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-teal-800 text-[10px] font-bold uppercase tracking-wider">
                        <span>⚡ Clyde Insight</span>
                      </div>
                      <button
                        onClick={() => openClydeWithPrompt("What happens to my funding options once my bank statements are verified?")}
                        className="text-[10px] text-teal-700 font-bold hover:underline cursor-pointer bg-teal-100/70 border border-teal-200/80 px-2 py-0.5 rounded"
                      >
                        Ask →
                      </button>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1.5 leading-snug line-clamp-3">
                      {profile.companyName} is currently at {currentLevel.name}. {facts.bankabilityScore ? `Bankability score: ${facts.bankabilityScore}/100.` : 'Bankability score is not available.'}
                    </p>
                  </div>
                  <div className="mt-2 pt-1.5 border-t border-teal-100 flex items-center justify-between text-[10px] text-teal-800 font-mono">
                    <span>Underwriter Score</span>
                    <span className="font-bold">+12 Pts Potential</span>
                  </div>
                </div>
              </Tooltip>
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): Momentum, Achievements & Fast Underwriter Audit */}
        <div className="lg:col-span-4 flex flex-col gap-3 min-h-0 overflow-hidden">
          {/* Panel 3: Momentum & Achievements (Auto-filling Grid) */}
          <div className="flex flex-col rounded-xl border border-slate-200/90 bg-slate-50/80 p-3.5 shadow-xs overflow-hidden flex-1 min-h-0">
            <div className="flex items-center justify-between pb-2.5 border-b border-slate-200/80 shrink-0">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-xs shadow-emerald-500/50" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Momentum & Milestones
                </h2>
              </div>
              <span className="text-[10px] font-mono text-emerald-800 font-bold bg-white px-2 py-0.5 rounded-md border border-emerald-200 shadow-xs">
                14-Day Streak 🔥
              </span>
            </div>

            {/* Auto-filling Achievements Grid with Context-Aware Tooltips */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-2 pt-2.5">
              {achievements.map((ach) => {
                const getAchTip = (id: string, title: string) => {
                  switch (id) {
                    case 'ach-1':
                      return {
                        title: 'Zero Derogatory Benchmark',
                        tag: 'BUREAU AUDIT',
                        content: 'Zero late payments or collections across Experian, TransUnion, and Equifax in trailing 24 months establishes prime borrower status.'
                      };
                    case 'ach-2':
                      return {
                        title: 'Corporate Veil Verification',
                        tag: 'LEGAL ENTITY',
                        content: 'Legally distinct Delaware LLC registration and EIN segregation provide independent commercial credit line architecture.'
                      };
                    case 'ach-3':
                      return {
                        title: 'Real-Time Ledger Telemetry',
                        tag: 'PLAID VERIFIED',
                        content: 'Direct bank API synchronization eliminates manual statement fraud review and expedites lender pre-approvals by up to 5 days.'
                      };
                    case 'ach-4':
                      return {
                        title: 'Optimal Utilization Zone',
                        tag: 'PRIME TIER',
                        content: 'Maintaining revolving credit card utilization below 10% secures top-bracket FICO algorithm scoring points.'
                      };
                    default:
                      return {
                        title,
                        tag: 'VERIFIED',
                        content: 'Underwriter milestone validated for institutional capital deployment.'
                      };
                  }
                };
                const achTip = getAchTip(ach.id, ach.title);

                return (
                  <Tooltip
                    key={ach.id}
                    title={achTip.title}
                    tag={achTip.tag}
                    tagType="emerald"
                    position="top"
                    content={achTip.content}
                    className="flex flex-col"
                  >
                    <div className="flex items-center gap-2.5 p-2 rounded-xl border border-slate-200 bg-white shadow-xs hover:border-slate-300 transition-all min-w-0 h-full">
                      <div className="w-7 h-7 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 text-teal-700 font-mono text-xs font-bold">
                        ✓
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-bold text-slate-900 truncate">
                          {ach.title}
                        </div>
                        <div className="text-[10px] text-slate-500 truncate mt-0.5">
                          {ach.description}
                        </div>
                      </div>
                    </div>
                  </Tooltip>
                );
              })}
            </div>

            {/* Fast Underwriter Review Callout (Clean Light Accent) */}
            <div className="mt-auto pt-3 shrink-0">
              <Tooltip
                title="Credit Committee Evaluation"
                tag="FAST TRACK"
                tagType="teal"
                position="top"
                content="Direct submission package compiles tri-bureau guarantor profile, Delaware entity documentation, and banking telemetry for expedited underwriting sign-off."
                className="w-full flex flex-col"
              >
                <div className="p-3 rounded-xl border border-teal-200/90 bg-gradient-to-br from-teal-50/60 via-white to-sky-50/40 text-slate-900 shadow-xs w-full">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider">
                      Underwriter Review
                    </span>
                    <span className="text-[10px] font-mono text-teal-800 bg-teal-100/80 border border-teal-200 px-2 py-0.5 rounded font-semibold">
                      {profile.readinessPoints} Pts Ready
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1.5 leading-snug">
                    Your dossier for {profile.companyName} reflects the live readiness data returned for this client.
                  </p>
                  <div className="mt-2.5 pt-2 border-t border-teal-100 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span>{profile.entityType}</span>
                    <span className="text-teal-700 font-bold">{facts.fundingTargetLabel}</span>
                  </div>
                  <button
                    onClick={() => setActiveTab('request-review')}
                    className="mt-2.5 w-full py-2 rounded-lg bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white font-bold text-xs transition-all shadow-xs active:scale-95 cursor-pointer text-center"
                  >
                    Submit Dossier to Committee →
                  </button>
                </div>
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
