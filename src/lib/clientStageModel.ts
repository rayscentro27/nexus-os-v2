/**
 * Client Stage Model — the five-stage business-model-aligned journey.
 *
 * The new operating model is:
 *   GoClear        = public-facing brand, lead generation, education, sales
 *   Nexus OS       = CRM, client portal, compliance, workflow, billing verification,
 *                    business foundation, funding readiness, funding pipeline
 *   CRJ / DisputeForMe = outsourced credit-dispute fulfillment
 *   Hermes         = client guidance and next-step support
 *   Alpha          = marketing / competitive research without client PII
 *
 * Nexus guides, tracks, analyzes, verifies, and coordinates.
 * The fulfillment provider performs outsourced dispute services.
 */

export type ClientStageId =
  | 'credit_review'
  | 'credit_improvement'
  | 'business_foundation'
  | 'funding_readiness'
  | 'funding_access';

export type ClientStageStatus =
  | 'not_started'
  | 'in_progress'
  | 'waiting_on_client'
  | 'waiting_on_nexus'
  | 'complete'
  | 'blocked';

export interface ClientStageView {
  id: ClientStageId;
  label: string;
  shortLabel: string;
  description: string;
  path: string;
  nextStep: string;
}

export const CLIENT_FIVE_STAGES: ClientStageView[] = [
  {
    id: 'credit_review',
    label: 'Credit Review',
    shortLabel: 'Credit Review',
    description: 'Starting credit snapshot, bureau status, utilization, derogatory accounts, discrepancies, and credit-risk summary.',
    path: '/client/credit-review',
    nextStep: 'Review your credit findings and starting snapshot.',
  },
  {
    id: 'credit_improvement',
    label: 'Credit Improvement',
    shortLabel: 'Credit Improvement',
    description: 'Outsourced credit fulfillment status: rounds, results, and verification progress.',
    path: '/client/credit-improvement',
    nextStep: 'Track your outsourced fulfillment round and verified results.',
  },
  {
    id: 'business_foundation',
    label: 'Business Foundation',
    shortLabel: 'Business Foundation',
    description: 'Entity, EIN, operating agreement, registered agent, address, domain, email, phone, licenses, banking, and trade profile.',
    path: '/client/business-foundation',
    nextStep: 'Complete the core business foundation milestones.',
  },
  {
    id: 'funding_readiness',
    label: 'Funding Readiness',
    shortLabel: 'Funding Readiness',
    description: 'Readiness score, strengths, blockers, missing requirements, and recommended next actions.',
    path: '/client/funding-readiness',
    nextStep: 'Resolve remaining blockers before recommending funding options.',
  },
  {
    id: 'funding_access',
    label: 'Funding Access',
    shortLabel: 'Funding Access',
    description: 'Readiness confirmation, recommended funding sequence, and application status.',
    path: '/client/funding-access',
    nextStep: 'Confirm readiness and review the recommended funding sequence.',
  },
];

export const clientStageById = (id: ClientStageId): ClientStageView =>
  CLIENT_FIVE_STAGES.find((stage) => stage.id === id) || CLIENT_FIVE_STAGES[0];

// ---- Fulfillment status (client-facing, simple states) ----

export type FulfillmentStatusId =
  | 'awaiting_intake'
  | 'ready_for_review'
  | 'provider_in_progress'
  | 'waiting_results'
  | 'new_report_needed'
  | 'results_received'
  | 'verification_in_progress'
  | 'round_complete';

export interface FulfillmentStatusDef {
  id: FulfillmentStatusId;
  label: string;
  tone: 'gray' | 'blue' | 'purple' | 'orange' | 'green';
  description: string;
}

export const FULFILLMENT_STATUS_DEFS: FulfillmentStatusDef[] = [
  { id: 'awaiting_intake', label: 'Awaiting Intake', tone: 'gray', description: 'Nexus needs your starting credit report before the fulfillment provider can begin.' },
  { id: 'ready_for_review', label: 'Ready for Review', tone: 'blue', description: 'Your report is being analyzed before handoff to the fulfillment provider.' },
  { id: 'provider_in_progress', label: 'In Progress', tone: 'purple', description: 'The outsourced fulfillment provider is working on the current round.' },
  { id: 'waiting_results', label: 'Waiting for Results', tone: 'blue', description: 'The provider filed the round. We are waiting for bureau results.' },
  { id: 'new_report_needed', label: 'New Report Needed', tone: 'orange', description: 'A current credit report is required to verify the latest changes.' },
  { id: 'results_received', label: 'Results Received', tone: 'green', description: 'Bureau responses arrived. Nexus is preparing verified outcome results.' },
  { id: 'verification_in_progress', label: 'Verification in Progress', tone: 'blue', description: 'Nexus is comparing before/after outcomes to identify verified changes.' },
  { id: 'round_complete', label: 'Round Complete', tone: 'green', description: 'The round finished. Verified outcomes are available and the next round can begin.' },
];

export const fulfillmentDefById = (id: FulfillmentStatusId): FulfillmentStatusDef =>
  FULFILLMENT_STATUS_DEFS.find((def) => def.id === id) || FULFILLMENT_STATUS_DEFS[0];

