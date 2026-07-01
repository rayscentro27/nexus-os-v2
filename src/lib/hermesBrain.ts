import { answerConversation } from './hermesConversationBrain';
import { orchestrateHermes } from './hermesOrchestrator';
import { answerOperationsQuestion, operationsFreshness } from './hermesOperationsContext';
import { answerMemoryQuestion } from './hermesMemoryContext';
import { getBackendStatusMessage } from './hermesBackendContextAdapter';

export interface HermesBrainAnswer { handled:boolean; text:string; source:string; intent:string; }
export function thinkWithHermes(message:string, hasPageContext=false):HermesBrainAnswer{
  const plan=orchestrateHermes(message,hasPageContext); const route=plan.routing.route;
  if(route==='casual') return {handled:true,text:answerConversation(message,plan.routing.intent as never)||'',source:'conversation_brain',intent:plan.routing.intent};
  if(route==='capability_status') {const freshness=operationsFreshness();return {handled:true,text:`${getBackendStatusMessage()} Page context: ${hasPageContext?'available for the current route':'not supplied'}. Mac Mini operations audit: ${freshness.stale?'stale':'available'} (${freshness.checkedAt}). Second-brain index: available as a bounded local report. Web search and live model status are not configured unless the explicit provider checks say otherwise. Execution remains approval-gated.`,source:'capability_status',intent:'capability_status'};}
  if(route==='operations') return {handled:true,text:answerOperationsQuestion(message),source:'operations_context',intent:plan.routing.intent};
  if(route==='reports_memory') return {handled:true,text:answerMemoryQuestion(message),source:'second_brain',intent:plan.routing.intent};
  if(route==='web_research') return {handled:true,text:'Live web search is not configured and proven in this layer. I can prepare an approval-gated research task, but I will not claim current web access.',source:'capability_status',intent:'web_research'};
  if(route==='ambiguous') return {handled:false,text:'',source:'router',intent:'ambiguous'};
  return {handled:false,text:'',source:'router',intent:plan.routing.intent};
}
