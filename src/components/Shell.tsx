import { useState, type ReactNode } from 'react';
import { UserMenu } from './auth';
import {
  CommandCenter, SystemHealth, AgentJobsView, ApprovalCenter, GoClearWorkspace,
  OpportunityLab, CreativeStudio, TradingLab, SeoOs, ModelRouter, Integrations,
  OpsImprovements, EventsFeed, IntakeOrientation,
} from './sections';

interface NavItem { key: string; label: string; icon: string; sub: string; render: (email: string | null) => ReactNode; }

const NAV: NavItem[] = [
  { key: 'command', label: 'Command Center', icon: '◎', sub: 'Hermes plain-language operator', render: (e) => <CommandCenter email={e} /> },
  { key: 'health', label: 'System Health', icon: '✚', sub: 'Live component status', render: () => <SystemHealth /> },
  { key: 'jobs', label: 'Agent Jobs', icon: '⚙', sub: 'Agents + job runner', render: () => <AgentJobsView /> },
  { key: 'approvals', label: 'Approvals', icon: '✓', sub: 'Approve / reject / request changes', render: (e) => <ApprovalCenter email={e} /> },
  { key: 'goclear', label: 'GoClear / Apex', icon: '◆', sub: 'Funding readiness workspace', render: () => <GoClearWorkspace /> },
  { key: 'opportunities', label: 'Opportunity Lab', icon: '⊛', sub: 'Money ideas, scored', render: () => <OpportunityLab /> },
  { key: 'intake', label: 'Intake & Orientation', icon: '⇪', sub: 'Transcripts → decisions', render: () => <IntakeOrientation /> },
  { key: 'creative', label: 'Creative Studio', icon: '✦', sub: 'Campaigns, briefs, QA', render: (e) => <CreativeStudio email={e} /> },
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
          {NAV.map((n) => (
            <button key={n.key} className={active === n.key ? 'active' : ''} onClick={() => setActive(n.key)}>
              <span className="ico">{n.icon}</span>{n.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="main">
        <div className="topbar">
          <div><h2>{current.label}</h2><div className="sub">{current.sub}</div></div>
          <UserMenu email={email} />
        </div>
        {current.render(email)}
      </main>
    </div>
  );
}