export interface FulfillmentInput {
  creditReportUploaded?: boolean;
  reviewInProgress?: boolean;
  analysisComplete?: boolean;
  fulfillmentRoundStarted?: boolean;
  providerFiled?: boolean;
  letterMailed?: boolean | null;
  responseReceived?: boolean;
  resultsReceived?: boolean;
  resultsVerified?: boolean;
  newReportRequired?: boolean;
  currentRound?: number;
  verifiedOutcomeCount?: number;
  verificationInProgress?: boolean;
}

export function computeFulfillmentStatus(input: FulfillmentInput): FulfillmentStatusId {
  if (!input.creditReportUploaded) return 'awaiting_intake';
  if (input.newReportRequired) return 'new_report_needed';
  if (input.resultsVerified) return 'round_complete';
  if (input.verificationInProgress) return 'verification_in_progress';
  if (input.resultsReceived) return 'results_received';
  if (input.providerFiled) return 'waiting_results';
  if (input.fulfillmentRoundStarted && !input.analysisComplete) return 'provider_in_progress';
  if (input.reviewInProgress || input.analysisComplete) return 'ready_for_review';
  return 'ready_for_review';
}

export interface ClientFulfillmentView {
  statusId: FulfillmentStatusId;
  statusLabel: string;
  tone: FulfillmentStatusDef['tone'];
  currentRound: number;
  description: string;
  nextClientAction: string;
  nextClientRoute: string;
  expectedMilestone: string;
  documentsNeeded: string[];
  verifiedOutcomes: number;
}

export function buildFulfillmentView(input: FulfillmentInput & { currentRound?: number }): ClientFulfillmentView {
  const statusId = computeFulfillmentStatus(input);
  const def = fulfillmentDefById(statusId);
  const round = input.currentRound || 0;
  const nextMap: Record<FulfillmentStatusId, { action: string; route: string }> = {
    awaiting_intake: { action: 'Upload your current credit report to begin processing.', route: '/client/credit-review' },
    ready_for_review: { action: 'No client action is required while Nexus analyzes the report.', route: '/client/credit-review' },
    provider_in_progress: { action: 'No client action is required while the fulfillment provider works.', route: '/client/credit-improvement' },
    waiting_results: { action: 'No client action is required while we wait for bureau results.', route: '/client/credit-improvement' },
    new_report_needed: { action: 'Upload a new credit report so Nexus can verify the latest changes.', route: '/client/credit-review' },
    results_received: { action: 'Outcome verification is being prepared for your review.', route: '/client/credit-improvement' },
    verification_in_progress: { action: 'Nexus is comparing before/after outcomes for verification.', route: '/client/credit-improvement' },
    round_complete: { action: 'Review the verified outcomes and decide whether to start the next round.', route: '/client/credit-improvement' },
  };
  const documentsMap: Record<FulfillmentStatusId, string[]> = {
    awaiting_intake: ['Current credit report'],
    ready_for_review: ['Current credit report'],
    provider_in_progress: [],
    waiting_results: [],
    new_report_needed: ['Updated credit report'],
    results_received: [],
    verification_in_progress: [],
    round_complete: [],
  };
  const milestone: Record<FulfillmentStatusId, string> = {
    awaiting_intake: 'Report analysis starts after upload',
    ready_for_review: 'Provider handoff after analysis',
    provider_in_progress: `Round ${round || 1} provider completion`,
    waiting_results: `Bureau response window (30–45 days typical)`,
    new_report_needed: 'New report verification',
    results_received: 'Verified outcome summary',
    verification_in_progress: 'Before/after comparison',
    round_complete: `Round ${round} verified`,
  };
  return {
    statusId,
    statusLabel: def.label,
    tone: def.tone,
    currentRound: round,
    description: def.description,
    nextClientAction: nextMap[statusId].action,
    nextClientRoute: nextMap[statusId].route,
    expectedMilestone: milestone[statusId],
    documentsNeeded: documentsMap[statusId],
    verifiedOutcomes: input.verifiedOutcomeCount || 0,
  };
}

// ---- Billing visibility ----

export interface BillingLineView {
  id: string;
  label: string;
  round: number;
  proposedAmount: number | null;
  outlet: string;
  billable: boolean;
  state: 'pending_verification' | 'pending_review' | 'approved' | 'paid' | 'reversed'; 
}

export function billingVisibility(input: {
  verifiedOutcomes?: number;
  verifiedDeletedIds?: string[];
  billedLines?: Array<{ id: string; label: string; round: number; outlet: string }>;
  paidIds?: string[];
  approvedIds?: string[];
}): BillingLineView[] {
  const verified = input.verifiedOutcomes || 0;
  const verifiedDeleted = input.verifiedDeletedIds || [];
  const lines: BillingLineView[] = [];
  for (const line of input.billedLines || []) {
    const isVerified = verifiedDeleted.includes(line.id) || verified > 0;
    lines.push({
      id: line.id,
      label: line.label,
      round: line.round || 1,
      outlet: line.outlet || 'Credit bureau',
      proposedAmount: isVerified ? 129 : null,
      billable: isVerified,
      state: isVerified
        ? input.paidIds?.includes(line.id) ? 'paid' : input.approvedIds?.includes(line.id) ? 'approved' : 'pending_review'
        : 'pending_verification',
    });
  }
  return lines;
}

export const OUTSOURCED_FULFILLMENT_EXPLANATION =
  'Nexus analyzes your credit report, coordinates the outsourced fulfillment provider (CRJ / DisputeForMe), and verifies before/after outcomes. The fulfillment provider performs dispute services. Nothing is mailed or submitted automatically from this portal.';