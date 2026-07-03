import { getReadinessTier, calculateOverallScore } from './readinessReviewScorecard';

/**
 * Nexus OS v2 — Readiness Review Report Draft Generator.
 *
 * Produces a client-facing readiness report draft from intake + admin data.
 * Draft-only — must go through Ray Review before delivery.
 * No live credit bureau, bank, or lender data used.
 */

export interface ReportDraftInput {
  intakeAnswers: Record<string, unknown>;
  creditScores: Record<string, number>;
  fundingScores: Record<string, number>;
  adminNotes: string;
  blockers: string[];
  nextSteps: string[];
  upgradePath: string;
  specialistLane: string;
  clientName?: string;
}

export interface ReportDraft {
  executiveSummary: string;
  readinessScore: number;
  readinessTier: string;
  creditFindings: string;
  businessFundingFindings: string;
  topBlockers: string[];
  recommendedNextSteps: string[];
  whatToAvoid: string[];
  upgradePath: string;
  disclaimer: string;
  generatedAt: string;
  status: 'draft';
}

export function generateReportDraft(input: ReportDraftInput): ReportDraft {
  const allScores = { ...input.creditScores, ...input.fundingScores };
  const overallScore = calculateOverallScore(allScores);
  const overallTier = getReadinessTier(overallScore);

  const creditScore = calculateOverallScore(input.creditScores);
  const creditTier = getReadinessTier(creditScore);
  const fundingScore = calculateOverallScore(input.fundingScores);
  const fundingTier = getReadinessTier(fundingScore);

  const executiveSummary = buildExecutiveSummary(input.clientName, overallTier.label, overallScore, input.blockers.length);
  const creditFindings = buildCreditFindings(creditTier.label, creditScore, input.creditScores, input.intakeAnswers);
  const businessFundingFindings = buildFundingFindings(fundingTier.label, fundingScore, input.fundingScores, input.intakeAnswers);
  const whatToAvoid = buildWhatToAvoid(input.blockers, overallTier.tier);
  const upgradePathText = buildUpgradePath(input.upgradePath, overallTier.tier);
  const disclaimer = buildDisclaimer();

  return {
    executiveSummary,
    readinessScore: overallScore,
    readinessTier: overallTier.label,
    creditFindings,
    businessFundingFindings,
    topBlockers: input.blockers,
    recommendedNextSteps: input.nextSteps,
    whatToAvoid,
    upgradePath: upgradePathText,
    disclaimer,
    generatedAt: new Date().toISOString(),
    status: 'draft',
  };
}

function buildExecutiveSummary(clientName: string | undefined, tierLabel: string, score: number, blockerCount: number): string {
  const name = clientName || 'Client';
  return `${name} has been assessed for credit and business funding readiness. Overall readiness score: ${score}/100 — ${tierLabel}. ${blockerCount > 0 ? `${blockerCount} blocker(s) identified that should be addressed before pursuing funding applications.` : 'No major blockers identified. The client is in a strong position to pursue funding options.'} This report is advisory only and does not guarantee credit improvements or funding approvals.`;
}

function buildCreditFindings(tierLabel: string, score: number, scores: Record<string, number>, answers: Record<string, unknown>): string {
  const findings: string[] = [];
  findings.push(`Credit readiness: ${tierLabel} (score: ${score}/100).`);

  if (scores.utilization > 30) findings.push('Credit card utilization is above 30%, which may negatively impact credit scores.');
  if (scores.inquiries && scores.inquiries > 3) findings.push('Multiple hard inquiries detected in the past 12 months.');
  if (scores.negatives && scores.negatives > 0) findings.push('Negative items on credit report require review.');
  if (answers.credit_reports_available === 'no' || !answers.credit_reports_available) findings.push('Credit reports have not been pulled yet. Accessing all three bureau reports is recommended.');

  if (findings.length === 1) findings.push('Credit profile appears stable with no major concerns identified.');
  return findings.join(' ');
}

function buildFundingFindings(tierLabel: string, score: number, _scores: Record<string, number>, answers: Record<string, unknown>): string {
  const findings: string[] = [];
  findings.push(`Business funding readiness: ${tierLabel} (score: ${score}/100).`);

  if (!answers.llc_or_corp) findings.push('No LLC or corporation on file. Business entity formation is a prerequisite for most funding options.');
  if (!answers.ein_number) findings.push('No EIN number on file. An EIN is required for business banking and credit applications.');
  if (!answers.duns_number) findings.push('No DUNS number on file. A DUNS number is required for business credit reporting.');
  if (!answers.business_bank_account) findings.push('No dedicated business bank account. Separating personal and business finances is critical.');
  if (!answers.business_website) findings.push('No business website on file. A professional web presence strengthens funding applications.');

  if (findings.length === 1) findings.push('Business foundation appears solid with key setup items in place.');
  return findings.join(' ');
}

