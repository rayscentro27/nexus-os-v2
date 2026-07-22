// Supabase Edge Function — Hermes chat (SERVER-SIDE ONLY; holds provider keys).
//
// Provider is selected by env (NOT hardcoded): HERMES_CHAT_PROVIDER = openrouter | gemini | ollama.
// The key for the chosen provider (OPENROUTER_API_KEY / GEMINI_API_KEY / OLLAMA_URL) lives in
// Supabase function secrets — never in the browser. If the provider/key is missing, returns
// { configured: false } and the UI says "Hermes chat provider is not configured yet." We never
// fake current facts. Private data is refused by the firewall before any external call.
//
// Prompt layout (ordered for prompt caching):
//   1. system: STABLE_CONTEXT_BLOCK  — byte-stable identity/Nexus/GoClear context (cached prefix)
//   2. system: dynamic safe context  — small, per-request, from the admin frontend (not cached)
//   3. recent safe history + pending action context (bounded / firewall-checked)
//   4. user:   Ray's current message
// Only PUBLIC / internal_summary data ever reaches the provider; the firewall scans the message
// (refuse) and every dynamic-context field (dropped if it trips the gate) before any external call.
//
// NOTE: deploy only when keys are configured.

import { isSensitive, json, cors } from '../_shared/firewall.ts';

// ── Cost / safety guards ──
const MAX_INPUT_CHARS = 24000;      // ~6000 tokens
const MAX_OUTPUT_TOKENS = 1200;     // hard cap on response length
const MAX_HISTORY_TURNS = 10;
const MAX_HISTORY_CHARS = 4000;
const ALLOWED_PROVIDERS = new Set(['openrouter', 'gemini', 'ollama']);
const MODEL_ALLOWLIST: Record<string, string[]> = {
  openrouter: ['openai/gpt-4o-mini', 'openai/gpt-4o', 'anthropic/claude-3.5-sonnet', 'google/gemini-2.0-flash-001', 'auto'],
  gemini: ['gemini-1.5-flash', 'gemini-1.5-pro'],
  ollama: ['llama3.1', 'qwen2.5:0.5b', 'gemma3:1b'],
};
const REJECT_ACTIONS = /\b(send|email|publish|post|deploy|charge|trade|dispute|seed|sql|drop|truncate|delete|start\s+live|stop\s+live|turn\s+on\s+live|activate\s+live|place\s+live\s+trades?)\b/i;
const SELF_AUTHORIZATION_ACTIONS = /\b(approve it yourself|approve yourself|self[- ]approve|execute it now|run it now)\b/i;

// Stable, cached identity + business context. Keep this byte-stable to maximize prompt-cache hits;
// bump HERMES_CONTEXT_VERSION to intentionally bust the cache after edits. Contains only
// internal_summary-level business context — never secrets or customer data.
const STABLE_CONTEXT_BLOCK = `[HERMES — STABLE CONTEXT]

IDENTITY
You are Hermes, Ray's private conversational advisor and report interpreter for Nexus OS.
You are direct, concise, practical, and honest — no filler, no hype. If you are unsure of a
current fact, say so; never fabricate.
Hermes was created by Ray Davis. If asked who created you, say Ray Davis.

WHO RAY IS
Ray (goclearonline@gmail.com) is the founder/operator. He values blunt recommendations with
trade-offs and the fastest SAFE next step, tight scope, no guarantees he cannot back, and clean
safety/repo discipline over speed.

WHAT NEXUS OS IS
Nexus OS is Ray's Supabase-first operating system: an event ledger (source of truth), a bounded
job runner, approvals, and an admin dashboard. It coordinates content, monetization research,
report review, and approval-gated actions. Nothing publishes, sends, trades, or deploys without
Ray's explicit approval.

GOCLEAR / APEX
GoClear (GoClearOnline) is Ray's main operating brand for his credit and funding readiness
direction. "Clear Credentials" is only the existing Facebook/social brand and is referenced just
when a workflow involves that page/account — it is not the main product name. Apex is the
funding/readiness side of the same GoClear money path; GoClear/Apex is Ray's credit and funding
readiness direction (not a separate legal entity, ownership structure, or product line).

FIRST MONEY PATH
The first money path is a $97 credit/funding readiness review. Understand it as: intake →
readiness review → safe report → follow-up recommendation → a possible task request (landing
page, outreach, or client workflow).

COMPLIANCE (hard)
Never promise or imply guaranteed funding, guaranteed approval, guaranteed credit repair,
guaranteed score increase, guaranteed deletion, or guaranteed financing outcomes. Use readiness,
education, preparation, and next-step language only.

YOUR ROLE
Advise on business and strategy, interpret safe Nexus reports in plain English, ask smart
follow-up questions, and recommend actions. You propose APPROVAL-GATED task requests but never
execute them. You do not publish, send, trade, deploy, or reset passwords directly. Private and
internal workers handle sensitive or executing tasks and return REDACTED status only.

DATA FIREWALL (hard)
You may use only PUBLIC and internal_summary data. You must NEVER receive or repeat SSNs, full
credit reports, bank or tax documents, passwords, reset tokens, service-role keys, secrets, or
raw customer files (customer_private, credit_sensitive, funding_sensitive, auth_sensitive,
secrets, or raw trading_sensitive). If asked to view sensitive data, refuse and offer to create
a private-worker task request if Ray approves. Never send private data to public search or
external models.

TASK REQUESTS
Create a structured task request only after Ray clearly approves — never auto-create one from
normal conversation. Each request is labeled by sensitivity and assigned to a worker; privileged
tasks go to private/internal (non-internet) workers with status-only visibility to you.

REPORT READER
Explain only safe summaries (system health, ledger event titles, counts). Translate them into
plain business meaning plus a recommended next step. Never echo private numbers to any external
source.

TONE
Confident, concise, advisory. Lead with the recommendation, then the why, then the next safe step.

MODEL-FIRST CONVERSATION
You may answer ordinary general-knowledge and conversational questions without requiring a Nexus
evidence source. First determine whether the message can be answered from general language,
identity, or the visible conversation. Use Nexus evidence only when current private Nexus facts or
governed actions are required. When Ray refers to "that," "them," "number three," or "what you just
said," use the most recent visible conversation first. When Ray corrects you, acknowledge the
mismatch and continue naturally. Do not expose hidden reasoning.`;

const CONTEXT_VERSION = Deno.env.get('HERMES_CONTEXT_VERSION') ?? 'v1';
const stableSystem = () => `${STABLE_CONTEXT_BLOCK}\n[context_version: ${CONTEXT_VERSION}]`;

// Server-side firewall scan. Uses the shared gate plus a belt-and-suspenders plural-SSN pattern
// (the shared \bssn\b does not match "SSNs"). Never weakens an existing rule — only adds coverage.
const PLURAL_SSN = /\bssns\b/i;
const blocked = (text: string): boolean => isSensitive(text) || PLURAL_SSN.test(text || '');

const MAX_CONTEXT_FIELD = 600;   // cap each dynamic field
const MAX_CONTEXT_TOTAL = 2000;  // cap the whole dynamic block

// Build the small dynamic context block from safe frontend-supplied fields. Any field that trips
// the firewall is dropped (never sent to the model). Returns '' when there's nothing safe to add.
function buildDynamicContext(mode: string, ctx: Record<string, unknown> | undefined): string {
  const lines: string[] = [`[CURRENT CONTEXT — not cached]`, `Mode: ${String(mode).slice(0, 40)}`];
  const add = (label: string, val: unknown) => {
    const s = (val == null ? '' : String(val)).trim();
    if (!s || blocked(s)) return;                 // empty or sensitive → skip
    lines.push(`${label}: ${s.slice(0, MAX_CONTEXT_FIELD)}`);
  };
  if (ctx) {
    add('Pending action awaiting approval', ctx.pending);
    add('Safe Nexus snapshot', ctx.facts);
    add('Latest safe report (internal_summary)', ctx.report);
    add('Latest task status (redacted)', ctx.taskStatus);
    const pending = ctx.pendingAction as Record<string, unknown> | undefined;
    if (pending) {
      add('Pending action title', pending.title);
      add('Pending action safe summary', pending.safe_summary);
      add('Pending action worker', pending.proposed_worker_type);
      add('Pending action visibility', pending.hermes_visibility);
    }
  }
  if (lines.length <= 2) return '';               // only the header/mode → nothing useful
  return lines.join('\n').slice(0, MAX_CONTEXT_TOTAL);
}

interface ChatMessage { role: 'system' | 'user' | 'assistant' | 'tool'; content: string; name?: string; tool_call_id?: string; }

type HermesTurnDecision =
  | { type: 'DIRECT_RESPONSE'; response: string }
  | { type: 'TOOL_REQUEST'; toolName: string; arguments: Record<string, unknown>; reasonSummary: string }
  | { type: 'CLARIFICATION'; question: string; missingFields: string[] };

type EvidenceObligation =
  | {
      required: false;
      reason:
        | 'GENERAL_CONVERSATION'
        | 'GENERAL_KNOWLEDGE'
        | 'WRITING'
        | 'BRAINSTORMING'
        | 'PERSONAL_CONVERSATION'
        | 'NON_CURRENT_REASONING';
    }
  | {
      required: true;
      obligation: 'CURRENT_NEXUS_FACT' | 'PRIVATE_OPERATIONAL_FACT' | 'GOVERNED_DRAFT_ACTION';
      allowedTools: string[];
      missingFields?: string[];
      reasonSummary: string;
    };

type PendingScheduleState = {
  kind: 'schedule_report';
  reportId?: string;
  reportName?: string;
  date?: string;
  time?: string;
  timezone?: string;
  createRequested: boolean;
  creationBlocked: boolean;
  status: 'collecting' | 'ready' | 'drafted' | 'cancelled';
  version: number;
  createdAt: string;
  updatedAt: string;
  expiresAt: string;
};

type HermesReferenceState = {
  sourceType: 'report_search' | 'report_list';
  query?: string;
  items: Array<{
    id: string;
    label: string;
    safeSummary?: string;
    createdAt?: string;
    metadata?: Record<string, string | number | boolean | null>;
  }>;
  version: number;
  createdAt: string;
  expiresAt: string;
};

type HermesSessionState = {
  pendingAction?: PendingScheduleState | null;
  referenceState?: HermesReferenceState | null;
  version: number;
};

type HermesTurnLane =
  | { lane: 'GENERAL_CONVERSATION' }
  | { lane: 'CURRENT_FACT'; allowedTools: string[] }
  | { lane: 'SCHEDULE_WORKFLOW'; allowedTools: string[]; workflowState: PendingScheduleState; instruction: string }
  | { lane: 'REPORT_REFERENCE'; allowedTools: string[]; referenceState: HermesReferenceState; reportId?: string; metadataOnly?: boolean }
  | { lane: 'CANCELLED_WORKFLOW'; remainingMessage?: string };

type ToolActionClass = 'READ_ONLY' | 'DRAFT_ONLY' | 'APPROVAL_REQUIRED';
type ToolResult = {
  ok: boolean;
  toolName: string;
  data?: Record<string, unknown>;
  errorCode?: string;
  evidenceSources: string[];
  freshness: string;
};
type ToolDefinition = {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  requiredRole: string[];
  requiredCapabilities: string[];
  dataClassification: 'PUBLIC' | 'INTERNAL_SUMMARY' | 'CLIENT_AGGREGATE' | 'SENSITIVE_INTERNAL';
  actionClass: ToolActionClass;
  execute: (ctx: ToolExecutionContext, args: Record<string, unknown>) => Promise<ToolResult>;
};
type ToolExecutionContext = {
  actorRole: string;
  tenantId: string;
  traceId: string;
  authorization: string;
};
type OpenRouterResult =
  | {
      ok: true;
      reply: string;
      toolCalls?: unknown[];
      model: string;
      fallbackUsed: boolean;
      usage: unknown;
      durationMs: number;
    }
  | {
      ok: false;
      errorCode: string;
      model: string;
      fallbackUsed: boolean;
      durationMs: number;
    };

type CapabilityDecision =
  | { allowed: true; mode: 'READ_ONLY' | 'DRAFT_ONLY' }
  | {
      allowed: false;
      reasonCode:
        | 'UNKNOWN_TOOL'
        | 'INVALID_ARGUMENTS'
        | 'UNAUTHORIZED_ACTOR'
        | 'TENANT_MISMATCH'
        | 'CAPABILITY_DENIED'
        | 'APPROVAL_REQUIRED'
        | 'SELF_APPROVAL_PROHIBITED'
        | 'RATE_LIMITED'
        | 'DUPLICATE_ACTION'
        | 'DATA_CLASSIFICATION_DENIED';
    };

const REPORTS = [
  { id: 'nexus_3_hermes_existing_openrouter_model_first', title: 'Hermes Existing OpenRouter Model-First Routing Repair', category: 'architecture', createdAt: '2026-07-20', freshness: 'CURRENT_BRANCH', source: 'reports/architecture/nexus_3_hermes_existing_openrouter_model_first.md', summary: 'Documents the old deterministic route, existing OpenRouter smoke proof, and model-first routing repair.' },
  { id: 'nexus_3_department_operations_status', title: 'Department Operations Status', category: 'runtime', createdAt: '2026-07-20', freshness: 'SYNTHETIC_READ_MODEL', source: 'reports/runtime/nexus_3_department_operations_status.json', summary: 'Reports Wave 4 department registry and queue read model state. Durable production queue persistence depends on the unapplied department migration.' },
  { id: 'nexus_3_hermes_model_first_status', title: 'Hermes Model-First Status', category: 'runtime', createdAt: '2026-07-20', freshness: 'CURRENT_BRANCH', source: 'reports/runtime/nexus_3_hermes_model_first_status.json', summary: 'Tracks OpenRouter provider, model-first routing state, direct model smoke, and pilot certification status.' },
  { id: 'nexus_3_capability_registry', title: 'Nexus Capability Registry', category: 'runtime', createdAt: '2026-07-20', freshness: 'REPORT_BACKED', source: 'reports/runtime/nexus_3_capability_registry.json', summary: 'Capability OS registry summary for activation, approval, and policy boundaries.' },
];

const SESSION_MEMORY = new Map<string, HermesSessionState>();

function isoIn(minutes: number): string {
  return new Date(Date.now() + minutes * 60_000).toISOString();
}

function traceId(): string {
  return `hermes-model-first-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`;
}

function safeObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringArg(args: Record<string, unknown>, key: string): string {
  return typeof args[key] === 'string' ? String(args[key]).slice(0, 240) : '';
}

function actorIdFromAuthorization(authorization: string): string {
  const fallback = '00000000-0000-0000-0000-000000000001';
  try {
    const token = authorization.replace(/^Bearer\s+/i, '');
    const payload = token.split('.')[1];
    if (!payload) return fallback;
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    const sub = typeof decoded?.sub === 'string' ? decoded.sub : '';
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(sub) ? sub : fallback;
  } catch {
    return fallback;
  }
}

function stateKey(userId: string, conversationId: string): string {
  return `${userId}:${conversationId || 'default'}`;
}

function scrubSessionState(state: HermesSessionState): HermesSessionState {
  const now = Date.now();
  const pending = state.pendingAction && Date.parse(state.pendingAction.expiresAt) > now && state.pendingAction.status !== 'cancelled'
    ? state.pendingAction
    : null;
  const reference = state.referenceState && Date.parse(state.referenceState.expiresAt) > now
    ? { ...state.referenceState, items: state.referenceState.items.slice(0, 20) }
    : null;
  return { pendingAction: pending, referenceState: reference, version: Number(state.version || 1) };
}

async function loadHermesState(userId: string, conversationId: string): Promise<HermesSessionState> {
  const url = Deno.env.get('SUPABASE_URL') || Deno.env.get('PROJECT_URL');
  const service = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  if (url && service) {
    const endpoint = `${url.replace(/\/$/, '')}/rest/v1/hermes_conversation_state?user_id=eq.${encodeURIComponent(userId)}&conversation_id=eq.${encodeURIComponent(conversationId)}&select=pending_action,reference_state,version&limit=1`;
    const res = await fetch(endpoint, { headers: { apikey: service, authorization: `Bearer ${service}` } }).catch(() => null);
    if (res?.ok) {
      const rows = await res.json().catch(() => []);
      const row = Array.isArray(rows) ? rows[0] : null;
      if (row) return scrubSessionState({ pendingAction: row.pending_action ?? null, referenceState: row.reference_state ?? null, version: Number(row.version || 1) });
    }
  }
  return scrubSessionState(SESSION_MEMORY.get(stateKey(userId, conversationId)) || { pendingAction: null, referenceState: null, version: 1 });
}

async function saveHermesState(userId: string, tenantId: string | null, conversationId: string, state: HermesSessionState): Promise<void> {
  const clean = scrubSessionState({ ...state, version: Number(state.version || 1) + 1 });
  SESSION_MEMORY.set(stateKey(userId, conversationId), clean);
  const url = Deno.env.get('SUPABASE_URL') || Deno.env.get('PROJECT_URL');
  const service = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  if (!url || !service) return;
  const body: Record<string, unknown> = {
    user_id: userId,
    conversation_id: conversationId,
    pending_action: clean.pendingAction,
    reference_state: clean.referenceState,
    version: clean.version,
    expires_at: isoIn(240),
    updated_at: new Date().toISOString(),
  };
  if (tenantId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(tenantId)) body.tenant_id = tenantId;
  await fetch(`${url.replace(/\/$/, '')}/rest/v1/hermes_conversation_state?on_conflict=user_id,conversation_id`, {
    method: 'POST',
    headers: { apikey: service, authorization: `Bearer ${service}`, 'content-type': 'application/json', prefer: 'resolution=merge-duplicates,return=minimal' },
    body: JSON.stringify(body),
  }).catch(() => undefined);
}

function reportTags(report: typeof REPORTS[number]): string[] {
  const text = `${report.id} ${report.title} ${report.category} ${report.summary} ${report.source}`.toLowerCase();
  const tags = new Set<string>();
  if (/hermes|model|openrouter|routing|pilot|certification|tool/.test(text)) ['hermes', 'model-first', 'openrouter', 'tool-gateway', 'certification'].forEach((tag) => tags.add(tag));
  if (/alpha|provider|routing/.test(text)) ['alpha', 'provider-routing'].forEach((tag) => tags.add(tag));
  if (/department|operations|queue|workflow|client/.test(text)) ['department-operations', 'workflow', 'client-workflow'].forEach((tag) => tags.add(tag));
  if (/capability|approval|policy|boundary|ray review/.test(text)) ['capability-os', 'approval-boundary', 'policy'].forEach((tag) => tags.add(tag));
  if (/revenue|readiness|funding|credit|money/.test(text)) ['revenue-readiness', 'credit-funding'].forEach((tag) => tags.add(tag));
  if (/repo|repository|intelligence/.test(text)) tags.add('repo-intelligence');
  return [...tags];
}

function searchReportCatalog(query: string, limit = 10) {
  const terms = query.toLowerCase().split(/[^a-z0-9]+/).filter((term) => term.length > 2);
  return REPORTS.map((report) => {
    const tags = reportTags(report);
    const haystack = `${report.id} ${report.title} ${report.category} ${report.summary} ${report.source} ${tags.join(' ')}`.toLowerCase();
    const score = terms.reduce((sum, term) => sum + (haystack.includes(term) ? 1 : 0), 0)
      + (/\bmodel[- ]?first\b/i.test(query) && tags.includes('model-first') ? 4 : 0)
      + (/\balpha\b/i.test(query) && tags.includes('alpha') ? 3 : 0)
      + (/\brepo|repository\b/i.test(query) && tags.includes('repo-intelligence') ? 3 : 0)
      + (/\brevenue|readiness|funding|credit\b/i.test(query) && tags.includes('revenue-readiness') ? 3 : 0)
      + (/\bclient|workflow\b/i.test(query) && tags.includes('client-workflow') ? 2 : 0)
      + (/\bcapability|approval|boundary\b/i.test(query) && tags.includes('capability-os') ? 3 : 0);
    return { report, tags, score };
  }).filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || String(b.report.createdAt).localeCompare(String(a.report.createdAt)))
    .slice(0, Math.max(1, Math.min(10, limit)))
    .map(({ report, tags }) => ({ id: report.id, title: report.title, safeSummary: report.summary, tags, createdAt: report.createdAt, sourceType: report.category }));
}

function currentPhoenixTime(timezone = 'America/Phoenix') {
  const tz = /phoenix|arizona/i.test(timezone) ? 'America/Phoenix' : timezone;
  const now = new Date();
  return {
    currentTime: now.toLocaleString('en-US', { timeZone: tz, weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }),
    timezone: tz,
    source: 'SYSTEM_CLOCK',
    freshness: 'CURRENT',
  };
}

async function supabaseCount(table: string, authorization: string): Promise<number | null> {
  const url = Deno.env.get('SUPABASE_URL') || Deno.env.get('PROJECT_URL');
  const anon = Deno.env.get('SUPABASE_ANON_KEY');
  if (!url || !anon || !authorization) return null;
  const res = await fetch(`${url.replace(/\/$/, '')}/rest/v1/${table}?select=*`, {
    method: 'HEAD',
    headers: {
      apikey: anon,
      authorization,
      prefer: 'count=exact',
    },
  }).catch(() => null);
  if (!res?.ok) return null;
  const range = res.headers.get('content-range') || '';
  const count = Number(range.split('/')[1]);
  return Number.isFinite(count) ? count : null;
}

function toolResult(toolName: string, data: Record<string, unknown>, evidenceSources: string[], freshness = 'CURRENT'): ToolResult {
  return { ok: true, toolName, data, evidenceSources, freshness };
}

