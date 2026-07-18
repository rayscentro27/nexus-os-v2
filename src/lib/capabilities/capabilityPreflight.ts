import { evaluateCapabilityPolicy } from './capabilityPolicy';
import type { CapabilityPolicyContext, CapabilityPreflightResult } from './capabilityTypes';

function eventActionFor(decision: CapabilityPreflightResult['decision']): CapabilityPreflightResult['event']['action'] {
  if (decision === 'ALLOW') return 'CAPABILITY_PREFLIGHT_PASSED';
  if (decision === 'REQUIRES_APPROVAL') return 'CAPABILITY_APPROVAL_REQUIRED';
  if (decision === 'DEPENDENCY_UNHEALTHY') return 'CAPABILITY_DEPENDENCY_BLOCKED';
  if (decision === 'CREDENTIAL_MISSING') return 'CAPABILITY_CREDENTIAL_MISSING';
  if (decision === 'DATA_CLASS_NOT_ALLOWED') return 'CAPABILITY_DATA_POLICY_DENIED';
  if (decision === 'COST_LIMIT_EXCEEDED') return 'CAPABILITY_COST_POLICY_DENIED';
  if (decision === 'NOT_CONFIGURED' || decision === 'BLOCKED_BY_POLICY' || decision === 'PROHIBITED') return 'CAPABILITY_DISABLED';
  return 'CAPABILITY_PREFLIGHT_DENIED';
}

export function runCapabilityPreflight(capabilityId: string, context: CapabilityPolicyContext): CapabilityPreflightResult {
  const decision = evaluateCapabilityPolicy(capabilityId, context);
  return {
    capabilityId,
    ...decision,
    event: {
      action: eventActionFor(decision.decision),
      capabilityId,
      summary: decision.reasons.join(' '),
      sanitized: true,
    },
  };
}

export function describePreflightBlock(result: CapabilityPreflightResult): string {
  if (result.allowed) return `${result.capabilityId} is allowed.`;
  const missingCredentials = result.missingCredentials?.length ? ` Missing credentials: ${result.missingCredentials.join(', ')}.` : '';
  const missingDependencies = result.missingDependencies?.length ? ` Blocked dependencies: ${result.missingDependencies.join(', ')}.` : '';
  return `${result.capabilityId} blocked: ${result.decision}. ${result.reasons.join(' ')}${missingCredentials}${missingDependencies}`;
}
