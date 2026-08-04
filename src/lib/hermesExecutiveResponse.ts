/**
 * Executive Response Layer for Nexus Hermes (TypeScript).
 *
 * Provides functions to transform raw operational data into concise,
 * plain-English executive reports for Ray.
 */

const PHOENIX_TZ = `America/Phoenix`;

// --- Types ---

export interface ExecutiveSystemStatus {
  overall: string;
  summary: string;
  workingNormally: string[];
  needsAttention: string[];
  research: string;
  trading: string;
  communications: string;
  clientOperations: string;
  recommendedNextAction: string;
  actionRequiredFromRay: 'YES' | 'NO';
  updated: string;
}

export interface ResearchOpportunity {
  title: string;
  whyItMatters: string;
  estimatedValue: string;
  effort: string;
  confidence: string;
  recommendedAction: string;
  duplicateCount: number;
  sourceId: string;
}

export interface ExecutiveResearchSummary {
  totalRuns: number;
  opportunityGroups: number;
  duplicatesConsolidated: number;
  activeFailures: number;
  mainTopics: string[];
  topOpportunities: ResearchOpportunity[];
  topRecommendation: string;
  recommendedNextAction: string;
  actionRequiredFromRay: 'YES' | 'NO';
}

export interface FailureItem {
  name: string;
  impact: string;
  actionRequired: string;
  owner: string;
  isCurrent: boolean;
}

export interface ExecutiveFailureReport {
  activeIssues: FailureItem[];
  externalSetupNeeded: FailureItem[];
  hiddenHistoricalCount: number;
  activeCount: number;
  totalActive: number;
}

// --- Phoenix Time ---

export function formatPhoenixTime(utcString?: string): string {
  const now = new Date();
  const phoenixNow = new Date(now.toLocaleString('en-US', { timeZone: PHOENIX_TZ }));

  if (!utcString) {
    return `${phoenixNow.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })} Phoenix time`;
  }

  const utcDate = new Date(utcString);
  const phoenixDate = new Date(utcDate.toLocaleString('en-US', { timeZone: PHOENIX_TZ }));

  const diffMs = phoenixNow.getTime() - phoenixDate.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  const timeStr = phoenixDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });

  if (diffDays === 0) {
    return `Today at ${timeStr}`;
  }
  if (diffDays === 1) {
    return `Yesterday at ${timeStr}`;
  }
  if (diffDays <= 7) {
    return `${diffDays} days ago at ${timeStr}`;
  }
  return phoenixDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric' }) + ` at ${timeStr}`;
}

// --- Technical Detail Hiding ---

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
const SCRIPT_PATH_RE = /scripts\/[\w/]+\.py/g;
const DATA_PATH_RE = /data\/[\w/_-]+\.json/g;
const ISO_TS_RE = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\.\d]*Z?/g;

export function hideTechnicalDetails(text: string): string {
  return text
    .replace(UUID_RE, '[ID hidden]')
    .replace(SCRIPT_PATH_RE, '[script]')
    .replace(DATA_PATH_RE, '[data file]')
    .replace(ISO_TS_RE, '[timestamp]');
}

// --- System Status from Process Registry ---

interface ProcessRecord {
  process_id?: string;
  name?: string;
  category?: string;
  mode?: string;
  enabled?: boolean;
  last_status?: string;
  telegram_allowed?: boolean;
}

function categorizeProcesses(registry: ProcessRecord[]) {
  const enabled = registry.filter(p => p.enabled);
  const completed = enabled.filter(p => p.last_status === 'completed');
  const failed = enabled.filter(p => p.last_status === 'failed');
  const blocked = registry.filter(p => p.mode === 'BLOCKED');

  return { enabled, completed, failed, blocked };
}

