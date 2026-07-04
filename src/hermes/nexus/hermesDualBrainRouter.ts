import { answerAsNexusHermes } from "./hermesNexusOperatorBrain";
import { answerAsHermesAlpha } from "../alpha/hermesAlphaOpportunityBrain";
export function routeHermesPrompt(prompt:string) {
  const q=prompt.toLowerCase(); const both=/both|operational.*opportun|opportun.*operational/.test(q);
  const alpha=/money|seo|marketing|affiliate|trading|business idea|opportun/.test(q);
  const nexus=/status|ready|blocked|report|scheduler|goclear|supabase|connector|api key|automat|disabled|test next/.test(q);
  if(both||(alpha&&nexus)) return { route:"both" as const, reason:"Prompt spans operations and opportunity research.", responses:[answerAsNexusHermes(prompt),answerAsHermesAlpha(prompt)] };
  if(alpha) return { route:"alpha" as const, reason:"Opportunity/research intent.", responses:[answerAsHermesAlpha(prompt)] };
  return { route:"nexus" as const, reason:"Operational/default intent.", responses:[answerAsNexusHermes(prompt)] };
}
export function createHermesHandoff(prompt:string,target:string){return {status:"draft_only",target,prompt,approvalRequired:true,externalExecution:false};}
