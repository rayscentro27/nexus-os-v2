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
  risks: Array<{
    id: string;
    title: string;
    impact: string;
    mitigation: string;
    evidenceState: string;
  }>;
  blockers: Array<{
    id: string;
    title: string;
    impact: string;
    owner?: string;
  }>;
  opportunities: Array<{
    id: string;
    title: string;
    state: string;
    nextStep: string;
  }>;
  systemHealth: Array<{
    capabilityId: string;
    status: string;
    summary: string;
  }>;
  unknowns: string[];
}

const slug = (value: string): string => value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
const sixHoursFromNow = () => new Date(Date.now() + 1000 * 60 * 60 * 6).toISOString();

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

function mitigationForBlocker(title: string): string {
  if (/client.*live-data|live-data.*client/i.test(title)) return 'Reproduce with a synthetic account, then trace whether the flag comes from Supabase, the client adapter, or the UI.';
  if (/resend/i.test(title)) return 'Verify the sending domain and API key in test mode before approving customer-facing communication.';
  if (/fake customer|synthetic customer/i.test(title)) return 'Insert or safely reprovision the synthetic record before relying on end-to-end customer certification.';
  if (/youtube|notebooklm/i.test(title)) return 'Keep the item report-backed until the missing research artifact is recovered or replaced.';
  return 'Assign the owner, confirm the evidence source, and decide whether it needs Ray Review or monitoring.';
}