export function buildExecutiveSystemStatus(registry: ProcessRecord[]): ExecutiveSystemStatus {
  const { enabled, completed, failed, blocked } = categorizeProcesses(registry);

  const working = completed.slice(0, 10).map(p => p.name || p.process_id || 'Unknown');
  const attention: string[] = [];
  for (const p of blocked) attention.push(`${p.name || p.process_id} — blocked`);
  for (const p of failed) attention.push(`${p.name || p.process_id} — last run failed`);

  const researchItems = registry.filter(p =>
    (p.category || '').includes('research') || (p.category || '').includes('notebook')
  );
  const researchCompleted = researchItems.filter(p => p.last_status === 'completed').length;

  const tradingItems = registry.filter(p =>
    (p.category || '').includes('trading') || (p.category || '').includes('signal')
  );
  const commsItems = registry.filter(p =>
    ['telegram', 'email', 'sms', 'whatsapp'].some(kw => (p.category || '').includes(kw))
  );
  const commsActive = commsItems.filter(p => p.enabled && p.last_status === 'completed');

  const clientItems = registry.filter(p =>
    (p.category || '').includes('client') || (p.category || '').includes('portal')
  );

  let overall = 'OPERATIONAL';
  if (failed.length > 0 || blocked.length > 2) overall = 'ATTENTION_NEEDED';
  else if (completed.length < enabled.length * 0.8) overall = 'MOSTLY_OPERATIONAL';

  const recommended = attention.length > 0
    ? `Address: ${attention[0]}`
    : 'System is running normally. No immediate action required.';

  return {
    overall,
    summary: `${completed.length} of ${enabled.length} enabled processes completed successfully.`,
    workingNormally: working,
    needsAttention: attention.slice(0, 5),
    research: `${researchCompleted} of ${researchItems.length} research processes completed`,
    trading: `${tradingItems.length} trading processes registered`,
    communications: `${commsActive.length} of ${commsItems.length} communication channels active`,
    clientOperations: `${clientItems.length} client operations processes active`,
    recommendedNextAction: recommended,
    actionRequiredFromRay: (failed.length > 0 || blocked.length > 0) ? 'YES' : 'NO',
    updated: formatPhoenixTime(),
  };
}

export function formatSystemStatusReport(status: ExecutiveSystemStatus): string {
  const lines: string[] = [
    'NEXUS SYSTEM STATUS',
    '',
    `Overall: ${status.overall.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}`,
    '',
    `Summary: ${status.summary}`,
    '',
  ];

  if (status.workingNormally.length > 0) {
    lines.push('Working normally');
    for (const item of status.workingNormally.slice(0, 8)) {
      lines.push(`  - ${item}`);
    }
    lines.push('');
  }

  if (status.needsAttention.length > 0) {
    lines.push('Needs attention');
    for (const item of status.needsAttention) {
      lines.push(`  - ${item}`);
    }
    lines.push('');
  } else {
    lines.push('Needs attention: None');
    lines.push('');
  }

  lines.push(
    `Research: ${status.research}`,
    `Trading: ${status.trading}`,
    `Communications: ${status.communications}`,
    `Client operations: ${status.clientOperations}`,
    '',
    `Recommended next action: ${status.recommendedNextAction}`,
    `Action required from Ray: ${status.actionRequiredFromRay}`,
    `Updated: ${status.updated}`,
  );

  return lines.join('\n');
}

// --- Research Summary ---

interface ScoredResearchItem {
  source_id?: string;
  title?: string;
  recommended_route?: string;
  monetization_score?: number;
  implementation_effort?: string;
  urgency?: string;
  confidence?: number;
  _duplicate_count?: number;
}

function normalizeResearchQuery(item: ScoredResearchItem): string {
  let title = (item.title || '').toLowerCase().trim();
  const route = (item.recommended_route || '').toLowerCase().trim();
  title = title.replace(/^adapt:\s*/, '').replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ');
  return `${title}|${route}`;
}

