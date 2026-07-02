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

export type CleanSourceStatus = 'success' | 'partial_success' | 'empty_success' | 'failed' | 'fallback_used';

export interface CleanSourceSummary {
  status: CleanSourceStatus; source: string; rowCount?: number; blocker?: string; adjacentContext?: string[];
}

export function cleanRecordSourceSummary(kind: 'approvals' | 'clients', live: LiveHermesResponse): CleanSourceSummary {
  const required = kind === 'approvals' ? ['task_requests', 'approvals'] : ['client_profiles'];
  const succeeded = required.filter((table) => live.tableResults?.[table]?.status === 'success');
  const failed = required.filter((table) => live.tableResults?.[table]?.status === 'error');
  const rowCount = required.reduce((total, table) => total + (live.rowCounts?.[table] || 0), 0);
  const source = kind === 'clients' ? 'client_profiles' : 'task_requests, approvals';
  if (succeeded.length === required.length) return { status: rowCount === 0 ? 'empty_success' : 'success', source, rowCount, adjacentContext: kind === 'clients' ? ['approvals/task_requests excluded from client evidence'] : undefined };
  if (succeeded.length > 0 && failed.length > 0) return { status: 'partial_success', source, rowCount, blocker: failed.map((table) => `${table}: ${live.tableResults?.[table]?.error || 'read failed'}`).join('; ') };
  if (live.sourceType === 'static_fallback') return { status: 'fallback_used', source, rowCount, blocker: live.blocker };
  return { status: 'failed', source, blocker: live.blocker || failed.map((table) => `${table}: ${live.tableResults?.[table]?.error || 'read failed'}`).join('; ') || 'source read did not succeed' };
}

const checkedAt = () => new Date().toISOString();

export function renderSystemHealthContract(): string {
  const blocked = systemHealthItems.filter((item) => item.tone === 'blocked' || item.tone === 'gated');
  const healthy = systemHealthItems.filter((item) => item.tone === 'healthy');
  const evidence = systemHealthItems.slice(0, 5).map((item) => `${item.label}: ${item.status} (${item.report}; ${item.lastRun})`).join('\n- ');
  return `**Status summary:** ${healthy.length} locally reported healthy; ${blocked.length} blocked or approval-gated. This is report-backed status, not a fresh production probe. Build/tests are represented by the latest local cycle evidence; Supabase and Deployment require separate authenticated verification; Hermes brain contracts are loaded.\n\n**Source checked:** bundled System Health registry and linked local reports.\n**Evidence:**\n- ${evidence}\n**Blockers:** ${blocked.map((item) => `${item.label} — ${item.status}`).join('; ') || 'No blocker is listed in the local registry.'}\n**Freshness:** registry read ${checkedAt()}; individual evidence freshness is shown above and may be older than this request. Authenticated browser, Supabase, and deployed-production health were not verified here.\n**Next safe action:** Next recommended action is to open the newest blocker report, then run an authenticated read-only browser/Supabase verification. No scheduler or external action was started.`;
}

export function renderResearchStatusContract(): string {
  const research = systemHealthItems.find((item) => item.id === 'research');
  const reports = reportRegistry.filter((item) => /research|youtube/i.test(`${item.title} ${item.category} ${item.path}`) && item.available).slice(0, 3);
  const reportText = reports.length ? reports.map((item) => `${item.title} (${item.path})`).join('; ') : 'no indexed research report was available';
  return `**Configuration state:** locally configured/reporting; live execution state is unknown without authenticated verification.\n**Source checked:** System Health research registry and local report registry.\n**Last known run/report:** ${research ? `${research.status}; ${research.lastRun}; ${research.report}` : reportText}. Additional indexed evidence: ${reportText}.\n**Blockers:** connector/API availability, current scheduler state, and current Supabase writes were not authenticated in this request. A local report can prove a prior dry run, not that the engine is running now.\n**Freshness:** checked ${checkedAt()}; source timestamps vary by report.\n**Next safe action:** perform a read-only authenticated check of research_runs/research_sources and compare it with the newest local report. No scheduler was activated.`;
}

export function renderRecordContract(kind: 'approvals' | 'clients', live: LiveHermesResponse): string {
  const clean = cleanRecordSourceSummary(kind, live);
  const sourceName = kind === 'approvals' ? 'Supabase task_requests and approvals' : 'Supabase client_profiles';
  const required = kind === 'approvals' ? ['task_requests', 'approvals'] : ['client_profiles'];
  const failed = required.filter((table) => live.tableResults?.[table]?.status !== 'success');
  const succeeded = required.filter((table) => live.tableResults?.[table]?.status === 'success');
  const count = required.reduce((total, table) => total + (live.rowCounts?.[table] || 0), 0);
  const label = kind === 'approvals' ? 'pending approval rows returned' : 'client rows returned';

  if (clean.status === 'failed' || clean.status === 'fallback_used') {
    const blockerText = live.blocker || failed.map((table) => `${table}: ${live.tableResults?.[table]?.error || 'access denied'}`).join('; ') || 'authentication or RLS denied access';
    return `**Source checked:** ${sourceName}.\n**Verification:** unverified; read-only, authenticated/RLS-applied when a session was available.\n**Result:** No verified count is available.\n**Blocker:** ${blockerText}\n**Freshness:** request-time check ${live.timestamp}; record-level updated timestamps were not normalized.\n**Next safe action:** sign in with the approved admin session and retry the same read-only query.`;
  }

  if (clean.status === 'success' || clean.status === 'empty_success') {
    const sourceUsed = succeeded.join(', ');
    return `**Result:** ${count} ${label}. Status: ${clean.status}.\n**Source checked:** ${sourceName}.\n**Verification:** verified read; read-only and authenticated when a session was available.\n**Provenance:** ${sourceUsed}.\n${kind === 'clients' ? '**Adjacent context:** approvals/task_requests excluded from client evidence.\n' : ''}**Freshness:** request-time check ${live.timestamp}.\n**Blocker:** none.\n**Next safe action:** ${count > 0 ? (kind === 'clients' ? 'open the client list and verify active status per record' : 'open Ray Review and inspect the highest-impact pending item') : (kind === 'clients' ? 'confirm this empty state is expected' : 'no approval action is needed unless another source is expected')}.`;
  }

  const partial = succeeded.length > 0;
  const state = partial ? 'partial verification' : 'unverified';
  const blockerText = failed.map((table) => `${table}: ${live.tableResults?.[table]?.error || 'read failed'}`).join('; ');
  const adjacentNote = kind === 'clients' ? '\n**Adjacent context:** approvals/task_requests were not used to count clients. Adjacent operational context is labeled separately from client records.' : '';
  return `**Source checked:** ${sourceName}.\n**Verification:** ${state}; read-only, authenticated/RLS-applied when a session was available.\n**Result:** ${count} ${label}.\n**Blocker:** ${blockerText}\n**Freshness:** request-time check ${live.timestamp}; record-level updated timestamps were not normalized.${adjacentNote}\n**Next safe action:** sign in with the approved admin session and retry the same read-only query.`;
}

