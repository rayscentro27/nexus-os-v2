import type { ContentOpportunity } from '../config/contentOpportunityTypes';

export function contentOpportunityLabel(opportunity: ContentOpportunity): string {
  return `${opportunity.recommended_format}: ${opportunity.target_keyword_topic}`;
}

export function contentOpportunityNeedsCompliance(opportunity: ContentOpportunity): boolean {
  return /credit|funding|trading|guarantee/i.test(`${opportunity.target_keyword_topic} ${opportunity.offer_tie_in}`);
}
