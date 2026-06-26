import type { ContentTestResult } from '../config/contentTestTypes';

export function contentTestConversionRate(test: Pick<ContentTestResult, 'clicks' | 'conversions'>): number {
  if (!test.clicks) return 0;
  return Math.round((test.conversions / test.clicks) * 10000) / 100;
}

export function contentTestValue(test: Pick<ContentTestResult, 'revenue' | 'estimated_value'>): number {
  return test.revenue || test.estimated_value || 0;
}
