import React from 'react';
import { PageId } from '../../types';
import { useNexus } from '../../context/NexusContext';
import { TruthBadge } from '../common/TruthBadge';
import { LiveProvenance, PrototypeNotice, fmt, when } from './LiveBits';

const SOURCES: Partial<Record<PageId, string>> = {
  'command-center': 'Nexus read model (projects, approvals, commerce, systems)',
  approvals: 'nexus_get_project_approvals (same reader as Nova)',
  projects: 'nexus_get_project (same reader as Nova)',
  research: 'Research R10 durable store (latest 15 jobs)',
  marketing: 'DEPARTMENT_DIRECTIVE results (Marketing)',
  campaigns: 'Nexus read model',
  creative: 'Project creative outputs (private storage, signed previews)',
  'business-hub': 'Project commerce offer + Printify draft + commerce funnel tables',
  finance: 'Cost governor + commerce orders',
  'trading-engine': 'Trading Core R1 store (OANDA practice)',
  systems: 'Live probes: Mac launchd, Oracle systemd, Contabo containers',
  nova: 'Nexus read model + directive events',
};

// Pages whose approved-design sections still read the package's reference data modules.
const PROTOTYPE_SECTIONS: Partial<Record<PageId, string>> = {
  research: 'Research queue analytics',
  marketing: 'Channel readiness & schedule panels',
  'business-hub': 'Ventures, funding & dossier panels',
  finance: 'Cash, budgets & projections',
  'trading-engine': 'Charts, replay, sensitivity & scorecards',
  systems: 'Recovery runbooks & operations panels',
  clients: 'Client tenants',
  documents: 'Documents',
  approvals: 'Decision dossiers',
  'development-labs': 'Lab experiments',
  'upgrade-control': 'Upgrade candidates',
};

const Chip: React.FC<{ label: string; value: unknown; truth?: string }> = ({ label, value, truth }) => (
  <div className="bg-white rounded-xl border border-slate-200/90 px-3 py-2 flex items-center justify-between gap-2 min-w-0">
    <span className="text-[11px] text-slate-500 truncate">{label}</span>
    <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-900 min-w-0 truncate">
      {fmt(value)}
      {truth && <TruthBadge truth={truth} size="xs" />}
    </span>
  </div>
);

const AreaFacts: React.FC<{ page: PageId }> = ({ page }) => {
  const { liveAreas } = useNexus();
  if (page === 'trading-engine') {
    const t = liveAreas.trading || {};
    const perf = t.performance || {};
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Chip label="Mode" value={t.mode ? `${t.mode} · ${t.broker}` : null} truth="PAPER" />
        <Chip label="Live trading" value={t.liveTradingEnabled === false ? 'LOCKED OFF' : null} truth="VERIFIED" />
        <Chip label="Strategy versions" value={(t.versions || []).map((v: any) => `${v.name} ${v.instrument} ${v.timeframe}`).join(', ') || null} truth="PAPER" />
        <Chip label="Paper trades / orders" value={t.counts ? `${t.counts.trades} / ${t.counts.orders}` : null} truth="PAPER" />
        <Chip label="Signals / risk events" value={t.counts ? `${t.counts.signals} / ${t.counts.risk_events}` : null} truth="PAPER" />
        <Chip label="Reconciliations" value={t.counts?.reconciliation_events} truth="PAPER" />
        <Chip label="Latest snapshot" value={perf.computed_at ? when(perf.computed_at) : null} truth="PAPER" />
        <Chip label="Contabo worker" value={t.contabo_worker ? 'DEFERRED' : null} truth="UNKNOWN" />
      </div>
    );
  }
  if (page === 'finance') {
    const f = liveAreas.finance || {};
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Chip label="Verified spend" value={typeof f.verifiedSpendUsd === 'number' ? `$${f.verifiedSpendUsd.toFixed(2)}` : null} truth="VERIFIED" />
        <Chip label="Verified revenue" value={typeof f.verifiedRevenueUsd === 'number' ? `$${f.verifiedRevenueUsd.toFixed(2)}` : 'NOT CONNECTED'} truth={typeof f.verifiedRevenueUsd === 'number' ? 'VERIFIED' : 'NOT_CONNECTED'} />
        <Chip label="Bank cash" value="NOT CONNECTED" truth="NOT_CONNECTED" />
        <Chip label="Paid spend authorized" value="$0 (cost governor)" truth="VERIFIED" />
      </div>
    );
  }
  if (page === 'marketing') {
    const m = (liveAreas.directives || []).find((d: any) => d.department === 'MARKETING' && d.marketing);
    if (!m) return <p className="text-xs text-slate-500">No Marketing directive result recorded.</p>;
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <Chip label="Latest Marketing directive" value={`${m.directiveId} · ${m.status}${m.isSmoke ? ' (smoke)' : ''}`} truth="VERIFIED" />
        <Chip label="Concept" value={m.marketing.campaign_concept} truth="PROPOSED" />
        <Chip label="Channel" value={m.marketing.channel_recommendation} truth="PROPOSED" />
      </div>
    );
  }
  if (page === 'business-hub') {
    const o = (liveAreas.commerce || [])[0];
    if (!o) return null;
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Chip label="Mode" value={o.interestTest?.mode} truth="VERIFIED" />
        <Chip label="Live checkout" value={o.liveSales?.checkoutStatus} truth="VERIFIED" />
        <Chip label="Interest submissions" value={o.funnel?.interestSubmissions} truth={o.funnel?.truthClass} />
        <Chip label="Live orders" value={o.funnel?.liveOrders} truth={o.funnel?.truthClass} />
      </div>
    );
  }
  if (page === 'nova') {
    const n = liveAreas.nova || {};
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        <Chip label="Nova (Telegram)" value={n.service} truth={n.service ? 'VERIFIED' : 'UNKNOWN'} />
        <Chip label="Hermes" value={n.hermes} truth={n.hermes ? 'VERIFIED' : 'UNKNOWN'} />
        <Chip label="Release" value={n.release} truth={n.release ? 'VERIFIED' : 'UNKNOWN'} />
      </div>
    );
  }
  return null;
};

export const LivePageBanner: React.FC<{ page: PageId }> = ({ page }) => {
  const source = SOURCES[page];
  const proto = PROTOTYPE_SECTIONS[page];
  if (!source && !proto) return null;
  return (
    <div className="space-y-2 mb-4">
      {source && <LiveProvenance source={source} />}
      <AreaFacts page={page} />
      {proto && <PrototypeNotice area={proto} />}
    </div>
  );
};

/** Visible when the authoritative read model cannot be reached; never falls back to demo data. */
export const LiveGate: React.FC = () => {
  const { liveStatus } = useNexus();
  if (liveStatus === 'ready' || liveStatus === 'loading') return null;
  const msg =
    liveStatus === 'forbidden'
      ? 'Your account is signed in but does not have the Nexus admin role.'
      : 'Live Nexus state is unavailable. Operational views are empty rather than showing invented data.';
  return (
    <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 flex items-center gap-2">
      <TruthBadge truth="NOT_CONNECTED" size="xs" />
      <span>{msg}</span>
    </div>
  );
};
