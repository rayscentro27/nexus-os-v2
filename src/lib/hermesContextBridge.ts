/**
 * Hermes Page Context Bridge — provides structured page context to Hermes
 * so it can review what is actually visible on the current page.
 */

export interface VisibleItem {
  type: string;
  title: string;
  status: string;
  score?: number;
  category?: string;
  revenueRange?: string;
  confidence?: string;
  sourceId?: string;
  dataSource: 'local_static' | 'report' | 'supabase' | 'backend' | 'unknown';
}

export interface PageContext {
  route: string;
  pageId: string;
  pageTitle: string;
  activeTab: string | null;
  selectedItem: VisibleItem | null;
  visibleItems: VisibleItem[];
  availableActions: string[];
  gatedActions: string[];
  blockedActions: string[];
  pageDataSource: 'local_static' | 'report' | 'supabase' | 'backend' | 'unknown';
  staleStatus: 'static' | 'simulated' | 'live' | 'unknown';
}

const PAGE_TITLES: Record<string, string> = {
  command: 'Command Center',
  hermes: 'Hermes Workroom',
  credit: 'Credit & Funding',
  trading: 'Trading Demo',
  clients: 'Clients',
  opportunity: 'Business Opportunities',
  research: 'Research Engine',
  monetization: 'Monetization',
  marketing: 'Marketing Drafts',
  rayreview: 'Ray Review',
  reports: 'Reports',
  health: 'System Health',
  automation: 'Automation Scheduler',
  settings: 'Settings',
  subscription: 'Subscription Command Center',
  seo: 'SEO / Marketing',
  integrations: 'Integrations',
  ops: 'Ops & Improvements',
  jobs: 'Agent Jobs',
  source: 'Source Intake & Review',
  creative: 'Creative Studio',
  design: 'Design Library',
  goclear: 'GoClear / Apex',
  clientworkflow: 'Client Workflow',
  business: 'Business Profile Builder',
  funding: 'Funding Readiness',
  partners: 'Partner Offers',
  cli: 'CLI / Tool Registry',
  proof: 'Events / Proof Ledger',
  feedback: 'Hermes Feedback',
};

/** Build a minimal page context from a pageId (for use when full context isn't available). */
export function buildPageContext(pageId: string, route?: string): PageContext {
  return {
    route: route || `/#${pageId}`,
    pageId,
    pageTitle: PAGE_TITLES[pageId] || pageId,
    activeTab: null,
    selectedItem: null,
    visibleItems: [],
    availableActions: [],
    gatedActions: ['live trade', 'publish', 'send email', 'submit dispute', 'charge payment'],
    blockedActions: ['external sends', 'real charges', 'live trading'],
    pageDataSource: 'local_static',
    staleStatus: 'static',
  };
}

/** Build full page context with visible items from data imports. */
export function buildFullPageContext(pageId: string, items: VisibleItem[], actions?: string[]): PageContext {
  const ctx = buildPageContext(pageId);
  ctx.visibleItems = items;
  ctx.availableActions = actions || [];
  return ctx;
}
