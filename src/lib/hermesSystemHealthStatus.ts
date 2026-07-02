import { getCapabilityReport } from './hermesCapabilityStatus';
import { getSectionSummary } from './nexusSectionStatusRegistry';

export function answerSystemHealthQuestion(message: string): string {
  const capability = getCapabilityReport();
  const sections = getSectionSummary();
  if (/where is the problem|what is the issue|what is not working/i.test(message)) {
    return 'The current problem is routing/fallback dominance: some valid page, scheduling, and system-status questions have been reaching fallback clarification instead of their intended handlers. The latest local audit identifies the missing intent boundaries; no external action was taken.';
  }
  return `**System health summary (last confirmed local checkpoint):**\n- Build/tests: build passed; 590/590 tests passed at commit 831dcc5. This is checkpoint evidence, not a fresh production probe.\n- Supabase: ${capability.supabase.userFacing} Authentication and RLS still determine each live read.\n- Deployment: Netlify production verification is not confirmed from this local workspace.\n- Sections: ${sections.live} live, ${sections.static} static, ${sections.report_snapshot} report-snapshot, ${sections.blocked} blocked.\n- Hermes brain: RouteDecision, safety, trace, live-record retrieval, selection memory, advisory continuity, and shared chat pipeline are present. The route-dominance audit identified page/status/scheduling coverage gaps now under repair.\n- Known blockers: authenticated browser/Supabase verification and production deployment verification.\n\n**Next recommended action:** run the authenticated browser transcript after deployment and compare the routing trace for every turn.`;
}
