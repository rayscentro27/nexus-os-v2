import { describe, expect, it } from 'vitest';
import { buildCapabilityOSSummary, buildCapabilityProposalsFromRepoIntelligence, getCapability, getCapabilityRegistry } from '../src/lib/capabilities/capabilityRegistry';
import { getCapabilitiesWithMissingCredentials, getCapabilityHealthRecords } from '../src/lib/capabilities/capabilityHealth';
import { evaluateCapabilityPolicy } from '../src/lib/capabilities/capabilityPolicy';
import { describePreflightBlock, runCapabilityPreflight } from '../src/lib/capabilities/capabilityPreflight';

describe('Capability OS registry', () => {
  it('registers required Nexus capabilities with unique IDs and governance fields', () => {
    const capabilities = getCapabilityRegistry();
    const ids = capabilities.map((capability) => capability.capabilityId);
    expect(new Set(ids).size).toBe(ids.length);
    [
      'executive_command_center',
      'hermes_executive_advisor',
      'alpha_supabase_access_prohibition',
      'document_upload',
      'bounded_document_worker',
      'stripe_test_checkout',
      'live_stripe',
      'task_requests',
      'approvals',
      'agent_jobs',
      'nexus_events',
      'repo_intelligence_registry',
      'github_mcp_reader',
      'github_mcp_writer',
      'live_trading',
    ].forEach((id) => expect(ids).toContain(id));
    for (const capability of capabilities) {
      expect(capability.departmentId).toBeTruthy();
      expect(capability.healthSource).toBeTruthy();
      expect(capability.rollbackPlan || capability.disablePlan).toBeTruthy();
      expect(capability.allowedDataClasses.filter((dataClass) => capability.prohibitedDataClasses.includes(dataClass))).toEqual([]);
      if (capability.activationMode === 'APPROVAL_GATED') expect(capability.approvalLevel).not.toBe('NONE');
      if (capability.sourceType !== 'NEXUS_NATIVE') expect(capability.costModel).toBeTruthy();
    }
  });

  it('classifies intentionally unsafe or deferred capabilities correctly', () => {
    expect(getCapability('live_stripe')).toMatchObject({ activationMode: 'DEFERRED', approvalLevel: 'RAY_EXPLICIT', rayApprovalState: 'DEFERRED' });
    expect(getCapability('live_trading')).toMatchObject({ activationMode: 'BLOCKED_BY_POLICY', healthStatus: 'PROHIBITED' });
    expect(getCapability('alpha_supabase_access_prohibition')).toMatchObject({ activationMode: 'PROHIBITED', alphaMayUse: false });
  });

  it('summarizes capability counts for Executive visibility', () => {
    const summary = buildCapabilityOSSummary();
    expect(summary.total).toBeGreaterThan(50);
    expect(summary.byActivationMode.ACTIVE).toBeGreaterThan(0);
    expect(summary.approvalGated).toBeGreaterThan(0);
    expect(summary.proposals.length).toBeGreaterThan(0);
    expect(summary.missingCredentials).toBeGreaterThan(0);
  });

  it('creates health and credential metadata without storing values', () => {
    const health = getCapabilityHealthRecords();
    expect(health.find((item) => item.capabilityId === 'live_stripe')?.status).toBe('DEFERRED');
    const missingCredentialCaps = getCapabilitiesWithMissingCredentials();
    expect(missingCredentialCaps.some((item) => item.capabilityId === 'github_mcp_reader')).toBe(true);
    expect(JSON.stringify(missingCredentialCaps)).not.toMatch(/sk_live_|whsec_|password-value/i);
  });
});

