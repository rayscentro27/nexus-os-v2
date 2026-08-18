import dailyBriefReport from '../../reports/hermes_modernization/daily_brief.json';

export type HermesDailyBriefReport = {
  status: string;
  confidence: string;
  top_priority: { title: string };
  revenue_status: {
    confirmed_revenue_usd: number | string;
    pending_test_revenue_usd: number | string;
    possible_offer_value_usd: number | string;
    blocked_revenue_usd: number | string;
  };
  opportunity_updates: Array<{ title: string; status: string; base_score: number | string; change: string }>;
  creative_updates: { selected_territory: string };
  builder_updates: { status: string; verification: string };
  worker_health: Array<{ worker_id: string; classification: string }>;
  cost_summary: { zero_token_executions: number | string; provider_cost_usd: number | string };
  deterministic_execution_share: number | string;
  ai_execution_share: number | string;
  blockers: Array<{ blocker?: string }>;
  decisions_needed: string[];
  highest_value_next_action: string;
  freshness: { status: string; live_supabase_read: string };
  learning_updates: { observation_count: number | string; proposal_count: number | string };
  workforce_updates: { worker_count: number | string; kilo_classification: string; kilo_decision: string };
};

export const hermesDailyBrief = dailyBriefReport as unknown as HermesDailyBriefReport;

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
    `Workforce: ${brief.workforce_updates.worker_count} certified records; Kilo is ${brief.workforce_updates.kilo_classification} and onboarding decision is ${brief.workforce_updates.kilo_decision}.`,
    `Blocked: ${brief.blockers.map((item) => item.blocker).slice(0, 3).join('; ') || 'UNKNOWN'}.`,
    `Ray decisions: ${brief.decisions_needed.join('; ')}.`,
    `Next action: ${brief.highest_value_next_action}`,
    `Live Supabase read: ${brief.freshness.live_supabase_read}.`,
  ].join('\n');
}
