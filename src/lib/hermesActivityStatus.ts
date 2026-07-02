import type { RouteDecision } from './hermesRouteDecision';
import { buildDailySummary, buildCeoDailySummary } from './hermesDailyActivityTranslator';

const WORK_OPENER = /\b(where are we at|where did we leave off|where were we|what['\u2019]?s next|what should we work on|what should we do first|what are we doing today|give me the rundown|catch me up|get me up to speed|continue from last time|pick up where we left off|what is the next move|what is next for (?:nexus|hermes))\b/i;
const TODAY_SUMMARY = /\b(what (?:did|do|have) we (?:complete|completed|get done|finish|work on) today|what got done today|what was done today|what changed today|today['\u2019]?s progress|todays progress|daily summary|summarize today|what was completed|what commits happened today|what did (?:opencode|codex) finish|what did we just complete|what did this last patch complete)\b/i;
const YESTERDAY_SUMMARY = /\b(what (?:did|do|have) we (?:work on|do|complete|finish|accomplish|get done|push|ship|deliver) yesterday|what (?:was|were|got) (?:done|completed|finished|shipped|pushed|delivered|accomplished) yesterday|what (?:changed|happened|went on|took place) yesterday|what did we push yesterday|yesterday['\u2019]?s (?:progress|summary|work|results)|summarize yesterday|give (?:me |us )?(?:the )?(?:ceo (?:version|summary)|daily summary|run ?down|recap|overview) (?:for |of )?yesterday)\b/i;
const RECENT_SUMMARY = /\b(what (?:did|do|have) we (?:work on|do|complete|finish|accomplish|get done|push|ship|deliver) (?:this week|last week|recently)|what (?:was|were|got) (?:done|completed|finished|shipped|pushed|delivered|accomplished) (?:this week|last week|recently)|what (?:changed|happened|went on) (?:this week|last week|recently)|(?:give (?:me |us )?|show )?(?:the )?(?:ceo (?:version|summary)|daily summary|run ?down|recap|overview) (?:for |of )?(?:this week|last week|recently))\b/i;

export type ActivityRecapType = 'work_continuation_or_next_step' | 'today_completed_summary' | 'yesterday_completed_summary' | 'recent_completed_summary';

export function classifyActivityStatusQuestion(message: string): ActivityRecapType | null {
  if (YESTERDAY_SUMMARY.test(message)) return 'yesterday_completed_summary';
  if (RECENT_SUMMARY.test(message)) return 'recent_completed_summary';
  if (TODAY_SUMMARY.test(message)) return 'today_completed_summary';
  if (WORK_OPENER.test(message)) return 'work_continuation_or_next_step';
  return null;
}

export function answerActivityStatusQuestion({ message, routeDecision }: { message: string; routeDecision: RouteDecision; contextPacket: unknown }): string {
  if (routeDecision.intent === 'work_continuation_or_next_step') {
    if (/what['\u2019]?s next|what should|next move|what is next/i.test(message)) return 'Next, verify the live browser behavior, then patch any remaining routing gaps before moving back into Credit/Funding and monetization workflows. The remaining verification blockers are authenticated Supabase access and production deployment.';
    return 'The last confirmed checkpoint is commit 556c95a, which added the Common Advisor layer, plain-English trace wording, approval-gated scheduling drafts, and precise Ray Review proof language. The remaining blockers are authenticated Supabase verification and production deployment verification.';
  }
  if (routeDecision.intent === 'yesterday_completed_summary') {
    const journal = buildDailySummary('yesterday');
    if (!/No activity events recorded/.test(journal)) return journal;
    return 'I do not have verified activity logs for yesterday in this browser session. I can check git history, report timestamps, or Ray Review activity if those are connected. Do you want me to look into one of those?';
  }
  if (routeDecision.intent === 'recent_completed_summary') {
    const journal = buildCeoDailySummary('today');
    if (!/No activity events recorded/.test(journal)) return journal;
    return 'I do not have a verified recent activity source loaded. I can check git history, report timestamps, or Ray Review activity for this period. Do you want me to look into one of those?';
  }
  const journal = buildDailySummary('today');
  if (!/No activity events recorded/.test(journal)) return journal;
  return 'I do not have a fresh activity report loaded in this browser session. The last confirmed work I know about is commit 556c95a: casual_common, general_advisor, plain-English trace wording, scheduling action routing, Ray Review proof language, and safety tests. At that checkpoint, the build passed and 503/503 tests passed.';
}
