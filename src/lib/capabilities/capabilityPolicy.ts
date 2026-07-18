import { getCapability } from './capabilityRegistry';
import type { CapabilityDataClass, CapabilityPolicyContext, CapabilityPolicyDecision, NexusCapability } from './capabilityTypes';

const roleRank: Record<CapabilityPolicyContext['actorRole'], number> = {
  unknown: 0,
  client: 1,
  client_ai: 1,
  alpha: 1,
  agent: 2,
  operator: 3,
  admin: 4,
  ray: 5,
};

function deny(decision: CapabilityPolicyDecision['decision'], reasons: string[], extra: Partial<CapabilityPolicyDecision> = {}): CapabilityPolicyDecision {
  return { allowed: false, decision, reasons, ...extra };
}

function requiredRoleForApproval(capability: NexusCapability): CapabilityPolicyContext['actorRole'] {
  if (capability.approvalLevel === 'NONE') return 'operator';
  if (capability.approvalLevel === 'OPERATOR') return 'operator';
  if (capability.approvalLevel === 'ADMIN') return 'admin';
  return 'ray';
}

export function evaluateCapabilityPolicy(capabilityId: string, context: CapabilityPolicyContext): CapabilityPolicyDecision {
  const capability = getCapability(capabilityId);
  if (!capability) return deny('UNKNOWN_CAPABILITY', [`Unknown capability: ${capabilityId}`]);

  if (capability.activationMode === 'PROHIBITED') return deny('PROHIBITED', [`${capability.name} is prohibited by policy.`]);
  if (capability.activationMode === 'BLOCKED_BY_POLICY') return deny('BLOCKED_BY_POLICY', [`${capability.name} is blocked by policy.`]);
  if (capability.activationMode === 'RETIRED') return deny('DENY', [`${capability.name} is retired.`]);
  if (capability.activationMode === 'DEFERRED') return deny('NOT_CONFIGURED', [`${capability.name} is intentionally deferred.`]);
  if (capability.activationMode === 'NOT_CONFIGURED') return deny('NOT_CONFIGURED', [`${capability.name} is not configured.`], { missingCredentials: capability.credentialRequirements });

  if (capability.activationMode === 'READ_ONLY' && !['read', 'recommend', 'propose'].includes(context.requestedAction)) {
    return deny('DENY', [`${capability.name} is read-only.`]);
  }

  if (capability.activationMode === 'TEST_ONLY' && context.environment === 'production' && context.requestedAction !== 'read') {
    return deny('DENY', [`${capability.name} is test-only and cannot execute in production.`]);
  }

  if (context.actorRole === 'alpha' && !capability.alphaMayUse) return deny('DATA_CLASS_NOT_ALLOWED', ['Alpha is not allowed to use this capability.']);
  if (context.actorRole === 'client_ai' && !capability.clientAiMayUse) return deny('DATA_CLASS_NOT_ALLOWED', ['Client-facing AI is not allowed to use this capability.']);
  if (context.actorRole === 'agent' && !capability.hermesMayExecute && ['execute', 'activate', 'write', 'install', 'disable'].includes(context.requestedAction)) {
    return deny('REQUIRES_APPROVAL', ['Agent execution is not allowed without governed approval.'], { requiredApprovalLevel: capability.approvalLevel });
  }

  const requestedClasses = context.requestedDataClasses ?? [];
  const prohibitedRequested = requestedClasses.filter((dataClass) => capability.prohibitedDataClasses.includes(dataClass));
  if (prohibitedRequested.length) {
    return deny('DATA_CLASS_NOT_ALLOWED', [`Requested data class is prohibited: ${prohibitedRequested.join(', ')}`]);
  }
  const notAllowed = requestedClasses.filter((dataClass) => !capability.allowedDataClasses.includes(dataClass) && dataClass !== 'NONE');
  if (notAllowed.length) {
    return deny('DATA_CLASS_NOT_ALLOWED', [`Requested data class is not allowed: ${notAllowed.join(', ')}`]);
  }

  const credentialReadiness = context.credentialReadiness ?? {};
  const missingCredentials = capability.credentialRequirements.filter((credential) => {
    const readiness = credentialReadiness[credential];
    return readiness === 'MISSING' || readiness === 'UNKNOWN' || (!readiness && ['execute', 'activate', 'write', 'install'].includes(context.requestedAction));
  });
  if (missingCredentials.length) return deny('CREDENTIAL_MISSING', ['Required credential readiness is missing or unknown.'], { missingCredentials });

  const dependencyHealth = context.dependencyHealth ?? {};
  const missingDependencies = capability.dependencies.filter((dependency) => ['BLOCKED', 'NOT_CONFIGURED', 'PROHIBITED', 'UNKNOWN', 'STALE'].includes(dependencyHealth[dependency] ?? 'HEALTHY'));
  if (missingDependencies.length && ['execute', 'activate', 'write', 'install'].includes(context.requestedAction)) {
    return deny('DEPENDENCY_UNHEALTHY', ['One or more dependencies are not healthy enough for execution.'], { missingDependencies });
  }

  if (context.costWithinLimit === false) return deny('COST_LIMIT_EXCEEDED', ['Capability cost policy is not within approved limit.']);

  const requiredRole = requiredRoleForApproval(capability);
  if (roleRank[context.actorRole] < roleRank[requiredRole] && ['execute', 'activate', 'write', 'install', 'disable'].includes(context.requestedAction)) {
    return deny('REQUIRES_APPROVAL', [`${capability.name} requires ${capability.approvalLevel} approval.`], { requiredApprovalLevel: capability.approvalLevel });
  }

  if (capability.approvalLevel !== 'NONE' && capability.activationMode === 'APPROVAL_GATED' && context.approvalState !== 'APPROVED' && ['execute', 'activate', 'write', 'install', 'disable'].includes(context.requestedAction)) {
    return deny('REQUIRES_APPROVAL', [`${capability.name} is approval-gated and does not have approved state.`], { requiredApprovalLevel: capability.approvalLevel });
  }

  if (capability.approvalLevel === 'LEGAL_AND_RAY') return deny('PROHIBITED', [`${capability.name} requires a separate legal and Ray decision.`], { requiredApprovalLevel: capability.approvalLevel });

  return { allowed: true, decision: 'ALLOW', reasons: [`${capability.name} policy check passed for ${context.requestedAction}.`] };
}

export function canDataClassUseCapability(capabilityId: string, dataClass: CapabilityDataClass, actorRole: CapabilityPolicyContext['actorRole']): boolean {
  return evaluateCapabilityPolicy(capabilityId, {
    actorRole,
    environment: 'test',
    requestedAction: 'read',
    requestedDataClasses: [dataClass],
  }).allowed;
}
