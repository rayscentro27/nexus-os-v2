import { reportRegistry } from '../../data/reportRegistry.js';
import { getExecutiveCommandCenterSnapshot } from '../executive/executiveCommandCenterAdapter';
import { answerExecutiveIntent } from '../executive/hermesExecutiveAdvisor';
import { evaluateCapabilityPolicy } from '../capabilities/capabilityPolicy';
import type { CapabilityDataClass, CapabilityApprovalLevel } from '../capabilities/capabilityTypes';
import type { EvidenceState } from '../executive/executiveTypes';
import type { HermesAdvisoryContext, HermesConversationInput } from './hermesConversationTypes';

export type HermesToolOperationMode = 'READ_ONLY' | 'ADVISORY' | 'DRAFT_ONLY' | 'APPROVAL_GATED' | 'BOUNDED_EXECUTION';

export interface HermesToolDefinition {
  toolId: string;
  name: string;
  description: string;
  capabilityId: string;
  operationMode: HermesToolOperationMode;
  inputSchema: unknown;
  outputSchema: unknown;
  allowedDataClasses: CapabilityDataClass[];
  prohibitedDataClasses: CapabilityDataClass[];
  allowedBrainIds: string[];
  approvalLevel: CapabilityApprovalLevel;
  requiresExplicitActionIntent: boolean;
  healthSource: string;
}

export interface HermesToolResult {
  toolId: string;
  text: string;
  evidenceState: EvidenceState | 'TEST_ONLY' | 'NOT_CONFIGURED' | 'BLOCKED_BY_POLICY' | 'PROHIBITED';
  evidenceIds: string[];
  sourceLabels: string[];
  observedAt: string;
}

export type HermesAnswerSourceType =
  | 'TOOL'
  | 'APPROVED_KNOWLEDGE'
  | 'OPERATING_CONTEXT'
  | 'CONVERSATION_MEMORY'
  | 'MODEL_REASONING'
  | 'HYBRID';

export interface HermesAnswerProvenance {
  answerId: string;
  sourceType: HermesAnswerSourceType;
  toolCalls: Array<{ toolId: string; evidenceIds: string[] }>;
  evidenceIds: string[];
  sourceLabels: string[];
  evidenceState: string;
  generatedAt: string;
  confidence: number;
  answerKind: 'FACT' | 'RECOMMENDATION' | 'INTERPRETATION' | 'MIXED';
}

export interface NexusReportCatalogItem {
  reportId: string;
  title: string;
  category: string;
  createdAt?: string;
  updatedAt?: string;
  sourcePath: string;
  summary: string;
  dataClass: string;
  allowedBrainIds: string[];
  evidenceState: string;
}

export interface HermesCustomerAggregate {
  totalAuthorizedRecords: number;
  syntheticRecords: number;
  realRecords: number | null;
  activeWorkflows: number;
  blockedWorkflows: number;
  evidenceState: string;
  observedAt: string;
  limitations: string[];
}

export interface HermesReasoningRequest {
  message: string;
  brainId: 'hermes';
  actorRole: string;
  sessionId: string;
  activeTopic?: { topicId: string; label: string; summary: string };
  recentConversation: Array<{ role: 'ray' | 'hermes'; text: string }>;
  availableTools: Array<{ toolId: string; description: string; inputSchema: unknown; dataClasses: string[] }>;
  evidenceSummary: { facts: string[]; policies: string[]; recommendations: string[]; unknowns: string[] };
  constraints: string[];
}

export interface HermesReasoningPlan {
  interpretedIntent: string;
  conversationMode: string;
  answerDirectly: boolean;
  directAnswerDraft?: string;
  requestedTools: Array<{ toolId: string; arguments: Record<string, unknown>; reason: string }>;
  requiresClarification: boolean;
  clarificationQuestion?: string;
  proposedAction?: { actionType: string; explicitUserIntentDetected: boolean };
  confidence: number;
}

const observedAt = () => new Date().toISOString();
const lowerClean = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

