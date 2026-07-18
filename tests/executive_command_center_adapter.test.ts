import { describe, expect, it } from 'vitest';
import {
  buildDepartmentStatuses,
  buildRepoIntelligenceItems,
  buildSystemHealth,
  getExecutiveCommandCenterSnapshot,
  normalizeApprovalRows,
  normalizeApprovalState,
  normalizeGovernedWorkRows,
  normalizeWorkLifecycle,
} from '../src/lib/executive/executiveCommandCenterAdapter';
import { answerExecutiveIntent, classifyExecutiveIntent } from '../src/lib/executive/hermesExecutiveAdvisor';

const source = {
  state: 'LIVE' as const,
  source: 'test',
  freshness: 'CURRENT' as const,
  confidence: 'HIGH' as const,
};

describe('Executive Command Center adapter', () => {
  it('normalizes approval states into the Executive vocabulary', () => {
    expect(normalizeApprovalState('pending')).toBe('PENDING');
    expect(normalizeApprovalState('approved')).toBe('APPROVED');
    expect(normalizeApprovalState('revise')).toBe('REVISION_REQUESTED');
    expect(normalizeApprovalState('held')).toBe('DEFERRED');
    expect(normalizeApprovalState('failed')).toBe('BLOCKED');
  });

  it('maps governed work from canonical task, approval, job evidence', () => {
    const work = normalizeGovernedWorkRows(
      [{ id: 'task-1', title: 'Prepare daily brief', status: 'requested', task_type: 'executive' }],
      [{ id: 'approval-1', task_request_id: 'task-1', status: 'pending' }],
      [],
      source,
    );
    expect(work).toHaveLength(1);
    expect(work[0]).toMatchObject({
      id: 'task-1',
      lifecycle: 'AWAITING_APPROVAL',
      approvalState: 'PENDING',
    });
  });

  it('does not treat report-only work-order artifacts as execution sources', () => {
    const work = normalizeGovernedWorkRows([], [], [], source);
    expect(work).toEqual([]);
  });

  it('keeps high-risk approvals pending rather than self-approved', () => {
    const approvals = normalizeApprovalRows([
      { id: 'approval-1', title: 'Enable live Stripe', status: 'pending', risk_level: 'high' },
    ], source);
    expect(approvals[0]).toMatchObject({
      state: 'PENDING',
      riskLevel: 'HIGH',
      requiredApprover: 'Ray Davis',
    });
  });

  it('classifies departments truthfully without creating autonomous agents', () => {
    const departments = buildDepartmentStatuses([], []);
    expect(departments.find((item) => item.departmentId === 'trading')?.currentStatus).toBe('BLOCKED');
    expect(departments.find((item) => item.departmentId === 'venture_studio')?.currentStatus).toBe('PLANNED');
  });

  it('marks live Stripe and live trading as deferred or policy-blocked health items', () => {
    const health = buildSystemHealth();
    expect(health.find((item) => item.component === 'Stripe live payments')?.status).toBe('DEFERRED');
    expect(health.find((item) => item.component === 'Live trading')?.status).toBe('BLOCKED_BY_POLICY');
    expect(health.find((item) => item.component === 'Alpha Supabase access')?.status).toBe('PROHIBITED');
  });

  it('loads repo-intelligence candidates and keeps GitHub MCP writer disabled', () => {
    const repos = buildRepoIntelligenceItems();
    const githubMcp = repos.find((item) => item.candidateId === 'github_mcp_server');
    expect(githubMcp).toBeTruthy();
    expect(githubMcp?.proposedDisposition).toBe('INTEGRATE_AS_CONTROLLED_EXTERNAL_TOOL');
    expect(githubMcp?.decisionRequired).toBe('PENDING');
  });

  it('builds a snapshot with evidence labels and no external execution capability', () => {
    const snapshot = getExecutiveCommandCenterSnapshot();
    expect(snapshot.metrics.length).toBeGreaterThanOrEqual(6);
    expect(snapshot.repoIntelligence.length).toBeGreaterThan(0);
    expect(snapshot.limitations.join(' ')).toMatch(/Static snapshot|external action/i);
  });

  it('keeps deterministic lifecycle mapping', () => {
    expect(normalizeWorkLifecycle('requested', 'PENDING')).toBe('AWAITING_APPROVAL');
    expect(normalizeWorkLifecycle('done', 'APPROVED')).toBe('COMPLETED');
    expect(normalizeWorkLifecycle('requested', 'REVISION_REQUESTED')).toBe('NEEDS_REVIEW');
  });
});

describe('Hermes executive advisor', () => {
  it('routes executive questions to explicit executive intents', () => {
    expect(classifyExecutiveIntent('What needs my attention today?')).toBe('executive_priorities');
    expect(classifyExecutiveIntent('What repo intelligence decisions need review?')).toBe('executive_repo_intelligence');
    expect(classifyExecutiveIntent('Give me the daily operating brief')).toBe('executive_daily_brief');
  });

  it('answers with facts, recommendations, and no execution claim', () => {
    const answer = answerExecutiveIntent('executive_daily_brief');
    expect(answer).toMatch(/Facts:/);
    expect(answer).toMatch(/Recommendations:/);
    expect(answer).toMatch(/live Stripe is deferred/i);
  });
});
