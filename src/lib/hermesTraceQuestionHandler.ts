import { getLastRoutingTrace, type RoutingTraceEntry } from './hermesRoutingTrace';
import { getCapabilityReport } from './hermesCapabilityStatus';
import type { RouteDecision } from './hermesRouteDecision';

export type TraceQuestionKind = 'source' | 'supabase' | 'model' | 'strategic_reasoning' | 'domain' | 'route' | 'memory' | 'why' | 'unknown';
export type TraceTarget = 'last_answer' | 'current_question' | 'general_capability';

export interface TraceQuestionClassification { kind: TraceQuestionKind; target: TraceTarget; }

export function classifyTraceQuestion(message: string): TraceQuestionClassification | null {
  const lower = message.toLowerCase();
  if (/\b(where\s+(?:did|does|are).*?(?:answer|response|that|this|source)|what\s+source|where\s+did\s+that\s+come\s+from)\b/.test(lower)) return { kind: 'source', target: /your questions|answers generally|in general/.test(lower) ? 'general_capability' : 'last_answer' };
  if (/\b(?:did|are)\s+(?:that|you).*?(?:supabase|database)|\busing\s+(?:supabase|the database)\b|why.*not use.*(?:supabase|database)/.test(lower)) return { kind: 'supabase', target: /did that|last answer|that answer|why/.test(lower) ? 'last_answer' : 'general_capability' };
  if (/\bstrategic reasoning|reasoning route|local reasoning|model reasoning\b/.test(lower)) return { kind: 'strategic_reasoning', target: 'last_answer' };
  if (/\b(?:did|are)\s+(?:that|you).*?(?:model|ai)|\busing\s+(?:a model|ai)\b|why.*not use.*(?:model|ai)/.test(lower)) return { kind: 'model', target: 'last_answer' };
  if (/\bwhat\s+domain\s+did\b/.test(lower)) return { kind: 'domain', target: /this question/.test(lower) ? 'current_question' : 'last_answer' };
  if (/\bwhat\s+route\s+did|where\s+did\s+(?:that|it)\s+route|what was allowed|what context was allowed\b/.test(lower)) return { kind: 'route', target: 'last_answer' };
  if (/\b(?:did|why did)\s+you.*memory|previous recommendation\b/.test(lower)) return { kind: 'memory', target: 'last_answer' };
  if (/\bwhy\s+did\s+you\s+answer\b/.test(lower)) return { kind: 'why', target: 'last_answer' };
  return null;
}

function traceSummary(trace: RoutingTraceEntry): string {
  return `- Source: ${trace.sourceDecision}\n- Route: ${trace.routeDecision?.routeId || trace.route}\n- Activation level: ${trace.activationLevel} (${trace.activationLevelName})\n- Domain: ${trace.detectedDomain}\n- Memory policy: ${trace.memoryPolicyApplied || 'not recorded'}; ${trace.memoryUsed ? 'used' : trace.memoryRejected ? `rejected — ${trace.memoryRejectionReason}` : 'not used'}\n- Retrieval policy: ${trace.retrievalPolicyApplied || 'not recorded'}\n- Supabase: ${trace.usedSupabase ? `used (${trace.supabaseTables.join(', ') || 'table not recorded'})` : 'not used'}\n- Model policy: ${trace.modelPolicyApplied || 'not recorded'}; ${trace.usedModel ? `used (${trace.modelRoute})` : 'not used'}\n- Answer builder: ${trace.finalAnswerHandler || trace.answerBuilder}`;
}

export function answerHermesTraceQuestion(message: string, trace: RoutingTraceEntry | null = getLastRoutingTrace(), policy?: { routeDecision: RouteDecision }): string | null {
  if (policy && policy.routeDecision.memoryPolicy !== 'last_trace_only') throw new Error('Trace handler requires last_trace_only policy');
  const classification = classifyTraceQuestion(message);
  if (!classification) return null;
  const capability = getCapabilityReport();
  if (!trace) {
    if (classification.kind === 'supabase') return `For my last answer: no routing trace is available. In general: ${capability.supabase.userFacing}`;
    return 'I do not have a routing trace for the previous Hermes answer yet.';
  }
  switch (classification.kind) {
    case 'source':
      return `For my last non-trace answer, the routing record says:\n\n${traceSummary(trace)}${classification.target === 'general_capability' ? `\n\nIn general, I answer from eligible conversation context, local reports/page data, authenticated Supabase reads when a question requires records, and the model only when the selected route actually calls it.` : ''}`;
    case 'supabase':
      return `For my last answer: ${trace.usedSupabase ? `yes — I used ${trace.supabaseTables.join(', ') || 'a recorded Supabase source'}.` : `no — it came from ${trace.sourceDecision}, not Supabase.`}\n\nIn general: ${capability.supabase.userFacing} Supported read paths include business_opportunities, monetization_opportunities, approvals, task_requests, research_sources, and client_profiles when authentication and RLS permit them.`;
    case 'model':
      return trace.usedModel ? `Yes. The last answer used model route ${trace.modelRoute}.` : `No. The last answer used ${trace.modelRoute} from ${trace.sourceDecision}; no model call was made.`;
    case 'strategic_reasoning':
      {
        const reasoningRoute = trace.route === 'local_reasoning' || trace.questionType === 'domain_reasoning' || trace.finalAnswerHandler?.includes('reason') || trace.finalAnswerHandler?.startsWith('trading_') ? 'local_reasoning' : trace.modelRoute;
        return `The last answer used **${reasoningRoute}**. Model used: ${trace.usedModel ? 'yes' : 'no'}. Supabase used: ${trace.usedSupabase ? 'yes' : 'no'}. I chose that route because ${reasoningRoute === 'local_reasoning' ? 'the available domain context was sufficient for local reasoning' : trace.correctnessHint}.`;
      }
    case 'domain':
      return classification.target === 'current_question' ? 'This question is a source_trace diagnostic.' : `For your last non-trace question, I detected **${trace.detectedDomain}**.`;
    case 'route':
      return `The last answer used ${trace.route} at activation level ${trace.activationLevel}, with ${trace.modelRoute}. Final handler: ${trace.finalAnswerHandler || trace.answerBuilder}. Allowed context: ${Object.entries(trace.allowedContext || {}).filter(([, allowed]) => allowed).map(([name]) => name).join(', ') || 'none'}. Blocked context: ${(trace.blockedContext || []).join(', ') || 'none'}.`;
    case 'memory':
      if (trace.memoryUsed) return `Yes. Memory was eligible and used${trace.selectedEntity ? ` for ${trace.selectedEntity}` : ''}.`;
      return `No. Prior memory was not used.${trace.memoryRejected ? ` Reason: ${trace.memoryRejectionReason}` : ''}`;
    case 'why':
      return `I used ${trace.finalAnswerHandler || trace.answerBuilder} because the router detected ${trace.detectedDomain} and selected activation level ${trace.activationLevel}.\n\n${traceSummary(trace)}`;
    default:
      return null;
  }
}