export const hermesToolRegistry: HermesToolDefinition[] = [
  ['hermes.current_time', 'Hermes Current Time Tool', 'current Phoenix date and time', 'hermes_current_time_tool', 'READ_ONLY', [], 'NONE'],
  ['hermes.project_status', 'Hermes Project Status Tool', 'project, roadmap, wave, and department status', 'hermes_project_status_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.list_reports', 'Hermes Report Catalog Tool', 'sanitized report catalog listing', 'hermes_report_catalog_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.read_report_summary', 'Hermes Report Summary Tool', 'sanitized report summary lookup', 'hermes_report_catalog_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.find_report', 'Hermes Report Finder Tool', 'find reports by title, category, or keyword', 'hermes_report_catalog_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.customer_aggregate', 'Hermes Customer Aggregate Tool', 'admin aggregate customer/workflow status without PII', 'hermes_customer_aggregate_tool', 'READ_ONLY', ['CLIENT_AGGREGATE'], 'ADMIN'],
  ['hermes.system_health', 'Hermes System Health Tool', 'Executive System Health read model', 'hermes_system_health_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.approval_summary', 'Hermes Approval Summary Tool', 'Ray Review approval summary', 'hermes_approval_summary_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.work_summary', 'Hermes Governed Work Summary Tool', 'governed work status summary', 'hermes_work_summary_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.revenue_summary', 'Hermes Revenue Summary Tool', 'revenue and opportunity summary', 'hermes_revenue_summary_tool', 'READ_ONLY', ['INTERNAL_METADATA', 'FINANCIAL_DATA'], 'ADMIN'],
  ['hermes.capability_status', 'Hermes Capability Status Tool', 'Capability OS status summary', 'hermes_capability_status_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
  ['hermes.explain_source', 'Hermes Provenance Tool', 'explain the source trace for the prior answer', 'hermes_provenance_tool', 'READ_ONLY', ['INTERNAL_METADATA'], 'NONE'],
].map(([toolId, name, description, capabilityId, operationMode, allowedDataClasses, approvalLevel]) => ({
  toolId: String(toolId),
  name: String(name),
  description: String(description),
  capabilityId: String(capabilityId),
  operationMode: operationMode as HermesToolOperationMode,
  inputSchema: { type: 'object' },
  outputSchema: { type: 'object' },
  allowedDataClasses: allowedDataClasses as CapabilityDataClass[],
  prohibitedDataClasses: ['CREDENTIALS', 'CLIENT_PII', 'PRODUCTION_CONTROL'],
  allowedBrainIds: ['hermes'],
  approvalLevel: approvalLevel as CapabilityApprovalLevel,
  requiresExplicitActionIntent: false,
  healthSource: 'src/lib/hermes/hermesGeneralTools.ts',
}));

export function getHermesToolDefinition(toolId: string): HermesToolDefinition | null {
  return hermesToolRegistry.find((tool) => tool.toolId === toolId) || null;
}

export function createHermesReasoningRequest(input: HermesConversationInput, advisoryContext?: HermesAdvisoryContext): HermesReasoningRequest {
  return {
    message: input.message,
    brainId: 'hermes',
    actorRole: input.actorRole || 'admin',
    sessionId: input.session?.sessionId || input.sessionId || 'hermes-default-session',
    activeTopic: advisoryContext ? {
      topicId: advisoryContext.topicId || advisoryContext.topic,
      label: advisoryContext.topicLabel || advisoryContext.topic,
      summary: advisoryContext.summary,
    } : undefined,
    recentConversation: [
      ...(input.session?.lastUserMessage ? [{ role: 'ray' as const, text: input.session.lastUserMessage }] : []),
      ...(input.session?.lastHermesResponse ? [{ role: 'hermes' as const, text: input.session.lastHermesResponse }] : []),
    ],
    availableTools: hermesToolRegistry.map((tool) => ({
      toolId: tool.toolId,
      description: tool.description,
      inputSchema: tool.inputSchema,
      dataClasses: tool.allowedDataClasses,
    })),
    evidenceSummary: {
      facts: ['Ray is Founder, Owner, CEO, and final authority.', 'Live Stripe remains deferred; live trading remains blocked.'],
      policies: ['Capability OS and Brain Profile policy decide access; model output is advisory only.'],
      recommendations: ['Use Nexus-native tool orchestration before adding an agent framework.'],
      unknowns: ['Live provider state requires focused authenticated provider smoke evidence.'],
    },
    constraints: ['No client PII to external model routing.', 'No action execution without explicit user intent and policy preflight.', 'Maximum 3 tool rounds per turn.'],
  };
}

function validateTool(toolId: string, actorRole: HermesConversationInput['actorRole'] = 'admin'): HermesToolDefinition {
  const tool = getHermesToolDefinition(toolId);
  if (!tool) throw new Error(`Unknown Hermes tool: ${toolId}`);
  const policy = evaluateCapabilityPolicy(tool.capabilityId, {
    actorRole: actorRole === 'ray' ? 'admin' : actorRole === 'client' ? 'client' : actorRole === 'alpha' ? 'alpha' : 'admin',
    environment: 'development',
    requestedAction: 'read',
    requestedDataClasses: tool.allowedDataClasses,
    costWithinLimit: true,
  });
  if (!policy.allowed && !['REQUIRES_APPROVAL'].includes(policy.decision)) throw new Error(`Hermes tool denied: ${toolId}: ${policy.decision}`);
  return tool;
}

function toolResult(toolId: string, text: string, evidenceIds: string[], sourceLabels: string[], evidenceState: HermesToolResult['evidenceState'] = 'REPORT_BACKED'): HermesToolResult {
  return { toolId, text, evidenceState, evidenceIds, sourceLabels, observedAt: observedAt() };
}

export function runHermesTool(toolId: string, args: Record<string, unknown> = {}, input?: HermesConversationInput, previousProvenance?: HermesAnswerProvenance): HermesToolResult {
  validateTool(toolId, input?.actorRole);
  if (toolId === 'hermes.current_time') return hermesCurrentTime(String(args.timezone || 'America/Phoenix'));
  if (toolId === 'hermes.project_status') return hermesProjectStatus(String(args.query || input?.message || ''));
  if (toolId === 'hermes.list_reports') return hermesListReports();
  if (toolId === 'hermes.read_report_summary') return hermesReadReportSummary(String(args.reportId || args.query || input?.message || ''));
  if (toolId === 'hermes.find_report') return hermesFindReport(String(args.query || input?.message || ''));
  if (toolId === 'hermes.customer_aggregate') return hermesCustomerAggregate();
  if (toolId === 'hermes.system_health') return toolResult(toolId, answerExecutiveIntent('executive_system_health'), ['executive_system_health'], ['Executive Command Center snapshot']);
  if (toolId === 'hermes.approval_summary') return toolResult(toolId, answerExecutiveIntent('executive_approval_status'), ['executive_approval_status'], ['Executive Command Center snapshot']);
  if (toolId === 'hermes.work_summary') return toolResult(toolId, answerExecutiveIntent('executive_work_status'), ['executive_work_status'], ['Executive Command Center snapshot']);
  if (toolId === 'hermes.revenue_summary') return toolResult(toolId, answerExecutiveIntent('executive_revenue_status'), ['executive_revenue_status'], ['Executive Command Center snapshot']);
  if (toolId === 'hermes.capability_status') return toolResult(toolId, answerExecutiveIntent('capability_status'), ['capability_os_registry'], ['Capability OS registry']);
  if (toolId === 'hermes.explain_source') return hermesExplainSource(previousProvenance);
  throw new Error(`Unhandled Hermes tool: ${toolId}`);
}

function hermesCurrentTime(timezone: string): HermesToolResult {
  const tz = /phoenix|arizona/i.test(timezone) ? 'America/Phoenix' : timezone;
  const now = new Date();
  const time = now.toLocaleTimeString('en-US', { timeZone: tz, hour: 'numeric', minute: '2-digit', hour12: true });
  const date = now.toLocaleDateString('en-US', { timeZone: tz, weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  return toolResult('hermes.current_time', `It’s ${time} in Phoenix. Today is ${date}.`, ['browser_clock'], [`Browser clock formatted for ${tz}`], 'LIVE');
}

function hermesProjectStatus(query: string): HermesToolResult {
  const lower = lowerClean(query);
  if (/department operations|governed automation|department/.test(lower)) {
    return toolResult('hermes.project_status', 'Department Operations and governed automation are **NEXT/PARTIAL**, not fully approved as the next operating phase. The foundations exist: Capability OS, governed work, Ray Review, brain boundaries, and Hermes conversation certification work. The gate is that Hermes general conversation must be certified before Department Operations is approved.', ['capability_os_registry', 'wave_4a_roadmap', 'hermes_conversation_certification'], ['Capability OS registry', 'Founder Mode roadmap', 'Hermes certification reports']);
  }
  if (/wave|hermes|done|finish|finished|complete|next/.test(lower)) {
    return toolResult('hermes.project_status', 'We are on **Nexus OS 3.0 Wave 4A.4**: Hermes general intelligence, governed tool use, broad conversation certification, and production verification. Prior Waves completed the Executive foundation, Knowledge/Brain layer, Capability OS, Workroom rendering, and advisory-context ownership. Department Operations remains next after this certification passes.', ['wave_4a_4', 'recent_commits', 'capability_os_registry'], ['Current prompt checkpoint', 'Git recent commits', 'Capability OS registry']);
  }
  return toolResult('hermes.project_status', 'Project status is report-backed: Hermes certification is the current gate; Department Operations is next; live Stripe is deferred; live trading is blocked; Alpha remains isolated from Supabase/client data.', ['executive_roadmap', 'capability_os_registry'], ['Founder Mode roadmap', 'Capability OS registry']);
}

function catalogItems(): NexusReportCatalogItem[] {
  return reportRegistry
    .filter((item: { available?: boolean; path?: string }) => item.available && item.path && !/secret|credential|cache|tmp|private/i.test(item.path))
    .map((item: { id: string; title: string; category: string; path: string; modified?: string; content?: string }) => ({
      reportId: item.id,
      title: item.title,
      category: item.category,
      updatedAt: item.modified,
      sourcePath: item.path,
      summary: String(item.content || '').split(/\n\s*\n/).find((part) => /status|ok|summary|generated|blocker/i.test(part))?.replace(/\s+/g, ' ').slice(0, 360) || `${item.category} report available.`,
      dataClass: 'INTERNAL_METADATA',
      allowedBrainIds: ['hermes'],
      evidenceState: 'REPORT_BACKED',
    }));
}

function latestReports(): NexusReportCatalogItem[] {
  return [...catalogItems()].sort((a, b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));
}

function hermesListReports(): HermesToolResult {
  const reports = latestReports();
  const categories = [...new Set(reports.map((item) => item.category))].slice(0, 8).join(', ');
  const top = reports.slice(0, 5).map((item) => `- ${item.title} (${item.category}; ${item.updatedAt || 'unknown date'})`).join('\n');
  return toolResult('hermes.list_reports', `Yes. I have ${reports.length} approved report snapshots indexed. Main categories include ${categories}.\n\nMost recent indexed reports:\n${top}`, reports.slice(0, 5).map((item) => item.reportId), ['Sanitized report registry']);
}

function hermesFindReport(query: string): HermesToolResult {
  const q = lowerClean(query);
  const reports = latestReports().filter((item) => lowerClean(`${item.title} ${item.category} ${item.reportId}`).includes(q) || q.split(' ').some((part) => part.length > 3 && lowerClean(`${item.title} ${item.category}`).includes(part))).slice(0, 5);
  if (!reports.length) return toolResult('hermes.find_report', 'I do not see an approved report matching that wording in the sanitized catalog. I did not scan arbitrary files.', ['report_catalog'], ['Sanitized report registry'], 'UNKNOWN');
  return toolResult('hermes.find_report', `Matching approved reports:\n${reports.map((item) => `- ${item.title} (${item.category}; ${item.updatedAt || 'unknown date'}): ${item.summary}`).join('\n')}`, reports.map((item) => item.reportId), ['Sanitized report registry']);
}

function hermesReadReportSummary(query: string): HermesToolResult {
  const result = hermesFindReport(query);
  if (result.evidenceState === 'UNKNOWN') return result;
  const firstId = result.evidenceIds[0];
  const report = latestReports().find((item) => item.reportId === firstId);
  if (!report) return result;
  return toolResult('hermes.read_report_summary', `${report.title}: ${report.summary}\n\nCategory: ${report.category}. Updated: ${report.updatedAt || 'unknown'}. Evidence state: report-backed sanitized summary.`, [report.reportId], ['Sanitized report registry']);
}

function hermesCustomerAggregate(): HermesToolResult {
  const state = getExecutiveCommandCenterSnapshot();
  const customerSummary = state.customerSummary;
  const syntheticSignals = customerSummary.filter((item) => /synthetic|test|fake/i.test(`${item.label} ${item.value} ${item.evidence.source}`)).length;
  const blocked = customerSummary.filter((item) => /block|missing|flag|approval|deferred|no_authenticated_session/i.test(`${item.status} ${item.label} ${item.value} ${item.evidence.source}`)).length;
  const aggregate: HermesCustomerAggregate = {
    totalAuthorizedRecords: customerSummary.length,
    syntheticRecords: syntheticSignals || customerSummary.length,
    realRecords: null,
    activeWorkflows: customerSummary.filter((item) => /active|ready|healthy|connected_with_records/i.test(item.status)).length,
    blockedWorkflows: blocked,
    evidenceState: 'AGGREGATE_REPORT_BACKED',
    observedAt: observedAt(),
    limitations: ['This is an admin aggregate/read-model answer.', 'No client names, addresses, account numbers, or credit details are exposed.', 'No active paying customer count is claimed from synthetic/test evidence.'],
  };
  return toolResult('hermes.customer_aggregate', `We have authorized aggregate customer/workflow evidence, mostly synthetic/test certification signals. Aggregate records visible: ${aggregate.totalAuthorizedRecords}. Synthetic/test signals: ${aggregate.syntheticRecords}. Real active paying customers: not confirmed by this tool. Active workflows: ${aggregate.activeWorkflows}; blocked workflows: ${aggregate.blockedWorkflows}.\n\nLimitation: ${aggregate.limitations.join(' ')}`, ['customer_operations_summary', 'executive_customer_signals'], ['Executive Command Center customer aggregate'], 'REPORT_BACKED');
}

function hermesExplainSource(previous?: HermesAnswerProvenance): HermesToolResult {
  if (!previous) return toolResult('hermes.explain_source', 'I do not have a previous answer provenance record in this session yet.', ['no_previous_provenance'], ['Hermes provenance memory'], 'UNKNOWN');
  const tools = previous.toolCalls.map((call) => `${call.toolId} (${call.evidenceIds.join(', ') || 'no evidence ids'})`).join('; ') || 'no tool calls';
  return toolResult('hermes.explain_source', `That answer came from ${previous.sourceLabels.join(', ') || previous.sourceType}. Evidence state: ${previous.evidenceState}. Tools: ${tools}. Answer type: ${previous.answerKind}. Generated: ${previous.generatedAt}. Confidence: ${Math.round(previous.confidence * 100)}%.`, previous.evidenceIds, previous.sourceLabels.length ? previous.sourceLabels : ['Hermes provenance memory'], previous.evidenceState as HermesToolResult['evidenceState']);
}

export function provenanceFromTool(tool: HermesToolResult, answerId: string, answerKind: HermesAnswerProvenance['answerKind'] = 'FACT', confidence = 0.92): HermesAnswerProvenance {
  return {
    answerId,
    sourceType: 'TOOL',
    toolCalls: [{ toolId: tool.toolId, evidenceIds: tool.evidenceIds }],
    evidenceIds: tool.evidenceIds,
    sourceLabels: tool.sourceLabels,
    evidenceState: tool.evidenceState,
    generatedAt: tool.observedAt,
    confidence,
    answerKind,
  };
}

export function provenanceFromContext(input: {
  answerId: string;
  sourceType: HermesAnswerSourceType;
  evidenceIds: string[];
  sourceLabels: string[];
  evidenceState: string;
  answerKind: HermesAnswerProvenance['answerKind'];
  confidence?: number;
}): HermesAnswerProvenance {
  return {
    answerId: input.answerId,
    sourceType: input.sourceType,
    toolCalls: [],
    evidenceIds: input.evidenceIds,
    sourceLabels: input.sourceLabels,
    evidenceState: input.evidenceState,
    generatedAt: observedAt(),
    confidence: input.confidence ?? 0.84,
    answerKind: input.answerKind,
  };
}
