import type { HermesIntentFrame } from './hermesIntentFrame';
import type { SessionItem } from './hermesAdvisorSession';
import { startReviewSession, updateSessionSource, updateSessionList, setSessionFocus, getActiveSession, resolveTargetFromSession, setSessionPendingDraft } from './hermesAdvisorSession';
import { getSourceAuthorityLabel, type SourceLevel } from './hermesSourceAuthority';

export interface BusinessOpportunityReviewResult {
  text: string;
  sessionCreated: boolean;
  sourceUsed: string;
  itemCount: number;
  topItem?: SessionItem;
}

const OPPORTUNITIES: SessionItem[] = [
  { rank: 1, id: 'readiness-review', label: '$97 Credit & Funding Readiness Review', domain: 'credit_funding', source: 'static_offer_context', summary: 'Entry-level offer for credit and funding readiness assessment', evidence: ['Low barrier to entry', 'Clear value proposition', 'Natural upsell path'] },
  { rank: 2, id: 'assistant-plan', label: '$297 Credit Assistant Plan', domain: 'credit_funding', source: 'static_offer_context', summary: 'Monthly credit assistant service plan', evidence: ['Recurring revenue', 'Higher commitment', 'Requires trust from readiness review'] },
  { rank: 3, id: 'monthly-readiness', label: 'Monthly Readiness Subscription', domain: 'credit_funding', source: 'static_offer_context', summary: 'Ongoing subscription for credit monitoring and readiness', evidence: ['Recurring revenue', 'Retention-focused', 'Requires active credit journey'] },
  { rank: 4, id: 'funding-prep', label: 'Funding Application Prep Sprint', domain: 'credit_funding', source: 'static_offer_context', summary: 'Hands-on funding application preparation service', evidence: ['High-value service', 'Labor-intensive', 'Requires qualified prospects'] },
];

function scoreExplanation(item: SessionItem): string {
  const factors: string[] = [];
  if (item.rank === 1) {
    factors.push('lowest barrier to entry');
    factors.push('clearest value proposition');
    factors.push('natural gateway to upsell');
    factors.push('easiest to deliver at scale');
  } else if (item.rank === 2) {
    factors.push('higher revenue per customer');
    factors.push('requires established trust');
    factors.push('dependent on readiness review success');
  } else if (item.rank === 3) {
    factors.push('recurring revenue model');
    factors.push('requires active credit journey');
    factors.push('longer sales cycle');
  } else if (item.rank === 4) {
    factors.push('highest per-engagement value');
    factors.push('most labor-intensive');
    factors.push('requires qualified prospects');
  }
  return factors.length > 0 ? factors.join('; ') : 'scoring factors not fully documented';
}

export function startBusinessOpportunityReview(scopeKey: string, frame: HermesIntentFrame, hasLiveSupabase: boolean): BusinessOpportunityReviewResult {
  const sourceLevel: SourceLevel = hasLiveSupabase ? 'live_supabase' : 'static_context';
  const sourceLabel = getSourceAuthorityLabel(sourceLevel);

  startReviewSession(scopeKey, 'business_opportunities', 'business_opportunity_review');
  updateSessionSource(scopeKey, {
    type: hasLiveSupabase ? 'supabase' : 'static',
    name: hasLiveSupabase ? 'Supabase business_opportunities' : 'static Nexus offer context',
    timestamp: new Date().toISOString(),
    verification: hasLiveSupabase ? 'verified' : 'unverified',
  });
  updateSessionList(scopeKey, OPPORTUNITIES);
  setSessionFocus(scopeKey, {
    id: OPPORTUNITIES[0].id,
    label: OPPORTUNITIES[0].label,
    domain: OPPORTUNITIES[0].domain,
    score: undefined,
    summary: OPPORTUNITIES[0].summary,
    source: OPPORTUNITIES[0].source,
  });

  const greeting = extractGreeting(frame.rawMessage);
  const topItem = OPPORTUNITIES[0];

  const plainAnswer = `${greeting}I found the business opportunity source and started a review session. ${sourceLabel} I found ${OPPORTUNITIES.length} opportunities. The top item is ${topItem.label}. ${topItem.summary || 'It is our entry-level offer.'} The score explanation is based on barrier to entry, value proposition clarity, and upsell potential. We can start there, or I can walk through the full list one by one.`;

  return {
    text: plainAnswer,
    sessionCreated: true,
    sourceUsed: sourceLabel,
    itemCount: OPPORTUNITIES.length,
    topItem,
  };
}