function buildWhatToAvoid(blockers: string[], tier: string): string[] {
  const avoid: string[] = [
    'Do not apply for funding until blockers are addressed.',
    'Do not open multiple new credit accounts in a short period.',
    'Do not make large purchases on business credit before securing funding.',
  ];

  if (tier === 'not_ready' || tier === 'needs_cleanup') {
    avoid.push('Do not submit funding applications until credit repair steps are completed.');
    avoid.push('Do not skip the readiness review follow-up.');
  }

  if (blockers.includes('Utilization above 30%')) {
    avoid.push('Do not increase credit card balances until utilization is below 30%.');
  }

  return avoid;
}

function buildUpgradePath(upgradePath: string, tier: string): string {
  switch (upgradePath) {
    case '297_assistant':
      return 'Recommended: $297 Credit Assistant Plan. This plan provides dedicated support to complete credit repair workflow and business setup. Ideal for clients who want hands-on guidance.';
    case 'monthly_sub':
      return 'Recommended: Monthly Readiness Subscription. Provides ongoing monitoring, score updates, and priority support. Ideal for clients who are Almost Ready or above.';
    case 'both':
      return 'Recommended: $297 Credit Assistant Plan + Monthly Readiness Subscription. Start with the assistant plan to address gaps, then transition to monthly monitoring.';
    case 'none':
      return 'No upgrade recommended at this time. The client can proceed with self-service actions outlined in the next steps.';
    default:
      if (tier === 'not_ready' || tier === 'needs_cleanup') {
        return 'Consider: $297 Credit Assistant Plan for dedicated support through credit repair and business setup.';
      }
      if (tier === 'almost_ready') {
        return 'Consider: $297 Credit Assistant Plan to close remaining gaps, or Monthly Readiness Subscription for ongoing monitoring.';
      }
      return 'Consider: Monthly Readiness Subscription to maintain readiness and monitor for funding opportunities.';
  }
}

function buildDisclaimer(): string {
  return `DISCLAIMER: This readiness review is for educational and advisory purposes only. It is not legal, financial, or credit advice. GoClear/Nexus does not guarantee credit score improvements, funding approvals, or dispute outcomes. No information in this report has been verified with credit bureaus, banks, or lenders. All recommendations require the client's approval before any action is taken. This report is a draft and has not been delivered to the client until explicitly approved through the Ray Review process.`;
}

export function formatReportDraftAsText(report: ReportDraft): string {
  const lines: string[] = [];
  lines.push('═══════════════════════════════════════════════════');
  lines.push('  $97 CREDIT & FUNDING READINESS REVIEW');
  lines.push('  Status: DRAFT — Not Yet Delivered');
  lines.push('═══════════════════════════════════════════════════');
  lines.push('');
  lines.push('EXECUTIVE SUMMARY');
  lines.push(report.executiveSummary);
  lines.push('');
  lines.push('READINESS SCORE');
  lines.push(`Overall: ${report.readinessScore}/100 — ${report.readinessTier}`);
  lines.push('');
  lines.push('CREDIT FINDINGS');
  lines.push(report.creditFindings);
  lines.push('');
  lines.push('BUSINESS FUNDING FINDINGS');
  lines.push(report.businessFundingFindings);
  lines.push('');
  lines.push('TOP BLOCKERS');
  report.topBlockers.forEach((b, i) => lines.push(`  ${i + 1}. ${b}`));
  if (report.topBlockers.length === 0) lines.push('  None identified.');
  lines.push('');
  lines.push('RECOMMENDED NEXT STEPS');
  report.recommendedNextSteps.forEach((s, i) => lines.push(`  ${i + 1}. ${s}`));
  lines.push('');
  lines.push('WHAT TO AVOID');
  report.whatToAvoid.forEach((a, i) => lines.push(`  ${i + 1}. ${a}`));
  lines.push('');
  lines.push('UPGRADE PATH');
  lines.push(report.upgradePath);
  lines.push('');
  lines.push('───────────────────────────────────────────────────');
  lines.push(report.disclaimer);
  lines.push('───────────────────────────────────────────────────');
  lines.push(`Generated: ${report.generatedAt}`);
  lines.push('Status: DRAFT — Requires Ray Review before delivery');
  return lines.join('\n');
}
