import type { RouteDecision } from './hermesRouteDecision';
import type { ConversationItem } from './hermesConversationState';

export interface HermesHandlerResult {
  userAnswer: string; internalTrace: string; selectedEntities: ConversationItem[];
  sources: string[]; nextActions: string[]; safeFallbackAnswer?: string;
}

const DIAGNOSTIC_LEAK = /I detected the general domain|Domain override applied|memory eligibility|\binvariant\b|routing trace/i;

export function renderHermesAnswer(result: HermesHandlerResult, decision: RouteDecision): { text: string; diagnosticSuppressed: boolean } {
  if (decision.diagnosticsPolicy === 'show_full_trace') return { text: `${result.userAnswer}\n\n${result.internalTrace}`, diagnosticSuppressed: false };
  if (decision.diagnosticsPolicy === 'show_summary') return { text: result.userAnswer, diagnosticSuppressed: false };
  if (DIAGNOSTIC_LEAK.test(result.userAnswer)) return { text: result.safeFallbackAnswer || 'I could not produce a policy-compliant answer from the allowed context. Name the target or open the relevant section.', diagnosticSuppressed: true };
  return { text: result.userAnswer, diagnosticSuppressed: false };
}

export function containsDiagnosticLeak(text: string): boolean { return DIAGNOSTIC_LEAK.test(text); }
