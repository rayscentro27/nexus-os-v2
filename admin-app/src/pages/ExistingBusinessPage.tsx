import React, { useMemo, useState } from 'react';
import { Building2, ArrowRight } from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { Card, Field, LiveProvenance, fmt, when } from '../components/live/LiveBits';

export const ExistingBusinessPage: React.FC = () => {
  const { liveAreas, navigateToObject } = useNexus();
  const businesses: any[] = liveAreas.businesses || [];
  const [selected, setSelected] = useState<string | null>(null);
  const active = useMemo(() => businesses.find(b => b.businessId === selected) || businesses[0], [businesses, selected]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Existing Business Center</h1>
        <p className="text-sm text-slate-500 mt-0.5">Operating ventures Nexus supports. Every metric shows its truth class; nothing is estimated without a label.</p>
        <div className="mt-2"><LiveProvenance source="registered ventures + Nexus projects, approvals and commerce funnel" /></div>
      </div>

      {businesses.length === 0 ? (
        <Card><p className="text-sm text-slate-500">No business records available — read model NOT CONNECTED.</p></Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/90 overflow-hidden divide-y divide-slate-100">
            {businesses.map(b => (
              <button key={b.businessId} type="button" onClick={() => setSelected(b.businessId)}
                className={`w-full text-left p-4 cursor-pointer transition-colors ${active?.businessId === b.businessId ? 'bg-blue-50/60' : 'hover:bg-slate-50'}`}>
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-slate-400" />
                  <span className="text-sm font-semibold text-slate-900">{b.businessName}</span>
                </div>
                <div className="mt-1 text-[11px] text-slate-500 font-mono">{b.businessId}</div>
                <div className="mt-1.5 text-xs text-slate-600">{b.status} · {b.activeProjects} active project(s) · {b.pendingApprovals} pending approval(s)</div>
              </button>
            ))}
          </div>

          {active && (
            <div className="lg:col-span-8 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card title="Operating metrics" right={<TruthBadge truth={active.revenue?.truthClass} size="xs" />}>
                  <Field label="Revenue" value={active.revenue?.value === null ? null : `$${fmt(active.revenue?.value)}`} truth={active.revenue?.truthClass} />
                  <Field label="Operating cost" value={active.operatingCost?.value === null ? null : `$${fmt(active.operatingCost?.value)}`} truth={active.operatingCost?.truthClass} />
                  <Field label="Profit / margin" value={active.profitOrMargin?.value} truth={active.profitOrMargin?.truthClass} />
                  <Field label="Orders (live)" value={active.orders?.value} truth={active.orders?.truthClass} />
                  <Field label="Customers" value={active.customers?.value} truth={active.customers?.truthClass} />
                </Card>
                <Card title="Demand">
                  <Field label="Traffic (page views)" value={active.traffic?.value} truth={active.traffic?.truthClass} />
                  <Field label="Leads (interest)" value={active.leads?.value} truth={active.leads?.truthClass} />
                  <Field label="Conversion" value={active.conversion?.value === null ? null : `${(active.conversion.value * 100).toFixed(1)}%`} truth={active.conversion?.truthClass} />
                  <Field label="Active campaigns" value={active.activeCampaigns} />
                  <Field label="7d / 30d / 90d trend" value={null} truth={active.trends?.truthClass} />
                </Card>
              </div>
              <Card title="Work and decisions">
                <Field label="Active projects" value={active.activeProjects} />
                <Field label="Pending approvals" value={active.pendingApprovals} />
                <Field label="Next action" value={active.nextAction} />
                <Field label="Last activity" value={when(active.lastActivity)} />
                {(active.currentBlockers || []).length > 0 && (
                  <div className="mt-2 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-3 py-2">{active.currentBlockers.join(' · ')}</div>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  {(active.projectIds || []).map((id: string) => (
                    <button key={id} type="button" onClick={() => navigateToObject('projects', id, 'project')}
                      className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1 cursor-pointer">
                      {id} <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  ))}
                  {(active.approvalIds || []).length > 0 && (
                    <button type="button" onClick={() => navigateToObject('approvals', active.approvalIds[0], 'approval')}
                      className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold cursor-pointer">Review approvals</button>
                  )}
                </div>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
