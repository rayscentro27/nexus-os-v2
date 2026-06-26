import type { SeoKeywordOpportunity } from '../config/seoKeywordTypes';

export function keywordOpportunityScore(keyword: Pick<SeoKeywordOpportunity, 'affiliate_relevance' | 'GoClear_relevance' | 'difficulty_estimate'>): number {
  const difficultyPenalty = /high/i.test(keyword.difficulty_estimate) ? 20 : /medium/i.test(keyword.difficulty_estimate) ? 10 : 0;
  return Math.max(0, Math.min(100, Math.round((keyword.affiliate_relevance + keyword.GoClear_relevance) / 2 - difficultyPenalty)));
}
