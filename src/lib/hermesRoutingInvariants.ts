import type { HermesDomain } from './hermesDomainClassifier';
import type { TopicBoundaryDecision } from './hermesTopicBoundary';

export const HERMES_ROUTING_INVARIANTS = [
  'Prior recommendations require an explicit follow-up reference or named entity match.',
  'Casual/identity questions start a new no-model, no-Supabase topic.',
  'Explicit domains override stale memory.',
  'Local reasoning may consume memory only after topic-boundary eligibility passes.',
  'Memory rejection is recorded with a reason.',
  'Clarification requires no page, data, memory match, domain, or safe default.',
  'Broad strategy questions create a fresh recommendation context.',
] as const;

export function findRoutingInvariantViolations(input: {
  domain: HermesDomain;
  boundary: TopicBoundaryDecision;
  usedMemory: boolean;
  usedSupabase: boolean;
  usedModel: boolean;
}): string[] {
  const violations: string[] = [];
  if (input.usedMemory && !input.boundary.shouldUsePriorMemory) violations.push('memory_used_without_eligibility');
  if (input.domain === 'casual_identity' && (input.usedMemory || input.usedSupabase || input.usedModel)) violations.push('casual_route_used_external_or_stale_context');
  if (input.boundary.domainOverrideApplied && input.usedMemory) violations.push('explicit_domain_failed_to_override_memory');
  return violations;
}
