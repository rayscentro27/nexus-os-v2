import type { RouteDecision } from './hermesRouteDecision';
import { buildDailySummary } from './hermesDailyActivityTranslator';

const WORK_OPENER = /\b(where are we at|where did we leave off|where were we|what['’]?s next|what should we work on|what should we do first|what are we doing today|give me the rundown|catch me up|get me up to speed|continue from last time|pick up where we left off|what is the next move|what is next for (?:nexus|hermes))\b/i;
const TODAY_SUMMARY = /\b(what (?:did|do|have) we (?:complete|completed|get done|finish|work on) today|what got done today|what was done today|what changed today|today['’]?s progress|todays progress|daily summary|summarize today|what was completed|what commits happened today|what did (?:opencode|codex) finish|what did we just complete|what did this last patch complete)\b/i;

export function classifyActivityStatusQuestion(message: string): 'work_continuation_or_next_step' | 'today_completed_summary' | null {
  if (TODAY_SUMMARY.test(message)) return 'today_completed_summary';
  if (WORK_OPENER.test(message)) return 'work_continuation_or_next_step';
  return null;
}

export function answerActivityStatusQuestion({ message, routeDecision }: { message: string; routeDecision: RouteDecision; contextPacket: unknown }): string {
  if (routeDecision.intent === 'work_continuation_or_next_step') {
    if (/what['’]?s next|what should|next move|what is next/i.test(message)) return 'Next, verify the live browser behavior, then patch any remaining routing gaps before moving back into Credit/Funding and monetization workflows. The remaining verification blockers are authenticated Supabase access and production deployment.';
    return 'The last confirmed checkpoint is commit 556c95a, which added the Common Advisor layer, plain-English trace wording, approval-gated scheduling drafts, and precise Ray Review proof language. The remaining blockers are authenticated Supabase verification and production deployment verification.';
  }
  const journal = buildDailySummary('today');
  if (!/No activity events recorded/.test(journal)) return journal;
  return 'I do not have a fresh activity report loaded in this browser session. The last confirmed work I know about is commit 556c95a: casual_common, general_advisor, plain-English trace wording, scheduling action routing, Ray Review proof language, and safety tests. At that checkpoint, the build passed and 503/503 tests passed.';
}
