import React, { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, ClipboardList, FileCheck2, GitBranch, ShieldCheck } from 'lucide-react';
import {
  getDepartmentOperationsSnapshot,
  sortQueueByPriority,
  type DepartmentQueueItem,
} from '../lib/departments/departmentOperations';

const views = ['Overview', 'Inbox', 'Queue', 'Blocked', 'Approvals', 'Incidents', 'Completed', 'Capabilities', 'Evidence'] as const;
type View = typeof views[number];

function statusTone(value: string) {
  const status = value.toUpperCase();
  if (/BLOCK|CRITICAL|HIGH/.test(status)) return 'red';
  if (/APPROVAL|VERIFY|MEDIUM|DEGRADED|PARTIAL/.test(status)) return 'amber';
  if (/COMPLETE|HEALTHY|ACTIVE|READY|PASS/.test(status)) return 'green';
  return 'blue';
}

function Pill({ children, tone = 'blue' }: { children: React.ReactNode; tone?: string }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

function QueueRow({ item }: { item: DepartmentQueueItem }) {
  return (
    <article className="glass2 exec-work-card" data-testid={`department-queue-${item.itemId}`}>
      <div className="between">
        <strong>{item.title}</strong>
        <Pill tone={statusTone(item.status)}>{item.status}</Pill>
      </div>
      <p>{item.departmentId.replace('_', ' ')} · {item.ownerRole || 'Unassigned'} · {item.operationMode}</p>
      <small>{item.priority} · urgency {item.urgency} · risk {item.riskLevel} · approval {item.requiresApproval ? 'required' : 'not required'}</small>
      <small>Evidence: {item.evidenceIds.join(', ')}</small>
    </article>
  );
}

export default function DepartmentOperationsWorkspace() {
  const [view, setView] = useState<View>('Overview');
  const snapshot = useMemo(() => getDepartmentOperationsSnapshot(), []);
  const blockedItems = snapshot.queueItems.filter((item) => item.status === 'BLOCKED' || item.blockerIds.length > 0);
  const approvalItems = snapshot.queueItems.filter((item) => item.requiresApproval);
  const completedItems = snapshot.queueItems.filter((item) => item.status === 'COMPLETE');
  const verifyingItems = snapshot.queueItems.filter((item) => item.status === 'VERIFYING');
  const visibleQueue = view === 'Blocked' ? blockedItems
    : view === 'Approvals' ? approvalItems
      : view === 'Completed' ? completedItems
        : view === 'Inbox' ? snapshot.queueItems.filter((item) => ['NEW', 'TRIAGED', 'PLANNED'].includes(item.status))
          : sortQueueByPriority(snapshot.queueItems);

  return (
    <section className="glass panel executive-panel" data-testid="department-operations-workspace">
      <div className="panel-head">
        <div>
          <h3>Department Operations</h3>
          <p className="exec-panel-subtitle">Governed queues, blockers, approvals, incidents, verification, and evidence. Synthetic seed only; no autonomous agents.</p>
        </div>
        <Pill tone="green">{snapshot.departments.length} active</Pill>
      </div>

      <div className="exec-topline" role="tablist" aria-label="Department Operations views">
        {views.map((item) => (
          <button type="button" className="btn ghost" key={item} onClick={() => setView(item)} aria-selected={view === item}>{item}</button>
        ))}
      </div>

      {view === 'Overview' && (
        <div className="exec-summary-grid">
          {snapshot.health.map((health) => (
            <article className="glass2 exec-summary-card" key={health.departmentId}>
              <ShieldCheck size={22} />
              <strong>{snapshot.departments.find((department) => department.departmentId === health.departmentId)?.name || health.departmentId}</strong>
              <b>{health.state}</b>
              <small>{health.openItems} open · {health.blockedItems} blocked · {health.awaitingApproval} approvals</small>
              <small>{health.topRisks[0] || 'No top risk recorded'}</small>
            </article>
          ))}
        </div>
      )}

      {['Inbox', 'Queue', 'Blocked', 'Approvals', 'Completed'].includes(view) && (
        <div className="exec-work-list">
          {visibleQueue.length ? visibleQueue.map((item) => <QueueRow key={item.itemId} item={item} />) : <div className="exec-empty">No items in this view.</div>}
          {view === 'Completed' && !completedItems.length && verifyingItems.length > 0 && <div className="exec-empty">{verifyingItems.length} item has verification evidence but is still VERIFYING until explicitly advanced.</div>}
        </div>
      )}

      {view === 'Incidents' && (
        <div className="exec-health-list">
          {snapshot.incidents.map((incident) => (
            <article className="exec-health-row" key={incident.incidentId}>
              <AlertTriangle size={18} />
              <strong>{incident.title}</strong>
              <Pill tone={statusTone(incident.status)}>{incident.status}</Pill>
              <small>{incident.impact} · owner {incident.ownerRole}</small>
            </article>
          ))}
        </div>
      )}

      {view === 'Capabilities' && (
        <div className="exec-capability-list">
          {snapshot.departments.map((department) => (
            <article className="exec-capability-card" key={department.departmentId}>
              <div className="between"><strong>{department.name}</strong><Pill tone="blue">{department.defaultOperationMode}</Pill></div>
              <p>{department.ownerRole} · escalation: {department.escalationTargets.join(', ')}</p>
              <small>Allowed capabilities: {department.allowedCapabilityIds.join(', ')}</small>
              <small>Prohibited data: {department.prohibitedDataClasses.join(', ')}</small>
            </article>
          ))}
        </div>
      )}

      {view === 'Evidence' && (
        <div className="exec-knowledge-status">
          <p><FileCheck2 size={18} /> <strong>Evidence IDs:</strong> {snapshot.evidenceIds.join(', ')}</p>
          <p><ClipboardList size={18} /> <strong>Verification:</strong> completion requires criteria results, evidence, verification, and no unresolved critical blocker.</p>
          <p><GitBranch size={18} /> <strong>Schema:</strong> durable queue tables are additive, admin-only, and separate from client data.</p>
          {snapshot.limitations.map((item) => <p key={item}><CheckCircle2 size={18} /> {item}</p>)}
        </div>
      )}
    </section>
  );
}
