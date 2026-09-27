import React from 'react';
import { PortalProvider, usePortal } from './context/PortalContext';
import type { TabType } from './types/portal';
import { TopBar } from './components/navigation/TopBar';
import { MissionNavigator } from './components/navigation/MissionNavigator';
import { ClydeWorkspace } from './components/clyde/ClydeWorkspace';
import { CelebrationModal } from './components/common/CelebrationModal';
import { GiantIcon } from './components/common/GiantIcon';

// Views
import { DashboardView } from './components/views/DashboardView';
import { CreditProfileView } from './components/views/CreditProfileView';
import { CreditUtilizationView } from './components/views/CreditUtilizationView';
import { DocumentsView } from './components/views/DocumentsView';
import { BusinessSetupView } from './components/views/BusinessSetupView';
import { BusinessBankabilityView } from './components/views/BusinessBankabilityView';
import { FundingReadinessView } from './components/views/FundingReadinessView';
import { RecommendationsView } from './components/views/RecommendationsView';
import { ResourcesView } from './components/views/ResourcesView';
import { RequestReviewView } from './components/views/RequestReviewView';
import { ProfileView } from './components/views/ProfileView';
import { SettingsView } from './components/views/SettingsView';

const PortalMain: React.FC = () => {
  const { activeTab, setIsClydeOpen, isClydeOpen, profile, currentLevel, liveReady } = usePortal();

  if (!liveReady) {
    return <div className="h-screen flex items-center justify-center bg-slate-50 text-slate-600 text-sm">Preparing your client portal…</div>;
  }

  const renderActiveView = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardView />;
      case 'profile':
        return <ProfileView />;
      case 'settings':
        return <SettingsView />;
      case 'credit-profile':
        return <CreditProfileView />;
      case 'credit-utilization':
        return <CreditUtilizationView />;
      case 'documents':
        return <DocumentsView />;
      case 'business-setup':
        return <BusinessSetupView />;
      case 'business-bankability':
        return <BusinessBankabilityView />;
      case 'funding-readiness':
        return <FundingReadinessView />;
      case 'recommendations':
        return <RecommendationsView />;
      case 'resources':
        return <ResourcesView />;
      case 'request-review':
        return <RequestReviewView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-slate-50 text-slate-900 font-sans overflow-hidden selection:bg-teal-500/20 selection:text-teal-900">
      {/* 3-Zone Clean Top Navigation Contract */}
      <TopBar />

      {/* Main Consolidated Workspace Frame */}
      <main className="flex-1 w-full max-w-[1680px] mx-auto px-3 sm:px-4 lg:px-6 py-2.5 overflow-hidden flex gap-3.5 min-h-0 bg-slate-50 pb-16 lg:pb-2.5">
        {/* Consolidated Mission Navigator Rail (Desktop Sidebar & Mobile Bottom Dock) */}
        <MissionNavigator />

        {/* Dynamic Main Viewport Canvas - Engineered to fit without scrolling */}
        <div className="flex-1 h-full min-w-0 flex flex-col overflow-y-auto lg:overflow-hidden pr-0.5 scrollbar-thin">
          {renderActiveView()}
        </div>
      </main>

      {/* Floating Clyde Copilot Trigger Button (Crisp Light Accent) */}
      <button
        onClick={() => setIsClydeOpen(!isClydeOpen)}
        className="fixed bottom-18 right-4 lg:bottom-9 lg:right-5 z-40 flex items-center gap-2.5 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 hover:border-teal-400 text-slate-900 shadow-xl hover:shadow-teal-500/15 active:scale-95 transition-all cursor-pointer group"
      >
        <div className="relative">
          <GiantIcon type="clyde" size="sm" glow={false} />
          <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-teal-500 ring-2 ring-white animate-ping" />
        </div>
        <div className="text-left hidden md:block">
          <div className="text-[11px] font-bold text-slate-900 group-hover:text-teal-700 transition-colors">
            Ask Clyde AI
          </div>
          <div className="text-[9px] text-teal-700 font-mono font-medium">
            {profile.readinessPoints} Pts · Active
          </div>
        </div>
      </button>

      {/* Clyde Deep Assistant Workspace */}
      <ClydeWorkspace />

      {/* Instant Gamification & Milestone Celebration Modal */}
      <CelebrationModal />

      {/* Consolidated High-Density Telemetry Status Ribbon (Clean Light Status Bar - Hidden on mobile in favor of bottom dock) */}
      <footer className="hidden lg:flex w-full border-t border-slate-200/90 bg-white h-7 px-4 items-center justify-between text-[11px] text-slate-500 shrink-0 select-none">
        <div className="flex items-center gap-2 truncate">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-500 shrink-0" />
          <span className="font-semibold text-slate-800">GoClear Institutional Capital</span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-700">Client: {profile.companyName}</span>
          <span className="text-slate-300 hidden sm:inline">|</span>
          <span className="text-teal-700 font-mono hidden sm:inline">{profile.ein}</span>
        </div>
        <div className="flex items-center gap-3 text-slate-500 text-[10px] shrink-0 font-mono">
          <span className="text-teal-700 font-bold">{profile.readinessPoints}/1,000 Pts</span>
          <span className="text-slate-300">·</span>
          <span className="hidden md:inline text-slate-600">{currentLevel.name}</span>
          <span className="text-slate-300 hidden md:inline">·</span>
          <span className="text-slate-500 hidden lg:inline">Confidential Commercial Underwriting</span>
        </div>
      </footer>
    </div>
  );
};

export default function App({ initialTab = 'dashboard' }: { initialTab?: TabType }) {
  return (
    <PortalProvider initialTab={initialTab}>
      <PortalMain />
    </PortalProvider>
  );
}
