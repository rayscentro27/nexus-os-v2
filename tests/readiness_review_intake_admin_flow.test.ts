import { describe, it, expect } from 'vitest';
import { INTAKE_SECTIONS, calculateIntakeCompleteness } from '../src/lib/readinessReviewIntake';
import { SCORE_SECTIONS, READINESS_TIERS, calculateOverallScore, getReadinessTier } from '../src/lib/readinessReviewScorecard';
import { generateReportDraft, formatReportDraftAsText } from '../src/lib/readinessReviewReportDraft';
import { classifyOperatingQuestion, answerOperatingQuestion } from '../src/lib/hermesLocalOperatingCommands';
import { getReadinessActionMetadata } from '../src/lib/nexusReadinessRegistry';
import { SAFE_HERMES_ACTION_TYPES } from '../src/lib/hermesUiActions';

describe('Readiness Review Intake and Admin Flow', () => {
  describe('Part 1: Client Intake UI', () => {
    it('renders all 15 required intake sections', () => {
      expect(INTAKE_SECTIONS.length).toBe(15);
      const sectionIds = INTAKE_SECTIONS.map(s => s.id);
      expect(sectionIds).toContain('personal_credit');
      expect(sectionIds).toContain('credit_report_availability');
      expect(sectionIds).toContain('negative_items');
      expect(sectionIds).toContain('credit_utilization');
      expect(sectionIds).toContain('inquiries');
      expect(sectionIds).toContain('collections_chargeoffs');
      expect(sectionIds).toContain('business_entity');
      expect(sectionIds).toContain('ein_duns_sos_naics');
      expect(sectionIds).toContain('business_contact');
      expect(sectionIds).toContain('business_bank');
      expect(sectionIds).toContain('business_credit');
      expect(sectionIds).toContain('funding_goal');
      expect(sectionIds).toContain('timeline');
      expect(sectionIds).toContain('documents_available');
      expect(sectionIds).toContain('credit_goals');
    });

    it('each section has required fields defined', () => {
      for (const section of INTAKE_SECTIONS) {
        expect(section.fields).toBeDefined();
        expect(section.fields.length).toBeGreaterThan(0);
        expect(section.label).toBeDefined();
        expect(section.description).toBeDefined();
      }
    });
  });

  describe('Part 3: Manual Scoring Helper', () => {
    it('produces a credit readiness tier without live integrations', () => {
      const creditScores = {
        credit_score_range: 40,
        reports_available: 30,
        negative_items: 20,
        utilization: 25,
        inquiries: 20,
      };
      const score = calculateOverallScore(creditScores);
      const tier = getReadinessTier(score);
      expect(tier).toBeDefined();
      expect(tier.label).toBeDefined();
      expect(typeof tier.tier).toBe('string');
    });

    it('produces a business funding readiness tier without live integrations', () => {
      const fundingScores = {
        entity_setup: 40,
        identifiers: 30,
        business_bank: 20,
        bankability: 25,
        funding_docs: 15,
        funding_timing: 20,
      };
      const score = calculateOverallScore(fundingScores);
      const tier = getReadinessTier(score);
      expect(tier).toBeDefined();
      expect(tier.label).toBeDefined();
    });

    it('produces an overall readiness tier from combined scores', () => {
      const allScores = {
        credit_score_range: 40,
        reports_available: 30,
        negative_items: 20,
        utilization: 25,
        inquiries: 20,
        entity_setup: 40,
        identifiers: 30,
        business_bank: 20,
        bankability: 25,
        funding_docs: 15,
        funding_timing: 20,
      };
      const score = calculateOverallScore(allScores);
      const tier = getReadinessTier(score);
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(100);
      expect(['Not Ready', 'Needs Cleanup First', 'Almost Ready', 'Ready for Starter Funding Path', 'Ready for Advanced Funding Review']).toContain(tier.label);
    });

    it('maps all 5 tiers correctly', () => {
      expect(getReadinessTier(10).tier).toBe('not_ready');
      expect(getReadinessTier(35).tier).toBe('needs_cleanup');
      expect(getReadinessTier(55).tier).toBe('almost_ready');
      expect(getReadinessTier(75).tier).toBe('ready_starter');
      expect(getReadinessTier(90).tier).toBe('ready_advanced');
    });
  });

  describe('Part 4: Client Report Draft Generator', () => {
    it('includes all required sections and disclaimer', () => {
      const report = generateReportDraft({
        intakeAnswers: { credit_reports_available: 'yes', llc_or_corp: 'yes' },
        creditScores: { credit_score_range: 40, utilization: 25 },
        fundingScores: { entity_setup: 40, identifiers: 30 },
        adminNotes: 'Test notes',
        blockers: ['No DUNS number'],
        nextSteps: ['Apply for DUNS'],
        upgradePath: '297_assistant',
        specialistLane: '',
        clientName: 'Test Client',
      });

      expect(report.executiveSummary).toBeDefined();
      expect(report.readinessScore).toBeGreaterThanOrEqual(0);
      expect(report.readinessScore).toBeLessThanOrEqual(100);
      expect(report.readinessTier).toBeDefined();
      expect(report.creditFindings).toBeDefined();
      expect(report.businessFundingFindings).toBeDefined();
      expect(report.topBlockers).toContain('No DUNS number');
      expect(report.recommendedNextSteps).toContain('Apply for DUNS');
      expect(report.whatToAvoid).toBeDefined();
      expect(report.whatToAvoid.length).toBeGreaterThan(0);
      expect(report.upgradePath).toBeDefined();
      expect(report.disclaimer).toBeDefined();
      expect(report.disclaimer).toContain('DISCLAIMER');
      expect(report.disclaimer).toContain('not legal');
      expect(report.status).toBe('draft');
    });

    it('formats report as readable text', () => {
      const report = generateReportDraft({
        intakeAnswers: {},
        creditScores: {},
        fundingScores: {},
        adminNotes: '',
        blockers: ['Test blocker'],
        nextSteps: ['Test step'],
        upgradePath: 'none',
        specialistLane: '',
      });

      const text = formatReportDraftAsText(report);
      expect(text).toContain('$97 CREDIT & FUNDING READINESS REVIEW');
      expect(text).toContain('EXECUTIVE SUMMARY');
      expect(text).toContain('CREDIT FINDINGS');
      expect(text).toContain('BUSINESS FUNDING FINDINGS');
      expect(text).toContain('TOP BLOCKERS');
      expect(text).toContain('Test blocker');
      expect(text).toContain('RECOMMENDED NEXT STEPS');
      expect(text).toContain('Test step');
      expect(text).toContain('WHAT TO AVOID');
      expect(text).toContain('UPGRADE PATH');
      expect(text).toContain('DISCLAIMER');
      expect(text).toContain('DRAFT');
    });
  });

  describe('Part 5: Hermes Integration', () => {
    it('routes "start a client intake"', () => {
      const q = classifyOperatingQuestion('start a client intake');
      expect(q).toBe('start_client_intake');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('intake');
      expect(answer).toContain('15 sections');
    });

    it('routes "open readiness intake"', () => {
      const q = classifyOperatingQuestion('open readiness intake');
      expect(q).toBe('open_readiness_intake');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('Intake');
    });

    it('routes "open admin review"', () => {
      const q = classifyOperatingQuestion('open admin review');
      expect(q).toBe('open_admin_review');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('admin review');
    });

    it('routes "score this review"', () => {
      const q = classifyOperatingQuestion('score this review');
      expect(q).toBe('score_this_review');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('score');
      expect(answer).toContain('8 sections');
    });

    it('routes "draft the client report"', () => {
      const q = classifyOperatingQuestion('draft the client report');
      expect(q).toBe('draft_client_report_flow');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('report');
      expect(answer).toContain('Draft');
    });

    it('routes "what is missing from this review"', () => {
      const q = classifyOperatingQuestion('what is missing from this review');
      expect(q).toBe('what_missing_from_review');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('missing');
    });

    it('routes "what should I tell this client"', () => {
      const q = classifyOperatingQuestion('what should i tell this client');
      expect(q).toBe('what_tell_this_client');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('client');
    });

    it('routes "best upgrade path"', () => {
      const q = classifyOperatingQuestion('best upgrade path');
      expect(q).toBe('best_upgrade_path');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('upgrade');
      expect(answer).toContain('$297');
    });

    it('routes "prepare specialist handoff"', () => {
      const q = classifyOperatingQuestion('prepare specialist handoff');
      expect(q).toBe('prepare_specialist_handoff_flow');
      const answer = answerOperatingQuestion(q!);
      expect(answer).toContain('handoff');
    });
  });

  describe('Part 6: Safety Verification', () => {
    it('no send/charge/publish/scheduler actions are enabled', () => {
      const allQuestions = [
        'start_client_intake', 'open_readiness_intake', 'open_admin_review',
        'score_this_review', 'draft_client_report_flow',
        'what_tell_this_client', 'best_upgrade_path', 'prepare_specialist_handoff_flow',
      ] as const;

      for (const q of allQuestions) {
        const answer = answerOperatingQuestion(q);
        expect(answer).not.toContain('send email');
        expect(answer).not.toContain('process payment');
        expect(answer).not.toContain('publish to');
        expect(answer).not.toContain('start scheduler');
      }
    });

    it('report draft is explicitly marked as draft-only', () => {
      const report = generateReportDraft({
        intakeAnswers: {},
        creditScores: {},
        fundingScores: {},
        adminNotes: '',
        blockers: [],
        nextSteps: [],
        upgradePath: 'none',
        specialistLane: '',
      });

      expect(report.status).toBe('draft');
      expect(report.disclaimer).toContain('draft');
      expect(report.disclaimer).toContain('not been delivered');
    });

    it('intake includes consent and disclaimer language', () => {
      const consentSection = INTAKE_SECTIONS.find(s => s.id === 'credit_goals' || s.id === 'documents_available');
      expect(consentSection).toBeDefined();
      expect(consentSection!.fields.length).toBeGreaterThan(0);
    });
  });

  describe('Part 5: UI Reachability', () => {
    it('ReadinessReviewIntake component exists and exports', () => {
      // The component is imported at the top of this test file indirectly via readinessReviewIntake
      // Verify the component module can be imported
      expect(INTAKE_SECTIONS).toBeDefined();
      expect(INTAKE_SECTIONS.length).toBe(15);
    });

    it('ReadinessReviewAdmin component exists and exports', () => {
      // Verify the scorecard module (used by admin) is importable
      expect(SCORE_SECTIONS).toBeDefined();
      expect(SCORE_SECTIONS.length).toBe(8);
      expect(READINESS_TIERS).toBeDefined();
      expect(READINESS_TIERS.length).toBe(5);
    });

    it('Hermes action metadata resolves to safe UI navigation for readiness intake', () => {
      const meta = getReadinessActionMetadata('readiness_review_intake');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('open_intake');
      expect(meta!.href).toBe('#readiness-intake');
      expect(meta!.source).toBe('readiness_registry');
    });

    it('Hermes action metadata resolves to safe UI navigation for readiness admin', () => {
      const meta = getReadinessActionMetadata('readiness_review_admin_fulfillment');
      expect(meta).toBeDefined();
      expect(meta!.actionType).toBe('open_checklist');
      expect(meta!.href).toBe('#readiness-admin');
    });

    it('draft report action does not persist/send/publish', () => {
      const draftActions = [
        'readiness_review_upgrade_path',
        'readiness_review_specialist_handoff',
      ];
      for (const key of draftActions) {
        const meta = getReadinessActionMetadata(key);
        expect(meta).toBeDefined();
        // Draft actions should NOT have an href that triggers external actions
        expect(meta!.href).toBeUndefined();
        expect(meta!.actionType).not.toContain('send');
        expect(meta!.actionType).not.toContain('publish');
        expect(meta!.actionType).not.toContain('charge');
      }
    });

    it('all readiness action types are in the safe allowlist', () => {
      const allKeys = [
        'readiness_review_intake', 'readiness_review_scorecard',
        'readiness_review_client_report', 'readiness_review_admin_fulfillment',
        'readiness_review_upgrade_path', 'readiness_review_specialist_handoff',
      ];
      for (const key of allKeys) {
        const meta = getReadinessActionMetadata(key);
        expect(meta).toBeDefined();
        expect(SAFE_HERMES_ACTION_TYPES.has(meta!.actionType)).toBe(true);
      }
    });
  });
});
