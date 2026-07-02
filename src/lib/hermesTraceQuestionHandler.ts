import { getLastRoutingTrace, type RoutingTraceEntry } from './hermesRoutingTrace';
import { answerModelCapabilityWithoutTrace, getCapabilityReport } from './hermesCapabilityStatus';
import type { RouteDecision } from './hermesRouteDecision';

export type TraceQuestionKind = 'source' | 'source_reason' | 'supabase' | 'model' | 'strategic_reasoning' | 'domain' | 'route' | 'memory' | 'why' | 'action_proof' | 'unknown';
export type TraceTarget = 'last_answer' | 'current_question' | 'general_capability';

export interface TraceQuestionClassification { kind: TraceQuestionKind; target: TraceTarget; }

export function classifyTraceQuestion(message: string): TraceQuestionClassification | null {
  const lower = message.toLowerCase();
  if (/\bwhat did you get (?:that|this|the) (?:last )?(?:answer|response) from\b|\bwhat part of your decision[- ]making process did you use\b|\bhow did you decide (?:that|this)\b/.test(lower)) return { kind: /decision[- ]making|how did you decide/.test(lower) ? 'why' : 'source', target: 'last_answer' };
  if (/\b(full trace|full routing trace|technical route|debug route|exact routedecision)\b/.test(lower)) return { kind: 'route', target: 'last_answer' };
  if (/\b(?:did that|was that|did you).*(?:saved record|actual(?:ly)? (?:saved|created)|only a draft|task request)\b/.test(lower)) return { kind: 'action_proof', target: 'last_answer' };
  if (/\bwhy\b.*\b(?:using|use|used|from|was|wasn['’]?t|not use)\b.*\b(?:local|source|live data|static fallback|fallback|supabase|model|memory)\b|\b(?:why local|so why local|why that source|why no live data)\b/i.test(lower)) return { kind: 'source_reason', target: 'last_answer' };
  if (/\b(where\s+(?:did|does|are).*?(?:answer|response|that|this|source)|what\s+source|where\s+did\s+that\s+come\s+from)\b/.test(lower)) return { kind: 'source', target: /your questions|answers generally|in general/.test(lower) ? 'general_capability' : 'last_answer' };
  if (/\b(?:did|are)\s+(?:that|you).*?(?:supabase|database)|\busing\s+(?:supabase|the database)\b|why.*not use.*(?:supabase|database)/.test(lower)) return { kind: 'supabase', target: /did that|last answer|that answer|why/.test(lower) ? 'last_answer' : 'general_capability' };
  if (/\bstrategic reasoning|reasoning route|local reasoning|model reasoning\b/.test(lower)) return { kind: 'strategic_reasoning', target: 'last_answer' };
  if (/\bwhat (?:model|ai) (?:did|does|do|are|is|was)|what model did that answer use\b/.test(lower)) return { kind: 'model', target: 'last_answer' };
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

function sourceName(trace: RoutingTraceEntry): string {
  if (trace.route === 'fallback_clarification' || trace.finalAnswerHandler === 'fallback_clarification') return 'an unresolved routing fallback, not verified Nexus data';
  if (trace.memoryUsed && trace.selectedEntity) return `our conversation follow-up memory for ${trace.selectedEntity}`;
  if (trace.usedSupabase) return `live Supabase data${trace.supabaseTables.length ? ` from ${trace.supabaseTables.join(', ')}` : ''}`;
  if (trace.usedModel) return `the model through ${trace.modelRoute}`;
  if (trace.sourceDecision === 'reasoning') return 'local reasoning and the allowed domain context';
  if (trace.sourceDecision === 'local') return 'local Nexus context';
  return trace.sourceDecision;
}

function assumptionsFrom(trace: RoutingTraceEntry): string {
  if (trace.usedSupabase) return 'No static-record assumption replaced the live read; authentication and RLS still limit completeness.';
  if (trace.sourceDecision === 'reasoning') return 'The answer used local reasoning and the assumptions stated or implied by that renderer.';
  if (trace.sourceDecision === 'local') return 'The answer relied on local or report-backed context and did not verify current production state.';
  return 'No additional assumptions were recorded.';
}

export function formatTraceForUser(trace: RoutingTraceEntry, mode: 'plain_summary' | 'compact_technical' | 'full_trace' = 'plain_summary'): string {
  if (mode === 'full_trace') return `Full routing trace:\n\n${traceSummary(trace)}\n- Decision reason: ${trace.routeDecision?.reason || trace.correctnessHint}\n- Allowed context: ${Object.entries(trace.allowedContext || {}).filter(([, value]) => value).map(([key]) => key).join(', ') || 'none'}\n- Blocked context: ${(trace.blockedContext || []).join(', ') || 'none'}`;
  if (mode === 'compact_technical') return `Route: ${trace.route.replace(/_/g, ' ')} · Level ${trace.activationLevel} · Domain: ${trace.detectedDomain} · Source: ${sourceName(trace)}.`;
  return `The routing record shows that answer came from ${sourceName(trace)}. I ${trace.memoryUsed ? 'used eligible conversation memory' : 'did not use selection memory'}, ${trace.usedSupabase ? 'used Supabase' : 'did not use Supabase'}, and ${trace.usedModel ? 'used the model' : 'did not use the model'}.`;
}

export function answerHermesTraceQuestion(message: string, trace: RoutingTraceEntry | null = getLastRoutingTrace(), policy?: { routeDecision: RouteDecision }): string | null {
  if (policy && policy.routeDecision.memoryPolicy !== 'last_trace_only') throw new Error('Trace handler requires last_trace_only policy');
  const classification = classifyTraceQuestion(message);
  if (!classification) return null;
  const capability = getCapabilityReport();
  if (!trace) {
    if (classification.kind === 'supabase') return `For my last answer: no routing trace is available. In general: ${capability.supabase.userFacing}`;
    if (classification.kind === 'model' || classification.kind === 'strategic_reasoning') return answerModelCapabilityWithoutTrace();
    return 'I do not have a routing trace for the previous Hermes answer yet.';
  }
  const fullTraceRequested = /\b(full trace|full routing trace|technical route|debug route|exact routedecision)\b/i.test(message);
  if (fullTraceRequested) return formatTraceForUser(trace, 'full_trace');
  switch (classification.kind) {
    case 'source':
      return `${formatTraceForUser(trace)}\n\n- Intent/route: ${trace.intent} / ${trace.route}\n- Sources/context: ${(trace.handlerResultSummary?.sources as string[] | undefined)?.join(', ') || trace.sourceDecision}\n- Live Supabase read: ${trace.usedSupabase ? `yes (${trace.supabaseTables.join(', ') || 'table not recorded'})` : 'no'}\n- Assumptions: ${assumptionsFrom(trace)}\n- Confidence: ${trace.confidence}\n- To improve certainty: ${trace.usedSupabase ? 'verify source freshness and any partial table errors' : 'run the approved current source read if the question depends on live operational state'}.\n\n${formatTraceForUser(trace, 'compact_technical')}${classification.target === 'general_capability' ? `\n\nIn general, I answer from eligible conversation context, local reports/page data, authenticated Supabase reads when records are required, and the model only when the route permits it.` : ''}`;
    case 'source_reason':
      if (trace.usedSupabase) return `For the last answer, I used Supabase because the question required supported live records from ${trace.supabaseTables.join(', ') || 'the authenticated data source'}. ${trace.usedModel ? 'The model was also used where the route allowed it.' : 'No model was needed.'}`;
      return `For the last answer, I used ${sourceName(trace)} because ${trace.routeDecision?.reason || trace.correctnessHint} Supabase is reserved for supported live-record questions, and ${trace.usedModel ? 'the model was used by that route.' : 'no model was needed.'}`;
    case 'supabase':
      return `For my last answer: ${trace.usedSupabase ? `yes — I used ${trace.supabaseTables.join(', ') || 'a recorded Supabase source'}.` : `no — it came from ${trace.sourceDecision}, not Supabase.`}\n\nIn general: ${capability.supabase.userFacing} Supported read paths include business_opportunities, monetization_opportunities, approvals, task_requests, research_sources, and client_profiles when authentication and RLS permit them.`;
    case 'model':
      return trace.usedModel ? `Yes. The last answer used model route ${trace.modelRoute}. ${capability.liveModel.userFacing}` : `No. The last answer used ${trace.modelRoute} from ${trace.sourceDecision}; no model call was made. ${capability.liveModel.userFacing}`;
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
      return `I used the ${trace.route} route for the ${trace.intent} intent. Sources/context: ${(trace.handlerResultSummary?.sources as string[] | undefined)?.join(', ') || trace.sourceDecision}. Live Supabase read: ${trace.usedSupabase ? 'yes' : 'no'}. Assumptions: ${assumptionsFrom(trace)} Confidence: ${trace.confidence}. This is a decision summary, not hidden chain-of-thought. To improve certainty, ${trace.usedSupabase ? 'check record freshness and partial failures.' : 'verify any time-sensitive claim against its approved live source.'}`;
    case 'action_proof': {
      const proof = trace.handlerResultSummary?.actionProof as { outcome?: string; id?: string; status?: string; title?: string; reason?: string } | null | undefined;
      if (!proof) return 'The last answer does not contain proof of a saved record or task request, so I cannot claim that anything was created.';
      if (proof.outcome === 'actual_record_created') return `Yes. A Ray Review record was created${proof.title ? ` for ${proof.title}` : ''} · status: ${proof.status || 'created'} · id: ${proof.id || 'not recorded'}. No external action was executed.`;
      if (proof.outcome === 'approval_task_created') return `An approval-gated task request was created${proof.title ? ` for ${proof.title}` : ''} · status: ${proof.status || 'pending'} · id: ${proof.id || 'not recorded'}. No external action was executed.`;
      if (proof.outcome === 'blocked') return `No record was created. The action was blocked because ${proof.reason || 'the required target or approval was missing'}.`;
      return 'It was a draft prepared in this conversation only. It was not saved, submitted, or activated.';
    }
    default:
      return null;
  }
}
