import { describe, it, expect } from 'vitest';
import {
  classifyOperatingQuestion,
  answerOperatingQuestion,
} from '../src/lib/hermesLocalOperatingCommands';
import {
  READINESS_WORKFLOWS,
  getReadinessWorkflow,
  getReadinessWorkflowSummary,
  getReadinessActionMetadata,
} from '../src/lib/nexusReadinessRegistry';
import { INTAKE_SECTIONS, calculateIntakeCompleteness } from '../src/lib/readinessReviewIntake';
import {
  SCORE_SECTIONS,
  READINESS_TIERS,
  calculateOverallScore,
  getReadinessTier,
} from '../src/lib/readinessReviewScorecard';

describe('Hermes Readiness Review Delivery Kit', () => {
  describe('Delivery Operating Questions', () => {
    it('classifies "how do I deliver the $97 review"', () => {
      expect(classifyOperatingQuestion('how do i deliver the $97')).toBe('how_to_deliver_97');
    });

    it('classifies "start a readiness review"', () => {
      expect(classifyOperatingQuestion('start a readiness review')).toBe('start_readiness_review');
    });

    it('classifies "what questions do I ask the client"', () => {
      expect(classifyOperatingQuestion('what questions do i ask the client')).toBe('what_questions_to_ask');
    });

    it('classifies "create the client intake"', () => {
      expect(classifyOperatingQuestion('create the client intake')).toBe('create_client_intake');
    });

    it('classifies "score client manually"', () => {
      expect(classifyOperatingQuestion('score this client manually')).toBe('score_client_manually');
    });

    it('classifies "create the client report"', () => {
      expect(classifyOperatingQuestion('create the client report')).toBe('create_client_report');
    });

    it('classifies "what should I tell the client"', () => {
      expect(classifyOperatingQuestion('what should i tell the client')).toBe('what_to_tell_client');
    });

    it('classifies "what is the upgrade recommendation"', () => {
      expect(classifyOperatingQuestion('what is the upgrade recommendation')).toBe('upgrade_recommendation');
    });

    it('classifies "prepare the $297 upsell"', () => {
      expect(classifyOperatingQuestion('prepare the $297 upsell')).toBe('prepare_297_upsell');
    });

    it('classifies "prepare monthly readiness subscription"', () => {
      expect(classifyOperatingQuestion('prepare the monthly readiness subscription')).toBe('prepare_monthly_subscription');
    });

    it('classifies "specialist handoff from review"', () => {
      expect(classifyOperatingQuestion('specialist handoff from review')).toBe('specialist_handoff_from_review');
    });

    it('returns answer for how_to_deliver_97', () => {
      const answer = answerOperatingQuestion('how_to_deliver_97');
      expect(answer).toContain('deliver');
      expect(answer).toContain('intake');
      expect(answer).toContain('score');
      expect(answer).toContain('report');
    });

    it('returns answer for start_readiness_review', () => {
      const answer = answerOperatingQuestion('start_readiness_review');
      expect(answer).toContain('Confirm payment');
      expect(answer).toContain('intake');
    });

    it('returns answer for upgrade_recommendation', () => {
      const answer = answerOperatingQuestion('upgrade_recommendation');
      expect(answer).toContain('$297');
      expect(answer).toContain('Monthly');
    });
  });

  describe('Delivery Kit Configs', () => {
    it('has 15 intake sections', () => {
      expect(INTAKE_SECTIONS.length).toBe(15);
    });

    it('calculates intake completeness for empty intake', () => {
      const result = calculateIntakeCompleteness({});
      expect(result.answered).toBe(0);
      expect(result.total).toBeGreaterThan(0);
      expect(result.complete).toBe(false);
    });

    it('calculates intake completeness for full intake', () => {
      const full: Record<string, string> = {};
      INTAKE_SECTIONS.forEach(s => {
        s.fields.forEach(f => { full[f.key] = 'provided'; });
      });
      const result = calculateIntakeCompleteness(full);
      expect(result.answered).toBe(result.total);
      expect(result.complete).toBe(true);
    });

    it('has 8 score sections', () => {
      expect(SCORE_SECTIONS.length).toBe(8);
    });

    it('has 5 readiness tiers', () => {
      expect(READINESS_TIERS.length).toBe(5);
    });

    it('maps scores to tiers correctly', () => {
      expect(getReadinessTier(92).label).toBe('Ready for Advanced Funding Review');
      expect(getReadinessTier(80).label).toBe('Ready for Starter Funding Path');
      expect(getReadinessTier(65).label).toBe('Almost Ready');
      expect(getReadinessTier(40).label).toBe('Needs Cleanup First');
      expect(getReadinessTier(10).label).toBe('Not Ready');
    });
  });

  describe('Workflow Registry', () => {
    it('has 6 delivery workflows', () => {
      expect(READINESS_WORKFLOWS.length).toBe(6);
    });

    it('retrieves intake workflow', () => {
      const w = getReadinessWorkflow('readiness_review_intake');
      expect(w).toBeDefined();
      expect(w!.steps.length).toBe(5);
      expect(w!.approvalRequired).toBe(false);
    });

    it('retrieves scorecard workflow', () => {
      const w = getReadinessWorkflow('readiness_review_scorecard');
      expect(w).toBeDefined();
      expect(w!.steps.length).toBe(7);
    });

    it('retrieves client report workflow', () => {
      const w = getReadinessWorkflow('readiness_review_client_report');
      expect(w).toBeDefined();
      expect(w!.approvalRequired).toBe(true);
    });

    it('retrieves specialist handoff workflow', () => {
      const w = getReadinessWorkflow('readiness_review_specialist_handoff');
      expect(w).toBeDefined();
      expect(w!.specialistLane).toBe('credit');
    });

    it('returns undefined for unknown workflow', () => {
      expect(getReadinessWorkflow('nonexistent')).toBeUndefined();
    });

    it('generates workflow summary', () => {
      const summary = getReadinessWorkflowSummary();
      expect(summary).toContain('Client Intake');
      expect(summary).toContain('Manual Scoring');
      expect(summary).toContain('Fulfillment');
    });
  });

  describe('Action Metadata', () => {
    it('returns intake action for readiness_review_intake', () => {
      const meta = getReadinessActionMetadata('readiness_review_intake');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('open_intake');
    });

    it('returns scorecard action for readiness_review_scorecard', () => {
      const meta = getReadinessActionMetadata('readiness_review_scorecard');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('open_scorecard');
    });

    it('returns report template action for readiness_review_client_report', () => {
      const meta = getReadinessActionMetadata('readiness_review_client_report');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('open_report_template');
    });

    it('returns checklist action for readiness_review_admin_fulfillment', () => {
      const meta = getReadinessActionMetadata('readiness_review_admin_fulfillment');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('open_checklist');
    });

    it('returns upgrade action for readiness_review_upgrade_path', () => {
      const meta = getReadinessActionMetadata('readiness_review_upgrade_path');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('draft_upgrade_recommendation');
    });

    it('returns specialist handoff action for readiness_review_specialist_handoff', () => {
      const meta = getReadinessActionMetadata('readiness_review_specialist_handoff');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('prepare_specialist_handoff');
    });

    it('returns null for unknown area', () => {
      expect(getReadinessActionMetadata('nonexistent')).toBeNull();
    });
  });
});
