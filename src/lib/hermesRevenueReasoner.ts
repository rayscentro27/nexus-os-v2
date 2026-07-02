export interface RevenueReasoningContext {
  usedSupabase: boolean;
  supabaseTables?: string[];
  supabaseNote?: string;
}

export function isRevenueStrategyQuestion(message: string): boolean {
  const revenueSignal = /\b(money|revenue|income|earn(?:ing|ings)?|monetiz\w*|profitable|sales)\b/i.test(message) || /\bhow much\b.*\b(?:make|earn)\b/i.test(message);
  return revenueSignal && /\b(most|fast\w*|highest|best|next|month|\d+\s+(?:days?|says?|weeks?))\b/i.test(message);
}

export function answerRevenueStrategy(context: RevenueReasoningContext): { text: string; handler: string; source: string } {
  const sourceNote = context.usedSupabase
    ? `Authenticated reads succeeded for ${context.supabaseTables?.join(', ') || 'the opportunity tables'}, but the revenue math below still uses explicit offer-ladder assumptions because normalized unit economics were not returned to this reasoner.`
    : `No authenticated live opportunity rows were available for this answer, so these are explicit planning assumptions based on the known GoClear/Apex offer ladder.${context.supabaseNote ? ` ${context.supabaseNote}` : ''}`;
  return {
    text: `**Plain answer:** The fastest 30-day money path is the $97 Credit & Funding Readiness Review, followed by the $297 assistant plan and then Monthly Readiness Subscription starts.\n\n**Revenue range (planning assumptions):**\n- Conservative: 10 reviews × $97 = **$970**\n- Realistic: 20 reviews × $97 + 5 assistant-plan upsells × $297 = **$3,425**\n- Stretch: 30 reviews × $97 + 10 upsells × $297 + 20 subscription starts × an assumed $49 first month = **$6,860**\n\nThe $49 subscription figure is an assumption, not a verified approved price. ${sourceNote}\n\n**Why this path:** low startup cost, fast manual fulfillment, and direct fit with the existing GoClear/Apex workflow.\n\n**Next safe action:** create a Ray Review card for the offer plan and prepare outreach and checkout in test/draft mode. No charges, sends, or publishing without approval.`,
    handler: 'revenue_30_day_reasoner',
    source: context.usedSupabase ? 'live_supabase_plus_offer_ladder' : 'local_offer_ladder_with_assumptions',
  };
}
