import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { getCapability } from '../src/lib/capabilities/capabilityRegistry';
import { classifyHermesConversationMode } from '../src/lib/hermes/hermesModeClassifier';
import { runHermesConversation } from '../src/lib/hermes/hermesConversationEngine';
import { hermesToolRegistry, runHermesTool } from '../src/lib/hermes/hermesGeneralTools';
import {
  activeDepartmentRegistry,
  canCompleteQueueItem,
  getDepartmentOperationsSnapshot,
  getTopDepartmentRisk,
  prepareDepartmentRayReviewDraft,
  prepareDepartmentTaskDraft,
  sortQueueByPriority,
  syntheticDepartmentBlockers,
  syntheticDepartmentQueue,
  syntheticWorkVerifications,
} from '../src/lib/departments/departmentOperations';

describe('Wave 4 Department Operations', () => {
  it('registers exactly the first five governed departments', () => {
    expect(activeDepartmentRegistry.map((item) => item.departmentId)).toEqual(['operations', 'engineering', 'research', 'knowledge', 'credit_funding']);
    expect(activeDepartmentRegistry.every((item) => item.executiveCoordinator === 'hermes')).toBe(true);
    expect(activeDepartmentRegistry.some((item) => item.defaultOperationMode === 'BOUNDED_EXECUTION')).toBe(false);
  });

  it('keeps department data classes and prohibited scopes explicit', () => {
    for (const department of activeDepartmentRegistry) {
      expect(department.allowedDataClasses.length).toBeGreaterThan(0);
      expect(department.prohibitedDataClasses).toContain('CREDENTIALS');
      expect(department.prohibitedDataClasses).toContain('PRODUCTION_CONTROL');
      expect(department.escalationTargets.length).toBeGreaterThan(0);
    }
  });

  it('sorts priority P0 before P1/P2/P3/P4 and preserves customer protection over research', () => {
    const sorted = sortQueueByPriority(syntheticDepartmentQueue);
    expect(sorted[0].priority).toBe('P0_COMPANY');
    expect(sorted.findIndex((item) => item.priority === 'P1_CUSTOMER')).toBeLessThan(sorted.findIndex((item) => item.priority === 'P4_RESEARCH'));
  });

  it('requires evidence and no high blocker before completion', () => {
    const credit = syntheticDepartmentQueue.find((item) => item.departmentId === 'credit_funding')!;
    expect(canCompleteQueueItem(credit, syntheticWorkVerifications, syntheticDepartmentBlockers)).toBe(false);
    const knowledge = syntheticDepartmentQueue.find((item) => item.departmentId === 'knowledge')!;
    expect(canCompleteQueueItem(knowledge, syntheticWorkVerifications, syntheticDepartmentBlockers)).toBe(true);
  });

  it('builds department health and risk from queue evidence', () => {
    const snapshot = getDepartmentOperationsSnapshot();
    expect(snapshot.health).toHaveLength(5);
    expect(snapshot.queueItems.every((item) => item.synthetic)).toBe(true);
    const risk = getTopDepartmentRisk();
    expect(risk.department.departmentId).toBe('engineering');
    expect(risk.item?.title).toMatch(/provider-state/i);
  });

  it('registers Hermes department tools through Capability OS', () => {
    const toolIds = hermesToolRegistry.map((tool) => tool.toolId);
    for (const toolId of ['hermes.department_list', 'hermes.department_status', 'hermes.department_queue', 'hermes.department_blockers', 'hermes.department_approvals', 'hermes.department_completed_work', 'hermes.department_incidents', 'hermes.department_dependencies', 'hermes.prepare_department_task', 'hermes.prepare_ray_review']) {
      expect(toolIds).toContain(toolId);
    }
    expect(getCapability('department_operations_registry')).toBeTruthy();
    expect(getCapability('hermes_department_queue_tool')).toBeTruthy();
    expect(getCapability('hermes_prepare_ray_review_tool')).toBeTruthy();
  });

  it('answers department questions through read-only Hermes tools', () => {
    expect(runHermesTool('hermes.department_list').text).toMatch(/Operations, Engineering, Research, Knowledge, Credit and Funding/);
    expect(runHermesTool('hermes.department_queue', { query: 'what is Engineering working on' }).text).toMatch(/Hermes provider-state reconciliation/);
    expect(runHermesTool('hermes.department_blockers', { query: 'what is blocked in Credit and Funding' }).text).toMatch(/Ray approval required/);
    expect(runHermesTool('hermes.department_approvals', { query: 'what needs my approval' }).text).toMatch(/Ray Davis/);
  });

  it('classifies natural department questions before generic project status', () => {
    expect(classifyHermesConversationMode('what departments are active').intent).toBe('department_list');
    expect(classifyHermesConversationMode('what is Engineering working on').intent).toBe('department_queue');
    expect(classifyHermesConversationMode('what is blocked in Credit and Funding').intent).toBe('department_blockers');
    expect(classifyHermesConversationMode('what needs my approval').intent).toBe('department_approvals');
  });

  it('Hermes answers department questions naturally and with evidence', () => {
    const departments = runHermesConversation({ message: 'what departments are active', actorRole: 'admin' });
    expect(departments.response).toMatch(/five|5|Operations|Engineering|Credit and Funding/i);
    expect(departments.action).toBeNull();
    const engineering = runHermesConversation({ message: 'what is Engineering working on', actorRole: 'admin' });
    expect(engineering.response).toMatch(/provider-state|Engineering Lead|DRAFT_ONLY/i);
    const blocked = runHermesConversation({ message: 'what is blocked in Credit and Funding', actorRole: 'admin' });
    expect(blocked.response).toMatch(/Ray approval|required|readiness/i);
  });

  it('preserves department-risk advisory context for rationale follow-ups', () => {
    const risk = runHermesConversation({ message: 'which department has the biggest risk', actorRole: 'admin' });
    expect(risk.response).toMatch(/Engineering|risk|P0_COMPANY|provider-state/i);
    expect(risk.session.advisoryContext?.topicId).toBe('department_operations_risk');
    const why = runHermesConversation({ message: 'why that one', actorRole: 'admin', session: risk.session });
    expect(why.mode).toBe('FOLLOW_UP_ADVICE');
    expect(why.response).toMatch(/Engineering|risk|priority|P0|because|provider-state/i);
    const firstStep = runHermesConversation({ message: 'what would the first step be', actorRole: 'admin', session: why.session });
    expect(firstStep.mode).toBe('FOLLOW_UP_ADVICE');
    expect(firstStep.response).toMatch(/First step|Planning only|nothing has been created|evidence|Ray Review/i);
  });

  it('keeps planning separate from governed drafts and Ray Review', () => {
    const plan = runHermesConversation({ message: 'prepare a plan for the top blocked item', actorRole: 'admin' });
    expect(plan.action).toBeNull();
    expect(plan.response).toMatch(/Plan, not execution|Nothing has been created/i);
    const taskDraft = runHermesConversation({ message: 'okay create a governed task draft for that first step', actorRole: 'admin' });
    expect(taskDraft.action).toMatchObject({ type: 'CREATE_GOVERNED_TASK', requiresApproval: true });
    expect(taskDraft.response).toMatch(/draft-only|nothing has been assigned|approved/i);
    const rayReview = runHermesConversation({ message: 'prepare a Ray Review request for it', actorRole: 'admin' });
    expect(rayReview.action).toMatchObject({ type: 'PREPARE_RAY_REVIEW', requiresApproval: true });
    expect(rayReview.response).toMatch(/Ray Review|cannot approve|execution/i);
  });

  it('draft helpers never claim execution', () => {
    expect(prepareDepartmentTaskDraft('create a governed task draft')).toMatch(/draft-only|nothing has been assigned/i);
    expect(prepareDepartmentRayReviewDraft('prepare Ray Review request')).toMatch(/Hermes cannot approve|separate from execution/i);
  });

  it('defines additive admin-only RLS for durable department objects', () => {
    const migration = fs.readFileSync(path.join(process.cwd(), 'supabase/migrations/20260720173000_department_operations.sql'), 'utf8');
    for (const table of ['nexus_departments', 'department_queue_items', 'department_blockers', 'department_incidents', 'department_work_verifications', 'governed_execution_plans']) {
      expect(migration).toMatch(new RegExp(`create table if not exists public\\.${table}`));
      expect(migration).toMatch(new RegExp(`alter table public\\.${table} enable row level security`));
      expect(migration).toContain(`'${table}'`);
    }
    expect(migration).toMatch(/admin_select_/);
    expect(migration).toMatch(/admin_insert_/);
    expect(migration).toMatch(/admin_update_/);
    expect(migration).not.toMatch(/to anon|to public/i);
    expect(migration).not.toMatch(/to\s+(client_ai|alpha)|role\s+(client_ai|alpha)|policy\s+.*(client_ai|alpha)/i);
  });
});
