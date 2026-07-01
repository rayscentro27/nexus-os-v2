import { getReportContext, listReportContexts } from './hermesReportContextAdapter';

export type HermesContextRequestType =
  | 'system_status' | 'reports_summary' | 'selected_report' | 'ray_review_summary'
  | 'offers_summary' | 'research_summary' | 'opportunities_summary' | 'trading_paper_summary'
  | 'scheduler_summary' | 'synthetic_client_status' | 'client_summary_safe'
  | 'approvals_summary' | 'blockers_summary' | 'activity_memory_summary';

export interface HermesBackendContextResult {
  ok: boolean;
  source: string;
  sourceType: 'static' | 'localStorage' | 'report' | 'supabase_anon' | 'backend' | 'unavailable';
  liveData: boolean;
  generatedAt: string;
  summary: string;
  records: Array<Record<string, unknown>>;
  limitations: string[];
  safetyLevel: 'safe_read_only';
  requiresApprovalForExecution: boolean;
}

const NOW = () => new Date().toISOString();
const staticResult = (source: string, summary: string, records: Array<Record<string, unknown>> = [], requiresApprovalForExecution = true): HermesBackendContextResult => ({
  ok: true, source, sourceType: 'static', liveData: false, generatedAt: NOW(), summary, records,
  limitations: ['Bundled local snapshot; not a live backend query', 'Verify time-sensitive decisions against the latest approved report'],
  safetyLevel: 'safe_read_only', requiresApprovalForExecution,
});

/** Safe synchronous foundation used by the current browser-only Hermes router. */
export function getHermesContext(query: string, request: { type: HermesContextRequestType; selectedReport?: string }): HermesBackendContextResult {
  switch (request.type) {
    case 'reports_summary': return listReportContexts();
    case 'selected_report': return getReportContext(request.selectedReport || query);
    case 'system_status': return getReportContext('operating_activation_master');
    case 'blockers_summary': return getReportContext('global_blocker_resolution_matrix');
    case 'ray_review_summary':
    case 'approvals_summary': return getReportContext('ray_review_queue');
    case 'offers_summary': return staticResult('src/data/monetizationData.js', 'The $97 Credit & Funding Readiness Review remains the shortest test-mode revenue proof. Complete only the approved synthetic/test checkout path; no real charge is authorized.', [{ confirmedRevenueUsd: 0, entryOfferUsd: 97 }]);
    case 'research_summary': return staticResult('src/data/hermesContextData.js', '50 research candidates are scored and 26 are marked actionable in the bundled Nexus snapshot. Review the candidate source and approval state before conversion.');
    case 'opportunities_summary': return staticResult('src/data/hermesContextData.js', 'The strongest currently documented opportunity is proving the $97 readiness review end-to-end, because its offer, test payment path, and synthetic onboarding package already exist.', [{ opportunity: '$97 Credit & Funding Readiness Review', status: 'approval-gated test proof' }]);
    case 'trading_paper_summary': return staticResult('Trading Demo page context', 'Visible trading data is bundled paper/demo context: Half Trend Forex Strategy is first, Vibe paper backtests are available, and live/funded trading remains blocked.');
    case 'scheduler_summary': return getReportContext('operating_activation_master');
    case 'synthetic_client_status': return staticResult('src/data/clientsData.js', 'Julius Erving is a synthetic test customer. The persistent Supabase insert is not confirmed and remains approval-gated; no real client record should be inferred.');
    case 'client_summary_safe': return staticResult('src/data/clientsData.js', 'Only synthetic/demo client summaries are available to Hermes in the current bundled context. No live client table is queried.');
    case 'activity_memory_summary': return {
      ok: false, source: 'browser localStorage activity journal', sourceType: 'localStorage', liveData: true, generatedAt: NOW(),
      summary: 'Activity memory is read locally by the Hermes memory adapter and is not available as durable cross-device backend memory.', records: [],
      limitations: ['Browser-local only', 'Not durable across devices'], safetyLevel: 'safe_read_only', requiresApprovalForExecution: false,
    };
  }
}

export function isBackendAvailable(): boolean { return false; }
export function isWebSearchAvailable(): boolean { return false; }
export function getBackendStatusMessage(): string {
  return 'I use local bundled Nexus context, selected approved report snapshots, page context, browser time, and localStorage activity memory. The read-only context adapter is available for those sources. I do not have live Supabase, live web search, or real AI model access from this chat layer.';
}
