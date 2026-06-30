export const hermesQuickPrompts = [
  'Summarize current system',
  'What should I do next?',
  'Next 100 steps',
  'Money actions today',
  'Review latest reports',
  'Show blockers',
];

const intentRules = [
  [/100 steps|delegate|large prompt/i, 'delegation'],
  [/money|revenue|offer/i, 'money'],
  [/scheduler|automation|running/i, 'scheduler'],
  [/credit|client readiness/i, 'credit'],
  [/trading|oanda|vibe/i, 'trading'],
  [/research|opportunit/i, 'research'],
  [/report|summary|system/i, 'summary'],
  [/block/i, 'blockers'],
  [/approv|reject|hold/i, 'approval'],
];

export function buildHermesResponse(message) {
  const intent = intentRules.find(([pattern]) => pattern.test(message))?.[1] || 'next';
  const responses = {
    delegation: 'I split this request into safe internal jobs, approval-gated jobs, blocked jobs, specialist assignments, required reports, and exact commands. The plan is queued locally; nothing external was executed.',
    money: 'The closest money proof is the $97 readiness review test path. Approve the synthetic customer insert, verify the live dashboard, then manually complete Stripe test Checkout. Revenue remains $0 until a real, separately approved production path exists.',
    scheduler: 'Two internal-safe launchd agents are loaded: the 08:00 operating cycle and 18:00 closeout. External sends, charges, inserts, publishing, and live trades remain gated.',
    credit: 'The Credit Specialist can review readiness, document gaps, and dispute drafts. It cannot send disputes or contact a client.',
    trading: 'Oanda practice reads and the Vibe paper bridge are proven. Recurring demo orders and all live execution remain approval-gated.',
    research: 'The research-to-money pipeline contains 50 candidates, including 26 immediately actionable items. I can route selected items to Research, Monetization, or Marketing specialists.',
    summary: 'Nexus has two safe schedules loaded, 64 Ray Review cards, nine offers, 11 message drafts, 50 research-to-money candidates, and $0 confirmed revenue. The primary operating gate is the fake-customer-to-test-payment journey.',
    blockers: 'Current blockers: fake customer not persistently inserted, live dashboard flag off, Stripe test Checkout unpaid, PaymentIntent unconfirmed, Resend permissions/domain mismatch, YouTube transcript absent, and NotebookLM export absent.',
    approval: 'Approve changes decision state and creates a receipt; it does not execute an external action. Reject closes the proposal. Hold preserves it with your feedback.',
    next: 'I recommend opening Ray Review, handling the synthetic customer and Stripe test cards first, then reviewing the $97 offer and communication drafts.',
  };
  const specialist = intent === 'credit' ? 'Credit Specialist' : intent === 'money' ? 'Monetization Specialist' : intent === 'trading' ? 'Trading Specialist' : intent === 'research' ? 'Research Specialist' : 'Hermes CEO Advisor';
  return { intent, specialist, text: responses[intent], queued: intent === 'delegation' };
}