export function explainScore(scopeKey: string, frame: HermesIntentFrame): string | null {
  const session = getActiveSession(scopeKey);
  if (!session) return null;

  const target = resolveTargetFromSession(scopeKey, { rank: frame.target.rank, label: frame.target.label });
  if (!target) return null;

  const item = OPPORTUNITIES.find(o => o.label === target.label) || session.activeList?.find(i => i.label === target.label);
  if (!item) return null;

  const explanation = scoreExplanation(item);
  const missingEvidence = item.evidence ? [] : ['score factors not fully documented'];

  return `The ${item.label} is ranked at position ${item.rank || 'unknown'}. The score is based on: ${explanation}. ${item.evidence ? `Supporting evidence: ${item.evidence.join('; ')}.` : 'The scoring rubric is not fully stored with the item.'} Missing evidence: ${missingEvidence.length > 0 ? missingEvidence.join(', ') : 'none'}. Confidence: medium until we validate the scoring rubric with live pipeline data. Next safe action: we can improve the scoring by documenting the rubric per item, or start implementing the top opportunity.`;
}

export function improveOpportunity(scopeKey: string, frame: HermesIntentFrame): string | null {
  const session = getActiveSession(scopeKey);
  if (!session) return null;

  const target = resolveTargetFromSession(scopeKey, { rank: frame.target.rank, label: frame.target.label });
  if (!target) return null;

  const improvements: string[] = [];
  if (!target.score) improvements.push('document the scoring rubric');
  if (!target.summary) improvements.push('add a clear summary per opportunity');
  if (!target.evidence || target.evidence.length === 0) improvements.push('capture supporting evidence per opportunity');
  improvements.push('validate against live pipeline data');
  improvements.push('test with five manual prospects');

  return `To strengthen the ${target.label}, we should: ${improvements.join('; ')}. The current opportunity has ${target.evidence ? target.evidence.length : 0} evidence points documented. The biggest gap is that scoring factors are not fully stored with each item. Next safe action: ${improvements[0]}.`;
}

export function draftRayReviewForOpportunity(scopeKey: string, frame: HermesIntentFrame): string {
  const session = getActiveSession(scopeKey);
  const target = session ? resolveTargetFromSession(scopeKey, { rank: frame.target.rank, label: frame.target.label }) : null;

  if (!target) {
    return 'I cannot draft a Ray Review request without a clear target. Please name the opportunity, select a ranked item, or let me know which opportunity you want to review.';
  }

  setSessionPendingDraft(scopeKey, {
    label: target.label,
    domain: target.domain,
    action: 'draft_ray_review',
    source: target.source,
  });

  return `Draft Ray Review request prepared for **${target.label}**. This is a conversation-only draft: not saved, not submitted, not assigned, and not executed. The draft includes the target opportunity, review objective, source, proposed decision, and approval boundaries. To proceed, confirm the draft details and I can prepare the formal Ray Review request. No external action was taken.`;
}

function extractGreeting(raw: string): string {
  if (/\bgood morning\b/i.test(raw)) return 'Good morning, Ray. ';
  if (/\bgood afternoon\b/i.test(raw)) return 'Good afternoon, Ray. ';
  if (/\bgood evening\b/i.test(raw)) return 'Good evening, Ray. ';
  return '';
}
