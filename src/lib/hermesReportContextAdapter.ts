import { reportRegistry } from '../data/reportRegistry';

export interface HermesReportContext {
  ok: boolean;
  source: string;
  sourceType: 'report' | 'unavailable';
  liveData: false;
  generatedAt: string;
  summary: string;
  records: Array<Record<string, unknown>>;
  limitations: string[];
  safetyLevel: 'safe_read_only';
  requiresApprovalForExecution: boolean;
}

function field(content: string, key: string): string | null {
  const match = content.match(new RegExp(`^- ${key}: (.+)$`, 'm'));
  return match?.[1]?.trim() || null;
}

function generatedAt(content: string, fallback?: string): string {
  return content.match(/^Generated:\s*(.+)$/m)?.[1]?.trim() || fallback || 'timestamp unavailable';
}

export function getReportContext(reportQuery?: string): HermesReportContext {
  const query = (reportQuery || '').toLowerCase();
  const report = reportRegistry.find(item => item.id.toLowerCase() === query || item.title.toLowerCase() === query)
    || reportRegistry.find(item => query && (item.title.toLowerCase().includes(query) || query.includes(item.title.toLowerCase())))
    || (query.includes('revenue') ? reportRegistry.find(item => item.id === 'revenue_dashboard') : undefined);

  if (!report?.available) {
    return {
      ok: false, source: report?.path || 'report registry', sourceType: 'unavailable', liveData: false,
      generatedAt: report?.modified || 'timestamp unavailable', summary: 'The requested approved report snapshot is not available in the bundled report registry.',
      records: [], limitations: ['No live filesystem access from the browser', 'Only build-time approved report snapshots are readable'],
      safetyLevel: 'safe_read_only', requiresApprovalForExecution: true,
    };
  }

  const isRevenue = report.id === 'revenue_dashboard';
  const records = isRevenue ? [{
    confirmedRevenueUsd: field(report.content, 'confirmed_revenue_usd'),
    pendingTestRevenueUsd: field(report.content, 'pending_test_revenue_usd'),
    possibleOfferValueUsd: field(report.content, 'possible_offer_value_usd'),
    blockedRevenueUsd: field(report.content, 'blocked_revenue_usd'),
    exactNextMoneyAction: field(report.content, 'exact_next_money_action'),
    externalActionPerformed: field(report.content, 'external_action_performed'),
  }] : [{ status: field(report.content, 'status') || field(report.content, 'ok'), path: report.path }];
  const summary = isRevenue
    ? `Confirmed revenue is $${field(report.content, 'confirmed_revenue_usd') || '0'}. Pending test revenue is $${field(report.content, 'pending_test_revenue_usd') || '0'}, possible offer value is $${field(report.content, 'possible_offer_value_usd') || '0'}, and $${field(report.content, 'blocked_revenue_usd') || '0'} remains blocked. Next: ${field(report.content, 'exact_next_money_action') || 'review the report and approval queue'}`
    : `${report.title} is an approved bundled report snapshot. ${field(report.content, 'status') ? `Status: ${field(report.content, 'status')}.` : 'Review its recorded status and next action.'}`;

  return {
    ok: true, source: report.path, sourceType: 'report', liveData: false, generatedAt: generatedAt(report.content, report.modified),
    summary, records, limitations: ['Static build-time report snapshot', 'Not a live database or payment feed'],
    safetyLevel: 'safe_read_only', requiresApprovalForExecution: true,
  };
}

export function listReportContexts(): HermesReportContext {
  return {
    ok: true, source: 'src/data/reportRegistry.js', sourceType: 'report', liveData: false,
    generatedAt: new Date().toISOString(), summary: `${reportRegistry.filter(item => item.available).length} approved report snapshots are available in the bundled registry.`,
    records: reportRegistry.map(item => ({ id: item.id, title: item.title, category: item.category, available: item.available, path: item.path, generatedAt: generatedAt(item.content, item.modified) })),
    limitations: ['Registry is refreshed at build time', 'No browser filesystem enumeration'], safetyLevel: 'safe_read_only', requiresApprovalForExecution: false,
  };
}
