import { summarizeOutcome } from './disputeStrategyKnowledge'

export function summarizeStrategyOutcomes(outcomes: Array<{ response_result?: string; option_type?: string; item_type?: string }>) {
  const grouped = outcomes.reduce<Record<string, number>>((acc, outcome) => {
    const key = outcome.response_result || 'not_sent'
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  return {
    grouped,
    summary: Object.entries(grouped).map(([result, count]) => `${count} ${result.replace(/_/g, ' ')}`).join(', ') || 'No outcomes recorded yet',
    nextRound: outcomes.length ? summarizeOutcome(outcomes[outcomes.length - 1].response_result || 'not_sent') : 'Collect first-round outcomes before changing strategy.',
  }
}

export function recommendNextRoundStrategy(outcome: { response_result?: string; item_type?: string; option_type?: string }) {
  const result = outcome.response_result || 'not_sent'
  if (result === 'verified') return 'Review method of verification, furnisher dispute, or stronger evidence upload.'
  if (result === 'no_response') return 'Prepare follow-up or escalation review.'
  if (result === 'client_evidence_needed') return 'Request evidence upload before the next round.'
  if (result === 'deleted' || result === 'corrected' || result === 'updated') return 'Track success and reassess funding readiness impact.'
  return 'Keep in specialist review until the client and GoClear approve the next action.'
}

export function getStrategyResearchBacklog() {
  return [
    'Compare option outcomes by item type and bureau/furnisher',
    'Track response time by mailing method',
    'Measure evidence impact by dispute reason',
    'Review follow-up strategy after verified outcomes',
    'Keep detailed strategy in admin/specialist views, not client-facing flow',
  ]
}
