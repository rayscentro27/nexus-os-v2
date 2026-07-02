import { systemHealthItems } from '../data/systemHealthData.js';
import { reportRegistry } from '../data/reportRegistry.js';
import type { LiveHermesResponse } from './hermesLiveContext';

export interface SourceEvidence {
  source: string;
  sourceType: 'live' | 'static' | 'derived' | 'unavailable';
  freshness: string;
  status: 'verified' | 'partial' | 'unverified';
  blocker?: string;
}

const checkedAt = () => new Date().toISOString();

export function renderSystemHealthContract(): string {
  const blocked = systemHealthItems.filter((item) => item.tone === 'blocked' || item.tone === 'gated');
  const healthy = systemHealthItems.filter((item) => item.tone === 'healthy');
  const evidence = systemHealthItems.slice(0, 5).map((item) => `${item.label}: ${item.status} (${item.report}; ${item.lastRun})`).join('\n- ');
  return `**Status summary:** ${healthy.length} locally reported healthy; ${blocked.length} blocked or approval-gated. This is report-backed status, not a fresh production probe.\n\n**Source checked:** bundled System Health registry and linked local reports.\n**Evidence:**\n- ${evidence}\n**Blockers:** ${blocked.map((item) => `${item.label} — ${item.status}`).join('; ') || 'No blocker is listed in the local registry.'}\n**Freshness:** registry read ${checkedAt()}; individual evidence freshness is shown above and may be older than this request. Authenticated browser, Supabase, and deployed-production health were not verified here.\n**Next safe action:** open the newest blocker report, then run an authenticated read-only browser/Supabase verification. No scheduler or external action was started.`;
}

export function renderResearchStatusContract(): string {
  const research = systemHealthItems.find((item) => item.id === 'research');
  const reports = reportRegistry.filter((item) => /research|youtube/i.test(`${item.title} ${item.category} ${item.path}`) && item.available).slice(0, 3);
  const reportText = reports.length ? reports.map((item) => `${item.title} (${item.path})`).join('; ') : 'no indexed research report was available';
  return `**Configuration state:** locally configured/reporting; live execution state is unknown without authenticated verification.\n**Source checked:** System Health research registry and local report registry.\n**Last known run/report:** ${research ? `${research.status}; ${research.lastRun}; ${research.report}` : reportText}. Additional indexed evidence: ${reportText}.\n**Blockers:** connector/API availability, current scheduler state, and current Supabase writes were not authenticated in this request. A local report can prove a prior dry run, not that the engine is running now.\n**Freshness:** checked ${checkedAt()}; source timestamps vary by report.\n**Next safe action:** perform a read-only authenticated check of research_runs/research_sources and compare it with the newest local report. No scheduler was activated.`;
}

export function renderRecordContract(kind: 'approvals' | 'clients', live: LiveHermesResponse): string {
  const sourceName = kind === 'approvals' ? 'Supabase task_requests and approvals' : 'Supabase client_profiles';
  const required = kind === 'approvals' ? ['task_requests', 'approvals'] : ['client_profiles'];
  const failed = required.filter((table) => live.tableResults?.[table]?.status !== 'success');
  const partial = failed.length > 0 && required.some((table) => live.tableResults?.[table]?.status === 'success');
  const count = required.reduce((total, table) => total + (live.rowCounts?.[table] || 0), 0);
  const blocker = live.blocker || failed.map((table) => `${table}: ${live.tableResults?.[table]?.error || 'not verified'}`).join('; ');
  const state = live.liveData ? (partial ? 'partial verification' : 'verified read') : 'unverified';
  const label = kind === 'approvals' ? 'pending approval rows returned' : 'client rows returned';
  return `**Source checked:** ${sourceName}.\n**Verification:** ${state}; read-only, authenticated/RLS-applied when a session was available.\n**Result:** ${live.liveData ? `${count} ${label}.` : `No verified count is available.`}\n${live.text}\n**Blocker:** ${blocker || 'none reported by the source adapter'}\n**Freshness:** request-time check ${live.timestamp}; record-level updated timestamps were not normalized.\n**Next safe action:** ${live.liveData ? (kind === 'approvals' ? 'open Ray Review and inspect the highest-impact pending item' : 'open the client list and verify active status per record') : 'sign in with the approved admin session and retry the same read-only query'}.`;
}

export function renderSpecialistHandoffContract(target?: string | null): string {
  if (!target) return '**Specialist lane:** not selected yet.\n**Context included:** the target, objective, constraints, relevant source evidence, and required approval boundary.\n**Missing:** name the task, record, report, or outcome to hand off; optionally name the specialist lane.\n**Draft status:** the handoff was not created, saved, assigned, or sent. Once the target is clear, I can prepare a conversation-only draft.';
  return `**Specialist lane:** choose the Nexus specialist whose scope matches ${target}.\n**Context included:** target, objective, current evidence, constraints, and approval boundaries.\n**Missing:** confirm the specialist lane and acceptance criteria.\n**Draft status:** a conversation-only handoff outline is prepared for ${target}; it was not saved, assigned, or sent.`;
}