function revenueNextStep(title: string): string {
  if (/97|readiness/i.test(title)) return 'Use the $97 readiness review as the bounded entry offer, with Stripe kept in test mode until production payment activation is separately approved.';
  if (/lead|reactivation/i.test(title)) return 'Pick the safest warm-list segment, prepare the draft for review, and do not send until communication settings are fixed.';
  if (/offer|nine/i.test(title)) return 'Select the clearest offer candidate and turn it into a Ray Review decision, not a live checkout.';
  return 'Convert the recommendation into a reviewed action before activating any external system.';
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
  const risks = blockers.map((item) => ({
    id: `risk_${slug(item.title)}`,
    title: item.title,
    impact: item.impact,
    mitigation: mitigationForBlocker(item.title),
    evidenceState: 'REPORT_BACKED',
  }));
  const opportunities = revenueActions.map((item) => ({
    id: `opportunity_${slug(item.title)}`,
    title: item.title,
    state: item.state,
    nextStep: revenueNextStep(item.title),
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
    risks,
    blockers,
    opportunities,
    systemHealth: [
      { capabilityId: 'hermes_workroom_runtime', status: 'HEALTHY', summary: 'Live Workroom response rendering and context use are production-equivalent certified.' },
      { capabilityId: 'stripe_test_checkout', status: 'TEST_ONLY', summary: 'Revenue path remains test mode.' },
      { capabilityId: 'live_trading', status: 'BLOCKED_BY_POLICY', summary: 'Live trading remains prohibited.' },
    ],
    unknowns: ['Live production route state must be rechecked after Workroom repair.'],
  };
}

function structuredRecommendation(item: HermesAdvisoryRecommendation): NonNullable<HermesAdvisoryContext['recommendation']> {
  return {
    id: item.id,
    title: item.label,
    summary: item.rationale,
    rationale: item.rationale,
    feasibility: item.feasibility || { status: 'UNKNOWN', reasons: ['Current evidence does not include a complete feasibility record.'] },
    risks: item.risks || [],
    blockers: item.blockers || [],
    dependencies: item.dependencies || [],
    nextStep: item.nextStep || 'Confirm the evidence source before turning this into broader work.',
    evidenceIds: item.evidenceIds || [],
  };
}

function advisoryFromRecommendations(input: {
  context: HermesOperatingContext;
  topic: string;
  topicId: string;
  topicLabel: string;
  topicType: NonNullable<HermesAdvisoryContext['topicType']>;
  sourceIntent: string;
  sourceResponseStrategy: string;
  summary: string;
  recommendations: HermesAdvisoryRecommendation[];
  evidenceIds: string[];
}): HermesAdvisoryContext {
  const preferred = input.recommendations[0];
  return {
    advisoryId: `${input.topicId}-${Date.now()}`,
    topic: input.topic,
    topicId: input.topicId,
    topicLabel: input.topicLabel,
    topicType: input.topicType,
    sourceIntent: input.sourceIntent,
    sourceResponseStrategy: input.sourceResponseStrategy,
    summary: input.summary,
    recommendations: input.recommendations,
    preferredRecommendationId: preferred?.id,
    recommendation: preferred ? structuredRecommendation(preferred) : undefined,
    alternatives: input.recommendations.slice(1).map((item) => ({
      id: item.id,
      title: item.label,
      summary: item.rationale,
      rationale: item.rationale,
      risks: item.risks,
      blockers: item.blockers,
      dependencies: item.dependencies,
      nextStep: item.nextStep,
    })),
    evidenceIds: input.evidenceIds,
    createdAt: input.context.generatedAt,
    updatedAt: input.context.generatedAt,
    expiresAt: sixHoursFromNow(),
    status: 'ACTIVE',
  };
}

function buildPriorityRecommendations(context: HermesOperatingContext): HermesAdvisoryRecommendation[] {
  return context.priorities.slice(0, 4).map((item) => ({
    id: item.id,
    label: item.title,
    rationale: item.summary,
    score: item.priority === 'P0' ? 100 : item.priority === 'P1' ? 94 : item.priority === 'P2' ? 86 : item.priority === 'P3' ? 72 : 60,
    risks: [
      item.summary,
      item.priority === 'P0' || item.priority === 'P1' ? 'customer or company protection risk if left unresolved' : 'lower-priority dependency can wait behind P0/P1 work',
    ],
    blockers: context.blockers.filter((blocker) => blocker.id === item.id || item.title.toLowerCase().includes(blocker.title.toLowerCase())).map((blocker) => blocker.impact),
    dependencies: context.approvals.slice(0, 2).map((approval) => approval.title),
    feasibility: {
      status: item.priority === 'P0' || item.priority === 'P1' ? 'HIGH' : item.priority === 'P2' ? 'MEDIUM' : 'UNKNOWN',
      reasons: [
        item.priority === 'P0' || item.priority === 'P1' ? 'It can be verified with bounded synthetic/admin evidence before any customer-facing change.' : 'It depends on the higher-protection workflow staying stable first.',
        'No live Stripe, live trading, or external writer activation is required.',
      ],
    },
    nextStep: item.priority === 'P2'
      ? 'Prepare the revenue action for review while keeping Stripe in test mode.'
      : 'Reproduce the item with synthetic/admin evidence and confirm the source of truth before expanding it.',
    evidenceIds: [item.id, 'hermes_operating_context_panel'],
  }));
}

export function buildOperatingContextAdvisory(context: HermesOperatingContext = buildHermesOperatingContext()): HermesAdvisoryContext {
  const recommendations = buildPriorityRecommendations(context);
  return advisoryFromRecommendations({
    context,
    topic: 'today_operating_priorities',
    topicId: 'today_operating_priorities',
    topicLabel: recommendations[0]?.label || 'Today operating priorities',
    topicType: 'EXECUTIVE_PRIORITY',
    sourceIntent: 'executive_priority',
    sourceResponseStrategy: 'executive_priority_response',
    summary: 'Prioritize today using the live Workroom operating context and Nexus P0-P4 order.',
    recommendations,
    evidenceIds: ['hermes_operating_context_panel', ...context.priorities.slice(0, 3).map((item) => item.id)],
  });
}

export function buildRiskAdvisory(context: HermesOperatingContext = buildHermesOperatingContext()): HermesAdvisoryContext {
  const riskRank = (risk: HermesOperatingContext['risks'][number]) => /client.*live-data|live-data.*client/i.test(risk.title) ? -1 : /client|customer/i.test(risk.title) ? 0 : /stripe|payment|revenue/i.test(risk.title) ? 1 : /resend|communication/i.test(risk.title) ? 2 : 3;
  const recommendations = [...context.risks].sort((a, b) => riskRank(a) - riskRank(b)).slice(0, 4).map((risk, index): HermesAdvisoryRecommendation => ({
    id: risk.id,
    label: risk.title,
    rationale: risk.impact,
    score: index === 0 ? 94 : 80 - index,
    risks: [risk.impact],
    blockers: context.blockers.filter((blocker) => blocker.title === risk.title || risk.title.toLowerCase().includes(blocker.title.toLowerCase())).map((blocker) => blocker.impact),
    dependencies: context.approvals.slice(0, 2).map((approval) => approval.title),
    feasibility: {
      status: 'HIGH',
      reasons: ['The mitigation can be validated with bounded synthetic/admin evidence.', 'No live payment, live trading, or external writer activation is required.'],
    },
    nextStep: risk.mitigation,
    evidenceIds: [risk.id, 'hermes_operating_context_panel'],
  }));
  return advisoryFromRecommendations({
    context,
    topic: 'executive_risk_mitigation',
    topicId: 'executive_risk_mitigation',
    topicLabel: recommendations[0]?.label || 'Executive risk mitigation',
    topicType: 'EXECUTIVE_RISK',
    sourceIntent: 'executive_risk',
    sourceResponseStrategy: 'executive_risk_response',
    summary: 'Identify the largest current operating exposure and its immediate mitigation.',
    recommendations,
    evidenceIds: ['hermes_operating_context_panel', ...context.risks.slice(0, 3).map((item) => item.id)],
  });
}

export function buildRevenueAdvisory(context: HermesOperatingContext = buildHermesOperatingContext()): HermesAdvisoryContext {
  const recommendations = context.revenueActions.slice(0, 4).map((action, index): HermesAdvisoryRecommendation => {
    const opportunity = context.opportunities.find((item) => item.title === action.title);
    const isReadiness = /97|readiness/i.test(action.title);
    return {
      id: action.id,
      label: action.title,
      rationale: isReadiness
        ? 'It is a bounded entry offer, an immediate monetization path, and it aligns with the existing readiness-review workflow.'
        : `${action.state}. ${opportunity?.nextStep || revenueNextStep(action.title)}`,
      score: isReadiness ? 92 : 82 - index,
      risks: [
        'Live payment activation is still deferred.',
        'Customer communication must remain approval-gated.',
        'Offer copy and fulfillment readiness must be checked before outreach.',
      ],
      blockers: [
        'Stripe remains test-only.',
        'Required review and configuration checks are not complete.',
        'Lead audience readiness must be confirmed before outreach.',
      ],
      dependencies: ['approved offer copy', 'test checkout verification', 'delivery workflow', 'permitted outreach path'],
      feasibility: {
        status: isReadiness ? 'HIGH' : 'MEDIUM',
        reasons: [
          isReadiness ? 'The first step can be prepared as an offer and test-mode journey without live payment activation.' : 'It can be evaluated as a report-backed revenue action before execution.',
          'The current boundary keeps Stripe test-only and customer communication under review.',
        ],
      },
      nextStep: opportunity?.nextStep || revenueNextStep(action.title),
      evidenceIds: [action.id, 'hermes_operating_context_panel'],
    };
  });
  return advisoryFromRecommendations({
    context,
    topic: 'today_revenue_actions',
    topicId: 'today_revenue_actions',
    topicLabel: recommendations[0]?.label || 'Today revenue actions',
    topicType: 'REVENUE_ACTION',
    sourceIntent: 'revenue_action',
    sourceResponseStrategy: 'revenue_action_response',
    summary: 'Choose the fastest bounded revenue action from the Workroom Money Actions context.',
    recommendations,
    evidenceIds: ['hermes_operating_context_panel', ...context.revenueActions.slice(0, 3).map((item) => item.id)],
  });
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

export function answerBiggestOperatingRisk(context: HermesOperatingContext = buildHermesOperatingContext()): {
  text: string;
  advisoryContext: HermesAdvisoryContext;
} {
  const advisoryContext = buildRiskAdvisory(context);
  const risk = context.risks.find((item) => /client|customer|live-data/i.test(item.title)) || context.risks[0];
  const affected = /client|customer/i.test(risk?.title || '') ? 'customer-facing workflow and evidence visibility' : 'Nexus operations';
  const text = risk
    ? `The biggest risk is **${risk.title}**.\n\nIt matters because ${risk.impact} The affected area is ${affected}, so it is a protection issue before it is a growth issue.\n\nImmediate mitigation: ${risk.mitigation}`
    : 'The biggest risk is unknown because the operating context did not provide a current risk record. Rebuild the context first, then choose the highest P0/P1 exposure.';
  return { text, advisoryContext };
}

export function answerRevenueAction(context: HermesOperatingContext = buildHermesOperatingContext()): {
  text: string;
  advisoryContext: HermesAdvisoryContext;
} {
  const advisoryContext = buildRevenueAdvisory(context);
  const action = context.revenueActions.find((item) => /97|readiness/i.test(item.title)) || context.revenueActions[0];
  const opportunity = action ? context.opportunities.find((item) => item.title === action.title) : undefined;
  const alternatives = advisoryContext.recommendations.slice(1, 3);
  const text = action
    ? `The fastest revenue action today is **${action.title}**.\n\nTarget it at the safest readiness-review audience already represented in the operating context. The offer is ${action.estimatedValue || 'a report-backed monetization action'}, and the practical move today is: ${opportunity?.nextStep || revenueNextStep(action.title)}\n\n${alternatives.length ? `Other viable money actions:\n${alternatives.map((item, index) => `${index + 2}. **${item.label}** — ${item.rationale}`).join('\n')}\n\n` : ''}Boundary: Stripe stays test-only. Do not open live checkout or send customer communication until the required review and configuration checks pass.`
    : 'The operating context does not show a current money action. Do not invent a revenue push; rebuild the revenue context or create a reviewed monetization proposal first.';
  return { text, advisoryContext };
}

export function answerFollowUpRationale(item: HermesAdvisoryRecommendation): string {
  return `I chose **${item.label}** because ${item.rationale}\n\nThe main dependency is ${item.dependencies?.[0] || 'the current evidence source being verified'}.`;
}

export function answerFollowUpFeasibility(item: HermesAdvisoryRecommendation): string {
  const status = item.feasibility?.status || 'UNKNOWN';
  const reasons = item.feasibility?.reasons?.length ? item.feasibility.reasons.join(' ') : 'The scope is realistic only if we keep the first pass bounded and evidence-backed.';
  return `${status === 'HIGH' ? 'Yes' : status === 'MEDIUM' ? 'Yes, with constraints' : 'It needs one more evidence check first'}. **${item.label}** is realistic at a bounded scope.\n\n${reasons}\n\nRealistic first step: ${item.nextStep || 'verify the evidence source before turning it into broader work.'}`;
}

export function answerFollowUpBlockers(item: HermesAdvisoryRecommendation): string {
  const blockers = item.blockers?.length ? item.blockers : item.risks || ['the evidence source is not verified yet'];
  return `The concrete blockers for **${item.label}** are:\n\n1. ${blockers.slice(0, 3).join('\n2. ')}\n\nMitigation: ${item.nextStep || 'verify the source, then decide whether this needs Ray Review or a governed task.'}`;
}

export function answerFollowUpDeepDive(item: HermesAdvisoryRecommendation): string {
  return `Going deeper on **${item.label}**:\n\nWhy it matters: ${item.rationale}\n\nDependencies: ${item.dependencies?.slice(0, 3).join(', ') || 'current operating evidence and owner confirmation'}.\n\nRisks: ${item.risks?.slice(0, 3).join(', ') || 'unclear evidence and dependency order'}.\n\nNext step: ${item.nextStep || 'confirm the evidence source, then decide whether to monitor, request review, or create governed work.'}`;
}
