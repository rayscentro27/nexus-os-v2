import type { AffiliateOpportunity } from '../config/affiliateOpportunityTypes';

export function affiliatePriorityScore(item: AffiliateOpportunity): number {
  const relevance = item.offer_relevance || 0;
  const riskPenalty = item.compliance_risk === 'high' ? 25 : item.compliance_risk === 'medium' ? 10 : 0;
  const proofBonus = item.proof_source ? 10 : 0;
  return Math.max(0, Math.min(100, relevance + proofBonus - riskPenalty));
}