describe('Capability policy and preflight', () => {
  it('allows an active read under the correct actor and data class', () => {
    const decision = evaluateCapabilityPolicy('executive_command_center', {
      actorRole: 'admin',
      environment: 'production',
      requestedAction: 'read',
      requestedDataClasses: ['INTERNAL_METADATA'],
    });
    expect(decision).toMatchObject({ allowed: true, decision: 'ALLOW' });
  });

  it('denies prohibited and policy-blocked capabilities', () => {
    expect(evaluateCapabilityPolicy('alpha_supabase_access_prohibition', { actorRole: 'alpha', environment: 'test', requestedAction: 'read', requestedDataClasses: ['CLIENT_PII'] }).decision).toBe('PROHIBITED');
    expect(evaluateCapabilityPolicy('live_trading', { actorRole: 'ray', environment: 'production', requestedAction: 'execute' }).decision).toBe('BLOCKED_BY_POLICY');
  });

  it('blocks deferred and test-only execution in unsafe contexts', () => {
    expect(evaluateCapabilityPolicy('live_stripe', { actorRole: 'ray', environment: 'production', requestedAction: 'activate' }).decision).toBe('NOT_CONFIGURED');
    expect(evaluateCapabilityPolicy('stripe_test_checkout', { actorRole: 'admin', environment: 'production', requestedAction: 'execute' }).decision).toBe('DENY');
  });

  it('blocks missing credentials, unhealthy dependencies, prohibited data, and cost overages', () => {
    expect(evaluateCapabilityPolicy('github_mcp_reader', { actorRole: 'admin', environment: 'test', requestedAction: 'activate' }).decision).toBe('NOT_CONFIGURED');
    expect(evaluateCapabilityPolicy('executive_daily_brief', { actorRole: 'admin', environment: 'test', requestedAction: 'execute', dependencyHealth: { executive_system_health: 'BLOCKED' } }).decision).toBe('DEPENDENCY_UNHEALTHY');
    expect(evaluateCapabilityPolicy('alpha_web_search_adapter', { actorRole: 'alpha', environment: 'test', requestedAction: 'read', requestedDataClasses: ['CLIENT_PII'] }).decision).toBe('DATA_CLASS_NOT_ALLOWED');
    expect(evaluateCapabilityPolicy('openrouter_connector', { actorRole: 'admin', environment: 'test', requestedAction: 'execute', costWithinLimit: false }).decision).toBe('NOT_CONFIGURED');
  });

  it('requires approval before approval-gated execution and denies unknown capabilities', () => {
    expect(evaluateCapabilityPolicy('governed_work', {
      actorRole: 'operator',
      environment: 'test',
      requestedAction: 'execute',
      credentialReadiness: {
        VITE_SUPABASE_URL: 'CONFIGURED',
        VITE_SUPABASE_ANON_KEY: 'CONFIGURED',
      },
    }).decision).toBe('REQUIRES_APPROVAL');
    expect(evaluateCapabilityPolicy('missing_capability', { actorRole: 'admin', environment: 'test', requestedAction: 'read' }).decision).toBe('UNKNOWN_CAPABILITY');
  });

  it('emits sanitized preflight events without executing', () => {
    const denied = runCapabilityPreflight('github_mcp_writer', { actorRole: 'agent', environment: 'test', requestedAction: 'write' });
    expect(denied.allowed).toBe(false);
    expect(denied.event.sanitized).toBe(true);
    expect(denied.event.action).toMatch(/CAPABILITY_/);
    expect(describePreflightBlock(denied)).toMatch(/github_mcp_writer blocked/);
    expect(JSON.stringify(denied)).not.toMatch(/token-value|password-value|sk_live_/);
  });
});

describe('Repo Intelligence capability proposals', () => {
  it('maps research candidates into proposals without activation', () => {
    const proposals = buildCapabilityProposalsFromRepoIntelligence();
    const githubMcp = proposals.find((proposal) => proposal.candidateName === 'github/github-mcp-server');
    expect(githubMcp).toBeTruthy();
    expect(githubMcp?.requestedActivationMode).toBe('NOT_CONFIGURED');
    expect(githubMcp?.status).toBe('AWAITING_REVIEW');
    expect(githubMcp?.rayDecisionRequired).toBe(true);
  });

  it('keeps GitHub MCP reader/writer governed and disabled for writes', () => {
    const reader = getCapability('github_mcp_reader');
    const writer = getCapability('github_mcp_writer');
    expect(reader?.activationMode).toBe('NOT_CONFIGURED');
    expect(reader?.alphaMayUse).toBe(true);
    expect(reader?.prohibitedDataClasses).toContain('CLIENT_PII');
    expect(writer?.activationMode).toBe('APPROVAL_GATED');
    expect(writer?.hermesMayExecute).toBe(false);
    expect(writer?.notes).toMatch(/Direct main writes/);
  });
});