const toolRegistry: Record<string, ToolDefinition> = {
  get_current_time: {
    name: 'get_current_time',
    description: 'Get current date and time. Use for current time/date questions.',
    inputSchema: { type: 'object', properties: { timezone: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_current_time_tool'],
    dataClassification: 'PUBLIC',
    actionClass: 'READ_ONLY',
    execute: async (_ctx, args) => toolResult('get_current_time', currentPhoenixTime(stringArg(args, 'timezone') || 'America/Phoenix'), ['system_clock']),
  },
  get_hermes_identity: {
    name: 'get_hermes_identity',
    description: 'Get Hermes identity and creation evidence state. Use for identity or age questions.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_general_language_interpretation'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_hermes_identity', { name: 'Hermes', role: "Ray Davis's private CEO advisor and Nexus executive coordinator", createdBy: 'Ray Davis', nature: 'AI advisor', creationDates: { evidenceState: 'PARTIAL' }, source: 'Hermes stable identity context' }, ['hermes_identity_context'], 'PARTIAL'),
  },
  get_nexus_version: {
    name: 'get_nexus_version',
    description: 'Get Nexus version/deployment metadata.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_project_status_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_nexus_version', { product: 'Nexus OS', versionLabel: 'Nexus OS 3.0 Wave 4 / Hermes model-first feature branch', deployedCommit: Deno.env.get('COMMIT_REF') || Deno.env.get('NETLIFY_COMMIT_REF') || 'unknown', branch: Deno.env.get('BRANCH') || 'unknown', buildTimestamp: Deno.env.get('BUILD_ID') || undefined, source: 'deployment environment and branch reports', freshness: 'CONFIG_BACKED' }, ['deployment_environment', 'model_first_status']),
  },
  get_project_status: {
    name: 'get_project_status',
    description: 'Get approved project status summary.',
    inputSchema: { type: 'object', properties: { query: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_project_status_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_project_status', { status: 'Hermes model-first routing repair is on the feature branch. Department Operations UI/tools are deployed, but durable production queue persistence depends on the separate unapplied migration. Stripe remains test/deferred; live trading remains blocked; Alpha remains isolated.' }, ['architecture_reports', 'capability_registry']),
  },
  get_system_health: {
    name: 'get_system_health',
    description: 'Get safe system health summary.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_system_health_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_system_health', { overallState: 'DEGRADED_CONFIG_AWARE', components: [{ name: 'OpenRouter Hermes chat', state: 'LIVE', source: 'hermes-chat diagnostic', freshness: 'CURRENT' }, { name: 'Stripe live payments', state: 'NOT_CONFIGURED', source: 'Capability OS', freshness: 'REPORT_BACKED' }, { name: 'Live trading', state: 'BLOCKED_BY_POLICY', source: 'Capability OS', freshness: 'REPORT_BACKED' }, { name: 'Alpha Supabase access', state: 'BLOCKED_BY_POLICY', source: 'Brain/Profile boundary', freshness: 'REPORT_BACKED' }, { name: 'Department queues', state: 'SYNTHETIC_READ_MODEL', source: 'Wave 4 report', freshness: 'REPORT_BACKED' }], limitations: ['This is a safe summary, not raw logs.', 'Alpha remains separate and has no Supabase/client PII access.'] }, ['executive_system_health', 'capability_os']),
  },
  list_reports: {
    name: 'list_reports',
    description: 'List approved sanitized reports. Use when Ray asks what reports exist or requests a report list. Do not use when Ray refers to a specific report already present in recent conversation.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_report_catalog_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('list_reports', { reports: REPORTS.map(({ summary: _summary, ...item }) => item) }, ['sanitized_report_registry']),
  },
  search_reports: {
    name: 'search_reports',
    description: 'Search approved sanitized report metadata by topic. Use for report discovery questions such as which reports cover, support, discuss, document, certify, or contain evidence about a topic.',
    inputSchema: { type: 'object', required: ['query'], properties: { query: { type: 'string' }, limit: { type: 'number' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_report_catalog_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async (_ctx, args) => toolResult('search_reports', { query: stringArg(args, 'query'), matches: searchReportCatalog(stringArg(args, 'query'), typeof args.limit === 'number' ? args.limit : 10) }, ['sanitized_report_registry']),
  },
  summarize_report: {
    name: 'summarize_report',
    description: 'Summarize one approved report by reportId. Use when Ray requests details or a summary of one specific known report, including the latest, second, or previously listed report. Do not use for a general report catalog request.',
    inputSchema: { type: 'object', required: ['reportId'], properties: { reportId: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_report_catalog_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async (_ctx, args) => {
      const reportId = stringArg(args, 'reportId');
      const normalizedReportId = reportId.toLowerCase();
      const report = REPORTS.find((item) => item.id === reportId || item.title.toLowerCase().includes(normalizedReportId))
        || (/\bmodel\b/.test(normalizedReportId) && /\bfirst\b/.test(normalizedReportId) ? REPORTS.find((item) => item.id === 'nexus_3_hermes_model_first_status') : undefined)
        || (/\bdepartment\b/.test(normalizedReportId) ? REPORTS.find((item) => item.id === 'nexus_3_department_operations_status') : undefined)
        || (/\bcapabilit/.test(normalizedReportId) ? REPORTS.find((item) => item.id === 'nexus_3_capability_registry') : undefined);
      if (!report) return { ok: false, toolName: 'summarize_report', errorCode: 'INVALID_ARGUMENTS', evidenceSources: ['sanitized_report_registry'], freshness: 'UNKNOWN' };
      return toolResult('summarize_report', { id: report.id, title: report.title, category: report.category, summary: report.summary, source: report.source, freshness: report.freshness }, [report.source], report.freshness);
    },
  },
  get_client_aggregate: {
    name: 'get_client_aggregate',
    description: 'Get aggregate client/customer counts and synthetic-vs-real status without PII.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_customer_aggregate_tool'],
    dataClassification: 'CLIENT_AGGREGATE',
    actionClass: 'READ_ONLY',
    execute: async (ctx) => {
      const clientProfiles = await supabaseCount('client_profiles', ctx.authorization);
      const invitedClients = await supabaseCount('tenant_memberships', ctx.authorization);
      const total = Math.max(clientProfiles ?? 0, invitedClients ?? 0);
      return toolResult('get_client_aggregate', { totalClients: total, activeClients: null, syntheticClients: total || null, realClients: null, dataState: total > 0 ? 'MIXED' : 'UNKNOWN', tenantScope: ctx.tenantId, source: clientProfiles == null && invitedClients == null ? 'authorized aggregate unavailable from current token; safe report-backed limitation' : 'authorized Supabase aggregate counts', freshness: clientProfiles == null && invitedClients == null ? 'UNKNOWN' : 'CURRENT', limitations: ['No names, addresses, credit data, SSNs, bank details, or raw documents returned.', 'Real paying customer count is not claimed from synthetic/test evidence.'] }, ['client_profiles_count', 'tenant_memberships_count']);
    },
  },
  get_approval_summary: {
    name: 'get_approval_summary',
    description: 'Get safe Ray Review approval summary.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_approval_summary_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async (ctx) => {
      const pending = await supabaseCount('approvals', ctx.authorization);
      return toolResult('get_approval_summary', { pending: pending ?? 0, items: [], source: pending == null ? 'approval summary unavailable through current token' : 'approvals aggregate', freshness: pending == null ? 'UNKNOWN' : 'CURRENT' }, ['approvals_count']);
    },
  },
  get_department_status: {
    name: 'get_department_status',
    description: 'Get Department Operations status; labels synthetic read model if migration is not applied.',
    inputSchema: { type: 'object', properties: { department: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['department_operations_registry'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_department_status', { state: 'ACTIVE_PARTIAL', dataState: 'SYNTHETIC_READ_MODEL', departments: ['Operations', 'Engineering', 'Research', 'Knowledge', 'Credit and Funding'], limitation: 'Durable production queue persistence depends on the separate unapplied Department Operations migration.' }, ['wave4_department_read_model'], 'REPORT_BACKED'),
  },
  get_revenue_status: {
    name: 'get_revenue_status',
    description: 'Get safe revenue status summary.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_revenue_summary_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_revenue_status', { actualRevenue: 'UNKNOWN', testRevenue: 'TEST_MODE_ONLY', projectedRevenue: '$97 readiness-review candidate', dataState: 'PROJECTED_AND_TEST', source: 'Executive revenue summary', limitation: 'Projected revenue is not collected money.' }, ['executive_revenue_status']),
  },
  get_repo_intelligence_status: {
    name: 'get_repo_intelligence_status',
    description: 'Get approved Repo Intelligence subsystem status, repository analysis status, code intelligence status, or repository monitoring status. Do not use when Ray asks where a prior answer came from.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['repo_intelligence_registry'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_repo_intelligence_status', { state: 'REPORT_BACKED', summary: 'Repo Intelligence remains a governed capability/research track. No arbitrary GitHub or shell execution is exposed to the model.' }, ['repo_intelligence_registry']),
  },
  get_answer_provenance: {
    name: 'get_answer_provenance',
    description: 'Explain what source, model, tool, report, or evidence supported a previous Hermes answer. Do not use for Repo Intelligence subsystem status.',
    inputSchema: { type: 'object', properties: { traceId: { type: 'string' }, conversationTurnId: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_provenance_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async (_ctx, args) => toolResult('get_answer_provenance', { sourceType: 'GENERAL_MODEL', model: Deno.env.get('HERMES_MODEL') || 'openai/gpt-4o-mini', toolName: stringArg(args, 'traceId') ? undefined : 'none', evidenceSources: ['model_first_trace', 'visible_history'], freshness: 'CURRENT', limitations: ['No hidden reasoning is stored or exposed.'] }, ['model_first_trace']),
  },
  draft_task: {
    name: 'draft_task',
    description: 'Create a governed task draft only after Ray explicitly asks to create a task draft. Do not use for discussion, planning, writing, or do-not-create turns. Does not approve or execute.',
    inputSchema: { type: 'object', required: ['title', 'summary'], properties: { title: { type: 'string' }, summary: { type: 'string' }, department: { type: 'string' }, riskClass: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['governed_work'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'DRAFT_ONLY',
    execute: async (_ctx, args) => toolResult('draft_task', { draftCreated: true, draftId: `draft-task-${crypto.randomUUID()}`, title: stringArg(args, 'title'), approvalRequired: true, executionStatus: 'NOT_EXECUTED' }, ['draft_task_memory']),
  },
  draft_ray_review: {
    name: 'draft_ray_review',
    description: 'Create a Ray Review draft only after Ray explicitly asks for a Ray Review draft or approval packet. Do not use for self-approval. Cannot approve itself.',
    inputSchema: { type: 'object', required: ['title', 'summary'], properties: { title: { type: 'string' }, summary: { type: 'string' }, riskClass: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['ray_review'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'DRAFT_ONLY',
    execute: async (_ctx, args) => toolResult('draft_ray_review', { draftCreated: true, draftId: `ray-review-${crypto.randomUUID()}`, title: stringArg(args, 'title'), approvalRequired: true, selfApproval: 'PROHIBITED', executionStatus: 'NOT_EXECUTED' }, ['ray_review_draft']),
  },
  draft_schedule: {
    name: 'draft_schedule',
    description: 'Create a schedule draft only after report, date, time, and timezone details are known and Ray explicitly asks to create the draft. Do not use for planning, clarification, or do-not-create turns.',
    inputSchema: { type: 'object', properties: { reportId: { type: 'string' }, reportName: { type: 'string' }, requestedDate: { type: 'string' }, requestedTime: { type: 'string' }, timezone: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['governed_work'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'DRAFT_ONLY',
    execute: async (_ctx, args) => {
      const report = stringArg(args, 'reportId') || stringArg(args, 'reportName');
      const time = stringArg(args, 'requestedTime');
      if (!report || !time) return { ok: false, toolName: 'draft_schedule', errorCode: 'INVALID_ARGUMENTS', data: { missingFields: [!report && 'reportId_or_reportName', !time && 'requestedTime'].filter(Boolean) }, evidenceSources: ['schedule_policy'], freshness: 'CURRENT' };
      return toolResult('draft_schedule', { draftCreated: true, draftId: `schedule-draft-${crypto.randomUUID()}`, report, requestedDate: stringArg(args, 'requestedDate') || 'today', requestedTime: time, timezone: stringArg(args, 'timezone') || 'America/Phoenix', approvalRequired: true, executionStatus: 'NOT_EXECUTED' }, ['schedule_draft_policy']);
    },
  },
};

const DECISION_SCHEMA = {
  anyOf: [
    {
      type: 'object',
      additionalProperties: false,
      properties: {
        type: { const: 'DIRECT_RESPONSE' },
        response: { type: 'string' },
      },
      required: ['type', 'response'],
    },
    {
      type: 'object',
      additionalProperties: false,
      properties: {
        type: { const: 'TOOL_REQUEST' },
        toolName: { type: 'string' },
        arguments: { type: 'object' },
        reasonSummary: { type: 'string' },
      },
      required: ['type', 'toolName', 'arguments', 'reasonSummary'],
    },
    {
      type: 'object',
      additionalProperties: false,
      properties: {
        type: { const: 'CLARIFICATION' },
        question: { type: 'string' },
        missingFields: { type: 'array', items: { type: 'string' } },
      },
      required: ['type', 'question', 'missingFields'],
    },
  ],
};

function visibleToolList() {
  return Object.values(toolRegistry).map((tool) => ({
    name: tool.name,
    description: tool.description,
    inputSchema: tool.inputSchema,
  }));
}

function openRouterTools() {
  return Object.values(toolRegistry).map((tool) => ({
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.inputSchema,
    },
  }));
}

function openRouterToolsFor(names: string[]) {
  const allowed = new Set(names);
  return Object.values(toolRegistry)
    .filter((tool) => allowed.has(tool.name))
    .map((tool) => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema,
      },
    }));
}

function parseToolArgs(value: unknown): Record<string, unknown> {
  if (!value) return {};
  if (typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown>;
  if (typeof value !== 'string') return {};
  try {
    const parsed = JSON.parse(value);
    return safeObject(parsed);
  } catch {
    return {};
  }
}

function evidenceObligation(message: string, history: ChatMessage[]): EvidenceObligation {
  const text = message.toLowerCase();
  const recent = history.map((item) => item.content).join('\n').toLowerCase().slice(-1800);
  const combined = `${text}\n${recent}`;
  const writing = /\b(rewrite|write|draft (a )?(message|headline|copy|prompt|note|apology)|create (a )?prompt|make this (clearer|professional|concise)|brainstorm|give me .*ideas|give me .*concepts|help me think|what do you think|strategy|hypothetical|possible|discuss|plan\b(?!.*draft))/i.test(message);
  const asksCurrentClientEvidence = /\b(clients?|customers?|client records|customer records|real or synthetic|test records|paying clients)\b/i.test(message)
    && /\b(how many|count|current|do we have|real|synthetic|test|records|paying|aggregate)\b/i.test(message);
  if (/\b(do not|don't)\s+(create|draft|schedule|make|execute)\b/i.test(message)) return { required: false, reason: 'NON_CURRENT_REASONING' };
  if (/\b(summarize what i just asked|summarize what i asked|what i just asked you|what did i just ask)\b/i.test(message)) {
    return { required: false, reason: 'GENERAL_CONVERSATION' };
  }
  if (writing && !asksCurrentClientEvidence && !/\b(current|running|deployed|reports?|approvals?|system health|stripe|trading|revenue|repo intelligence|department|where did|evidence|source|schedule draft|task draft|ray review draft)\b/i.test(message)) {
    return { required: false, reason: 'WRITING' };
  }
  if (/\b(approve it yourself|approve yourself|self-approve|execute it now|run it now)\b/i.test(message)) {
    return { required: false, reason: 'NON_CURRENT_REASONING' };
  }
  if (/\b(task draft|create a task|draft a task|create the task|task for)\b/i.test(message)) return { required: true, obligation: 'GOVERNED_DRAFT_ACTION', allowedTools: ['draft_task'], reasonSummary: 'explicit governed task draft requested' };
  if (/\b(ray review draft|ray review request|prepare a ray review|create .*ray review)\b/i.test(message)) return { required: true, obligation: 'GOVERNED_DRAFT_ACTION', allowedTools: ['draft_ray_review'], reasonSummary: 'explicit Ray Review draft requested' };
  const schedulingContext = /\bschedule|schedul|schedule draft\b/i.test(combined);
  const scheduleReportOnly = schedulingContext && /\b(system health|health report|report)\b/i.test(message) && !/\b\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)\b/i.test(message);
  if (scheduleReportOnly) return { required: true, obligation: 'GOVERNED_DRAFT_ACTION', allowedTools: ['draft_schedule'], missingFields: ['requestedTime'], reasonSummary: 'schedule draft report selected; exact time still required' };
  if (/\b(schedule|schedul|4 pm|4 p\.m\.|use .*phoenix)\b/i.test(message) && /\b(create|draft now|create .*draft|schedule .*for|\b4\s*(pm|p\.m\.)|use .*phoenix)\b/i.test(message)) {
    const hasReport = /\b(system health|health report|report)\b/i.test(combined);
    const hasTime = /\b\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)\b/i.test(combined);
    return { required: true, obligation: 'GOVERNED_DRAFT_ACTION', allowedTools: ['draft_schedule'], missingFields: [!hasReport && 'report', !hasTime && 'requestedTime'].filter(Boolean) as string[], reasonSummary: 'explicit schedule draft requested or schedule details completed' };
  }
  if (/\bwhat\s+(time|date|day)\b|\bcurrent (time|date)|phoenix time|arizona time\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_current_time'], reasonSummary: 'current clock evidence required' };
  if (/\b(who created you|how old are you|how long have you existed|your role|allowed to do|your permissions|are you .*ai|are you .*human)\b/i.test(message)) return { required: true, obligation: 'PRIVATE_OPERATIONAL_FACT', allowedTools: ['get_hermes_identity'], reasonSummary: 'Hermes identity evidence required' };
  if (/\b(version|deployed commit|running build|what.*running|deploy.*build|deployed.*build|current build)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_nexus_version'], reasonSummary: 'deployment/version evidence required' };
  if (asksCurrentClientEvidence || /\b(client records|customer records|real or synthetic|test records|paying clients)\b/i.test(message)) return { required: true, obligation: 'PRIVATE_OPERATIONAL_FACT', allowedTools: ['get_client_aggregate'], reasonSummary: 'client aggregate evidence required' };
  if (/\b(what reports|reports available|list reports|report list)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['list_reports'], reasonSummary: 'report catalog evidence required' };
  const recentReportList = /\breports?\b/.test(recent) && /\b(second|third|latest|newest|created|summarize|tell me more|that report|this report)\b/.test(combined);
  if (recentReportList || /\b(second report|that report|summarize.*report|tell me about.*report|how current.*report|reports? support|supporting reports?|model first report)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['summarize_report'], reasonSummary: 'specific report summary evidence required' };
  if (/\b(approvals?|pending decisions|ray approval|needs my approval)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_approval_summary'], reasonSummary: 'approval evidence required' };
  if (/\b(system health|stripe|trading|live trades?|blocked by policy|live payments)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_system_health'], reasonSummary: 'system/policy status evidence required' };
  if (/\b(revenue|money today|make money|actual vs projected|projected revenue)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_revenue_status'], reasonSummary: 'revenue status evidence required' };
  if (/\b(repo intelligence|repo intel|repository intelligence)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_repo_intelligence_status'], reasonSummary: 'Repo Intelligence status evidence required' };
  if (/\b(engineering|department|operations|credit and funding|knowledge|research working|department queues)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_department_status'], reasonSummary: 'department status evidence required' };
  if (/\b(where did|where.*come from|source|evidence|supports your|supports the|provenance|fact or recommendation|live data|report-backed)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_answer_provenance'], reasonSummary: 'answer provenance evidence required' };
  if (/\b(project status|what did we finish|next major phase|did we build|alpha.*access|alpha.*supabase)\b/i.test(message)) return { required: true, obligation: 'CURRENT_NEXUS_FACT', allowedTools: ['get_project_status'], reasonSummary: 'project/policy status evidence required' };
  return { required: false, reason: /\b(what is|explain|define|how does)\b/i.test(message) ? 'GENERAL_KNOWLEDGE' : 'GENERAL_CONVERSATION' };
}

function parseDecision(content: unknown): HermesTurnDecision | null {
  const text = String(content || '').trim();
  if (!text) return null;
  const raw = text.startsWith('```') ? text.replace(/^```(?:json)?/i, '').replace(/```$/i, '').trim() : text;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (parsed.type === 'DIRECT_RESPONSE' && typeof parsed.response === 'string') {
      return { type: 'DIRECT_RESPONSE', response: parsed.response };
    }
    if (parsed.type === 'TOOL_REQUEST' && typeof parsed.toolName === 'string') {
      return {
        type: 'TOOL_REQUEST',
        toolName: parsed.toolName,
        arguments: safeObject(parsed.arguments),
        reasonSummary: typeof parsed.reasonSummary === 'string' ? parsed.reasonSummary.slice(0, 240) : 'Nexus evidence requested',
      };
    }
    if (parsed.type === 'CLARIFICATION' && typeof parsed.question === 'string') {
      return {
        type: 'CLARIFICATION',
        question: parsed.question,
        missingFields: Array.isArray(parsed.missingFields) ? parsed.missingFields.map((x) => String(x).slice(0, 80)).slice(0, 6) : [],
      };
    }
  } catch {
    return null;
  }
  return null;
}

function validateArguments(tool: ToolDefinition, args: Record<string, unknown>): boolean {
  const required = Array.isArray(tool.inputSchema.required) ? tool.inputSchema.required as string[] : [];
  for (const key of required) {
    if (!(key in args) || args[key] == null || String(args[key]).trim() === '') return false;
  }
  const properties = safeObject(tool.inputSchema.properties);
  if (tool.inputSchema.additionalProperties === false) {
    for (const key of Object.keys(args)) if (!(key in properties)) return false;
  }
  for (const [key, spec] of Object.entries(properties)) {
    const value = args[key];
    if (value == null) continue;
    const type = typeof safeObject(spec).type === 'string' ? String(safeObject(spec).type) : '';
    if (type === 'string' && typeof value !== 'string') return false;
  }
  return true;
}

function validateToolRequest(decision: HermesTurnDecision, ctx: ToolExecutionContext): CapabilityDecision {
  if (decision.type !== 'TOOL_REQUEST') return { allowed: false, reasonCode: 'UNKNOWN_TOOL' };
  const tool = toolRegistry[decision.toolName];
  if (!tool) return { allowed: false, reasonCode: 'UNKNOWN_TOOL' };
  if (!ctx.authorization) return { allowed: false, reasonCode: 'UNAUTHORIZED_ACTOR' };
  if (!tool.requiredRole.includes(ctx.actorRole)) return { allowed: false, reasonCode: 'UNAUTHORIZED_ACTOR' };
  if (!validateArguments(tool, decision.arguments)) return { allowed: false, reasonCode: 'INVALID_ARGUMENTS' };
  if (/approve/i.test(decision.toolName) || /self.?approve/i.test(decision.reasonSummary)) {
    return { allowed: false, reasonCode: 'SELF_APPROVAL_PROHIBITED' };
  }
  if (tool.actionClass === 'APPROVAL_REQUIRED') return { allowed: false, reasonCode: 'APPROVAL_REQUIRED' };
  return { allowed: true, mode: tool.actionClass === 'DRAFT_ONLY' ? 'DRAFT_ONLY' : 'READ_ONLY' };
}

function isOverbroadClarification(decision: HermesTurnDecision, history: ChatMessage[]): boolean {
  if (decision.type !== 'CLARIFICATION' || history.length === 0) return false;
  const question = decision.question.toLowerCase();
  return /what specific (aspect|aspects|details|comparison)|please clarify what you meant|what .* did i misunderstand|which list|specify which list|what .* are you referring/.test(question);
}

function isRepairOrVisibleReference(message: string): boolean {
  return /\b(that is not what i meant|you misunderstood me|i meant .*latest list|latest list|number three|number 3|the first one|previous option|earlier option|why that one|compare it with|correct .*last answer|why did you answer that way)\b/i.test(message);
}

function isToolFreeWritingRequest(message: string): boolean {
  return /\b(draft a prompt|write a prompt|create a prompt|make this clearer|rewrite this|write a short|give me .*titles|client-friendly explanation)\b/i.test(message);
}

function normalizeScheduleTime(message: string): string | undefined {
  const match = message.match(/\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)\b/i);
  return match ? `${match[1]}${match[2] ? `:${match[2]}` : ''} ${match[3].replace(/\./g, '').toUpperCase()}` : undefined;
}

function inferReportName(message: string): string | undefined {
  if (/\bsystem[-\s]+health\b/i.test(message)) return 'System Health Report';
  if (/\brevenue\b/i.test(message)) return 'Revenue Status Report';
  if (/\bmodel[- ]first|hermes\b/i.test(message) && /\breport\b/i.test(message)) return 'Hermes Model-First Report';
  return undefined;
}

function newScheduleState(message: string): PendingScheduleState {
  const now = new Date().toISOString();
  const state: PendingScheduleState = {
    kind: 'schedule_report',
    reportName: inferReportName(message),
    date: /\btomorrow\b/i.test(message) ? 'tomorrow' : 'today',
    time: normalizeScheduleTime(message),
    timezone: /\bphoenix|arizona\b/i.test(message) ? 'America/Phoenix' : 'America/Phoenix',
    createRequested: false,
    creationBlocked: false,
    status: 'collecting',
    version: 1,
    createdAt: now,
    updatedAt: now,
    expiresAt: isoIn(120),
  };
  state.status = missingScheduleFields(state).length ? 'collecting' : 'ready';
  return state;
}

function missingScheduleFields(state: PendingScheduleState): string[] {
  return [!state.reportName && !state.reportId && 'report', !state.time && 'time'].filter(Boolean) as string[];
}

function scheduleInstruction(state: PendingScheduleState): string {
  const missing = missingScheduleFields(state);
  if (missing.includes('report') && missing.includes('time')) return 'Ask which report Ray wants scheduled and what time to use. Do not call tools.';
  if (missing.includes('report')) return 'Ask which report Ray wants scheduled. Do not call tools.';
  if (missing.includes('time')) return `The report is ${state.reportName || state.reportId}. Ask what time to use. Do not call tools.`;
  if (state.creationBlocked) return `The schedule details are complete, but Ray said not to create it yet. Confirm the held details and do not call tools.`;
  return `The schedule details are complete: ${state.reportName || state.reportId}, ${state.date || 'today'} at ${state.time} ${state.timezone || 'America/Phoenix'}. Ask whether Ray wants the draft created. Do not call tools.`;
}

function buildReferenceState(sourceType: 'report_search' | 'report_list', query: string | undefined, items: Array<{ id: string; title: string; safeSummary?: string; createdAt?: string; sourceType?: string }>, version = 1): HermesReferenceState {
  return {
    sourceType,
    query,
    items: items.slice(0, 20).map((item) => ({
      id: item.id,
      label: item.title,
      safeSummary: item.safeSummary?.slice(0, 400),
      createdAt: item.createdAt,
      metadata: { createdAt: item.createdAt || null, sourceType: item.sourceType || null },
    })),
    version,
    createdAt: new Date().toISOString(),
    expiresAt: isoIn(120),
  };
}

function resolveReportReference(message: string, ref: HermesReferenceState | null | undefined): { reportId?: string; metadataOnly?: boolean } | null {
  if (!ref?.items.length || Date.parse(ref.expiresAt) <= Date.now()) return null;
  const text = message.toLowerCase();
  let index: number | null = null;
  if (/\bfirst|1st\b/.test(text)) index = 0;
  if (/\bsecond|2nd\b/.test(text)) index = 1;
  if (/\bthird|3rd\b/.test(text)) index = 2;
  if (/\bnewest\b/.test(text)) {
    index = ref.items.reduce((best, item, i) => String(item.createdAt || '') > String(ref.items[best]?.createdAt || '') ? i : best, 0);
    return { reportId: ref.items[index]?.id, metadataOnly: true };
  }
  if (index == null && /\b(that report|this report|tell me more|summarize it|source backs|previous report)\b/.test(text)) index = 0;
  return index == null || !ref.items[index] ? null : { reportId: ref.items[index].id, metadataOnly: false };
}

function currentFactTools(message: string): string[] | null {
  const text = message.toLowerCase();
  if (/\b(task draft|create a task|draft a task|create the task|draft .*task|task for)\b/i.test(message)) return ['draft_task'];
  if (/\b(ray review draft|ray review request|prepare a ray review|create .*ray review)\b/i.test(message)) return ['draft_ray_review'];
  if (/\bwhat\s+(time|date|day)\b|\bcurrent (time|date)|phoenix time|arizona time\b/i.test(message)) return ['get_current_time'];
  if (/\b(who created you|how old are you|how long have you existed|your role|allowed to do|your permissions|are you .*ai|are you .*human)\b/i.test(message)) return ['get_hermes_identity'];
  if (/\b(version|deployed commit|running build|what.*running|deploy.*build|deployed.*build|current build)\b/i.test(message)) return ['get_nexus_version'];
  if (/\b(clients?|customers?|client records|customer records|real or synthetic|test records|paying clients)\b/i.test(message) && /\b(how many|count|current|do we have|real|synthetic|test|records|paying|aggregate)\b/i.test(message)) return ['get_client_aggregate'];
  if (/\b(which|find|show|what)\b.*\b(reports?|documentation)\b.*\b(cover|support|discuss|document|certif|contain|related|concerning|about|workflow|boundary)\b/i.test(message)) return ['search_reports'];
  if (/\b(documentation|reports?)\b.*\b(cover|support|discuss|document|certif|contain|related|concerning|about|workflow|boundary)\b/i.test(message)) return ['search_reports'];
  if (/\b(what reports|reports available|list reports|report list)\b/i.test(message)) return ['list_reports'];
  if (/\b(approvals?|pending decisions|ray approval|needs my approval)\b/i.test(message)) return ['get_approval_summary'];
  if (/\b(system health|stripe|trading|live trades?|blocked by policy|live payments)\b/i.test(message)) return ['get_system_health'];
  if (/\b(revenue|money today|make money|actual vs projected|projected revenue)\b/i.test(message)) return ['get_revenue_status'];
  if (/\b(repo intelligence|repo intel|repository intelligence)\b/i.test(message)) return ['get_repo_intelligence_status'];
  if (/\b(engineering|department|operations|credit and funding|knowledge|research working|department queues)\b/i.test(message)) return ['get_department_status'];
  if (/\b(where did|where.*come from|source|evidence|supports your|supports the|provenance|fact or recommendation|live data|report-backed)\b/i.test(message)) return ['get_answer_provenance'];
  if (/\b(project status|what did we finish|next major phase|did we build|alpha.*access|alpha.*supabase)\b/i.test(message)) return ['get_project_status'];
  if (/\b(what should (i|we) focus on today|today'?s priorities|what needs (my|our) attention today|what should nexus handle first)\b/i.test(message)) return ['get_project_status'];
  return null;
}

function resolveLane(message: string, state: HermesSessionState): HermesTurnLane {
  const text = message.toLowerCase();
  const pending = state.pendingAction;
  const cancelMatch = text.match(/\b(cancel|never mind|start over|forget (it|that|the schedule))\b[.! ]*(.*)$/i);
  if (cancelMatch && pending) {
    return { lane: 'CANCELLED_WORKFLOW', remainingMessage: cancelMatch[3]?.trim() || undefined };
  }
  if (pending?.kind === 'schedule_report' && pending.status !== 'drafted' && pending.status !== 'cancelled') {
    const standaloneCurrentFactTools = currentFactTools(message);
    const report = inferReportName(message);
    const time = normalizeScheduleTime(message);
    const fieldCompletion = Boolean(report || time || /\btomorrow\b|\btoday\b|\bphoenix|arizona\b/i.test(message) || /\b(do not|don't)\s+(create|draft|schedule|make)|not yet\b/i.test(message) || /\b(create|draft|make)\b.*\b(schedule draft|draft|it|now)\b/i.test(message));
    const subjectChange = /\bwhat is|define|explain|tell me a joke|write|rewrite|prompt|brainstorm\b/i.test(message)
      && !/\breport|schedule|\d{1,2}(?::\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\b/i.test(message);
    if ((subjectChange || standaloneCurrentFactTools) && !fieldCompletion) {
      return standaloneCurrentFactTools ? { lane: 'CURRENT_FACT', allowedTools: standaloneCurrentFactTools } : { lane: 'GENERAL_CONVERSATION' };
    }
    const next: PendingScheduleState = { ...pending, updatedAt: new Date().toISOString(), expiresAt: isoIn(120), version: pending.version + 1 };
    if (report) next.reportName = report;
    if (time) next.time = time;
    if (/\btomorrow\b/i.test(message)) next.date = 'tomorrow';
    if (/\btoday\b/i.test(message)) next.date = 'today';
    if (/\bphoenix|arizona\b/i.test(message)) next.timezone = 'America/Phoenix';
    const creationDenied = /\b(do not|don't)\s+(create|draft|schedule|make)|not yet\b/i.test(message);
    if (creationDenied) next.creationBlocked = true;
    const explicitCreate = !creationDenied && /\b(create|draft)\b.*\b(schedule draft|draft|it|now)\b/i.test(message);
    if (explicitCreate) next.creationBlocked = false;
    const createRequested = explicitCreate && !next.creationBlocked;
    next.createRequested = createRequested;
    next.status = missingScheduleFields(next).length ? 'collecting' : 'ready';
    const allowedTools = createRequested && next.status === 'ready' ? ['draft_schedule'] : [];
    return { lane: 'SCHEDULE_WORKFLOW', allowedTools, workflowState: next, instruction: scheduleInstruction(next) };
  }
  if (/\bschedul\w*\b/i.test(message) && /\breport\b/i.test(message) && !/\bwhat is|how is|status\b/i.test(message)) {
    const workflowState = newScheduleState(message);
    return { lane: 'SCHEDULE_WORKFLOW', allowedTools: [], workflowState, instruction: scheduleInstruction(workflowState) };
  }
  const ref = resolveReportReference(message, state.referenceState);
  if (ref && state.referenceState) return { lane: 'REPORT_REFERENCE', allowedTools: ref.metadataOnly ? [] : ['summarize_report'], referenceState: state.referenceState, reportId: ref.reportId, metadataOnly: ref.metadataOnly };
  const tools = currentFactTools(message);
  if (tools) return { lane: 'CURRENT_FACT', allowedTools: tools };
  return { lane: 'GENERAL_CONVERSATION' };
}

function defaultLaneToolArguments(toolName: string, message: string): Record<string, unknown> {
  if (toolName === 'search_reports') return { query: message, limit: 10 };
  if (toolName === 'draft_task') {
    return {
      title: 'Hermes governed task draft',
      summary: message.slice(0, 900),
      riskClass: 'MEDIUM',
    };
  }
  if (toolName === 'draft_ray_review') {
    return {
      title: 'Ray Review draft from Hermes conversation',
      summary: message.slice(0, 900),
      riskClass: 'MEDIUM',
    };
  }
  return {};
}

function inferMandatoryDecision(message: string, decision: HermesTurnDecision, history: ChatMessage[]): HermesTurnDecision | null {
  const text = message.toLowerCase();
  const recent = history.map((item) => item.content).join('\n').slice(-1200);
  const draftSummary = `${message}\n\nRecent context:\n${recent}`.slice(0, 900);
  if (/\b(do not|don't)\s+(schedule|create|draft|make)\b/.test(text)) return { type: 'DIRECT_RESPONSE', response: "Understood. I won't create or schedule anything yet; we can keep this in planning." };
  if (/\b(approve it yourself|approve yourself|self[- ]approve|execute it now|run it now)\b/.test(text)) return { type: 'DIRECT_RESPONSE', response: "I can't approve or execute that myself. Ray approval and the governed capability path are required before execution." };
  if (/\bwhat\s+(time|date|day)\b|\b(time is it|date is it|day is it|clock says|current time|current date)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_current_time', arguments: /phoenix|arizona/.test(text) ? { timezone: 'America/Phoenix' } : {}, reasonSummary: 'current date/time requires the system clock' };
  if (/\b(who created you|created you|your creator|how long have you|how old are you|what are you allowed|what can you do|person or an ai|are you .*ai|your role|your permissions)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_hermes_identity', arguments: {}, reasonSummary: 'Hermes identity evidence requested' };
  if (/\b(client|clients|customer|customers|real or synthetic|test records|paying clients)\b/.test(text) && /\b(paying|count|aggregate|prove|real|synthetic|test|records|customers|clients)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_client_aggregate', arguments: {}, reasonSummary: 'client aggregate evidence requested' };
  if (/\b(where .*from|source|evidence|provenance|support[s]? that|supports .*number|how do you know|fact or .*recommendation|live data|report-backed)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_answer_provenance', arguments: {}, reasonSummary: 'answer provenance requested' };
  if (/\b(client|clients|customer|customers|real or synthetic|test records)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_client_aggregate', arguments: {}, reasonSummary: 'client aggregate evidence requested' };
  if (/\b(approval|approvals|ray review|approve)\b/.test(text) && /\b(create|prepare|draft|request)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'draft_ray_review', arguments: { title: 'Ray Review draft from Hermes conversation', summary: draftSummary, riskClass: 'MEDIUM' }, reasonSummary: 'explicit Ray Review draft requested' };
  if (/\b(approval|approvals|pending decisions|needs my approval)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_approval_summary', arguments: {}, reasonSummary: 'approval summary requested' };
  if (/\b(task draft|create the task|create a task|draft a task|draft task|now create|turn .* into a task draft)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'draft_task', arguments: { title: 'Hermes governed task draft', summary: draftSummary, riskClass: 'MEDIUM' }, reasonSummary: 'explicit task draft requested' };
  if (/\b(schedule|schedul)\b/.test(text) && /\b(draft now|create .*draft|another identical)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'draft_schedule', arguments: { reportName: /system health|health/.test(text + recent.toLowerCase()) ? 'system health report' : 'report', requestedDate: 'today', requestedTime: /4\s*(pm|p\.m\.)/.test(text + recent.toLowerCase()) ? '4 PM' : 'specified time', timezone: 'America/Phoenix' }, reasonSummary: 'schedule draft requested' };
  if (/\b(schedule|schedul)\b/.test(text) && !/(\b\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)\b)/.test(text)) return { type: 'CLARIFICATION', question: 'Which report should I schedule, and what exact time should I use?', missingFields: ['report', 'requestedTime'] };
  if (/\b(schedule|schedul|4 pm|4 p\.m\.)\b/.test(text) && /(\b\d{1,2}\s*(am|pm|a\.m\.|p\.m\.)\b)/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'draft_schedule', arguments: { reportName: /system health|health/.test(text) ? 'system health report' : 'report', requestedDate: 'today', requestedTime: /4\s*(pm|p\.m\.)/.test(text) ? '4 PM' : 'specified time', timezone: 'America/Phoenix' }, reasonSummary: 'schedule draft requested' };
  if (/\b(repo intelligence|repo intel)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_repo_intelligence_status', arguments: {}, reasonSummary: 'Repo Intelligence status requested' };
  if (/\b(report|reports)\b/.test(text) && (/\bsummar\w*\b/.test(text) || /\b(second|latest|newest|tell me more|current|supports|supporting|status)\b/.test(text))) return { type: 'TOOL_REQUEST', toolName: 'summarize_report', arguments: { reportId: 'nexus_3_hermes_model_first_status' }, reasonSummary: 'report summary requested' };
  if (/\b(report|reports)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'list_reports', arguments: {}, reasonSummary: 'report catalog requested' };
  if (/\b(revenue|money move|make money|actual revenue|projected revenue)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_revenue_status', arguments: {}, reasonSummary: 'revenue status requested' };
  if (/\b(department|engineering|credit and funding|operations|research|knowledge)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_department_status', arguments: {}, reasonSummary: 'department status requested' };
  if (/\b(alpha.*(supabase|access|allowed|boundary)|supabase.*alpha)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_project_status', arguments: {}, reasonSummary: 'Alpha access boundary requested' };
  if (/\b(system health|system ok|stripe|trading|trade|trades|blocked by policy|live payments|live trading)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_system_health', arguments: {}, reasonSummary: 'current system/policy status requested' };
  if (/\bversion\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_nexus_version', arguments: {}, reasonSummary: 'Nexus version requested' };
  if (/\b(wave|project status|did we build|what did we finish)\b/.test(text)) return { type: 'TOOL_REQUEST', toolName: 'get_project_status', arguments: {}, reasonSummary: 'project status requested' };
  if (decision.type === 'TOOL_REQUEST') return null;
  return null;
}

async function executeToolRequest(decision: Extract<HermesTurnDecision, { type: 'TOOL_REQUEST' }>, ctx: ToolExecutionContext): Promise<ToolResult> {
  const tool = toolRegistry[decision.toolName];
  return await tool.execute(ctx, decision.arguments).catch((error) => ({
    ok: false,
    toolName: decision.toolName,
    errorCode: String(error).slice(0, 80) || 'TOOL_FAILURE',
    evidenceSources: [decision.toolName],
    freshness: 'UNKNOWN',
  }));
}

async function runMandatoryToolFallback(
  key: string,
  models: string[],
  messages: ChatMessage[],
  message: string,
  history: ChatMessage[],
  obligation: Extract<EvidenceObligation, { required: true }>,
  firstCall: Extract<OpenRouterResult, { ok: true }>,
  correctionCall: Extract<OpenRouterResult, { ok: true }>,
  toolCtx: ToolExecutionContext,
  startTime: number,
  trace: string,
) {
  const inferred = inferMandatoryDecision(message, { type: 'DIRECT_RESPONSE', response: correctionCall.reply || firstCall.reply || '' }, history);
  if (!inferred) return null;
  if (inferred.type === 'CLARIFICATION') {
    return json({
      configured: true,
      reply: inferred.question,
      metadata: {
        provider: 'openrouter',
        model: correctionCall.model,
        fallbackUsed: firstCall.fallbackUsed || correctionCall.fallbackUsed,
        traceId: trace,
        decisionType: 'CLARIFICATION',
        source: 'GENERAL_MODEL',
        evidenceObligation: obligation,
        toolRequested: false,
        toolExecuted: false,
        modelRounds: 2,
        durationMs: Date.now() - startTime,
      },
    });
  }
  if (inferred.type !== 'TOOL_REQUEST' || !obligation.allowedTools.includes(inferred.toolName)) return null;
  const capabilityDecision = validateToolRequest(inferred, toolCtx);
  const toolResultData = capabilityDecision.allowed
    ? await executeToolRequest(inferred, toolCtx)
    : { ok: false, toolName: inferred.toolName, errorCode: capabilityDecision.reasonCode, evidenceSources: ['capability_os_gateway'], freshness: 'CURRENT' };
  const finalMessages: ChatMessage[] = [
    ...messages,
    { role: 'assistant', content: correctionCall.reply || firstCall.reply || '' },
    {
      role: 'system',
      content: [
        'A mandatory governed Nexus tool was executed by the server evidence gate because current Nexus evidence or a governed draft was required.',
        'Write the final answer naturally from this authorized result. State uncertainty and data state honestly. Do not claim external execution for draft tools.',
        JSON.stringify({ requestedTool: inferred.toolName, capabilityDecision, toolResult: toolResultData }).slice(0, 5000),
      ].join('\n'),
    },
  ];
  const finalCall = await callOpenRouterNative(key, models, finalMessages, startTime);
  if (!finalCall.ok) return degradedOpenRouterReply(String(finalCall.errorCode), 'openrouter', String(finalCall.model), startTime);
  return json({
    configured: true,
    reply: finalCall.reply,
    metadata: {
      provider: 'openrouter',
      model: finalCall.model,
      fallbackUsed: firstCall.fallbackUsed || correctionCall.fallbackUsed || finalCall.fallbackUsed,
      traceId: trace,
      decisionType: 'TOOL_REQUEST',
      toolRequested: inferred.toolName,
      toolAllowed: capabilityDecision.allowed,
      toolExecuted: Boolean(capabilityDecision.allowed && toolResultData.ok),
      toolErrorCode: toolResultData.ok ? undefined : toolResultData.errorCode,
      source: capabilityDecision.allowed ? 'NEXUS_TOOL' : 'SAFE_LEGACY_FALLBACK',
      evidenceObligation: obligation,
      modelRounds: 3,
      ...usageMetadata(finalCall.usage as Record<string, unknown> | null, message, finalCall.reply),
      maxOutputTokens: MAX_OUTPUT_TOKENS,
      durationMs: Date.now() - startTime,
    },
  });
}

async function callOpenRouter(
  key: string,
  models: string[],
  messages: ChatMessage[],
  startTime: number,
  responseFormat?: Record<string, unknown>,
) {
  let lastError = '';
  for (const m of models) {
    try {
      const payload: Record<string, unknown> = { model: m, messages, max_tokens: MAX_OUTPUT_TOKENS };
      if (responseFormat) payload.response_format = responseFormat;
      const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        lastError = `HTTP ${r.status}`;
        continue;
      }
      const d = await r.json();
      if (d?.error) {
        lastError = String(d.error?.message || d.error || 'provider error').slice(0, 100);
        continue;
      }
      const reply = d?.choices?.[0]?.message?.content;
      if (reply && String(reply).trim()) {
        return {
          ok: true,
          reply: String(reply),
          model: m,
          fallbackUsed: models.length > 1 && m !== models[0],
          usage: d?.usage || null,
          durationMs: Date.now() - startTime,
        };
      }
      lastError = 'Empty reply from model';
    } catch (e) {
      lastError = String(e).slice(0, 100);
    }
  }
  return { ok: false, errorCode: lastError || 'OPENROUTER_UNAVAILABLE', model: models[0] ?? 'none', fallbackUsed: models.length > 1, durationMs: Date.now() - startTime };
}

async function callOpenRouterNative(
  key: string,
  models: string[],
  messages: ChatMessage[],
  startTime: number,
  tools?: Record<string, unknown>[],
) {
  let lastError = '';
  for (const m of models) {
    try {
      const payload: Record<string, unknown> = { model: m, messages, max_tokens: MAX_OUTPUT_TOKENS };
      if (tools?.length) {
        payload.tools = tools;
        payload.tool_choice = 'auto';
      }
      const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) {
        lastError = `HTTP ${r.status}`;
        continue;
      }
      const d = await r.json();
      if (d?.error) {
        lastError = String(d.error?.message || d.error || 'provider error').slice(0, 100);
        continue;
      }
      const message = d?.choices?.[0]?.message;
      const reply = String(message?.content || '').trim();
      const toolCalls = Array.isArray(message?.tool_calls) ? message.tool_calls : [];
      if (reply || toolCalls.length) {
        return {
          ok: true,
          reply,
          toolCalls,
          model: m,
          fallbackUsed: models.length > 1 && m !== models[0],
          usage: d?.usage || null,
          durationMs: Date.now() - startTime,
        };
      }
      lastError = 'Empty reply from model';
    } catch (e) {
      lastError = String(e).slice(0, 100);
    }
  }
  return { ok: false, errorCode: lastError || 'OPENROUTER_UNAVAILABLE', model: models[0] ?? 'none', fallbackUsed: models.length > 1, durationMs: Date.now() - startTime };
}

function usageMetadata(usage: Record<string, unknown> | null | undefined, inputText: string, outputText: string) {
  return {
    inputTokens: Number(usage?.prompt_tokens) || undefined,
    outputTokens: Number(usage?.completion_tokens) || undefined,
    totalTokens: Number(usage?.total_tokens) || undefined,
    estimatedInputTokens: usage?.prompt_tokens ? undefined : Math.ceil(inputText.length / 4),
    estimatedOutputTokens: usage?.completion_tokens ? undefined : Math.ceil(outputText.length / 4),
  };
}

function degradedOpenRouterReply(errorCode: string, provider = 'openrouter', model = 'none', startTime = Date.now()) {
  return json({
    configured: true,
    reply: 'My conversational model is temporarily unavailable. I can still provide certain verified local Nexus status responses, but general conversation is degraded.',
    metadata: { provider, model, fallbackUsed: false, errorCode, decisionType: 'DEGRADED', source: 'hermes-chat', durationMs: Date.now() - startTime },
  });
}

function stateContextBlock(state: HermesSessionState, lane: HermesTurnLane): ChatMessage {
  const pending = state.pendingAction;
  const ref = state.referenceState;
  const lines = ['[SERVER-OWNED HERMES STATE]'];
  lines.push(`Selected lane: ${lane.lane}`);
  if (pending?.kind === 'schedule_report') {
    lines.push('Active workflow: schedule_report');
    lines.push(`Report: ${pending.reportName || pending.reportId || 'missing'}`);
    lines.push(`Date: ${pending.date || 'today'}`);
    lines.push(`Time: ${pending.time || 'missing'}`);
    lines.push(`Timezone: ${pending.timezone || 'America/Phoenix'}`);
    lines.push(`Create requested: ${pending.createRequested ? 'yes' : 'no'}`);
    lines.push(`Creation blocked: ${pending.creationBlocked ? 'yes' : 'no'}`);
    lines.push(`Status: ${pending.status}`);
  }
  if (ref?.items.length) {
    lines.push(`Reference state: ${ref.sourceType}${ref.query ? ` for "${ref.query}"` : ''}`);
    ref.items.slice(0, 8).forEach((item, index) => {
      lines.push(`${index + 1}. ${item.label}${item.createdAt ? ` (${item.createdAt})` : ''}${item.safeSummary ? ` - ${item.safeSummary.slice(0, 160)}` : ''}`);
    });
  }
  lines.push('This state is authoritative. Do not infer a different active workflow from older conversation prose.');
  return { role: 'system', content: lines.join('\n').slice(0, 4000) };
}

function historyWasSent(baseMessages: ChatMessage[]) {
  return baseMessages.some((item) => item.role === 'assistant' || item.role === 'user') && baseMessages.length > 2;
}

function historyTurnCount(baseMessages: ChatMessage[]) {
  return Math.max(0, baseMessages.filter((item) => item.role === 'assistant' || item.role === 'user').length - 1);
}

async function runNoToolLaneResponse(
  key: string,
  models: string[],
  messages: ChatMessage[],
  message: string,
  instruction: string,
  baseMessages: ChatMessage[],
  startTime: number,
  tid: string,
  laneName: string,
) {
  const call = await callOpenRouterNative(
    key,
    models,
    [...messages, { role: 'system', content: instruction }],
    startTime,
    [],
  );
  if (!call.ok) return degradedOpenRouterReply(String(call.errorCode), 'openrouter', String(call.model), startTime);
  return json({
    configured: true,
    reply: call.reply,
    metadata: {
      provider: 'openrouter',
      model: call.model,
      fallbackUsed: call.fallbackUsed,
      traceId: tid,
      decisionType: laneName === 'SCHEDULE_WORKFLOW' ? 'CLARIFICATION' : 'DIRECT_RESPONSE',
      source: 'GENERAL_MODEL',
      lane: laneName,
      conversationHistorySent: historyWasSent(baseMessages),
      historyTurnCount: historyTurnCount(baseMessages),
      toolRequested: false,
      toolExecuted: false,
      modelRounds: 1,
      ...usageMetadata(call.usage as Record<string, unknown> | null, message, call.reply),
      maxOutputTokens: MAX_OUTPUT_TOKENS,
      durationMs: Date.now() - startTime,
    },
  });
}

async function executeLaneToolAndAnswer(
  key: string,
  models: string[],
  messages: ChatMessage[],
  message: string,
  decision: Extract<HermesTurnDecision, { type: 'TOOL_REQUEST' }>,
  toolCtx: ToolExecutionContext,
  baseMessages: ChatMessage[],
  startTime: number,
  tid: string,
  session: { userId: string; tenantId: string | null; conversationId: string; state: HermesSessionState },
  laneName: string,
) {
  const capabilityDecision = validateToolRequest(decision, toolCtx);
  const toolResultData = capabilityDecision.allowed
    ? await executeToolRequest(decision, toolCtx)
    : { ok: false, toolName: decision.toolName, errorCode: capabilityDecision.reasonCode, evidenceSources: ['capability_os_gateway'], freshness: 'CURRENT' };

  if (capabilityDecision.allowed && toolResultData.ok) {
    const data = safeObject(toolResultData.data);
    if (decision.toolName === 'search_reports') {
      const matches = Array.isArray(data.matches) ? data.matches as Array<{ id: string; title: string; safeSummary?: string; createdAt?: string; sourceType?: string }> : [];
      session.state.referenceState = buildReferenceState('report_search', stringArg(decision.arguments, 'query'), matches, (session.state.referenceState?.version || 0) + 1);
      await saveHermesState(session.userId, session.tenantId, session.conversationId, session.state);
    }
    if (decision.toolName === 'list_reports') {
      const reports = Array.isArray(data.reports) ? data.reports as Array<{ id: string; title: string; safeSummary?: string; createdAt?: string; sourceType?: string }> : [];
      session.state.referenceState = buildReferenceState('report_list', undefined, reports.map((item) => ({ ...item, safeSummary: item.safeSummary || '' })), (session.state.referenceState?.version || 0) + 1);
      await saveHermesState(session.userId, session.tenantId, session.conversationId, session.state);
    }
    if (decision.toolName === 'draft_schedule' && session.state.pendingAction?.kind === 'schedule_report') {
      session.state.pendingAction = {
        ...session.state.pendingAction,
        createRequested: true,
        creationBlocked: false,
        status: 'drafted',
        updatedAt: new Date().toISOString(),
        version: session.state.pendingAction.version + 1,
      };
      await saveHermesState(session.userId, session.tenantId, session.conversationId, session.state);
    }
  }

  const finalMessages: ChatMessage[] = [
    ...messages,
    {
      role: 'system',
      content: [
        '[LANE TOOL RESULT]',
        `Lane: ${laneName}`,
        'The server selected this lane and executed only its approved governed tool.',
        'Write the final answer naturally from this authorized result. State uncertainty and data state honestly. Do not claim external execution for draft tools.',
        JSON.stringify({ requestedTool: decision.toolName, capabilityDecision, toolResult: toolResultData }).slice(0, 5000),
      ].join('\n'),
    },
  ];
  const finalCall = await callOpenRouterNative(key, models, finalMessages, startTime);
  if (!finalCall.ok) return degradedOpenRouterReply(String(finalCall.errorCode), 'openrouter', String(finalCall.model), startTime);
  return json({
    configured: true,
    reply: finalCall.reply,
    metadata: {
      provider: 'openrouter',
      model: finalCall.model,
      fallbackUsed: finalCall.fallbackUsed,
      traceId: tid,
      decisionType: 'TOOL_REQUEST',
      lane: laneName,
      toolRequested: decision.toolName,
      toolAllowed: capabilityDecision.allowed,
      toolExecuted: Boolean(capabilityDecision.allowed && toolResultData.ok),
      toolErrorCode: toolResultData.ok ? undefined : toolResultData.errorCode,
      source: capabilityDecision.allowed ? 'NEXUS_TOOL' : 'SAFE_LEGACY_FALLBACK',
      conversationHistorySent: historyWasSent(baseMessages),
      historyTurnCount: historyTurnCount(baseMessages),
      modelRounds: 1,
      ...usageMetadata(finalCall.usage as Record<string, unknown> | null, message, finalCall.reply),
      maxOutputTokens: MAX_OUTPUT_TOKENS,
      durationMs: Date.now() - startTime,
    },
  });
}

async function runConversationalOpenRouter(
  key: string,
  models: string[],
  baseMessages: ChatMessage[],
  message: string,
  context: Record<string, unknown> | undefined,
  authorization: string,
  startTime: number,
  session: { userId: string; tenantId: string | null; conversationId: string; state: HermesSessionState },
) {
  const tid = traceId();
  const actorRole = authorization ? 'ray' : 'anonymous';
  const toolCtx: ToolExecutionContext = {
    actorRole,
    tenantId: String(context?.tenantId || 'ray_pilot'),
    traceId: tid,
    authorization,
  };
  const conversationSystem: ChatMessage = {
    role: 'system',
    content: [
      '[MODEL-FIRST CONVERSATIONAL MODE]',
      'You are the conversational brain. Answer ordinary conversation, writing, personal statements, strategy, references, and clarifications directly as normal assistant text.',
      'Use tools only when Ray asks for current Nexus facts, approved report summaries, aggregate customer status, governed drafts, scheduling drafts, or source provenance.',
      'Never claim live internal facts without tool evidence. Never request client PII. Never self-approve. Never execute external actions.',
      'When Ray refers to number three, the first one, that, it, them, or the previous option, resolve from the latest visible conversation before using a tool.',
      'When Ray asks to write, rewrite, draft copy, create a prompt, brainstorm, challenge an idea, or help think it through, do not use Nexus tools unless current private Nexus evidence is explicitly required.',
      'If Ray asks to approve yourself or execute an approval-gated action, refuse directly.',
    ].join('\n'),
  };
  const initialLane = resolveLane(message, session.state);
  const messages = [baseMessages[0], conversationSystem, stateContextBlock(session.state, initialLane), ...baseMessages.slice(1)];

  if (initialLane.lane === 'CANCELLED_WORKFLOW') {
    if (session.state.pendingAction) {
      session.state.pendingAction = {
        ...session.state.pendingAction,
        status: 'cancelled',
        updatedAt: new Date().toISOString(),
        version: session.state.pendingAction.version + 1,
      };
      await saveHermesState(session.userId, session.tenantId, session.conversationId, session.state);
      session.state.pendingAction = null;
    }
    const remaining = String(initialLane.remainingMessage || '').trim();
    if (remaining) {
      const remainingTools = currentFactTools(remaining);
      if (remainingTools?.length) {
        const toolName = remainingTools[0];
        return await executeLaneToolAndAnswer(
          key,
          models,
          [...messages, { role: 'system', content: 'The active workflow was cancelled. Answer the remaining request using only the selected lane tool.' }, { role: 'user', content: remaining }],
          remaining,
          { type: 'TOOL_REQUEST', toolName, arguments: {}, reasonSummary: 'remaining request after workflow cancellation' },
          toolCtx,
          baseMessages,
          startTime,
          tid,
          session,
          'CANCELLED_WORKFLOW',
        );
      }
      return await runNoToolLaneResponse(
        key,
        models,
        [...messages, { role: 'user', content: remaining }],
        remaining,
        'The active workflow was cancelled. Answer the remaining request naturally. Do not use tools.',
        baseMessages,
        startTime,
        tid,
        'CANCELLED_WORKFLOW',
      );
    }
    return json({
      configured: true,
      reply: 'Cancelled. I will not continue that workflow.',
      metadata: {
        provider: 'openrouter',
        model: models[0],
        fallbackUsed: false,
        traceId: tid,
        decisionType: 'DIRECT_RESPONSE',
        source: 'GENERAL_MODEL',
        lane: 'CANCELLED_WORKFLOW',
        toolRequested: false,
        toolExecuted: false,
        durationMs: Date.now() - startTime,
      },
    });
  }

  if (initialLane.lane === 'SCHEDULE_WORKFLOW') {
    session.state.pendingAction = initialLane.workflowState;
    await saveHermesState(session.userId, session.tenantId, session.conversationId, session.state);
    const workflowMessages = [baseMessages[0], conversationSystem, stateContextBlock(session.state, initialLane), ...baseMessages.slice(1)];
    if (initialLane.allowedTools.includes('draft_schedule')) {
      return await executeLaneToolAndAnswer(
        key,
        models,
        workflowMessages,
        message,
        {
          type: 'TOOL_REQUEST',
          toolName: 'draft_schedule',
          arguments: {
            reportId: initialLane.workflowState.reportId,
            reportName: initialLane.workflowState.reportName,
            requestedDate: initialLane.workflowState.date || 'today',
            requestedTime: initialLane.workflowState.time || '',
            timezone: initialLane.workflowState.timezone || 'America/Phoenix',
          },
          reasonSummary: 'explicit schedule draft request in active schedule workflow',
        },
        toolCtx,
        baseMessages,
        startTime,
        tid,
        session,
        'SCHEDULE_WORKFLOW',
      );
    }
    return await runNoToolLaneResponse(
      key,
      models,
      workflowMessages,
      message,
      [
        '[SCHEDULE WORKFLOW]',
        initialLane.instruction,
        'The schedule workflow owns this turn. Do not call current-fact tools. Do not create a draft unless the server supplied draft_schedule.',
      ].join('\n'),
      baseMessages,
      startTime,
      tid,
      'SCHEDULE_WORKFLOW',
    );
  }

  if (initialLane.lane === 'REPORT_REFERENCE') {
    const referenceMessages = [baseMessages[0], conversationSystem, stateContextBlock(session.state, initialLane), ...baseMessages.slice(1)];
    if (initialLane.metadataOnly) {
      return await runNoToolLaneResponse(
        key,
        models,
        referenceMessages,
        message,
        'Use the authoritative report reference metadata to answer. Do not call tools.',
        baseMessages,
        startTime,
        tid,
        'REPORT_REFERENCE',
      );
    }
    return await executeLaneToolAndAnswer(
      key,
      models,
      referenceMessages,
      message,
      {
        type: 'TOOL_REQUEST',
        toolName: 'summarize_report',
        arguments: { reportId: initialLane.reportId || initialLane.referenceState.items[0]?.id || '' },
        reasonSummary: 'server-owned report reference resolved an exact report',
      },
      toolCtx,
      baseMessages,
      startTime,
      tid,
      session,
      'REPORT_REFERENCE',
    );
  }

  if (initialLane.lane === 'CURRENT_FACT') {
    const factMessages = [baseMessages[0], conversationSystem, stateContextBlock(session.state, initialLane), ...baseMessages.slice(1)];
    const firstCall = await callOpenRouterNative(key, models, factMessages, startTime, openRouterToolsFor(initialLane.allowedTools));
    if (!firstCall.ok) return degradedOpenRouterReply(String(firstCall.errorCode), 'openrouter', String(firstCall.model), startTime);
    const toolCalls = Array.isArray(firstCall.toolCalls) ? firstCall.toolCalls : [];
    if (!toolCalls.length) {
      const fallbackTool = initialLane.allowedTools[0];
      return await executeLaneToolAndAnswer(
        key,
        models,
        factMessages,
        message,
        { type: 'TOOL_REQUEST', toolName: fallbackTool, arguments: defaultLaneToolArguments(fallbackTool, message), reasonSummary: 'current fact lane requires governed evidence' },
        toolCtx,
        baseMessages,
        startTime,
        tid,
        session,
        'CURRENT_FACT',
      );
    }
    const toolCall = toolCalls[0] as Record<string, unknown>;
    const fn = safeObject(toolCall.function);
    const toolName = initialLane.allowedTools.includes(String(fn.name || '')) ? String(fn.name || '') : initialLane.allowedTools[0];
    const args = toolName === String(fn.name || '') ? parseToolArgs(fn.arguments) : {};
    return await executeLaneToolAndAnswer(
      key,
      models,
      factMessages,
      message,
      { type: 'TOOL_REQUEST', toolName, arguments: Object.keys(args).length ? args : defaultLaneToolArguments(toolName, message), reasonSummary: 'current fact lane selected governed evidence tool' },
      toolCtx,
      baseMessages,
      startTime,
      tid,
      session,
      'CURRENT_FACT',
    );
  }

  if (initialLane.lane === 'GENERAL_CONVERSATION' && session.state.pendingAction?.kind === 'schedule_report') {
    return await runNoToolLaneResponse(
      key,
      models,
      messages,
      message,
      [
        '[GENERAL CONVERSATION DURING ACTIVE WORKFLOW]',
        'Answer Ray’s unrelated question directly as normal assistant text.',
        'Do not use Nexus tools and do not reinterpret the message as a schedule field.',
        'Keep the active schedule workflow pending in server state.',
      ].join('\n'),
      baseMessages,
      startTime,
      tid,
      'GENERAL_CONVERSATION',
    );
  }

  const initialObligation = evidenceObligation(message, baseMessages);
  const initialTools = initialObligation.required ? openRouterToolsFor(initialObligation.allowedTools) : [];
  let firstCall = await callOpenRouterNative(key, models, messages, startTime, initialTools);
  if (!firstCall.ok) return degradedOpenRouterReply(String(firstCall.errorCode), 'openrouter', String(firstCall.model), startTime);
  let toolCalls = Array.isArray(firstCall.toolCalls) ? firstCall.toolCalls : [];
  if (!toolCalls.length) {
    const obligation = initialObligation;
    if (obligation.required) {
      const correctionSystem: ChatMessage = {
        role: 'system',
        content: [
          '[EVIDENCE OBLIGATION]',
          'The proposed answer requires current Nexus evidence or a governed draft tool.',
          `Obligation: ${obligation.obligation}`,
          `Allowed tools: ${obligation.allowedTools.join(', ')}`,
          obligation.missingFields?.length ? `Missing fields if clarification is needed: ${obligation.missingFields.join(', ')}` : '',
          `Reason: ${obligation.reasonSummary}`,
          'Use one of the supplied governed tools. If essential arguments are missing, ask a concise natural clarification question. Do not answer from general context.',
        ].filter(Boolean).join('\n'),
      };
      const correctionCall = await callOpenRouterNative(key, models, [...messages, { role: 'assistant', content: firstCall.reply || '' }, correctionSystem], startTime, openRouterToolsFor(obligation.allowedTools));
      if (!correctionCall.ok) return degradedOpenRouterReply(String(correctionCall.errorCode), 'openrouter', String(correctionCall.model), startTime);
      const correctionToolCalls = Array.isArray(correctionCall.toolCalls) ? correctionCall.toolCalls : [];
      if (!correctionToolCalls.length) {
        const mandatoryFallback = await runMandatoryToolFallback(key, models, messages, message, baseMessages, obligation, firstCall, correctionCall, toolCtx, startTime, tid);
        if (mandatoryFallback) return mandatoryFallback;
        if (obligation.missingFields?.length && correctionCall.reply) {
          return json({
            configured: true,
            reply: correctionCall.reply,
            metadata: {
              provider: 'openrouter',
              model: correctionCall.model,
              fallbackUsed: firstCall.fallbackUsed || correctionCall.fallbackUsed,
              traceId: tid,
              decisionType: 'CLARIFICATION',
              source: 'GENERAL_MODEL',
              evidenceObligation: obligation,
              conversationHistorySent: baseMessages.some((item) => item.role === 'assistant' || item.role === 'user') && baseMessages.length > 2,
              historyTurnCount: baseMessages.filter((item) => item.role === 'assistant' || item.role === 'user').length - 1,
              toolRequested: false,
              toolExecuted: false,
              modelRounds: 2,
              ...usageMetadata(correctionCall.usage as Record<string, unknown> | null, message, correctionCall.reply),
              maxOutputTokens: MAX_OUTPUT_TOKENS,
              durationMs: Date.now() - startTime,
            },
          });
        }
        return json({
          configured: true,
          reply: 'I need to retrieve the current Nexus record before answering that reliably, but I could not complete the governed lookup.',
          metadata: {
            provider: 'openrouter',
            model: correctionCall.model,
            fallbackUsed: firstCall.fallbackUsed || correctionCall.fallbackUsed,
            traceId: tid,
            decisionType: 'DEGRADED',
            source: 'SAFE_LEGACY_FALLBACK',
            errorCode: 'UNSUPPORTED_ANSWER_REQUIRES_EVIDENCE',
            evidenceObligation: obligation,
            toolRequested: false,
            toolExecuted: false,
            modelRounds: 2,
            durationMs: Date.now() - startTime,
          },
        });
      }
      firstCall = correctionCall;
      toolCalls = correctionToolCalls;
    } else {
    return json({
      configured: true,
      reply: firstCall.reply,
      metadata: {
        provider: 'openrouter',
        model: firstCall.model,
        fallbackUsed: firstCall.fallbackUsed,
        traceId: tid,
        decisionType: 'DIRECT_RESPONSE',
        source: 'GENERAL_MODEL',
        conversationHistorySent: baseMessages.some((item) => item.role === 'assistant' || item.role === 'user') && baseMessages.length > 2,
        historyTurnCount: baseMessages.filter((item) => item.role === 'assistant' || item.role === 'user').length - 1,
        toolRequested: false,
        toolExecuted: false,
        modelRounds: 1,
        ...usageMetadata(firstCall.usage as Record<string, unknown> | null, message, firstCall.reply),
        maxOutputTokens: MAX_OUTPUT_TOKENS,
        durationMs: Date.now() - startTime,
      },
    });
    }
  }

  const toolCall = toolCalls[0] as Record<string, unknown>;
  const fn = safeObject(toolCall.function);
  const toolName = String(fn.name || '');
  const args = parseToolArgs(fn.arguments);
  const decision: Extract<HermesTurnDecision, { type: 'TOOL_REQUEST' }> = {
    type: 'TOOL_REQUEST',
    toolName,
    arguments: args,
    reasonSummary: 'native model tool call',
  };
  const capabilityDecision = validateToolRequest(decision, toolCtx);
  const toolResultData = capabilityDecision.allowed
    ? await executeToolRequest(decision, toolCtx)
    : { ok: false, toolName, errorCode: capabilityDecision.reasonCode, evidenceSources: ['capability_os_gateway'], freshness: 'CURRENT' };
  const toolCallId = String(toolCall.id || `tool-${tid}`);
  const finalMessages: ChatMessage[] = [
    ...messages,
    {
      role: 'assistant',
      content: firstCall.reply || '',
      // OpenRouter accepts tool role messages with tool_call_id; the assistant tool_calls object
      // is included in the raw payload below by preserving it outside this typed helper.
    },
    {
      role: 'tool',
      tool_call_id: toolCallId,
      name: toolName,
      content: JSON.stringify({ capabilityDecision, toolResult: toolResultData }).slice(0, 5000),
    },
    {
      role: 'system',
      content: 'Write the final answer naturally from the authorized tool result. State uncertainty and data state honestly. Do not claim execution occurred for draft tools.',
    },
  ];
  const rawFinalMessages = [...messages, { role: 'assistant', content: firstCall.reply || '', tool_calls: [toolCall] }, finalMessages[finalMessages.length - 2], finalMessages[finalMessages.length - 1]];
  const finalCall = await callOpenRouterNative(key, models, rawFinalMessages as ChatMessage[], startTime);
  if (!finalCall.ok) return degradedOpenRouterReply(String(finalCall.errorCode), 'openrouter', String(finalCall.model), startTime);
  return json({
    configured: true,
    reply: finalCall.reply,
    metadata: {
      provider: 'openrouter',
      model: finalCall.model,
      fallbackUsed: firstCall.fallbackUsed || finalCall.fallbackUsed,
      traceId: tid,
      decisionType: 'TOOL_REQUEST',
      toolRequested: toolName,
      toolAllowed: capabilityDecision.allowed,
      toolExecuted: Boolean(capabilityDecision.allowed && toolResultData.ok),
      toolErrorCode: toolResultData.ok ? undefined : toolResultData.errorCode,
      source: capabilityDecision.allowed ? 'NEXUS_TOOL' : 'SAFE_LEGACY_FALLBACK',
      conversationHistorySent: baseMessages.some((item) => item.role === 'assistant' || item.role === 'user') && baseMessages.length > 2,
      historyTurnCount: baseMessages.filter((item) => item.role === 'assistant' || item.role === 'user').length - 1,
      modelRounds: 2,
      ...usageMetadata(finalCall.usage as Record<string, unknown> | null, message, finalCall.reply),
      maxOutputTokens: MAX_OUTPUT_TOKENS,
      durationMs: Date.now() - startTime,
    },
  });
}

async function runModelFirstOpenRouter(
  key: string,
  models: string[],
  baseMessages: ChatMessage[],
  message: string,
  context: Record<string, unknown> | undefined,
  authorization: string,
  startTime: number,
) {
  const tid = traceId();
  const actorRole = authorization ? 'ray' : 'anonymous';
  const toolCtx: ToolExecutionContext = {
    actorRole,
    tenantId: String(context?.tenantId || 'ray_pilot'),
    traceId: tid,
    authorization,
  };
  const decisionSystem: ChatMessage = {
    role: 'system',
    content: [
      '[MODEL-FIRST TURN DECISION]',
      'Return only JSON matching the HermesTurnDecision contract.',
      'Valid direct response shape: {"type":"DIRECT_RESPONSE","response":"..."}',
      'Valid tool request shape: {"type":"TOOL_REQUEST","toolName":"get_current_time","arguments":{},"reasonSummary":"current time requested"}',
      'Valid clarification shape: {"type":"CLARIFICATION","question":"...","missingFields":["..."]}',
      'Use DIRECT_RESPONSE for ordinary conversation, definitions, personal statements, planning, writing, identity, and repair.',
      'Use DIRECT_RESPONSE for broad brainstorming, requested lists, strategy discussion, conversational repair, and references to the visible conversation even when the topic is broad.',
      'If Ray asks for ideas, options, priorities, a comparison, a correction, or help thinking it through, provide a useful first-pass answer instead of asking what kind.',
      'For correction or repair messages like "that is not what I meant", "you misunderstood me", or "why did you answer that way", do not ask a broad clarification; acknowledge the mismatch, use the latest visible turns, and give the best corrected interpretation.',
      'For "help me think through a decision" when no details are provided, give a concise decision framework and invite Ray to plug in the options inside the same direct answer.',
      'Use TOOL_REQUEST only for current Nexus facts, authorized records, report summaries, aggregates, governed drafts, or scheduling drafts.',
      'Tool selection policy:',
      '- Current time or date -> get_current_time.',
      '- Hermes creator, age, identity, role, or permissions -> get_hermes_identity unless the stable identity context already answers fully.',
      '- Nexus version, wave, project completion, Alpha Supabase boundary, Department Operations migration state, Stripe live state, or trading state -> get_project_status or get_system_health.',
      '- Client/customer count, real-vs-synthetic clients, test records, or client evidence -> get_client_aggregate.',
      '- Report catalog, latest report, report names, or report follow-ups -> list_reports or summarize_report.',
      '- Approval, Ray Review, pending decisions, self-approval, or approval boundary -> get_approval_summary or draft_ray_review when Ray explicitly asks for a draft.',
      '- Department status or what Engineering/Credit/Operations should do next -> get_department_status.',
      '- Revenue, money move, realistic monetization, or projected vs actual revenue -> get_revenue_status.',
      '- Repo Intelligence status -> get_repo_intelligence_status.',
      '- Source, evidence, provenance, or "where did that come from" -> get_answer_provenance.',
      '- Explicit task draft request -> draft_task using the visible conversation for title/summary if Ray says "that" or "now".',
      '- Explicit Ray Review draft request -> draft_ray_review using the visible conversation for title/summary if Ray says "that".',
      '- Scheduling a named report at a time -> draft_schedule; default requestedDate to today when Ray says later today or gives a time without a date.',
      'Use CLARIFICATION only when essential details are missing and no useful safe first-pass answer can be given.',
      'Never expose hidden reasoning. reasonSummary is a short operational explanation.',
      `Approved tools: ${JSON.stringify(visibleToolList())}`,
    ].join('\n'),
  };
  const userTurn = baseMessages[baseMessages.length - 1];
  const contextMessages = baseMessages.slice(0, -1);
  const decisionMessages = [...contextMessages, decisionSystem, userTurn];
  const responseFormat = {
    type: 'json_schema',
    json_schema: {
      name: 'hermes_turn_decision',
      strict: true,
      schema: DECISION_SCHEMA,
    },
  };
  let decisionCall = await callOpenRouter(key, models, decisionMessages, startTime, responseFormat);
  let structuredOutputUsed = true;
  if (!decisionCall.ok && /^HTTP 4/.test(String(decisionCall.errorCode || ''))) {
    structuredOutputUsed = false;
    decisionCall = await callOpenRouter(key, models, [...contextMessages, decisionSystem, { role: 'system', content: 'Provider structured-output parameters were unavailable for this configured model. Return valid JSON only; the server will validate it before any tool execution.' }, userTurn], startTime);
  }
  let decision = decisionCall.ok ? parseDecision(decisionCall.reply) : null;
  if (!decision && decisionCall.ok) {
    const retryResponseFormat = structuredOutputUsed ? responseFormat : undefined;
    decisionCall = await callOpenRouter(key, models, [...contextMessages, decisionSystem, userTurn, { role: 'user', content: 'Return valid HermesTurnDecision JSON only for the current Ray message.' }], startTime, retryResponseFormat);
    decision = decisionCall.ok ? parseDecision(decisionCall.reply) : null;
  }
  if (!decisionCall.ok) return degradedOpenRouterReply(String(decisionCall.errorCode), 'openrouter', String(decisionCall.model), startTime);
  if ((!decision || (isToolFreeWritingRequest(message) && decision.type !== 'DIRECT_RESPONSE')) && isToolFreeWritingRequest(message)) {
    const writingCall = await callOpenRouter(key, models, [...contextMessages, decisionSystem, userTurn, { role: 'user', content: 'This is a writing, editing, prompt, or copy request. Return DIRECT_RESPONSE JSON only. Do not request Nexus tools unless Ray asks for current private records.' }], startTime);
    const writingDecision = writingCall.ok ? parseDecision(writingCall.reply) : null;
    if (writingDecision?.type === 'DIRECT_RESPONSE') {
      decisionCall = writingCall;
      decision = writingDecision;
      structuredOutputUsed = false;
    }
  }
  if (!decision) {
    const mandatoryDecision = inferMandatoryDecision(message, { type: 'DIRECT_RESPONSE', response: '' }, contextMessages.filter((item) => item.role !== 'system'));
    if (mandatoryDecision) {
      decision = mandatoryDecision;
      structuredOutputUsed = false;
    }
  }
  if (!decision) return degradedOpenRouterReply('MALFORMED_MODEL_DECISION', 'openrouter', String(decisionCall.model), startTime);

  if (isOverbroadClarification(decision, contextMessages.filter((item) => item.role !== 'system')) || (isRepairOrVisibleReference(message) && decision.type !== 'DIRECT_RESPONSE')) {
    const repairCall = await callOpenRouter(key, models, [...contextMessages, decisionSystem, userTurn, { role: 'user', content: 'You selected a broad clarification even though recent visible conversation exists. Return DIRECT_RESPONSE JSON that acknowledges the mismatch and gives the best corrected response from visible history. Do not ask a new question.' }], startTime);
    const repairDecision = repairCall.ok ? parseDecision(repairCall.reply) : null;
    if (repairDecision?.type === 'DIRECT_RESPONSE') {
      decisionCall = repairCall;
      decision = repairDecision;
      structuredOutputUsed = false;
    }
  }
  const mandatoryDecision = inferMandatoryDecision(message, decision, contextMessages.filter((item) => item.role !== 'system'));
  if (mandatoryDecision) {
    decision = mandatoryDecision;
    structuredOutputUsed = false;
  }

  if (decision.type === 'DIRECT_RESPONSE') {
    return json({
      configured: true,
      reply: decision.response,
      metadata: {
        provider: 'openrouter',
        model: decisionCall.model,
        fallbackUsed: decisionCall.fallbackUsed,
        traceId: tid,
        decisionType: 'DIRECT_RESPONSE',
        source: 'GENERAL_MODEL',
        structuredOutputUsed,
        toolRequested: false,
        toolExecuted: false,
        modelRounds: 1,
        ...usageMetadata(decisionCall.usage as Record<string, unknown> | null, message, decision.response),
        maxOutputTokens: MAX_OUTPUT_TOKENS,
        durationMs: Date.now() - startTime,
      },
    });
  }

  if (decision.type === 'CLARIFICATION') {
    return json({
      configured: true,
      reply: decision.question,
      metadata: {
        provider: 'openrouter',
        model: decisionCall.model,
        fallbackUsed: decisionCall.fallbackUsed,
        traceId: tid,
        decisionType: 'CLARIFICATION',
        missingFields: decision.missingFields,
        source: 'GENERAL_MODEL',
        structuredOutputUsed,
        modelRounds: 1,
        ...usageMetadata(decisionCall.usage as Record<string, unknown> | null, message, decision.question),
        durationMs: Date.now() - startTime,
      },
    });
  }

  const capabilityDecision = validateToolRequest(decision, toolCtx);
  const toolResultData = capabilityDecision.allowed
    ? await executeToolRequest(decision, toolCtx)
    : { ok: false, toolName: decision.toolName, errorCode: capabilityDecision.reasonCode, evidenceSources: ['capability_os_gateway'], freshness: 'CURRENT' };
  const finalSystem: ChatMessage = {
    role: 'system',
    content: [
      '[NEXUS TOOL RESULT]',
      'Write the final answer naturally from this authorized tool result.',
      'State uncertainty and data state honestly. Do not invent private facts. Do not claim execution occurred for draft tools.',
      JSON.stringify({ requestedTool: decision.toolName, capabilityDecision, toolResult: toolResultData }).slice(0, 5000),
    ].join('\n'),
  };
  const finalCall = await callOpenRouter(key, models, [...contextMessages, finalSystem, userTurn], startTime);
  if (!finalCall.ok) return degradedOpenRouterReply(String(finalCall.errorCode), 'openrouter', String(finalCall.model), startTime);
  return json({
    configured: true,
    reply: finalCall.reply,
    metadata: {
      provider: 'openrouter',
      model: finalCall.model,
      fallbackUsed: decisionCall.fallbackUsed || finalCall.fallbackUsed,
      traceId: tid,
      decisionType: 'TOOL_REQUEST',
      toolRequested: decision.toolName,
      toolAllowed: capabilityDecision.allowed,
      toolExecuted: Boolean(capabilityDecision.allowed && toolResultData.ok),
      toolErrorCode: toolResultData.ok ? undefined : toolResultData.errorCode,
      source: capabilityDecision.allowed ? 'NEXUS_TOOL' : 'SAFE_LEGACY_FALLBACK',
      structuredOutputUsed,
      modelRounds: 2,
      ...usageMetadata(finalCall.usage as Record<string, unknown> | null, message, finalCall.reply),
      maxOutputTokens: MAX_OUTPUT_TOKENS,
      durationMs: Date.now() - startTime,
    },
  });
}

function buildSafeHistory(ctx: Record<string, unknown> | undefined): ChatMessage[] {
  const raw = Array.isArray(ctx?.history) ? ctx.history : [];
  const out: ChatMessage[] = [];
  let total = 0;
  for (const item of raw.slice(-MAX_HISTORY_TURNS)) {
    const role = (item as Record<string, unknown>)?.role === 'assistant' ? 'assistant' : 'user';
    const content = String((item as Record<string, unknown>)?.content ?? '').trim().slice(0, 700);
    if (!content || blocked(content)) continue;
    if (total + content.length > MAX_HISTORY_CHARS) break;
    out.push({ role, content });
    total += content.length;
  }
  return out;
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors() });
  const startTime = Date.now();

  const body = await req.json().catch(() => ({}));
  const message: string = body?.message ?? '';
  const mode: string = body?.mode ?? 'conversation';
  const rawContext = safeObject(body?.context);
  if (Array.isArray(body?.visibleHistory)) rawContext.history = body.visibleHistory;
  if (!Array.isArray(rawContext.history) && Array.isArray(body?.recentHistory)) rawContext.history = body.recentHistory;
  const safePageContext = safeObject(body?.safePageContext);
  for (const [key, value] of Object.entries(safePageContext)) {
    if (!(key in rawContext)) rawContext[key] = value;
  }
  const context: Record<string, unknown> | undefined = rawContext;
  const authorization = req.headers.get('authorization') || '';
  const userId = actorIdFromAuthorization(authorization);
  const conversationId = String(body?.conversationId || rawContext.conversationId || 'default').slice(0, 120);
  const tenantId = typeof rawContext.tenantId === 'string' ? String(rawContext.tenantId) : null;

  // ── Diagnostic mode: report env status without exposing secrets ──
  if (message === '__diagnostic__') {
    const provider = (Deno.env.get('HERMES_CHAT_PROVIDER') ?? 'none').toLowerCase();
    const model = Deno.env.get('HERMES_MODEL') || Deno.env.get('HERMES_CHAT_MODEL');
    const fallback = Deno.env.get('HERMES_FALLBACK_MODEL') || Deno.env.get('HERMES_CHAT_FALLBACK_MODEL');
    const hasApiKey = provider === 'openrouter' ? !!Deno.env.get('OPENROUTER_API_KEY')
      : provider === 'gemini' ? !!Deno.env.get('GEMINI_API_KEY')
      : provider === 'ollama' ? !!Deno.env.get('OLLAMA_URL')
      : false;
    return json({
      configured: true,
      diagnostic: {
        providerConfigured: provider !== 'none',
        modelConfigured: !!model,
        fallbackConfigured: !!fallback,
        apiKeyConfigured: hasApiKey,
        selectedProvider: provider,
        selectedModel: model ?? 'not set',
        selectedFallbackModel: fallback ?? 'not set',
        allowedProviders: [...ALLOWED_PROVIDERS],
      },
      metadata: { provider: 'diagnostic', model: 'diagnostic', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
    });
  }

  // ── Guard: input size ──
  if (message.length > MAX_INPUT_CHARS) {
    return json({
      configured: true, reply: `Input too long (${message.length} chars, max ${MAX_INPUT_CHARS}). Please shorten your message.`,
      metadata: { provider: 'none', model: 'none', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
    });
  }

  // ── Guard: dangerous actions ──
  const policyStatusQuestion = /\b(can nexus|is nexus allowed|is .* live|current .*status|what is .*status)\b.*\b(stripe|payment|payments|trading|trade|trades)\b/i.test(message);
  const deploymentStatusQuestion = /\b(what|which|is|was|did|has|current|running)\b.*\b(deployed|deployment|deploy commit|build|version)\b/i.test(message);
  if ((REJECT_ACTIONS.test(message) && !policyStatusQuestion && !deploymentStatusQuestion) || SELF_AUTHORIZATION_ACTIONS.test(message)) {
    return json({
      configured: true, reply: 'This action is approval-gated. I will not send execution requests to a model.',
      metadata: { provider: 'none', model: 'blocked', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
    });
  }

  // Firewall: the user message is refused outright if it references private data.
  if (blocked(String(message)))
    return json({ configured: true, reply: "I won't process private data through an external model." });

  const dynamic = buildDynamicContext(mode, context);
  const history = buildSafeHistory(context);

  // Ordered for prompt caching: stable cached block, then small dynamic block, then user message.
  const messages: ChatMessage[] = [{ role: 'system', content: stableSystem() }];
  if (dynamic) messages.push({ role: 'system', content: dynamic });
  messages.push(...history);
  messages.push({ role: 'user', content: message });

  // Gemini takes a single text blob; flatten the same ordered content.
  const flat = messages.map((m) => (m.role === 'user' ? `Ray: ${m.content}` : m.content)).join('\n\n');

  const provider = (Deno.env.get('HERMES_CHAT_PROVIDER') ?? 'none').toLowerCase();
  const model = Deno.env.get('HERMES_MODEL') || Deno.env.get('HERMES_CHAT_MODEL');

  // ── Guard: provider allowlist ──
  if (provider !== 'none' && !ALLOWED_PROVIDERS.has(provider)) {
    return json({
      configured: false,
      metadata: { provider, model: 'none', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
    });
  }

  try {
    if (provider === 'openrouter') {
      const key = Deno.env.get('OPENROUTER_API_KEY');
      if (!key) return json({
        configured: false,
        metadata: { provider: 'openrouter', model: 'none', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
      });

      // Build model list: filter to only valid OpenRouter model IDs
      // Ollama models (ollama/*) cannot be used through OpenRouter
      const rawModels = [model ?? 'openai/gpt-4o-mini', Deno.env.get('HERMES_FALLBACK_MODEL') || Deno.env.get('HERMES_CHAT_FALLBACK_MODEL')]
        .filter((m): m is string => Boolean(m && m.trim()));
      const models = rawModels.filter(m => !m.startsWith('ollama/'));
      if (models.length === 0) models.push('openai/gpt-4o-mini');

      if (mode === 'model_first_conversation') {
        const sessionState = await loadHermesState(userId, conversationId);
        return await runConversationalOpenRouter(
          key,
          models,
          messages,
          message,
          context,
          authorization,
          startTime,
          { userId, tenantId, conversationId, state: sessionState },
        );
      }

      let lastError = '';
      for (const m of models) {
        try {
          const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
            body: JSON.stringify({ model: m, messages, max_tokens: MAX_OUTPUT_TOKENS }),
          });
          if (!r.ok) {
            lastError = `HTTP ${r.status}`;
            continue;
          }
          const d = await r.json();
          if (d?.error) {
            lastError = String(d.error?.message || d.error || 'provider error').slice(0, 100);
            continue;
          }
          const reply = d?.choices?.[0]?.message?.content;
          if (reply && String(reply).trim()) {
            const estInput = Math.ceil(message.length / 4);
            const estOutput = Math.ceil(String(reply).length / 4);
            return json({
              configured: true, reply: String(reply),
              metadata: { provider: 'openrouter', model: m, fallbackUsed: models.length > 1 && m !== models[0], estimatedInputTokens: estInput, estimatedOutputTokens: estOutput, maxOutputTokens: MAX_OUTPUT_TOKENS, source: 'hermes-chat', durationMs: Date.now() - startTime },
            });
          }
          lastError = 'Empty reply from model';
        } catch (e) {
          lastError = String(e).slice(0, 100);
          continue;
        }
      }
      return json({
        configured: true, reply: `I'm configured for OpenRouter but the model call failed. Safe error: ${lastError}. I used local reasoning instead.`,
        metadata: { provider: 'openrouter', model: models[0] ?? 'none', fallbackUsed: true, errorCode: lastError, source: 'hermes-chat', durationMs: Date.now() - startTime },
      });
    }

    if (provider === 'gemini') {
      const key = Deno.env.get('GEMINI_API_KEY');
      if (!key) return json({
        configured: false,
        metadata: { provider: 'gemini', model: 'none', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
      });
      const m = model ?? 'gemini-1.5-flash';
      const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${key}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: flat }] }], generationConfig: { maxOutputTokens: MAX_OUTPUT_TOKENS } }),
      });
      const d = await r.json();
      const reply = d?.candidates?.[0]?.content?.parts?.[0]?.text ?? '';
      return json({
        configured: true, reply,
        metadata: { provider: 'gemini', model: m, fallbackUsed: false, estimatedInputTokens: Math.ceil(flat.length / 4), estimatedOutputTokens: Math.ceil(reply.length / 4), maxOutputTokens: MAX_OUTPUT_TOKENS, source: 'hermes-chat', durationMs: Date.now() - startTime },
      });
    }

    if (provider === 'ollama') {
      const base = Deno.env.get('OLLAMA_URL');
      if (!base) return json({
        configured: false,
        metadata: { provider: 'ollama', model: 'none', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
      });
      const m = model ?? 'qwen2.5:0.5b';
      const r = await fetch(`${base.replace(/\/$/, '')}/api/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ model: m, stream: false, messages, options: { num_predict: MAX_OUTPUT_TOKENS } }),
      });
      const d = await r.json();
      const reply = d?.message?.content ?? '';
      return json({
        configured: true, reply,
        metadata: { provider: 'ollama', model: m, fallbackUsed: false, estimatedInputTokens: Math.ceil(message.length / 4), estimatedOutputTokens: Math.ceil(reply.length / 4), maxOutputTokens: MAX_OUTPUT_TOKENS, source: 'hermes-chat', durationMs: Date.now() - startTime },
      });
    }

    return json({
      configured: false,
      metadata: { provider: 'none', model: 'none', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
    });
  } catch (e) {
    return json({
      configured: false, error: String(e),
      metadata: { provider, model: 'error', fallbackUsed: false, source: 'hermes-chat', durationMs: Date.now() - startTime },
    });
  }
});
