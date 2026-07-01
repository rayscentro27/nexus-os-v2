import { answerConversation } from './hermesConversationBrain';
import { orchestrateHermes } from './hermesOrchestrator';
import { answerOperationsQuestion, operationsFreshness } from './hermesOperationsContext';
import { answerMemoryQuestion } from './hermesMemoryContext';
import { getBackendStatusMessage } from './hermesBackendContextAdapter';
import hermesOperations from '../../reports/hermes_operations_status_latest.json';

export interface HermesBrainAnswer { handled:boolean; text:string; source:string; intent:string; }
export function thinkWithHermes(message:string, hasPageContext=false):HermesBrainAnswer{
  const plan=orchestrateHermes(message,hasPageContext); const route=plan.routing.route;
  if(route==='casual') return {handled:true,text:answerConversation(message,plan.routing.intent as never)||'',source:'conversation_brain',intent:plan.routing.intent};
  if(route==='capability_status') {
    if(/holding back|why.*hold/i.test(message)) return {handled:true,text:answerOperationsQuestion(message),source:'operations_context',intent:'capability_status'};
    const freshness=operationsFreshness();return {handled:true,text:`${getBackendStatusMessage()} Page context: ${hasPageContext?'available for the current route':'not supplied'}. Mac Mini operations audit: ${freshness.stale?'stale':'available'} (${freshness.checkedAt}). Second-brain index: available as a bounded local report. Web search and live model status are not configured unless the explicit provider checks say otherwise. Execution remains approval-gated.`,source:'capability_status',intent:'capability_status'};}
  if(route==='nexus_supabase' && /approv|ray review|pending|card/i.test(message)) {
    const review=hermesOperations.ray_review;
    return {handled:true,text:`Ray Review needs attention: the latest Hermes operations snapshot shows ${review.pending_count} pending approval card(s). Persistence is ${review.persistence_verified?'verified':'not verified'} and the recorded flow is ${review.approval_flow}.\n\nPlain English: I am not using the old local zero-card fallback. When a live authenticated Supabase session is available, I will query task_requests/approvals and replace this with live rows. If live querying is unavailable, this is a report snapshot from ${hermesOperations.generated_at}.\n\nSafe next action: open Ray Review and approve/hold/reject the highest-impact pending card. Anything that sends, publishes, charges, trades, deploys, seeds, or changes a scheduler still needs explicit Ray approval.\n\nSource: Hermes operations Ray Review snapshot + live Supabase path when authenticated.`,source:'ray_review_snapshot',intent:'supabase_context'};
  }
  if(route==='operations') return {handled:true,text:answerOperationsQuestion(message),source:'operations_context',intent:plan.routing.intent};
  if(route==='reports_memory') return {handled:true,text:answerMemoryQuestion(message),source:'second_brain',intent:plan.routing.intent};
  if(route==='web_research') return {handled:true,text:'Live web search is not configured and proven in this layer. I can prepare an approval-gated research task, but I will not claim current web access.',source:'capability_status',intent:'web_research'};
  if(route==='ambiguous') return {handled:false,text:'',source:'router',intent:'ambiguous'};
  return {handled:false,text:'',source:'router',intent:plan.routing.intent};
}
