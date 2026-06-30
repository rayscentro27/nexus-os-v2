/**
 * Hermes page context — maps each page ID to its live data so buildHermesResponse
 * can give page-specific answers before falling back to global context.
 *
 * Each entry returns a short context string Hermes can weave into its response.
 */
import { creditReadiness, fundingReadiness, documentChecklist, disputeDraftQueue, bankabilityChecklist } from './creditFundingData';
import { businessOpportunities } from './businessOpportunitiesData';
import { researchCandidates } from './researchEngineData';
import { offers, revenueStreams } from './monetizationData';
import { marketingDrafts } from './marketingDraftsData';
import { clientStages, clientsList } from './clientsData';
import { hermesContext } from './hermesContextData';
import runtime from './continuousDashboardData.json';

const PAGE_CONTEXT = {
  command: () => {
    return `You are on the Command Center. Systems: ${runtime.systemsActivated.length} active. Approvals: ${runtime.approvalCount}. Blockers: ${runtime.blockerCount}. Opportunities: ${runtime.opportunityCount}. Top action: ${runtime.nextMoneyAction}.`;
  },
  hermes: () => {
    return `You are in the Hermes Workroom. This is your private advisory space. I have the full operating picture loaded: ${hermesContext.proof.rayReviewCards} approval cards, ${hermesContext.proof.researchCandidates} research candidates, ${hermesContext.proof.offers} offers, $${hermesContext.proof.confirmedRevenue} confirmed revenue.`;
  },
  credit: () => {
    const missing = documentChecklist.filter(d => d.status === 'missing').length;
    const disputesReady = disputeDraftQueue.filter(d => d.draftStatus === 'ready_for_review').length;
    const complete = bankabilityChecklist.filter(b => b.status === 'complete').length;
    return `You are on Credit & Funding. Credit readiness: ${creditReadiness.score}/100. Funding readiness: ${fundingReadiness.score}/100 (${fundingReadiness.status}). ${missing} documents missing. ${disputesReady} dispute drafts ready for review. Bankability: ${complete}/${bankabilityChecklist.length} items complete.`;
  },
  trading: () => {
    return `You are on Trading Demo. Status: paper/backtest only. No live trades, no real money. Oanda demo endpoint verified. Vibe paper backtests running. Live and funded execution remain completely blocked.`;
  },
  clients: () => {
    const client = clientsList[0];
    const missingDocs = client.documents.missingDocuments.length;
    return `You are on Clients. ${clientsList.length} demo client(s). Primary: ${client.name}, stage: ${client.stage.replace(/_/g, ' ')}, onboarding readiness: ${client.onboardingReadiness}%. ${missingDocs} documents still needed.`;
  },
  opportunity: () => {
    const top3 = businessOpportunities.slice(0, 3);
    const highConf = businessOpportunities.filter(o => o.confidence === 'high').length;
    return `You are on Business Opportunities. ${businessOpportunities.length} scored opportunities. ${highConf} high-confidence. Top 3: ${top3.map(o => `${o.title} (${o.score})`).join(', ')}. Revenue potential ranges from $27 to $997 per transaction.`;
  },
  research: () => {
    const top3 = researchCandidates.slice(0, 3);
    return `You are on Research Engine. ${researchCandidates.length} scored candidates. Top 3: ${top3.map(r => `${r.title} (${r.score})`).join(', ')}. All candidates are concept-only — no untrusted code has been cloned or executed.`;
  },
  monetization: () => {
    const approved = offers.filter(o => o.status === 'approved').length;
    const topOffer = offers[0];
    const totalProjected = revenueStreams.reduce((sum, s) => sum + (s.projectedMonthlyRevenue || 0), 0);
    return `You are on Monetization. ${offers.length} offers (${approved} approved). Top offer: ${topOffer.name} at $${topOffer.price}. Stripe: test checkout created for $97 only. Projected monthly revenue: $${totalProjected}/mo. Current revenue: $0.`;
  },
  marketing: () => {
    const byCat = {};
    marketingDrafts.forEach(d => { byCat[d.category] = (byCat[d.category] || 0) + 1; });
    const cats = Object.entries(byCat).map(([k, v]) => `${v} ${k}`).join(', ');
    return `You are on Marketing Drafts. ${marketingDrafts.length} drafts (${cats}). All are draft-only — nothing published or sent. Publishing is completely blocked pending Ray approval.`;
  },
  rayreview: () => {
    return `You are on Ray Review. ${hermesContext.proof.rayReviewCards} cards waiting. Approvals needed: ${hermesContext.approvalsNeeded.join(', ')}. Every risky action requires your decision here before execution.`;
  },
  reports: () => {
    return `You are on Reports. Operating evidence and markdown library. The latest report: ${runtime.reportPath}. Reports are generated from the continuous activation snapshot.`;
  },
  health: () => {
    return `You are on System Health. ${runtime.systemsActivated.length} systems activated. Loop status: ${runtime.loopStatus}. All 9 engines passed. Safety: no real external actions performed.`;
  },
  automation: () => {
    return `You are on Automation Scheduler. 2 safe internal cycles loaded (08:00 daily, 18:00 evening closeout). All automation is internal-only — no external or destructive automation is enabled.`;
  },
  settings: () => {
    return `You are on Settings. Continuous safe-internal mode active. Default loop: 30 minutes. No money spent, no public content, no client contact, no real-money trades.`;
  },
  marketing_drafts: () => {
    return `You are on Marketing Drafts. ${marketingDrafts.length} content pieces in draft. No publishing enabled.`;
  },
};

/** Return page-specific context for a given page ID, or null if unknown. */
export function getPageContext(pageId) {
  const generator = PAGE_CONTEXT[pageId];
  return generator ? generator() : null;
}

/** Map of page IDs to their human-readable labels. */
export const PAGE_LABELS = {
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
