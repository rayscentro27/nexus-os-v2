import operationsSnapshot from '../../reports/nexus_operations_status_latest.json';
import processInventorySnapshot from '../../reports/nexus_process_inventory_latest.json';
import schedulerInventorySnapshot from '../../reports/nexus_scheduler_inventory_latest.json';
import hermesOperationsSnapshot from '../../reports/hermes_operations_status_latest.json';
import { rayReviewCards } from '../data/rayReviewData.js';
import { isSupabaseConfigured, supabase } from './supabaseClient';

export const HERMES_OPERATIONAL_INTELLIGENCE_VERSION = 'Hermes Operational Intelligence v2.1';
export const PROCESS_REGISTRY_SCHEMA_VERSION = 'nexus-process-registry-v1';

export type OperationalState =
  | 'CONNECTED'
  | 'UNAVAILABLE'
  | 'NOT_CHECKED'
  | 'LOCAL_FALLBACK'
  | 'CURRENT'
  | 'STALE'
  | 'SIMULATED'
  | 'UNKNOWN';

export interface OperationalProbe {
  label: string;
  state: OperationalState;
  checkedAt: string;
  source: string;
  detail: string;
  recordCount?: number;
  failureReason?: string;
}

export interface OperationalAnswer {
  handled: boolean;
  text: string;
  provenance: {
    source: string;
    lastUpdated: string;
    recordCount: number;
    confidence: OperationalState;
    unavailableSources: string[];
  };
}

type SnapshotItem = {
  name?: string;
  status?: string;
  checked_at?: string;
  proof?: string;
  command?: string;
  loaded?: boolean;
  running_now?: boolean;
  last_metadata_fetch?: string | null;
  last_transcript_fetch?: string | null;
  safe_next_action?: string;
  limitations?: string[];
};

const nowIso = () => new Date().toISOString();
const asRecord = (value: unknown): Record<string, unknown> => (value && typeof value === 'object' ? value as Record<string, unknown> : {});
const operations = asRecord(operationsSnapshot);
const processInventory = asRecord(processInventorySnapshot);
const schedulerInventory = asRecord(schedulerInventorySnapshot);
const hermesOperations = asRecord(hermesOperationsSnapshot);

function itemsFrom(snapshot: Record<string, unknown>): SnapshotItem[] {
  const items = snapshot.items;
  return Array.isArray(items) ? items as SnapshotItem[] : [];
}

function checkedAt(snapshot: Record<string, unknown>): string {
  return typeof snapshot.checked_at === 'string' ? snapshot.checked_at : 'unknown';
}

export function ageHours(timestamp: string, now = new Date()): number | null {
  const parsed = Date.parse(timestamp);
  if (!Number.isFinite(parsed)) return null;
  return Math.max(0, (now.getTime() - parsed) / 36e5);
}

export function freshnessState(timestamp: string, maxFreshHours = 24): OperationalState {
  const age = ageHours(timestamp);
  if (age === null) return 'UNKNOWN';
  return age <= maxFreshHours ? 'CURRENT' : 'STALE';
}

export function getBundledOperationalSnapshot() {
  const processes = itemsFrom(processInventory);
  const schedulers = itemsFrom(schedulerInventory);
  const operationsCheckedAt = checkedAt(operations);
  const hermesCheckedAt = typeof hermesOperations.generated_at === 'string' ? hermesOperations.generated_at : checkedAt(hermesOperations);
  const processCheckedAt = checkedAt(processInventory);
  const schedulerCheckedAt = checkedAt(schedulerInventory);
  const freshState = freshnessState(processCheckedAt);
  return {
    checkedAt: processCheckedAt,
    operationsCheckedAt,
    hermesCheckedAt,
    schedulerCheckedAt,
    freshness: freshState,
    stale: freshState === 'STALE',
    processes,
    schedulers,
    runningProcesses: processes.filter((item) => item.status === 'live_running' || item.running_now),
    failedProcesses: processes.filter((item) => /fail|error|down/i.test(String(item.status || ''))),
    simulatedProcesses: processes.filter((item) => /simulated|mock/i.test(`${item.status || ''} ${item.proof || ''} ${item.command || ''}`)),
    blockedProcesses: processes.filter((item) => /blocked|gated/i.test(`${item.status || ''} ${item.safe_next_action || ''}`)),
    loadedSchedulers: schedulers.filter((item) => item.loaded),
  };
}

