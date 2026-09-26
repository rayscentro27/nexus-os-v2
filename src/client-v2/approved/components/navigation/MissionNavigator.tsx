import React, { useState } from 'react';
import { usePortal } from '../../context/PortalContext';
import { TabType } from '../../types/portal';
import { GiantIcon, GiantIconType } from '../common/GiantIcon';

interface NavItem {
  tab: TabType;
  label: string;
  sublabel: string;
  iconType: GiantIconType;
  progress: number;
}

export const MissionNavigator: React.FC = () => {
  const { activeTab, setActiveTab, profile, currentLevel, setIsClydeOpen, missions, facts } = usePortal();
  const [isMoreMenuOpen, setIsMoreMenuOpen] = useState(false);

  const nextMission = missions.find((m) => !m.completed) || missions[0];
  const readinessPercent = Math.round((profile.readinessPoints / profile.readinessTarget) * 100);

  const navItems: NavItem[] = [
    {
      tab: 'dashboard',
      label: 'Command Center',
      sublabel: 'Readiness Core & Missions',
      iconType: 'rocket',
      progress: readinessPercent
    },
    {
      tab: 'credit-profile',
      label: 'Credit Profile',
      sublabel: facts.creditScore ? `${facts.creditScore} Credit score · Live` : 'Credit profile · Awaiting data',
      iconType: 'shield',
      progress: facts.creditScore || 0
    },
    {
      tab: 'credit-utilization',
      label: 'Credit Utilization',
      sublabel: facts.utilizationPercent ? `${facts.utilizationPercent}% Current · ${facts.utilizationTargetPercent}% Target` : 'Utilization · Awaiting data',
      iconType: 'gauge',
      progress: facts.utilizationPercent ? Math.max(0, 100 - facts.utilizationPercent) : 0
    },
    {
      tab: 'documents',
      label: 'Document Vault',
      sublabel: facts.documentTotalCount ? `${facts.documentVerifiedCount} of ${facts.documentTotalCount} Files Cleared` : 'Files cleared · Awaiting data',
      iconType: 'vault',
      progress: facts.documentTotalCount ? Math.round((facts.documentVerifiedCount / facts.documentTotalCount) * 100) : 0
    },
    {
      tab: 'business-setup',
      label: 'Business Setup',
      sublabel: profile.entityType,
      iconType: 'building',
      progress: 88
    },
    {
      tab: 'business-bankability',
      label: 'Bankability Strength',
      sublabel: facts.bankabilityScore ? `${facts.bankabilityScore}/100 Score` : 'Score · Awaiting data',
      iconType: 'bank-column',
      progress: facts.bankabilityScore
    },
    {
      tab: 'funding-readiness',
      label: 'Funding Programs',
      sublabel: facts.fundingTargetLabel,
      iconType: 'target',
      progress: profile.readinessPoints
    },
    {
      tab: 'recommendations',
      label: 'Strategic Actions',
      sublabel: `${missions.filter((mission) => !mission.completed).length} Open Tasks`,
      iconType: 'compass',
      progress: missions.length ? Math.round((missions.filter((mission) => mission.completed).length / missions.length) * 100) : 0
    },
    {
      tab: 'resources',
      label: 'Capital Library',
      sublabel: 'Underwriter Guides',
      iconType: 'library',
      progress: 100
    },
    {
      tab: 'request-review',
      label: 'Underwriter Audit',
      sublabel: 'Submit Dossier',
      iconType: 'profile',
      progress: 25
    }
  ];

  const secondaryTabs: { tab: TabType; label: string; iconType: GiantIconType }[] = [
    { tab: 'credit-utilization', label: 'Utilization Simulator', iconType: 'gauge' },
    { tab: 'business-setup', label: 'Business Setup (Delaware LLC)', iconType: 'building' },
    { tab: 'funding-readiness', label: 'Funding Program Match', iconType: 'target' },
    { tab: 'recommendations', label: 'Strategic Opportunities', iconType: 'compass' },
    { tab: 'resources', label: 'Capital Academy Guides', iconType: 'library' },
    { tab: 'request-review', label: 'Underwriter Audit Review', iconType: 'profile' }
  ];

  const isSecondaryActive = secondaryTabs.some((item) => item.tab === activeTab);

  return (
    <>
      {/* 1. Desktop Executive Mission Navigator Rail (Hidden on Mobile) */}
      <aside className="hidden lg:flex w-full lg:w-64 xl:w-68 shrink-0 flex-col gap-2.5 h-full min-h-0 select-none">
        {/* Consolidated Client Identity Card (Clean White Surface) */}
        <div className="relative overflow-hidden rounded-xl border border-slate-200/90 bg-white p-3 shadow-xs shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="relative w-10 h-10 rounded-lg overflow-hidden ring-1.5 ring-teal-500/40 shrink-0">
              <img
                src={profile.avatarUrl}
                alt={profile.name}
                referrerPolicy="no-referrer"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-900 truncate">{profile.name}</h3>
                <span className="text-[10px] font-bold text-teal-700 font-mono">
                  {profile.readinessPoints} Pts
                </span>
              </div>
              <p className="text-[11px] text-slate-600 font-medium truncate leading-tight">
                {profile.companyName}
              </p>
              <div className="mt-1 flex items-center justify-between text-[10px] text-slate-500">
                <span className="truncate">{currentLevel.name}</span>
                <span className="font-mono text-amber-600 font-semibold text-[10px]">
                  {readinessPercent}%
                </span>
              </div>
            </div>
          </div>

          {/* Mini Progress Bar */}
          <div className="mt-2 w-full h-1 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-teal-500 to-sky-500 rounded-full transition-all duration-500"
              style={{
                width: `${readinessPercent}%`
              }}
            />
          </div>
        </div>

        {/* Compact Clyde Quick Launcher (Clean Light Highlight) */}
        <div
          onClick={() => setIsClydeOpen(true)}
          className="group relative overflow-hidden rounded-lg border border-teal-200/80 bg-gradient-to-r from-teal-50/70 via-sky-50/50 to-white px-2.5 py-1.5 cursor-pointer hover:border-teal-400 transition-all shadow-xs shrink-0 flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-md bg-teal-100 flex items-center justify-center text-teal-700 text-[11px] font-bold">
              ⚡
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-bold text-slate-800 group-hover:text-teal-700 transition-colors">
                  Clyde AI Copilot
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-ping" />
              </div>
            </div>
          </div>
          <span className="text-[10px] text-teal-700 font-semibold">Ask →</span>
        </div>

        {/* Mission Navigator Items - Consolidated and Screen-Fitted */}
        <nav className="flex-1 min-h-0 overflow-y-auto pr-0.5 space-y-1 scrollbar-thin">
          <div className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Architecture
          </div>

          {navItems.map((item) => {
            const isActive = activeTab === item.tab;

            return (
              <button
                key={item.tab}
                onClick={() => setActiveTab(item.tab)}
                className={`w-full group relative flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg transition-all duration-150 text-left cursor-pointer border ${
                  isActive
                    ? 'border-teal-500/40 bg-teal-50/70 text-slate-900 shadow-xs ring-1 ring-teal-500/20 font-medium'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-white hover:border-slate-200/80'
                }`}
              >
                {/* Visual Anchor Icon */}
                <div
                  className={`p-1 rounded-md shrink-0 transition-transform group-hover:scale-105 ${
                    isActive ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-600 group-hover:bg-slate-200/80 group-hover:text-slate-900'
                  }`}
                >
                  <GiantIcon type={item.iconType} size="sm" glow={false} />
                </div>

                {/* Label & Progress */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[11px] font-semibold truncate ${
                        isActive ? 'text-teal-900 font-bold' : 'text-slate-700 group-hover:text-slate-900'
                      }`}
                    >
                      {item.label}
                    </span>
                    <span className={`text-[10px] font-mono tabular-nums ${isActive ? 'text-teal-700 font-bold' : 'text-slate-400'}`}>
                      {item.progress}%
                    </span>
                  </div>
                  <p className={`text-[10px] truncate leading-none ${isActive ? 'text-teal-700/80' : 'text-slate-400 group-hover:text-slate-600'}`}>
                    {item.sublabel}
                  </p>
                </div>

                {/* Active Marker Indicator */}
                {isActive && (
                  <div className="w-1 h-4 rounded-full bg-gradient-to-b from-teal-500 to-sky-500 shrink-0" />
                )}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* 2. Mobile Bottom-Docked Navigation Bar (Icon-Only, Prioritizing Readiness & Next Mission) */}
      <div className="lg:hidden">
        {/* Secondary Hubs Sheet Popup (When user taps More) */}
        {isMoreMenuOpen && (
          <div
            className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-xs animate-fade-in"
            onClick={() => setIsMoreMenuOpen(false)}
          >
            <div
              className="absolute bottom-20 inset-x-3 max-w-md mx-auto bg-white rounded-2xl border border-slate-200 p-3.5 shadow-2xl space-y-2 animate-slide-up"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 px-1">
                <div>
                  <span className="text-xs font-bold text-slate-900 uppercase tracking-wider block">
                    Financial Architecture Hubs
                  </span>
                  <span className="text-[10px] text-slate-500">
                    Switch directly to specialized capital modules
                  </span>
                </div>
                <button
                  onClick={() => setIsMoreMenuOpen(false)}
                  aria-label="Close navigation sheet"
                  className="w-7 h-7 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center text-xs transition-colors cursor-pointer"
                >
                  ✕
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                {secondaryTabs.map((item) => {
                  const isActive = activeTab === item.tab;
                  return (
                    <button
                      key={item.tab}
                      onClick={() => {
                        setActiveTab(item.tab);
                        setIsMoreMenuOpen(false);
                      }}
                      className={`flex items-center gap-2.5 p-2.5 rounded-xl text-left border transition-all cursor-pointer min-h-[48px] ${
                        isActive
                          ? 'border-teal-500 bg-teal-50/80 text-teal-900 font-bold shadow-xs ring-1 ring-teal-500/20'
                          : 'border-slate-100 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:border-slate-200'
                      }`}
                    >
                      <div
                        className={`p-1.5 rounded-lg shrink-0 ${
                          isActive
                            ? 'bg-teal-600 text-white'
                            : 'bg-white text-slate-600 border border-slate-200'
                        }`}
                      >
                        <GiantIcon type={item.iconType} size="sm" glow={false} />
                      </div>
                      <span className="text-xs truncate font-medium">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Fixed Mobile Bottom Dock (Icon-Only, Touch-Friendly, Prioritizing Readiness & Next Mission) */}
        <nav
          aria-label="Mobile Navigation Dock"
          className="fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200/90 shadow-[0_-4px_25px_rgba(15,23,42,0.08)] px-3 pt-2 pb-[calc(env(safe-area-inset-bottom,0px)+8px)] select-none"
        >
          <div className="flex items-center justify-between max-w-md mx-auto w-full">
            {/* Priority Action 1: Readiness (Command Center Priority) */}
            <button
              onClick={() => setActiveTab('dashboard')}
              aria-label={`Readiness Command Center (${readinessPercent}%)`}
              title={`Readiness: ${readinessPercent}% (${profile.readinessPoints} Pts)`}
              className={`relative min-w-[50px] min-h-[48px] px-2 py-1.5 rounded-xl flex items-center justify-center transition-all cursor-pointer active:scale-90 ${
                activeTab === 'dashboard'
                  ? 'bg-teal-50 text-teal-800 border border-teal-300 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <div className="relative flex items-center justify-center">
                <GiantIcon type="rocket" size="sm" glow={false} />
                <span className="absolute -top-1.5 -right-2 px-1 py-0.2 rounded-full text-[9px] font-mono font-black bg-teal-600 text-white shadow-xs">
                  {readinessPercent}%
                </span>
              </div>
              {activeTab === 'dashboard' && (
                <span className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-teal-600" />
              )}
            </button>

            {/* Action 2: Credit Profile (Tri-Bureau) */}
            <button
              onClick={() => setActiveTab('credit-profile')}
              aria-label="Personal Credit Profile"
              title="Personal Guarantor Credit Health (742 FICO)"
              className={`relative min-w-[48px] min-h-[48px] px-2 py-1.5 rounded-xl flex items-center justify-center transition-all cursor-pointer active:scale-90 ${
                activeTab === 'credit-profile'
                  ? 'bg-teal-50 text-teal-800 border border-teal-300 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <GiantIcon type="shield" size="sm" glow={false} />
              {activeTab === 'credit-profile' && (
                <span className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-teal-600" />
              )}
            </button>

            {/* Priority Action 3: Next Mission (Center Elevated Focal Button - Icon-Only, No Secondary Label) */}
            <div className="relative -mt-6 flex flex-col items-center">
              <button
                onClick={() => setActiveTab(nextMission.targetTab)}
                aria-label={`Next Mission: ${nextMission.title} (+${nextMission.points} Pts)`}
                title={`Next Mission: ${nextMission.title} (+${nextMission.points} Pts)`}
                className="group relative w-13 h-13 rounded-full bg-gradient-to-r from-teal-500 via-sky-500 to-teal-400 text-white shadow-lg shadow-teal-500/35 ring-4 ring-white flex items-center justify-center active:scale-90 transition-transform cursor-pointer"
              >
                <GiantIcon
                  type={
                    nextMission.category === 'Credit'
                      ? 'gauge'
                      : nextMission.category === 'Documents'
                      ? 'vault'
                      : nextMission.category === 'Bankability'
                      ? 'bank-column'
                      : 'target'
                  }
                  size="sm"
                  glow={false}
                />
                {/* Points Badge */}
                <span className="absolute -top-1.5 right-0 px-1.5 py-0.2 rounded-full text-[9px] font-mono font-black bg-amber-400 text-slate-950 border border-white shadow-xs">
                  +{nextMission.points}
                </span>
              </button>
            </div>

            {/* Action 4: Document Vault */}
            <button
              onClick={() => setActiveTab('documents')}
              aria-label="Document Vault"
              title="Secure Document Vault"
              className={`relative min-w-[48px] min-h-[48px] px-2 py-1.5 rounded-xl flex items-center justify-center transition-all cursor-pointer active:scale-90 ${
                activeTab === 'documents'
                  ? 'bg-teal-50 text-teal-800 border border-teal-300 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <GiantIcon type="vault" size="sm" glow={false} />
              {activeTab === 'documents' && (
                <span className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-teal-600" />
              )}
            </button>

            {/* Action 5: More Hubs Drawer */}
            <button
              onClick={() => setIsMoreMenuOpen(!isMoreMenuOpen)}
              aria-label="More Navigation Hubs"
              title="More Financial Hubs"
              className={`relative min-w-[48px] min-h-[48px] px-2 py-1.5 rounded-xl flex items-center justify-center transition-all cursor-pointer active:scale-90 ${
                isMoreMenuOpen || isSecondaryActive
                  ? 'bg-slate-100 text-teal-800 border border-slate-300 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <div className="w-6 h-6 flex items-center justify-center">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </div>
              {(isMoreMenuOpen || isSecondaryActive) && (
                <span className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-teal-600" />
              )}
            </button>
          </div>
        </nav>
      </div>
    </>
  );
};
