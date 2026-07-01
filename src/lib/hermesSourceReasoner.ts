/**
 * Hermes Source Reasoner — compares page data, Supabase data, and reports.
 *
 * Produces plain-English explanations of live vs static state,
 * mismatches, and what actions are needed.
 */

export interface PageDataSource {
  sectionId: string;
  sourceType: 'live_supabase' | 'static_fallback' | 'report_snapshot' | 'localStorage_only' | 'unavailable';
  liveData: boolean;
  rowCount: number;
  staticCount: number;
  mismatch: string | null;
  tableNamesUsed: string[];
  records: unknown[];
}

export interface ReasoningResult {
  answer: string;
  sourceType: string;
  liveData: boolean;
  confidence: 'high' | 'medium' | 'low';
  suggestions: string[];
}

/** Reason about a page's data source vs Supabase. */
export function reasonAboutPage(pageData: PageDataSource | null, message: string): ReasoningResult {
  const lower = message.toLowerCase();

  if (!pageData) {
    return {
      answer: 'I don\'t have page context for the current section. Can you tell me which page you\'re looking at?',
      sourceType: 'unknown',
      liveData: false,
      confidence: 'low',
      suggestions: ['Navigate to a section and ask again.'],
    };
  }

  // Why does this page show data but Supabase says none?
  if (/why.*show.*data.*supabase.*none|why.*disagree|mismatch|split.?brain/i.test(lower)) {
    if (pageData.sourceType === 'static_fallback' && pageData.staticCount > 0 && pageData.rowCount === 0) {
      return {
        answer: `The ${pageData.sectionId} page is showing ${pageData.staticCount} static items from a bundled data file, but Supabase has 0 live rows in ${pageData.tableNamesUsed.join(', ') || 'the expected table'}. This is a split-brain: the UI reads a build-time snapshot, while Supabase has no live data yet. The fix is to seed/sync the static data into Supabase or wire this page to read live rows.`,
        sourceType: pageData.sourceType,
        liveData: false,
        confidence: 'high',
        suggestions: ['Seed the Supabase table with the static dataset', 'Wire this page to the live-first loader'],
      };
    }
    if (pageData.liveData) {
      return {
        answer: `The ${pageData.sectionId} page is live-connected to Supabase. It has ${pageData.rowCount} live rows in ${pageData.tableNamesUsed.join(', ')}. There is no mismatch.`,
        sourceType: pageData.sourceType,
        liveData: true,
        confidence: 'high',
        suggestions: [],
      };
    }
  }

  // Is this live or static?
  if (/is this live|is this static|what.*source|live or static/i.test(lower)) {
    const label = pageData.liveData ? 'live Supabase' : 'static snapshot';
    const detail = pageData.liveData
      ? `${pageData.rowCount} live rows from ${pageData.tableNamesUsed.join(', ')}`
      : `${pageData.staticCount} static items. Supabase has ${pageData.rowCount} rows.`;
    return {
      answer: `This page is ${label}. ${detail}${pageData.mismatch ? ' Mismatch: ' + pageData.mismatch : ''}`,
      sourceType: pageData.sourceType,
      liveData: pageData.liveData,
      confidence: 'high',
      suggestions: pageData.liveData ? [] : ['Wire this page to Supabase or seed the table'],
    };
  }

  // What data can you see on this page?
  if (/what.*data.*see|what.*visible|what.*show/i.test(lower)) {
    const count = pageData.liveData ? pageData.rowCount : pageData.staticCount;
    const label = pageData.liveData ? 'live Supabase rows' : 'static snapshot items';
    const first3 = pageData.records.slice(0, 3).map((r: any) => r.title || r.name || r.id || 'item').join(', ');
    return {
      answer: `I can see ${count} ${label} on the ${pageData.sectionId} page. ${first3 ? 'Examples: ' + first3 + '.' : ''} Source: ${pageData.sourceType}.`,
      sourceType: pageData.sourceType,
      liveData: pageData.liveData,
      confidence: 'medium',
      suggestions: [],
    };
  }

  // Compare page data to Supabase
  if (/compare.*supabase|compare.*page|page.*vs.*supabase|supabase.*vs.*page/i.test(lower)) {
    if (pageData.liveData) {
      return {
        answer: `The page and Supabase agree: ${pageData.rowCount} live rows from ${pageData.tableNamesUsed.join(', ')}. This section is fully live-connected.`,
        sourceType: pageData.sourceType,
        liveData: true,
        confidence: 'high',
        suggestions: [],
      };
    }
    return {
      answer: `The page shows ${pageData.staticCount} static items, but Supabase has ${pageData.rowCount} live rows in ${pageData.tableNamesUsed.join(', ') || 'the expected table'}. ${pageData.mismatch || 'This section is not yet live-connected.'}`,
      sourceType: pageData.sourceType,
      liveData: false,
      confidence: 'high',
      suggestions: ['Seed Supabase table', 'Wire page to live-first loader'],
    };
  }

  // Which sections are live vs static?
  if (/which sections.*live|which.*static|what.*connected|what.*not connected/i.test(lower)) {
    const status = pageData.liveData ? 'LIVE' : 'STATIC';
    return {
      answer: `The ${pageData.sectionId} section is ${status}. ${pageData.liveData ? `It has ${pageData.rowCount} live Supabase rows.` : `It shows ${pageData.staticCount} static items. Supabase has ${pageData.rowCount} rows.`}`,
      sourceType: pageData.sourceType,
      liveData: pageData.liveData,
      confidence: 'high',
      suggestions: [],
    };
  }

  // What do we need to sync?
  if (/what.*sync|need.*sync|how.*fix|next.*fix/i.test(lower)) {
    if (pageData.liveData) {
      return { answer: 'This section is already live-connected. No sync needed.', sourceType: pageData.sourceType, liveData: true, confidence: 'high', suggestions: [] };
    }
    return {
      answer: `To sync ${pageData.sectionId}: seed the ${pageData.tableNamesUsed.join(', ') || 'target'} table in Supabase with the ${pageData.staticCount} static items, then wire this page to use the live-first loader. A dry-run seed plan is available in reports/static_to_supabase_seed_plan.md.`,
      sourceType: pageData.sourceType,
      liveData: false,
      confidence: 'high',
      suggestions: ['Run the seed plan dry-run', 'Wire the page to live-first loader'],
    };
  }

  // Default: summarize current state
  const label = pageData.liveData ? 'live Supabase' : 'static snapshot';
  return {
    answer: `The ${pageData.sectionId} section is currently ${label}. ${pageData.liveData ? `${pageData.rowCount} live rows.` : `${pageData.staticCount} static items, ${pageData.rowCount} Supabase rows.`}${pageData.mismatch ? ' ' + pageData.mismatch : ''}`,
    sourceType: pageData.sourceType,
    liveData: pageData.liveData,
    confidence: 'medium',
    suggestions: pageData.liveData ? [] : ['Consider wiring to Supabase'],
  };
}

/** Store page data context for Hermes reasoning (call from sections). */
const pageContextStore: Record<string, PageDataSource> = {};

export function setPageContext(sectionId: string, data: PageDataSource): void {
  pageContextStore[sectionId] = data;
}

export function getPageContext(sectionId: string): PageDataSource | null {
  return pageContextStore[sectionId] || null;
}

export function getAllPageContexts(): Record<string, PageDataSource> {
  return { ...pageContextStore };
}
