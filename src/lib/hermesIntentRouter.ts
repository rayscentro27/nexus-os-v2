import { classifyConversationIntent } from './hermesConversationBrain';

export type HermesOrchestratorRoute = 'casual' | 'capability_status' | 'page_context' | 'nexus_supabase' | 'operations' | 'reports_memory' | 'web_research' | 'execution' | 'ambiguous';
export interface RoutedHermesIntent { route: HermesOrchestratorRoute; intent: string; confidence: 'high'|'medium'|'low'; reason: string; }

export function routeHermesIntent(message: string, hasPageContext = false): RoutedHermesIntent {
  const text=message.toLowerCase().trim();
  const casual=classifyConversationIntent(message);
  if (casual) return {route:'casual',intent:casual,confidence:'high',reason:'conversation brain matched before tools'};
  if (/why.*holding back|holding back|where.*answers|can you (see|access|search)|are you connected|model|web access|social media|supabase status|what can you do/.test(text)) return {route:'capability_status',intent:'capability_status',confidence:'high',reason:'explicit capability/status question'};
  if (hasPageContext && /this page|this report|this strategy|what can i click|what am i looking at|first one|second one|last one/.test(text)) return {route:'page_context',intent:'page_context',confidence:'high',reason:'current page reference'};
  if (/run (a )?full nexus audit|audit nexus|reality audit|what is real and what is fake|what is live.*static.*unproven|live.*static.*unproven|what is running|what is not running|not running|installed but not proven|report-only|report only|what is connected|check everything|what (processes|background jobs) (are )?(running|active)|failed overnight|youtube research.*(running|writing|supabase)|is youtube research|cli tools|token.*limitations|env.*limitations|mac mini|operations status|explain.*nexus audit|explain.*plain language/.test(text)) return {route:'operations',intent:/audit|check everything|real and what is fake|live.*static.*unproven/.test(text)?'run_nexus_audit':'operations_status',confidence:'high',reason:'Mac Mini/operations evidence requested'};
  if (/what needs (my |ray )?approval|approvals? (are )?pending|how many ray review cards|did my approval persist|ray review|approve|pending.*approval|supabase|database|client profiles?|business opportunit|research candidates?|monetization|task requests?/.test(text)) return {route:'nexus_supabase',intent:'supabase_context',confidence:'high',reason:'live Nexus data request'};
  if (/what did we|what changed|what did codex|commits? (were )?pushed|what was seeded|what failed|what remains blocked|what should (we|i) work on next/.test(text)) return {route:'reports_memory',intent:'memory_activity',confidence:'high',reason:'historical/second-brain request'};
  if (/search the (web|internet)|look .* up online|latest external|current news/.test(text)) return {route:'web_research',intent:'web_research',confidence:'high',reason:'external research requested'};
  if (/\b(send|publish|charge|trade|deploy|seed|insert|delete|truncate|start|stop|restart|execute|run)\b/.test(text)) return {route:'execution',intent:'execution_request',confidence:'medium',reason:'state-changing verb detected'};
  return {route:'ambiguous',intent:'ambiguous',confidence:'low',reason:'no safe deterministic route'};
}