export function renderSpecialistHandoffContract(target?: string | null): string {
  if (!target) return '**Specialist lane:** not selected yet.\n**Context included:** the target, objective, constraints, relevant source evidence, and required approval boundary.\n**Missing:** name the task, record, report, or outcome to hand off; optionally name the specialist lane.\n**Draft status:** the handoff was not created, saved, assigned, or sent. Once the target is clear, I can prepare a conversation-only draft.';
  return `**Specialist lane:** choose the Nexus specialist whose scope matches ${target}.\n**Context included:** target, objective, current evidence, constraints, and approval boundaries.\n**Missing:** confirm the specialist lane and acceptance criteria.\n**Draft status:** a conversation-only handoff outline is prepared for ${target}; it was not saved, assigned, or sent.`;
}

const SPECIALIST_AGENT_REGISTRY: Record<string, { status: string; description: string; relatedWorkflows: string[] }> = {
  credit: { status: 'not registered', description: 'No verified live Credit Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Credit & Funding Readiness Review', 'credit/funding context in Nexus'] },
  funding: { status: 'not registered', description: 'No verified live Funding Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Funding Application Prep Sprint', 'funding readiness workflow'] },
  research: { status: 'not registered', description: 'No verified live Research Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Research engine', 'YouTube research pipeline'] },
  grant: { status: 'not registered', description: 'No verified live Grant Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Grant writing context', 'funding applications'] },
  trading: { status: 'not registered', description: 'No verified live Trading Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Trading proof reports', 'strategy validation'] },
  crm: { status: 'not registered', description: 'No verified live CRM Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Client profiles', 'client pipeline'] },
  content: { status: 'not registered', description: 'No verified live Content Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Content creation', 'marketing context'] },
  sales: { status: 'not registered', description: 'No verified live Sales Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Revenue strategy', 'monetization workflow'] },
  marketing: { status: 'not registered', description: 'No verified live Marketing Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Marketing context', 'monetization offers'] },
  automation: { status: 'not registered', description: 'No verified live Automation Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Scheduling', 'automated reports'] },
  compliance: { status: 'not registered', description: 'No verified live Compliance Specialist Agent is registered in the specialist registry.', relatedWorkflows: ['Safety audits', 'compliance checks'] },
};

function extractSpecialistDomain(message: string): string | null {
  const lower = message.toLowerCase();
  for (const domain of Object.keys(SPECIALIST_AGENT_REGISTRY)) {
    if (new RegExp(`\\b${domain}\\b`, 'i').test(lower)) return domain;
  }
  return null;
}

export function renderSpecialistAgentInventoryContract(message: string): string {
  const domain = extractSpecialistDomain(message);
  const checkedAt = new Date().toISOString();
  if (domain) {
    const entry = SPECIALIST_AGENT_REGISTRY[domain];
    const relatedText = entry.relatedWorkflows.length ? entry.relatedWorkflows.join(', ') : 'none identified';
    return `**Specialist asked about:** ${domain} specialist agent.\n**Status:** ${entry.status}. ${entry.description}\n**Source checked:** specialist agent registry, module inventory, documented workflows.\n**Verification state:** no live specialist agent verified for this domain.\n**Related workflows/context:** ${relatedText} — these exist as Nexus context but are not a live specialist agent.\n**Blocker:** no verified live specialist agent is registered. Nexus having ${domain} context is not the same as having a live ${domain} Specialist Agent.\n**Freshness:** checked ${checkedAt}; registry is a build-time snapshot.\n**Next safe action:** draft a specialist agent definition for Ray Review, or confirm whether a specialist is planned in the product roadmap.`;
  }
  return `**Specialist asked about:** general specialist agent inventory.\n**Status:** no verified live specialist agents are registered in the specialist registry.\n**Source checked:** specialist agent registry, module inventory, documented workflows.\n**Verification state:** no live specialist agents verified.\n**Known workflow context:** credit/funding readiness, research engine, trading proof, client profiles, scheduling — these are Nexus context modules, not live specialist agents.\n**Blocker:** no specialist agents have been registered as live, verified agents.\n**Freshness:** checked ${checkedAt}; registry is a build-time snapshot.\n**Next safe action:** draft specialist agent definitions for Ray Review, or confirm whether specialist agents are planned in the product roadmap.`;
}
