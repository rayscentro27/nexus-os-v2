import { useState, type ReactNode } from 'react';
import { UserMenu } from './auth';
import {
  CommandCenter, SystemHealth, AgentJobsView, ApprovalCenter, GoClearWorkspace,
  OpportunityLab, CreativeStudio, TradingLab, SeoOs, ModelRouter, Integrations,
  OpsImprovements, EventsFeed, IntakeOrientation, DesignLibrary,
} from './sections';
import { tabById } from '../config/nexusTabs';
import { StatusBadge, TabConnectionStatus } from './TabStatus';
import { CommandCenterMissionControl } from './command-center/MissionControl';
import { SourceIntakeReviewPage } from './source-intake/SourceIntakeReviewPage';

interface NavItem { key: string; label: string; icon: string; sub: string; render: (email: string | null) => ReactNode; }

const NAV: NavItem[] = [
  { key: 'command', label: 'Command Center', icon: '◎', sub: 'Hermes plain-language operator', render: (e) => <CommandCenter email={e} /> },
  { key: 'health', label: 'System Health', icon: '✚', sub: 'Live component status', render: () => <SystemHealth /> },
  { key: 'jobs', label: 'Agent Jobs', icon: '⚙', sub: 'Agents + job runner', render: () => <AgentJobsView /> },
  { key: 'approvals', label: 'Approvals', icon: '✓', sub: 'Approve / reject / request changes', render: (e) => <ApprovalCenter email={e} /> },
  { key: 'goclear', label: 'GoClear / Apex', icon: '◆', sub: 'Funding readiness workspace', render: () => <GoClearWorkspace /> },
  { key: 'opportunities', label: 'Opportunity Lab', icon: '⊛', sub: 'Money ideas, scored', render: () => <OpportunityLab /> },
  { key: 'intake', label: 'Source Intake & Review', icon: '⇪', sub: 'Submit, score, and route sources', render: () => <IntakeOrientation /> },
  { key: 'creative', label: 'Creative Studio', icon: '✦', sub: 'Campaigns, briefs, design dept', render: (e) => <CreativeStudio email={e} /> },
  { key: 'design', label: 'Design Library', icon: '◈', sub: 'Inspiration, patterns, UI quality', render: () => <DesignLibrary /> },
  { key: 'trading', label: 'Trading Lab', icon: '↗', sub: 'Research/testing (no live)', render: () => <TradingLab /> },
  { key: 'seo', label: 'SEO / Marketing', icon: '⌕', sub: 'Sites + opportunities', render: () => <SeoOs /> },
  { key: 'models', label: 'Model Router', icon: '⌥', sub: 'Providers + routes', render: () => <ModelRouter /> },
  { key: 'integrations', label: 'Integrations', icon: '⧉', sub: 'Registered, not activated', render: () => <Integrations /> },
  { key: 'ops', label: 'Ops & Improvements', icon: '⚕', sub: 'Self-healing + scout', render: () => <OpsImprovements /> },
  { key: 'events', label: 'Events Feed', icon: '≡', sub: 'Proof log', render: () => <EventsFeed /> },
];

export function Shell({ email }: { email: string | null }) {
  const [active, setActive] = useState('command');
  const current = NAV.find((n) => n.key === active) ?? NAV[0];
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand"><div className="logo" /><h1>Nexus <span className="v">OS v2</span></h1></div>
        <nav className="nav">
          {NAV.map((n) => {
            const cfg = tabById(n.key);
            return (
              <button key={n.key} className={active === n.key ? 'active' : ''} onClick={() => setActive(n.key)}>
                <span className="ico">{n.icon}</span>{n.label}
                {cfg && <StatusBadge status={cfg.status} label={cfg.statusLabel} />}
              </button>
            );
          })}
        </nav>
      </aside>
      <main className={`main${active === 'command' || active === 'intake' ? ' wide' : ''}`}>
        <div className="topbar">
          <div><h2>{current.label}</h2><div className="sub">{current.sub}</div></div>
          <UserMenu email={email} />
        </div>
        <TabConnectionStatus tabId={active} />
        {active === 'command'
          ? <CommandCenterMissionControl email={email} onNavigate={setActive} />
          : active === 'intake'
            ? <SourceIntakeReviewPage email={email} onNavigate={setActive} />
            : current.render(email)}
      </main>
    </div>
  );
}
