import React, { useEffect, useMemo, useState } from 'react';
import NexusSidebar from './NexusSidebar';
import NexusDepartmentPanel, { StatusCard } from './NexusDepartmentPanel';
import RayReviewCenter from './RayReviewCenter';
import ReportCenter from './ReportCenter';
import HermesWorkroom from './HermesWorkroom';
import AutomationSchedulerPanel from './AutomationSchedulerPanel';
import RevenueDashboard from './RevenueDashboard';
import CommunicationDashboard from './CommunicationDashboard';
import MarketingDraftCenter from './MarketingDraftCenter';
import ResearchMoneyPipeline from './ResearchMoneyPipeline';
import NexusActivationStatus from './NexusActivationStatus';
import { navigationById } from '../data/nexusNavigationConfig';
import { forceAuthResetAndRedirect } from '../lib/authSessionCleanup';

const allowed = new Set(Object.keys(navigationById));
function hashDepartment() { const id = window.location.hash.replace(/^#\/?/, ''); return allowed.has(id) ? id : 'command'; }

function CommandCenter({ navigate }) { return <div className="nxos-stack"><div className="nxos-metric-grid"><StatusCard label="Safe schedules" value="2 loaded" tone="good" detail="08:00 and 18:00" /><StatusCard label="Ray Review" value="64 cards" tone="warn" detail="12 approve-today" /><StatusCard label="Research-to-money" value="50 candidates" tone="good" detail="26 immediately actionable" /><StatusCard label="Confirmed revenue" value="$0" tone="neutral" detail="$97 test path pending" /></div><section className="nxos-callout"><h2>What can make money today</h2><p>Prove the $97 readiness journey using the synthetic Julius Erving customer and Stripe test mode. The database insert, dashboard flag, and test completion remain individually approval-gated.</p><div className="nxos-actions"><button type="button" className="primary" onClick={() => navigate('review')}>Open Ray Review</button><button type="button" onClick={() => navigate('monetization')}>Open Monetization</button><button type="button" onClick={() => navigate('hermes')}>Ask Hermes</button></div></section><div className="nxos-two-col"><section className="nxos-table-card"><h2>Running safely</h2>{['Daily operating cycle — 25/25', 'Evening closeout — 6/6', 'Research scoring and memory', 'Oanda practice read checks', 'Vibe paper dry-run', 'NotebookLM watched folder'].map((item) => <div className="nxos-table-row" key={item}><strong>{item}</strong><span>Internal safe</span></div>)}</section><section className="nxos-table-card"><h2>Blocked or gated</h2>{['Real charges', 'Email/SMS sending', 'Social publishing', 'Persistent client insertion', 'Live/funded trading', 'Dispute sending'].map((item) => <div className="nxos-table-row" key={item}><strong>{item}</strong><span>Blocked</span></div>)}</section></div></div>; }

function GenericStatus({ type }) {
  const content = {
    health: [['Build', 'Passed'], ['Safety', 'Passed'], ['RLS', '25/25 enabled'], ['Tool policy violations', '0'], ['Stripe mode', 'Test'], ['Oanda endpoint', 'Practice only']],
    clients: [['Test customer', 'Julius Erving'], ['Business', 'Doctor J LLC'], ['Persistent insert', 'Approval-gated'], ['Dashboard flag', 'Off'], ['Payment onboarding', 'Dry-run ready'], ['Real clients', 'Blocked']],
    credit: [['Credit Specialist', 'Available'], ['Funding Specialist', 'Available'], ['Dispute sending', 'Blocked'], ['Applications submitted', '0'], ['Readiness offer', '$97 test path'], ['Approved knowledge only', 'Required']],
    opportunities: [['Research candidates', '50'], ['Immediately actionable', '26'], ['Offers registered', '9'], ['Partner pathways', '2'], ['External outreach', '0'], ['Next step', 'Ray Review']],
    trading: [['Oanda endpoint', 'Practice verified'], ['Open trades', '0'], ['Vibe backtest', '50 trades passed'], ['Bridge', 'Dry-run passed'], ['Recurring demo orders', 'Approval-gated'], ['Live trading', 'Blocked']],
    tools: [['CLI registry', 'Active'], ['Tool access policy', 'Validated'], ['Violations', '0'], ['Supabase CLI', 'Connected'], ['Stripe CLI', 'Test mode'], ['Destructive commands', 'Blocked']],
    settings: [['External actions', 'Approval required'], ['Service role in frontend', 'Blocked'], ['Demo/static fallback', 'Enabled'], ['Client live flag', 'Off'], ['Live trading', 'Blocked'], ['Stripe live mode', 'Blocked']],
  }[type] || [];
  return <section className="nxos-table-card">{content.map(([name, status]) => <div className="nxos-table-row" key={name}><strong>{name}</strong><span>{status}</span></div>)}</section>;
}

export default function NexusAppShell({ email }) {
  const [active, setActive] = useState(hashDepartment);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { const update = () => setActive(hashDepartment()); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update); }, []);
  function navigate(id) { if (!allowed.has(id)) return; setActive(id); window.location.hash = id; window.scrollTo({ top: 0, behavior: 'smooth' }); }
  const meta = navigationById[active] || navigationById.command;
  const panel = useMemo(() => {
    if (active === 'command') return <CommandCenter navigate={navigate} />;
    if (active === 'activation') return <NexusActivationStatus onNavigate={navigate} />;
    if (active === 'review') return <RayReviewCenter />;
    if (active === 'reports') return <ReportCenter />;
    if (active === 'hermes') return <HermesWorkroom />;
    if (active === 'automation') return <AutomationSchedulerPanel onOpenReport={() => navigate('reports')} onReview={() => navigate('review')} />;
    if (active === 'monetization') return <RevenueDashboard />;
    if (active === 'marketing') return <MarketingDraftCenter />;
    if (active === 'research') return <ResearchMoneyPipeline />;
    if (active === 'opportunities') return <ResearchMoneyPipeline />;
    if (active === 'credit') return <GenericStatus type="credit" />;
    if (active === 'clients') return <GenericStatus type="clients" />;
    return <GenericStatus type={active} />;
  }, [active]);
  async function signOut() { await forceAuthResetAndRedirect('/admin/login'); }
  return <div className="nxos-root"><NexusSidebar activeId={active} onNavigate={navigate} open={menuOpen} onClose={() => setMenuOpen(false)} /><main className="nxos-main"><header className="nxos-topbar"><button type="button" className="nxos-menu" onClick={() => setMenuOpen((value) => !value)} aria-label="Toggle departments">☰</button><div className="nxos-breadcrumb">Nexus OS <span>/</span> {meta.label}</div><div className="nxos-user"><span>{email || 'admin'}</span><a href="/client/dashboard">Client portal</a><button type="button" onClick={signOut}>Sign out</button></div></header><NexusDepartmentPanel title={meta.label} description={meta.description}>{panel}</NexusDepartmentPanel></main>{menuOpen && <button type="button" className="nxos-overlay" aria-label="Close menu" onClick={() => setMenuOpen(false)} />}</div>;
}