export function deduplicateResearch(items: ScoredResearchItem[]): {
  deduplicated: ScoredResearchItem[];
  duplicatesConsolidated: number;
} {
  const groups = new Map<string, { representative: ScoredResearchItem; count: number }>();
  let duplicatesConsolidated = 0;

  for (const item of items) {
    const key = normalizeResearchQuery(item);
    if (groups.has(key)) {
      groups.get(key)!.count++;
      duplicatesConsolidated++;
    } else {
      groups.set(key, { representative: item, count: 1 });
    }
  }

  const deduplicated = Array.from(groups.values()).map(g => ({
    ...g.representative,
    _duplicate_count: g.count,
  }));

  deduplicated.sort((a, b) => (b.monetization_score || 0) - (a.monetization_score || 0));

  return { deduplicated, duplicatesConsolidated };
}

export function buildExecutiveResearchSummary(
  items: ScoredResearchItem[],
  maxItems = 5
): ExecutiveResearchSummary {
  if (!items || items.length === 0) {
    return {
      totalRuns: 0,
      opportunityGroups: 0,
      duplicatesConsolidated: 0,
      activeFailures: 0,
      mainTopics: [],
      topOpportunities: [],
      topRecommendation: 'No research data available.',
      recommendedNextAction: 'Run research to generate opportunities.',
      actionRequiredFromRay: 'NO',
    };
  }

  const { deduplicated, duplicatesConsolidated } = deduplicateResearch(items);

  // Extract topics
  const topicSet = new Set<string>();
  for (const item of deduplicated) {
    const title = (item.title || '').toLowerCase().replace(/^adapt:\s*/, '');
    for (const kw of ['credit', 'funding', 'grant', 'payment', 'client', 'social', 'trading', 'youtube', 'research']) {
      if (title.includes(kw)) topicSet.add(kw.charAt(0).toUpperCase() + kw.slice(1));
    }
  }

  // Build opportunities
  const opportunities: ResearchOpportunity[] = deduplicated.slice(0, maxItems).map(item => {
    const score = item.monetization_score || 0;
    const value = score >= 80 ? 'High' : score >= 70 ? 'Medium' : 'Moderate';
    const effort = (item.implementation_effort || 'medium').replace(/\b\w/g, c => c.toUpperCase());
    const confidence = item.confidence ? `${Math.round(item.confidence * 100)}%` : 'Not assessed';
    const route = (item.recommended_route || 'review').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const action = route !== 'Review' ? `Route to ${route}` : 'Review for suitability';
    const impact = (item.urgency === 'high' && score >= 75)
      ? 'Directly supports revenue or client operations'
      : item.urgency === 'high'
        ? 'High urgency, review quickly'
        : 'Contributes to business intelligence';

    return {
      title: (item.title || 'Unknown').replace(/^Adapt:\s*/, ''),
      whyItMatters: impact,
      estimatedValue: value,
      effort,
      confidence,
      recommendedAction: action,
      duplicateCount: item._duplicate_count || 1,
      sourceId: item.source_id || 'unknown',
    };
  });

  const topRec = opportunities.length > 0
    ? `${opportunities[0].title} — ${opportunities[0].whyItMatters}`
    : 'No research opportunities identified.';

  return {
    totalRuns: items.length,
    opportunityGroups: deduplicated.length,
    duplicatesConsolidated,
    activeFailures: 0,
    mainTopics: Array.from(topicSet).slice(0, 5),
    topOpportunities: opportunities,
    topRecommendation: topRec,
    recommendedNextAction: `Review the top ${opportunities.length} opportunities.`,
    actionRequiredFromRay: opportunities.length > 0 ? 'YES' : 'NO',
  };
}

