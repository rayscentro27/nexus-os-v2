export type ActivationLevel = 0 | 1 | 2 | 3 | 4 | 5 | 6;
export type MemoryPolicy = 'none' | 'last_trace_only' | 'selection_only' | 'long_term_allowed' | 'selection_and_long_term';
export type RetrievalPolicy = 'none' | 'supabase_first' | 'local_reports' | 'local_reports_then_supabase' | 'supabase_then_static_fallback' | 'static_fallback_allowed';
export type ModelPolicy = 'forbidden' | 'allowed_if_needed' | 'required';
export type DiagnosticsPolicy = 'hidden' | 'show_summary' | 'show_full_trace';
export type ActionPolicy = 'none' | 'approval_required' | 'blocked';

export interface RouteDecision {
  routeId: string;
  activationLevel: ActivationLevel;
  domain: string;
  intent: string;
  confidence: number;
  memoryPolicy: MemoryPolicy;
  retrievalPolicy: RetrievalPolicy;
  modelPolicy: ModelPolicy;
  diagnosticsPolicy: DiagnosticsPolicy;
  actionPolicy: ActionPolicy;
  reason: string;
  allowedContext: {
    lastTrace: boolean; selectionMemory: boolean; longTermMemory: boolean;
    supabase: boolean; localReports: boolean; staticFallback: boolean;
    model: boolean; routingDiagnostics: boolean;
  };
  blockedContext: string[];
}

export type RouteDecisionInput = Omit<RouteDecision, 'allowedContext' | 'blockedContext' | 'confidence'> & {
  confidence?: number;
  allowedContext?: Partial<RouteDecision['allowedContext']>;
  blockedContext?: string[];
};

export function createRouteDecision(input: RouteDecisionInput): RouteDecision {
  const allowedContext: RouteDecision['allowedContext'] = {
    lastTrace: input.memoryPolicy === 'last_trace_only',
    selectionMemory: input.memoryPolicy === 'selection_only' || input.memoryPolicy === 'selection_and_long_term',
    longTermMemory: input.memoryPolicy === 'long_term_allowed' || input.memoryPolicy === 'selection_and_long_term',
    supabase: ['supabase_first', 'local_reports_then_supabase', 'supabase_then_static_fallback'].includes(input.retrievalPolicy),
    localReports: ['local_reports', 'local_reports_then_supabase'].includes(input.retrievalPolicy),
    staticFallback: ['supabase_then_static_fallback', 'static_fallback_allowed'].includes(input.retrievalPolicy),
    model: input.modelPolicy !== 'forbidden',
    routingDiagnostics: input.diagnosticsPolicy !== 'hidden',
    ...input.allowedContext,
  };
  const blockedContext = input.blockedContext || Object.entries(allowedContext).filter(([, allowed]) => !allowed).map(([name]) => name);
  const decision: RouteDecision = { ...input, confidence: Math.max(0, Math.min(1, input.confidence ?? 0.9)), allowedContext, blockedContext };
  assertRouteDecisionIntegrity(decision);
  return decision;
}

export function explainRouteDecision(decision: RouteDecision): string {
  return `${decision.routeId} selected Level ${decision.activationLevel} for ${decision.domain}/${decision.intent}. Memory=${decision.memoryPolicy}; retrieval=${decision.retrievalPolicy}; model=${decision.modelPolicy}; diagnostics=${decision.diagnosticsPolicy}; action=${decision.actionPolicy}. ${decision.reason}`;
}
export function isMemoryAllowed(decision: RouteDecision, kind: 'trace' | 'selection' | 'long_term' = 'selection'): boolean {
  return kind === 'trace' ? decision.allowedContext.lastTrace : kind === 'long_term' ? decision.allowedContext.longTermMemory : decision.allowedContext.selectionMemory;
}
export function isSupabaseAllowed(decision: RouteDecision): boolean { return decision.allowedContext.supabase; }
export function isModelAllowed(decision: RouteDecision): boolean { return decision.allowedContext.model; }
export function isDiagnosticsAllowed(decision: RouteDecision): boolean { return decision.allowedContext.routingDiagnostics; }
export function isActionApprovalRequired(decision: RouteDecision): boolean { return decision.actionPolicy === 'approval_required'; }

export function assertRouteDecisionIntegrity(decision: RouteDecision): true {
  const errors: string[] = [];
  if (decision.modelPolicy === 'forbidden' && decision.allowedContext.model) errors.push('forbidden model cannot be allowed');
  if (decision.retrievalPolicy === 'none' && (decision.allowedContext.supabase || decision.allowedContext.localReports)) errors.push('retrieval none cannot allow retrieval');
  if (decision.memoryPolicy === 'none' && (decision.allowedContext.lastTrace || decision.allowedContext.selectionMemory || decision.allowedContext.longTermMemory)) errors.push('memory none cannot allow memory');
  if (decision.memoryPolicy === 'last_trace_only' && (decision.allowedContext.selectionMemory || decision.allowedContext.longTermMemory)) errors.push('last_trace_only cannot attach broad memory');
  if (decision.actionPolicy === 'blocked' && decision.activationLevel !== 0) errors.push('blocked action must use Level 0');
  if (decision.diagnosticsPolicy === 'hidden' && decision.allowedContext.routingDiagnostics) errors.push('hidden diagnostics cannot be attached');
  if (errors.length) throw new Error(`Invalid Hermes RouteDecision: ${errors.join('; ')}`);
  return true;
}
