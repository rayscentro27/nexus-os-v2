export const OUTCOME_ANALYTICS_LANGUAGE = {
  disclaimer: 'These observations describe what Nexus recorded before and after client actions. They do not establish that a strategy caused a credit-report, score, or funding outcome.',
  prohibited: [/\bcaused (deletion|removal|a score increase|a score|funding)/i, /\bguaranteed (success|funding)/i, /strategy (worked|failed) because/i, /resulted in funding approval/i, /proven legal violation/i],
  requiredBlockedExamples: ['caused deletion','caused removal','caused a score increase','caused funding','guaranteed success','guaranteed funding','strategy worked because','strategy failed because','resulted in funding approval','proven legal violation'],
} as const

export type ComparisonObservationType =
  | 'account_present_on_both_reports' | 'account_not_found_on_later_report' | 'account_newly_present'
  | 'balance_changed' | 'status_changed' | 'payment_status_changed' | 'ownership_changed'
  | 'bureau_coverage_changed' | 'no_measurable_change' | 'uncertain_comparison'

export function validateOutcomeLanguage(text: string) {
  const blockedPatterns = OUTCOME_ANALYTICS_LANGUAGE.prohibited.filter(pattern => pattern.test(text)).map(pattern => pattern.source)
  return { safe: blockedPatterns.length === 0, blockedPatterns, disclaimer: OUTCOME_ANALYTICS_LANGUAGE.disclaimer }
}

export interface ComparableAccount { canonicalAccountId: string; matchConfidence?: 'high'|'medium'|'low'; furnisher?: string; maskedAccountReference?: string; balance?: number|null; accountStatus?: string|null; ownership?: string|null; bureaus?: string[] }
export interface OutcomeObservation { type: ComparisonObservationType; canonicalAccountId?: string; confidence: 'high'|'medium'|'low'; summary: string; causal: false }

export function compareCanonicalReportAccounts(prior: ComparableAccount[], later: ComparableAccount[]): OutcomeObservation[] {
  const laterById = new Map(later.map(account => [account.canonicalAccountId, account]))
  const observations: OutcomeObservation[] = []
  for (const before of prior) {
    const after = laterById.get(before.canonicalAccountId)
    if (!after) {
      observations.push({ type: before.matchConfidence === 'low' ? 'uncertain_comparison' : 'account_not_found_on_later_report', canonicalAccountId: before.canonicalAccountId, confidence: before.matchConfidence === 'low' ? 'low' : 'high', summary: before.matchConfidence === 'low' ? 'Nexus could not confidently match this account on the later report.' : 'This account was not found on the later report.', causal: false })
      continue
    }
    const changed: OutcomeObservation[] = []
    if (before.balance != null && after.balance != null && before.balance !== after.balance) changed.push({ type: 'balance_changed', canonicalAccountId: before.canonicalAccountId, confidence: 'high', summary: 'A later report showed a different balance.', causal: false })
    if (before.accountStatus && after.accountStatus && before.accountStatus !== after.accountStatus) changed.push({ type: 'status_changed', canonicalAccountId: before.canonicalAccountId, confidence: 'high', summary: 'A later report showed a different account status.', causal: false })
    if (before.ownership && after.ownership && before.ownership !== after.ownership) changed.push({ type: 'ownership_changed', canonicalAccountId: before.canonicalAccountId, confidence: 'medium', summary: 'A later report showed different ownership information.', causal: false })
    if (JSON.stringify([...(before.bureaus || [])].sort()) !== JSON.stringify([...(after.bureaus || [])].sort())) changed.push({ type: 'bureau_coverage_changed', canonicalAccountId: before.canonicalAccountId, confidence: 'medium', summary: 'A later report showed different bureau coverage.', causal: false })
    const noChange: OutcomeObservation = { type: 'no_measurable_change', canonicalAccountId: before.canonicalAccountId, confidence: 'high', summary: 'No measurable change was detected yet.', causal: false }
    observations.push(...(changed.length ? changed : [noChange]))
  }
  for (const after of later) if (!prior.some(before => before.canonicalAccountId === after.canonicalAccountId)) observations.push({ type: 'account_newly_present', canonicalAccountId: after.canonicalAccountId, confidence: after.matchConfidence === 'low' ? 'low' : 'medium', summary: 'An account was present on the later report but not the earlier report.', causal: false })
  return observations
}

export function summarizeOutcomeFunnel(events: Array<{event_type?: string}>) {
  const stages = ['strategy_presented','strategy_viewed','client_strategy_saved','client_strategy_selected','evidence_requested','evidence_uploaded','draft_generated','draft_reviewed','client_authorized','client_withdrew','strategy_completed','exception_created']
  return Object.fromEntries(stages.map(stage => [stage, events.filter(event => event.event_type === stage).length]))
}