export async function probeSupabaseHealth(): Promise<OperationalProbe> {
  const checkedAt = nowIso();
  if (!isSupabaseConfigured || !supabase) {
    return {
      label: 'Supabase',
      state: 'UNAVAILABLE',
      checkedAt,
      source: 'browser_config',
      detail: 'Supabase browser client is not configured.',
      failureReason: 'missing_browser_env',
    };
  }
  try {
    const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
    if (sessionError) {
      return {
        label: 'Supabase',
        state: 'UNAVAILABLE',
        checkedAt,
        source: 'supabase.auth.getSession',
        detail: 'Supabase session probe failed.',
        failureReason: sessionError.message,
      };
    }
    if (!sessionData.session) {
      return {
        label: 'Supabase',
        state: 'UNAVAILABLE',
        checkedAt,
        source: 'supabase.auth.getSession',
        detail: 'Supabase client is configured, but no authenticated session is present.',
        failureReason: 'no_authenticated_session',
      };
    }
    const { error, count } = await supabase
      .from('system_health')
      .select('id', { count: 'exact', head: true });
    if (error) {
      return {
        label: 'Supabase',
        state: 'UNAVAILABLE',
        checkedAt,
        source: 'system_health',
        detail: 'Authenticated Supabase probe failed under current RLS/session.',
        failureReason: error.message,
      };
    }
    return {
      label: 'Supabase',
      state: 'CONNECTED',
      checkedAt,
      source: 'system_health',
      detail: 'Authenticated read probe succeeded.',
      recordCount: count ?? 0,
    };
  } catch (error) {
    return {
      label: 'Supabase',
      state: 'UNAVAILABLE',
      checkedAt,
      source: 'supabase_probe',
      detail: 'Supabase probe threw before completing.',
      failureReason: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function probeHermesModelHealth(): Promise<OperationalProbe> {
  const checkedAt = nowIso();
  if (!supabase || (import.meta.env.VITE_HERMES_CHAT_ENABLED as string | undefined) !== 'true') {
    return {
      label: 'Model',
      state: 'LOCAL_FALLBACK',
      checkedAt,
      source: 'hermes_model_gateway',
      detail: 'Hermes model gateway is not enabled in this browser environment; deterministic local fallback is active.',
      failureReason: 'gateway_not_enabled',
    };
  }
  try {
    const { data, error } = await supabase.functions.invoke('hermes-chat', {
      body: { message: 'health probe: answer ok only', mode: 'health_probe', context: { facts: 'No client data. Probe only.' } },
    });
    if (error || !data || data.configured === false || !data.reply) {
      return {
        label: 'Model',
        state: 'UNAVAILABLE',
        checkedAt,
        source: 'hermes-chat',
        detail: 'Hermes model gateway did not return a usable probe response.',
        failureReason: error?.message || String(data?.error || 'not_configured_or_empty'),
      };
    }
    return {
      label: 'Model',
      state: 'CONNECTED',
      checkedAt,
      source: 'hermes-chat',
      detail: `Provider probe succeeded${data.metadata?.provider ? ` via ${data.metadata.provider}` : ''}.`,
      recordCount: 1,
    };
  } catch (error) {
    return {
      label: 'Model',
      state: 'UNAVAILABLE',
      checkedAt,
      source: 'hermes-chat',
      detail: 'Hermes model gateway probe threw before completing.',
      failureReason: error instanceof Error ? error.message : String(error),
    };
  }
}

function sourceFooter(input: OperationalAnswer['provenance']): string {
  const unavailable = input.unavailableSources.length ? input.unavailableSources.join(', ') : 'none';
  return `\n\nSource: ${input.source}\nLast updated: ${input.lastUpdated}\nRecord count: ${input.recordCount}\nConfidence/state: ${input.confidence}\nUnavailable sources: ${unavailable}`;
}

function processLabel(item: SnapshotItem): string {
  return item.name || item.command || item.proof || 'unnamed process';
}

export function answerOperationalQuestion(message: string): OperationalAnswer {
  const text = message.toLowerCase();
  const snapshot = getBundledOperationalSnapshot();
  const unavailableSources = snapshot.stale ? ['fresh_local_collector', 'live_supabase_registry', 'production_runtime_registry'] : ['live_supabase_registry', 'production_runtime_registry'];
  const provenance = {
    source: 'bundled Mac Mini operations snapshot plus local registry metadata',
    lastUpdated: snapshot.checkedAt,
    recordCount: snapshot.processes.length,
    confidence: snapshot.freshness,
    unavailableSources,
  };
  const stalePrefix = snapshot.stale
    ? `The bundled operations snapshot is stale (${snapshot.checkedAt}), so this is not a current live-process certification.\n\n`
    : '';

  if (/\b(running right now|currently run|currently running|what is running|processes currently run)\b/.test(text)) {
    const rows = snapshot.runningProcesses.slice(0, 8).map((item) => `- ${processLabel(item)} (${item.proof || item.status || 'proof unavailable'})`);
    const body = rows.length
      ? `${stalePrefix}Processes with bundled direct running proof:\n${rows.join('\n')}`
      : `${stalePrefix}No process has current direct running proof in the bundled snapshot.`;
    return { handled: true, text: `${body}${sourceFooter(provenance)}`, provenance };
  }

  if (/\b(ran today|what ran|latest successes|most recently)\b/.test(text)) {
    const schedulers = snapshot.schedulers.slice(0, 8).map((item) => `- ${processLabel(item)}: ${item.status || 'unknown'}; proof: ${item.proof || 'not recorded'}`);
    return {
      handled: true,
      text: `${stalePrefix}I can list scheduled/observed jobs from the snapshot, but I cannot certify today's run history without the live registry or refreshed collector.\n${schedulers.join('\n') || '- No scheduler rows available.'}${sourceFooter(provenance)}`,
      provenance,
    };
  }

  if (/\b(failed|failure|what failed|which processes failed)\b/.test(text)) {
    const rows = snapshot.failedProcesses.map((item) => `- ${processLabel(item)}: ${item.status || 'failed'}; ${item.proof || 'no proof text'}`);
    return {
      handled: true,
      text: `${stalePrefix}${rows.length ? `Failures in the bundled snapshot:\n${rows.join('\n')}` : 'No failed process rows are present in the bundled snapshot. This is not proof that production has no failures.'}${sourceFooter(provenance)}`,
      provenance,
    };
  }

  if (/\b(blocked|mock-only|mock only|simulated|not configured|unavailable)\b/.test(text)) {
    const simulated = snapshot.simulatedProcesses.map(processLabel);
    const blocked = snapshot.blockedProcesses.map(processLabel);
    const lines = [
      /\b(plan|prepare)\b/.test(text) ? 'Plan, not execution: this is conversation-only. Nothing has been created, nothing has been saved, no task has been assigned, approved, or executed.' : '',
      `Simulated/mock rows: ${simulated.length ? simulated.slice(0, 6).join('; ') : 'none in bundled process inventory'}.`,
      `Blocked/gated rows: ${blocked.length ? blocked.slice(0, 6).join('; ') : 'none in bundled process inventory'}.`,
      'Known unavailable sources: live Supabase registry and production runtime registry were not queried by this browser answer.',
    ].filter(Boolean);
    return { handled: true, text: `${stalePrefix}${lines.join('\n')}${sourceFooter(provenance)}`, provenance };
  }

  if (/\b(research ran|research produce|research results|where.*research.*go|youtube)\b/.test(text)) {
    const youtube = asRecord(operations.youtube_research);
    const status = typeof youtube.status === 'string' ? youtube.status : 'unknown';
    const destination = 'local reports/data exports unless an explicit Supabase write script is run and verified';
    return {
      handled: true,
      text: `${stalePrefix}Research status from the bundled snapshot: ${status}.\nResults destination: ${destination}.\nHermes/Alpha/Clyde/Ray Review consumer status: not live-certified from this answer; report-backed only unless a fresh ingestion record exists.${sourceFooter(provenance)}`,
      provenance,
    };
  }

  if (/\bwhat (?:still )?needs my approval\b|\bwhat needs approval before action\b|\bapproval|approvals|ray review\b/.test(text)) {
    const pending = rayReviewCards.filter((card) => String(card.status || '').toLowerCase() === 'pending');
    const top = pending.slice(0, 5).map((card) => `- ${card.title} (${card.category}; ${card.riskLevel || 'risk not labeled'})`);
    return {
      handled: true,
      text: `${stalePrefix}Approval inventory from the bundled Ray Review registry:\n${top.length ? top.join('\n') : '- No pending bundled Ray Review cards are present.'}\n\napproval_required: ${pending.length > 0 ? 'true for pending Ray Review items' : 'none in bundled registry'}\napproval_status: ${pending.length > 0 ? 'pending Ray Davis / Ray Review decision' : 'no pending bundled approvals'}\napproval_reason: Credit and Funding, Engineering, external, consequential, or approval-gated work remains blocked until Ray Review.\nray_review_id: ${pending[0]?.id || 'unavailable in bundled registry'}\nproposed_action: open Ray Review, inspect Engineering and Credit and Funding items, then approve, revise, or hold from the review queue.\nexecution_blocked: true; Hermes cannot approve, send, charge, deploy, trade, or submit from this answer.\nnext_permitted_action: Ray Davis may open Ray Review and inspect the highest-impact pending item.\nprovenance: bundled Ray Review registry plus operational snapshot; not a fresh Supabase approval query.${sourceFooter({ ...provenance, source: 'bundled Ray Review registry plus local operational snapshot', recordCount: pending.length })}`,
      provenance: { ...provenance, source: 'bundled Ray Review registry plus local operational snapshot', recordCount: pending.length },
    };
  }

  if (/\b(provider|model|supabase connected|is supabase connected|version|deployed)\b/.test(text)) {
    const liveSections = Object.keys(asRecord(hermesOperations.live_sections));
    return {
      handled: true,
      text: `${stalePrefix}Hermes version: ${HERMES_OPERATIONAL_INTELLIGENCE_VERSION}.\nProvider/model status: Nexus-native deterministic Workroom response; TEST_ONLY / EVIDENCE_CONFLICTED for live provider use because no current model probe ran in this synchronous answer. OpenRouter or another provider is not certified active from this response.\nProcess registry schema: ${PROCESS_REGISTRY_SCHEMA_VERSION}.\nSupabase/model/deployment require live probes; this synchronous answer did not run them.\nBundled Hermes live-section claims: ${liveSections.length ? liveSections.join(', ') : 'none'}; treat them as report-backed, not current live proof.${sourceFooter(provenance)}`,
      provenance,
    };
  }

  if (/\b(process|job|scheduler|schedule|approval|approvals|client.*attention|system health|stale reports?)\b/.test(text)) {
    return {
      handled: true,
      text: `${stalePrefix}Operational summary:\n- Process rows in bundled snapshot: ${snapshot.processes.length}\n- Running-proof rows: ${snapshot.runningProcesses.length}\n- Scheduler rows: ${snapshot.schedulers.length}\n- Loaded scheduler rows: ${snapshot.loadedSchedulers.length}\n- Failed rows in snapshot: ${snapshot.failedProcesses.length}\n\nThis answer distinguishes configured/loaded records from running proof. It does not claim production or Supabase state without a live probe.${sourceFooter(provenance)}`,
      provenance,
    };
  }

  return {
    handled: false,
    text: '',
    provenance,
  };
}
