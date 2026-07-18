import { getCapabilityRegistry } from './capabilityRegistry';
import type { CapabilityHealthStatus, CredentialRequirement, NexusCapability } from './capabilityTypes';

export interface CapabilityHealthRecord {
  capabilityId: string;
  status: CapabilityHealthStatus;
  source: string;
  observedAt?: string;
  freshness?: string;
  summary: string;
  impact?: string;
  remediation?: string;
}

export function getCapabilityHealthRecords(capabilities: NexusCapability[] = getCapabilityRegistry()): CapabilityHealthRecord[] {
  return capabilities.map((capability) => ({
    capabilityId: capability.capabilityId,
    status: capability.healthStatus,
    source: capability.healthSource,
    observedAt: capability.lastVerifiedAt,
    freshness: capability.healthFreshness,
    summary: `${capability.name}: ${capability.healthStatus}`,
    impact: capability.notes ?? capability.description,
    remediation: capability.healthStatus === 'HEALTHY' ? 'Maintain current controls.' : capability.disablePlan,
  }));
}

export function credentialReadinessFor(capability: NexusCapability): CredentialRequirement[] {
  if (!capability.credentialRequirements.length) {
    return [{
      credentialId: 'NONE',
      required: false,
      environment: 'none',
      readiness: 'NOT_REQUIRED',
      owner: capability.departmentId,
      rotationRequirement: 'Not applicable',
      secretLocationCategory: 'Not applicable',
    }];
  }
  return capability.credentialRequirements.map((credentialId) => ({
    credentialId,
    required: true,
    environment: credentialId.startsWith('VITE_') ? 'browser' : credentialId.includes('SERVICE_ROLE') || credentialId.includes('SECRET') ? 'server' : credentialId.includes('MCP') ? 'external_host' : 'local_operator',
    readiness: capability.activationMode === 'DEFERRED' ? 'DEFERRED' : capability.activationMode === 'PROHIBITED' || capability.activationMode === 'BLOCKED_BY_POLICY' ? 'PROHIBITED' : capability.activationMode === 'NOT_CONFIGURED' ? 'MISSING' : 'UNKNOWN',
    owner: capability.departmentId,
    rotationRequirement: credentialId === 'NONE' ? 'Not applicable' : 'Rotate through approved platform owner; never commit values.',
    secretLocationCategory: credentialId.startsWith('VITE_') ? 'frontend public environment, non-secret only' : 'server/edge/local protected environment',
  }));
}

export function getCapabilitiesWithMissingCredentials(capabilities: NexusCapability[] = getCapabilityRegistry()): NexusCapability[] {
  return capabilities.filter((capability) => credentialReadinessFor(capability).some((credential) => credential.required && credential.readiness === 'MISSING'));
}

export function getDependencyMap(capabilities: NexusCapability[] = getCapabilityRegistry()): Record<string, string[]> {
  return capabilities.reduce<Record<string, string[]>>((acc, capability) => {
    acc[capability.capabilityId] = [...capability.dependencies];
    return acc;
  }, {});
}
