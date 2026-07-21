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
const REJECT_ACTIONS = /\b(send|email|publish|post|deploy|charge|trade|dispute|seed|sql|drop|truncate|delete|start\s+live|stop\s+live|activate\s+live)\b/i;

// Stable, cached identity + business context. Keep this byte-stable to maximize prompt-cache hits;
// bump HERMES_CONTEXT_VERSION to intentionally bust the cache after edits. Contains only
// internal_summary-level business context — never secrets or customer data.
const STABLE_CONTEXT_BLOCK = `[HERMES — STABLE CONTEXT]

IDENTITY
You are Hermes, Ray's private conversational advisor and report interpreter for Nexus OS.
You are direct, concise, practical, and honest — no filler, no hype. If you are unsure of a
current fact, say so; never fabricate.

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

interface ChatMessage { role: 'system' | 'user' | 'assistant'; content: string; }

type HermesTurnDecision =
  | { type: 'DIRECT_RESPONSE'; response: string }
  | { type: 'TOOL_REQUEST'; toolName: string; arguments: Record<string, unknown>; reasonSummary: string }
  | { type: 'CLARIFICATION'; question: string; missingFields: string[] };

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

function traceId(): string {
  return `hermes-model-first-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`;
}

function safeObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringArg(args: Record<string, unknown>, key: string): string {
  return typeof args[key] === 'string' ? String(args[key]).slice(0, 240) : '';
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
    execute: async () => toolResult('get_system_health', { overallState: 'DEGRADED_CONFIG_AWARE', components: [{ name: 'OpenRouter Hermes chat', state: 'LIVE', source: 'hermes-chat diagnostic', freshness: 'CURRENT' }, { name: 'Stripe live payments', state: 'NOT_CONFIGURED', source: 'Capability OS', freshness: 'REPORT_BACKED' }, { name: 'Live trading', state: 'BLOCKED_BY_POLICY', source: 'Capability OS', freshness: 'REPORT_BACKED' }, { name: 'Department queues', state: 'SYNTHETIC_READ_MODEL', source: 'Wave 4 report', freshness: 'REPORT_BACKED' }], limitations: ['This is a safe summary, not raw logs.'] }, ['executive_system_health', 'capability_os']),
  },
  list_reports: {
    name: 'list_reports',
    description: 'List approved sanitized reports.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_report_catalog_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('list_reports', { reports: REPORTS.map(({ summary: _summary, ...item }) => item) }, ['sanitized_report_registry']),
  },
  summarize_report: {
    name: 'summarize_report',
    description: 'Summarize an approved report by reportId.',
    inputSchema: { type: 'object', required: ['reportId'], properties: { reportId: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_report_catalog_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async (_ctx, args) => {
      const reportId = stringArg(args, 'reportId');
      const report = REPORTS.find((item) => item.id === reportId || item.title.toLowerCase().includes(reportId.toLowerCase()));
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
    description: 'Get approved repository intelligence status summary; no shell or GitHub execution.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['repo_intelligence_registry'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async () => toolResult('get_repo_intelligence_status', { state: 'REPORT_BACKED', summary: 'Repo Intelligence remains a governed capability/research track. No arbitrary GitHub or shell execution is exposed to the model.' }, ['repo_intelligence_registry']),
  },
  get_answer_provenance: {
    name: 'get_answer_provenance',
    description: 'Explain source/provenance for the previous answer or trace.',
    inputSchema: { type: 'object', properties: { traceId: { type: 'string' }, conversationTurnId: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['hermes_provenance_tool'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'READ_ONLY',
    execute: async (_ctx, args) => toolResult('get_answer_provenance', { sourceType: 'GENERAL_MODEL', model: Deno.env.get('HERMES_MODEL') || 'openai/gpt-4o-mini', toolName: stringArg(args, 'traceId') ? undefined : 'none', evidenceSources: ['model_first_trace', 'visible_history'], freshness: 'CURRENT', limitations: ['No hidden reasoning is stored or exposed.'] }, ['model_first_trace']),
  },
  draft_task: {
    name: 'draft_task',
    description: 'Create a governed task draft only; does not approve or execute.',
    inputSchema: { type: 'object', required: ['title', 'summary'], properties: { title: { type: 'string' }, summary: { type: 'string' }, department: { type: 'string' }, riskClass: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['governed_work'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'DRAFT_ONLY',
    execute: async (_ctx, args) => toolResult('draft_task', { draftCreated: true, draftId: `draft-task-${crypto.randomUUID()}`, title: stringArg(args, 'title'), approvalRequired: true, executionStatus: 'NOT_EXECUTED' }, ['draft_task_memory']),
  },
  draft_ray_review: {
    name: 'draft_ray_review',
    description: 'Create a Ray Review draft only; cannot approve itself.',
    inputSchema: { type: 'object', required: ['title', 'summary'], properties: { title: { type: 'string' }, summary: { type: 'string' }, riskClass: { type: 'string' } }, additionalProperties: false },
    requiredRole: ['ray', 'admin'],
    requiredCapabilities: ['ray_review'],
    dataClassification: 'INTERNAL_SUMMARY',
    actionClass: 'DRAFT_ONLY',
    execute: async (_ctx, args) => toolResult('draft_ray_review', { draftCreated: true, draftId: `ray-review-${crypto.randomUUID()}`, title: stringArg(args, 'title'), approvalRequired: true, selfApproval: 'PROHIBITED', executionStatus: 'NOT_EXECUTED' }, ['ray_review_draft']),
  },
  draft_schedule: {
    name: 'draft_schedule',
    description: 'Create a schedule draft only after report and exact time are known.',
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
      'Use TOOL_REQUEST only for current Nexus facts, authorized records, report summaries, aggregates, governed drafts, or scheduling drafts.',
      'Use CLARIFICATION only when essential details are missing.',
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
  if (!decision) return degradedOpenRouterReply('MALFORMED_MODEL_DECISION', 'openrouter', String(decisionCall.model), startTime);

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
  const context: Record<string, unknown> | undefined = body?.context;

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
  if (REJECT_ACTIONS.test(message)) {
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
        return await runModelFirstOpenRouter(
          key,
          models,
          messages,
          message,
          context,
          req.headers.get('authorization') || '',
          startTime,
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
