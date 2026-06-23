/**
 * Hermes conversation-first intent layer (pure, deterministic, no side effects).
 *
 * Hermes defaults to Interview Mode: normal conversation, NO command routing, NO jobs.
 * Casual/general/opinion/public questions never queue Nexus jobs. Nexus is touched only in
 * Operator Mode for clear action requests; Advisor Mode reads context but does not create jobs.
 */

export type HermesMode = 'interview' | 'advisor' | 'operator';

export type Intent =
  | 'casual_conversation'
  | 'general_question'
  | 'opinion_request'
  | 'public_current_info_question'
  | 'nexus_read_request'
  | 'nexus_action_request'
  | 'publish_request'
  | 'trading_request'
  | 'deploy_request';

export const MODE_DESC: Record<HermesMode, string> = {
  interview: 'conversation only, no Nexus access',
  advisor: 'read-only Nexus context',
  operator: 'can queue gated jobs',
};

export interface AwareSnapshot {
  approvals?: number; jobs?: number; incidents?: number; campaigns?: number; receipts?: number;
}

/** "switch to advisor/operator/interview mode" → target mode, else null. */
export function detectModeSwitch(text: string): HermesMode | null {
  const t = (text || '').toLowerCase();
  if (/\b(switch to |go to |enter |back to )?(interview|chat) mode\b/.test(t)) return 'interview';
  if (/\b(switch to |go to |enter )?advisor mode\b/.test(t)) return 'advisor';
  if (/\b(switch to |go to |enter )?operator mode\b/.test(t)) return 'operator';
  return null;
}

export function classifyIntent(text: string): Intent {
  const t = (text || '').toLowerCase().trim();
  const negatedAction = /\b(do not|don'?t|never|without)\b/.test(t);

  if (!negatedAction && /\b(publish|post (it|this|to)|go live)\b/.test(t)) return 'publish_request';
  if (/\b(buy|sell|go (long|short)|execute (a )?trade|place (a )?trade|live trade)\b/.test(t)) return 'trading_request';
  if (/\b(deploy|ship to prod|restart (the )?(server|service))\b/.test(t)) return 'deploy_request';

  // Clear Nexus ACTION verbs only.
  if (/\b(queue|run (a |the )?job|create (a |the )?job|kick off|prepare (a |the )?(publish )?package|review .*transcript in nexus|generate .*in nexus)\b/.test(t))
    return 'nexus_action_request';
  // Nexus READ requests.
  if (/\b(check (nexus|approvals)|nexus status|summari[sz]e nexus|show (me )?(the )?(jobs|approvals|queue|status)|read nexus|what'?s queued)\b/.test(t))
    return 'nexus_read_request';

  // Public / current-info questions Hermes cannot answer from its own knowledge.
  if (/\b(who (won|played|is winning|scored)|score of|world cup|super bowl|last night|today'?s (game|news|weather|price)|current (price|news|weather|score)|latest news|right now|stock price)\b/.test(t))
    return 'public_current_info_question';

  // Opinion / advice.
  if (/\b(what do you think|your (honest )?(take|opinion|view)|should (i|we)|do you think|how do you feel|thoughts on)\b/.test(t))
    return 'opinion_request';

  // Casual greetings / chit-chat.
  if (/^(hi|hey+|hello|yo|sup|good (morning|afternoon|evening|night)|how are you|how'?s it going|what'?s up|howdy|morning|evening)\b/.test(t))
    return 'casual_conversation';

  return 'general_question';
}

export interface HermesPlan {
  intent: Intent;
  reply: string;
  allowJob: boolean;        // true ONLY when a Nexus job should actually be queued (operator mode)
  suggestMode: HermesMode | null;
}

const ACTIONISH: Intent[] = ['nexus_action_request', 'publish_request', 'trading_request', 'deploy_request'];

export function planResponse(text: string, mode: HermesMode, aware?: AwareSnapshot): HermesPlan {
  const intent = classifyIntent(text);
  const t = (text || '').toLowerCase();
  const plan = (reply: string, allowJob = false, suggestMode: HermesMode | null = null): HermesPlan =>
    ({ intent, reply, allowJob, suggestMode });

  // Conversational intents NEVER queue jobs, in any mode.
  if (intent === 'casual_conversation') {
    const morning = /good morning|^morning\b/.test(t);
    return plan(morning
      ? 'Good morning Ray. What are we focused on today — GoClear leads, Nexus testing, or clearing blockers?'
      : "Hey Ray — what's on your mind? GoClear leads, Nexus testing, or clearing blockers?");
  }
  if (intent === 'public_current_info_question') {
    return plan('I need current public info to verify that. I can check public sources if you want, but I will not touch Nexus for that.');
  }
  if (intent === 'opinion_request') {
    if (/goclear|apex|funding readiness/.test(t)) {
      return plan('My honest take: GoClear is closest to money if we turn it into a simple $97 readiness review with a clear intake, a safe report, and a follow-up path. The current dashboard is more of a concept board than an operating workflow.');
    }
    return plan("My honest take, briefly: tell me the specific thing and I'll give you a direct recommendation, the trade-offs, and the fastest safe next step — no fluff.");
  }
  if (intent === 'general_question') {
    return plan("Happy to talk it through. In Interview Mode I answer from what I know and won't touch Nexus — if you want me to pull live Nexus context, say 'switch to Advisor Mode.'");
  }

  // From here: read/action intents — behavior depends on mode.
  if (mode === 'interview') {
    if (intent === 'nexus_read_request')
      return plan('I can do that, but that means switching from Interview Mode into Advisor Mode so I can read Nexus context. Do you want me to switch?', false, 'advisor');
    return plan('That requires Operator Mode. I can switch and queue it through the safe runner if you approve.', false, 'operator');
  }

  if (mode === 'advisor') {
    if (intent === 'nexus_read_request') {
      const a = aware || {};
      return plan(`Advisor Mode (read-only): pending approvals ${a.approvals ?? 0}, queued jobs ${a.jobs ?? 0}, open incidents ${a.incidents ?? 0}, active campaigns ${a.campaigns ?? 0}, publish receipts ${a.receipts ?? 0}. I can summarize any of these — but I can't create jobs or approvals here.`);
    }
    return plan('That is an action. Switch to Operator Mode and I will queue it through the safe runner (dry-run; approval required before any real publish/send/trade/deploy).', false, 'operator');
  }

  // operator mode — read/action requests queue a single gated job
  if (ACTIONISH.includes(intent) || intent === 'nexus_read_request') {
    return plan('Queuing that as a gated job for the runner (dry-run by default; no real publish/send/trade/deploy without explicit approval).', true);
  }
  return plan('Got it.');
}