export function formatResearchSummary(data: ExecutiveResearchSummary): string {
  const lines: string[] = [
    'RESEARCH SUMMARY',
    '',
    `Total research items: ${data.totalRuns}`,
    `Meaningful opportunity groups: ${data.opportunityGroups}`,
  ];

  if (data.duplicatesConsolidated > 0) {
    lines.push(`Duplicate results consolidated: ${data.duplicatesConsolidated}`);
  }

  lines.push(data.activeFailures > 0 ? `Active failures: ${data.activeFailures}` : 'Active failures: None');
  lines.push('');

  if (data.mainTopics.length > 0) {
    lines.push('Main topics');
    data.mainTopics.forEach((t, i) => lines.push(`  ${i + 1}. ${t}`));
    lines.push('');
  }

  if (data.topOpportunities.length > 0) {
    lines.push('Top opportunities');
    for (let i = 0; i < data.topOpportunities.length; i++) {
      const opp = data.topOpportunities[i];
      lines.push(`  ${i + 1}. ${opp.title}`);
      lines.push(`     Why: ${opp.whyItMatters}`);
      lines.push(`     Value: ${opp.estimatedValue} | Effort: ${opp.effort} | Confidence: ${opp.confidence}`);
      lines.push(`     Action: ${opp.recommendedAction}`);
      if (opp.duplicateCount > 1) lines.push(`     (${opp.duplicateCount} similar runs consolidated)`);
      lines.push('');
    }
  } else {
    lines.push('No opportunities found.', '');
  }

  lines.push(
    `Top recommendation: ${data.topRecommendation}`,
    '',
    `Recommended next action: ${data.recommendedNextAction}`,
    `Action required from Ray: ${data.actionRequiredFromRay}`,
  );

  return lines.join('\n');
}

// --- Pagination ---

const TELEGRAM_MAX = 4000;

export function paginateResponse(text: string, page = 1): { text: string; totalPages: number; currentPage: number } {
  const maxSize = TELEGRAM_MAX - 200;
  const pages: string[] = [];
  let current = '';
  let currentLen = 0;

  for (const line of text.split('\n')) {
    const lineLen = line.length + 1;
    if (currentLen + lineLen > maxSize && current) {
      pages.push(current);
      current = line;
      currentLen = lineLen;
    } else {
      current += (current ? '\n' : '') + line;
      currentLen += lineLen;
    }
  }
  if (current) pages.push(current);

  const totalPages = Math.max(1, pages.length);
  page = Math.max(1, Math.min(page, totalPages));
  let result = pages[page - 1] || 'No data available.';

  if (totalPages > 1) {
    result += `\n\nPage ${page}/${totalPages} — Say 'next page' or 'show page N'`;
  }

  return { text: result, totalPages, currentPage: page };
}

// --- Failure Report ---

interface BlockedAction {
  action?: string;
  status?: string;
  lane?: string;
  note?: string;
  required_runner?: string;
  name?: string;
  last_status?: string;
}

const STATUS_TRANSLATIONS: Record<string, string> = {
  BLOCKED_BY_PROVIDER_CONFIGURATION: 'External provider setup is incomplete',
  BLOCKED_BY_LEGAL_OR_POLICY_BOUNDARY: 'Intentionally restricted by current operating policy',
  WAITING_FOR_VALID_SIGNAL: 'Trading engine is active and waiting for a strategy signal',
  BLOCKED_AUTONOMOUS_EXECUTION: 'Requires direct Ray intervention',
  APPROVAL_GATED_LIVE_READY: 'Ready pending Ray approval',
  APPROVAL_GATED_LIVE_PENDING_ENV: 'Waiting for environment configuration',
  APPROVAL_GATED_LIVE_PENDING_RUNNER: 'Waiting for approved runner',
  APPROVAL_GATED_LIVE_PENDING_GUARD: 'Waiting for guard configuration',
};

function categorizeFailure(item: BlockedAction): 'ACTIVE_NOW' | 'RESOLVED' | 'EXTERNAL' | 'BOUNDARY' | 'HISTORICAL' {
  const status = (item.status || '').toUpperCase();
  const lastStatus = (item.last_status || '').toLowerCase();

  if (lastStatus === 'completed' || status.includes('RESOLVED')) return 'RESOLVED';
  if (status.includes('BLOCKED_AUTONOMOUS') || status.includes('LEGAL_OR_POLICY')) return 'BOUNDARY';
  if (status.includes('PENDING') || status.includes('PROVIDER')) return 'EXTERNAL';
  if (lastStatus === 'failed' || lastStatus === 'blocked') return 'ACTIVE_NOW';
  return 'HISTORICAL';
}

