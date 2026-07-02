import type { RouteDecision } from './hermesRouteDecision';
import type { ConversationState } from './hermesConversationState';
import { evaluateMemoryEligibility } from './hermesMemoryEligibility';
import { getLastTurnTraceMemory, getLongTermBusinessContext, getSelectionMemory } from './hermesMemoryStores';
import { getLastRoutingTrace } from './hermesRoutingTrace';
import { getAdvisoryContinuity } from './hermesAdvisoryContinuity';
import { getFallbackContinuity } from './hermesFallbackContinuity';

export interface HermesContextPacket {
  message: string; routeDecision: RouteDecision; pageContext: Record<string, unknown> | null;
  lastTrace: ReturnType<typeof getLastTurnTraceMemory>; selectionMemory: ReturnType<typeof getSelectionMemory> | null;
  routingTrace: ReturnType<typeof getLastRoutingTrace>;
  longTermBusinessContext: ReturnType<typeof getLongTermBusinessContext> | null;
  advisoryContinuity: ReturnType<typeof getAdvisoryContinuity>;
  fallbackContinuity: ReturnType<typeof getFallbackContinuity>;
  retrieval: { supabaseAllowed: boolean; localReportsAllowed: boolean; staticFallbackAllowed: boolean };
  modelAllowed: boolean; memoryEligibility: ReturnType<typeof evaluateMemoryEligibility>;
  summary: Record<string, unknown>;
}

export function buildContextPacket(input: { routeDecision: RouteDecision; message: string; session?: unknown; pageContext?: Record<string, unknown> | null; conversationState: ConversationState }): HermesContextPacket {
  const selection = getSelectionMemory();
  const trace = getLastTurnTraceMemory();
  const eligibility = evaluateMemoryEligibility({ message: input.message, routeDecision: input.routeDecision, detectedDomain: input.routeDecision.domain, previousSelectionMemory: selection, previousTraceMemory: trace });
  const packet: HermesContextPacket = {
    message: input.message, routeDecision: input.routeDecision,
    pageContext: input.pageContext || null,
    lastTrace: input.routeDecision.allowedContext.lastTrace ? trace : null,
    routingTrace: input.routeDecision.allowedContext.lastTrace ? getLastRoutingTrace() : null,
    selectionMemory: input.routeDecision.allowedContext.selectionMemory && eligibility.selectionAllowed ? selection : null,
    longTermBusinessContext: input.routeDecision.allowedContext.longTermMemory ? getLongTermBusinessContext() : null,
    advisoryContinuity: input.routeDecision.allowedContext.longTermMemory ? getAdvisoryContinuity() : null,
    fallbackContinuity: input.routeDecision.allowedContext.longTermMemory ? getFallbackContinuity() : null,
    retrieval: { supabaseAllowed: input.routeDecision.allowedContext.supabase, localReportsAllowed: input.routeDecision.allowedContext.localReports, staticFallbackAllowed: input.routeDecision.allowedContext.staticFallback },
    modelAllowed: input.routeDecision.allowedContext.model,
    memoryEligibility: eligibility,
    summary: {},
  };
  packet.summary = {
    lastTraceAttached: Boolean(packet.lastTrace || packet.routingTrace), selectionMemoryAttached: Boolean(packet.selectionMemory),
    longTermMemoryAttached: Boolean(packet.longTermBusinessContext), advisoryContinuityAttached: Boolean(packet.advisoryContinuity), fallbackContinuityAttached: Boolean(packet.fallbackContinuity), pageContextAttached: Boolean(packet.pageContext),
    supabaseAllowed: packet.retrieval.supabaseAllowed, localReportsAllowed: packet.retrieval.localReportsAllowed,
    staticFallbackAllowed: packet.retrieval.staticFallbackAllowed, modelAllowed: packet.modelAllowed,
    blockedContext: input.routeDecision.blockedContext,
  };
  return packet;
}
