import dailyBriefReport from '../../reports/hermes_modernization/daily_brief.json';

export type HermesDailyBriefReport = typeof dailyBriefReport;

export const hermesDailyBrief = dailyBriefReport;

export function renderHermesDailyBrief(brief: HermesDailyBriefReport = hermesDailyBrief): string {
  const revenue = brief.revenue_status;
  const cost = brief.cost_summary;
  const opportunity = brief.opportunity_updates[0];
  const workers = brief.worker_health
    .map((worker) => `${worker.worker_id}: ${worker.classification}`)
    .join(', ');

  return [
    'Hermes Daily Brief (report-backed):',
    '',
    `Status: ${brief.status}; confidence: ${brief.confidence}; freshness: ${brief.freshness.status}.`,
    `Top priority: ${brief.top_priority.title}`,
    `Money: confirmed revenue $${revenue.confirmed_revenue_usd}; pending test revenue $${revenue.pending_test_revenue_usd}; possible offer value $${revenue.possible_offer_value_usd}; blocked revenue $${revenue.blocked_revenue_usd}.`,
    `Opportunity: ${opportunity.title} is ${opportunity.status}; score ${opportunity.base_score}; trend ${opportunity.change}.`,
    `Creative: ${brief.creative_updates.selected_territory}; builder ${brief.builder_updates.status}; verification ${brief.builder_updates.verification}.`,
    `Workers: ${workers}.`,
    `Execution: deterministic share ${brief.deterministic_execution_share}; AI share ${brief.ai_execution_share}; zero-token executions ${cost.zero_token_executions}; provider cost $${cost.provider_cost_usd}.`,
    `Learning: ${brief.learning_updates.observation_count} measured observations and ${brief.learning_updates.proposal_count} proposal candidates; automatic promotion is disabled.`,
    `Blocked: ${brief.blockers.map((item) => item.blocker).slice(0, 3).join('; ') || 'UNKNOWN'}.`,
    `Ray decisions: ${brief.decisions_needed.join('; ')}.`,
    `Next action: ${brief.highest_value_next_action}`,
    `Live Supabase read: ${brief.freshness.live_supabase_read}.`,
  ].join('\n');
}
