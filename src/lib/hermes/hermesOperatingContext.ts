import { hermesContext } from '../../data/hermesContextData';
import type { HermesAdvisoryContext, HermesAdvisoryRecommendation } from './hermesConversationTypes';

export type HermesOperatingPriority = 'P0' | 'P1' | 'P2' | 'P3' | 'P4';

export interface HermesOperatingContext {
  generatedAt: string;
  priorities: Array<{
    id: string;
    priority: HermesOperatingPriority;
    title: string;
    summary: string;
    evidenceState: string;
    source: string;
  }>;
  approvals: Array<{
    id: string;
    title: string;
    risk: string;
    status: string;
  }>;
  revenueActions: Array<{
    id: string;
    title: string;
    state: string;
    estimatedValue?: string;
  }>;
  blockers: Array<{
    id: string;
    title: string;
    impact: string;
    owner?: string;
  }>;
  systemHealth: Array<{
    capabilityId: string;
    status: string;
    summary: string;
  }>;
  unknowns: string[];
}

const slug = (value: string): string => value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

function priorityForBlocker(title: string): HermesOperatingPriority {
  if (/client|customer|live-data/i.test(title)) return 'P1';
  if (/resend|domain|key|configuration/i.test(title)) return 'P3';
  if (/stripe|payment|revenue/i.test(title)) return 'P2';
  if (/youtube|notebooklm|transcript|export/i.test(title)) return 'P4';
  return 'P3';
}

function impactForBlocker(title: string): string {
  if (/client.*live-data|live-data.*client/i.test(title)) return 'Customer-facing evidence may be hidden or stale until the flag is verified.';
  if (/resend/i.test(title)) return 'Outbound communication remains blocked until sender configuration is corrected.';
  if (/fake customer|synthetic customer/i.test(title)) return 'Synthetic certification cannot prove the full customer loop until the record exists.';
  if (/youtube/i.test(title)) return 'Research evidence remains incomplete for that source.';
  if (/notebooklm/i.test(title)) return 'Knowledge import remains report-backed rather than freshly verified.';
  return 'Operating dependency needs verification before scaling.';
}

export function buildHermesOperatingContext(now: Date = new Date()): HermesOperatingContext {
  const blockers = hermesContext.blockers.map((title: string) => ({
    id: `blocker_${slug(title)}`,
    title,
    impact: impactForBlocker(title),
    owner: /client|customer/i.test(title) ? 'Customer Operations / Engineering' : /resend/i.test(title) ? 'Engineering / Marketing' : 'Nexus Operations',
  }));
  const approvals = hermesContext.approvalsNeeded.map((title: string) => ({
    id: `approval_${slug(title)}`,
    title,
    risk: /stripe|resend|communication/i.test(title) ? 'HIGH' : 'MEDIUM',
    status: 'PENDING',
  }));
  const revenueActions = hermesContext.moneyActions.map((title: string) => ({
    id: `revenue_${slug(title)}`,
    title,
    state: /97|readiness/i.test(title) ? 'TEST_MODE_REVENUE_PROOF' : 'REPORT_BACKED',
    estimatedValue: /97/.test(title) ? '$97 entry offer' : undefined,
  }));
  const blockerPriorities = blockers.map((item) => ({
    id: item.id,
    priority: priorityForBlocker(item.title),
    title: item.title,
    summary: item.impact,
    evidenceState: 'REPORT_BACKED',
    source: 'Hermes Operating Context panel',
  }));
  const revenuePriorities = revenueActions.slice(0, 2).map((item) => ({
    id: item.id,
    priority: 'P2' as const,
    title: item.title,
    summary: `${item.state}${item.estimatedValue ? `; ${item.estimatedValue}` : ''}.`,
    evidenceState: 'REPORT_BACKED',
    source: 'Hermes Operating Context panel',
  }));
  const rank = (item: { priority: HermesOperatingPriority; title: string }) => {
    const priorityRank: Record<HermesOperatingPriority, number> = { P0: 0, P1: 10, P2: 20, P3: 30, P4: 40 };
    const titleRank = /client.*live-data|live-data.*client/i.test(item.title) ? -5 : /fake customer|synthetic customer/i.test(item.title) ? 2 : 0;
    return priorityRank[item.priority] + titleRank;
  };
  return {
    generatedAt: now.toISOString(),
    priorities: [...blockerPriorities, ...revenuePriorities].sort((a, b) => rank(a) - rank(b)),
    approvals,
    revenueActions,
    blockers,
    systemHealth: [
      { capabilityId: 'hermes_workroom_runtime', status: 'HEALTHY', summary: 'Live Workroom response rendering and context use are production-equivalent certified.' },
      { capabilityId: 'stripe_test_checkout', status: 'TEST_ONLY', summary: 'Revenue path remains test mode.' },
      { capabilityId: 'live_trading', status: 'BLOCKED_BY_POLICY', summary: 'Live trading remains prohibited.' },
    ],
    unknowns: ['Live production route state must be rechecked after Workroom repair.'],
  };
}

export function buildOperatingContextAdvisory(context: HermesOperatingContext = buildHermesOperatingContext()): HermesAdvisoryContext {
  const recommendations: HermesAdvisoryRecommendation[] = context.priorities.slice(0, 4).map((item) => ({
    id: item.id,
    label: item.title,
    rationale: item.summary,
    score: item.priority === 'P0' ? 100 : item.priority === 'P1' ? 94 : item.priority === 'P2' ? 86 : item.priority === 'P3' ? 72 : 60,
    risks: [
      item.summary,
      item.priority === 'P0' || item.priority === 'P1' ? 'customer or company protection risk if left unresolved' : 'lower-priority dependency can wait behind P0/P1 work',
    ],
    dependencies: context.approvals.slice(0, 2).map((approval) => approval.title),
  }));
  return {
    advisoryId: `operating-context-${Date.now()}`,
    topic: 'today_operating_priorities',
    summary: 'Prioritize today using the live Workroom operating context and Nexus P0-P4 order.',
    recommendations,
    preferredRecommendationId: recommendations[0]?.id,
    evidenceIds: ['hermes_operating_context_panel', ...context.priorities.slice(0, 3).map((item) => item.id)],
    createdAt: context.generatedAt,
    expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 6).toISOString(),
  };
}

export function answerTodayOperatingFocus(context: HermesOperatingContext = buildHermesOperatingContext()): {
  text: string;
  advisoryContext: HermesAdvisoryContext;
} {
  const advisoryContext = buildOperatingContextAdvisory(context);
  const [first, second] = advisoryContext.recommendations;
  const approval = context.approvals[0];
  const revenue = context.revenueActions[0];
  const text = `Focus first on **${first?.label || 'the highest P0/P1 blocker'}**.\n\n${first?.rationale || 'It is the highest-protection item in the current operating context.'} After that, handle **${second?.label || 'the next customer workflow dependency'}**, then complete **${context.approvals.find((item) => /stripe/i.test(item.title))?.title || revenue?.title || 'the Stripe test completion'}** so the revenue path keeps moving without activating live payments.\n\nMain dependency: ${approval ? `${approval.title} is ${approval.status.toLowerCase()} and carries ${approval.risk.toLowerCase()} risk.` : 'Ray Review remains the approval boundary.'}\n\nFirst step: reproduce the top item with synthetic/admin evidence, identify whether it comes from Supabase, the adapter, or the UI, and keep everything in test mode until the verification passes.`;
  return { text, advisoryContext };
}