export function buildExecutiveFailureReport(
  approvalGatedActions: BlockedAction[],
  blockedProcesses: BlockedAction[]
): ExecutiveFailureReport {
  const all: BlockedAction[] = [...approvalGatedActions, ...blockedProcesses];
  const activeIssues: FailureItem[] = [];
  const externalSetup: FailureItem[] = [];
  let hiddenHistorical = 0;

  for (const item of all) {
    const cat = categorizeFailure(item);
    const name = (item.name || item.action || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const lane = (item.lane || 'general').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const status = item.status || 'UNKNOWN';
    const translated = STATUS_TRANSLATIONS[status] || status.replace(/_/g, ' ');

    if (cat === 'ACTIVE_NOW') {
      activeIssues.push({
        name,
        impact: `${lane} operations may be affected`,
        actionRequired: item.required_runner?.replace(/_/g, ' ') || item.note || 'Review and resolve',
        owner: 'Ray',
        isCurrent: true,
      });
    } else if (cat === 'EXTERNAL') {
      externalSetup.push({
        name: translated,
        impact: `Requires external provider setup`,
        actionRequired: item.required_runner?.replace(/_/g, ' ') || 'Configure provider',
        owner: 'Ray',
        isCurrent: true,
      });
    } else {
      hiddenHistorical++;
    }
  }

  return {
    activeIssues: activeIssues.slice(0, 5),
    externalSetupNeeded: externalSetup.slice(0, 3),
    hiddenHistoricalCount: hiddenHistorical,
    activeCount: activeIssues.length,
    totalActive: activeIssues.length + externalSetup.length,
  };
}

export function formatFailureReport(data: ExecutiveFailureReport): string {
  const lines: string[] = ['CURRENT ISSUES', ''];

  if (data.activeIssues.length > 0) {
    for (let i = 0; i < data.activeIssues.length; i++) {
      const issue = data.activeIssues[i];
      lines.push(`${i + 1}. ${issue.name}`);
      lines.push(`   Impact: ${issue.impact}`);
      lines.push(`   Action: ${issue.actionRequired}`);
      lines.push(`   Owner: ${issue.owner}`);
      lines.push('');
    }
  }

  if (data.externalSetupNeeded.length > 0) {
    lines.push('External setup needed');
    for (let i = 0; i < data.externalSetupNeeded.length; i++) {
      lines.push(`  ${i + 1}. ${data.externalSetupNeeded[i].name}`);
    }
    lines.push('');
  }

  if (data.totalActive === 0) {
    lines.push('No current issues.', '');
  }

  if (data.hiddenHistoricalCount > 0) {
    lines.push(`Historical issues hidden: ${data.hiddenHistoricalCount}`);
    lines.push('Say "show historical failures" to view them.', '');
  }

  lines.push(`Updated: ${formatPhoenixTime()}`);
  return lines.join('\n');
}

// --- Detail Expansion ---

export function formatTechnicalDetail(itemType: string, itemIndex: number, context: Record<string, unknown>): string {
  const lines = [`TECHNICAL DETAILS — ${itemType} #${itemIndex}`, ''];

  if (itemType === 'opportunity' && Array.isArray(context.topOpportunities)) {
    const items = context.topOpportunities as ResearchOpportunity[];
    if (itemIndex >= 1 && itemIndex <= items.length) {
      const opp = items[itemIndex - 1];
      lines.push(
        `Title: ${opp.title}`,
        `Source ID: ${opp.sourceId}`,
        `Value: ${opp.estimatedValue}`,
        `Effort: ${opp.effort}`,
        `Confidence: ${opp.confidence}`,
        `Duplicates consolidated: ${opp.duplicateCount}`,
      );
    } else {
      lines.push(`Item ${itemIndex} not found. Available: 1-${items.length}`);
    }
  } else {
    lines.push(`Details for ${itemType} #${itemIndex} not available in current context.`);
  }

  return lines.join('\n');
}
