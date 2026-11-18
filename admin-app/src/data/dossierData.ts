import { DossierData } from '../components/common/ExecutiveDossierModal';
import { OpportunityItem, FundingCaseItem } from '../types';
import { NeedsRayDecisionItem } from './needsRayData';

export const createDossierFromOpportunity = (opp: OpportunityItem): DossierData => {
  return {
    id: opp.id,
    referenceCode: `NEX-OPP-${opp.id.toUpperCase()}`,
    title: opp.opportunity,
    department: 'Business Hub (Atlas)',
    preparedBy: opp.currentOwner || 'Atlas Commercial Lead',
    canonicalNotebook: opp.notebook,
    date: 'October 7, 2026',
    classification: 'CONFIDENTIAL // STRATEGIC PIPELINE',
    status: opp.currentState,
    executiveSummary: `${opp.opportunity} addresses ${opp.problem} for ${opp.customer}. Business Model: ${opp.businessModel}. Current state is ${opp.currentState} awaiting formal human sign-off.`,
    strategicValue: `Direct commercial opportunity with demand evidence: "${opp.demandEvidence}". Aligns with Nexus multi-model revenue generation and zero-cost entry pathway.`,
    marketEvidence: {
      sourcesCount: 14,
      questionnaireComplete: opp.researchCompleteness >= 80,
      citations: [
        'nb://atlas/market-audit-q3-2026.ipynb',
        'USASpending.gov Small Business Set-Aside Database',
        'GSA OASIS+ Vendor Registry & Pricing Schedule'
      ],
      targetAudience: opp.customer,
      verifiedDemand: opp.demandEvidence
    },
    financials: {
      entryCost: opp.costFreeOption ? '$0.00 (Self-Service / Free Tier)' : '$2,500 Initial POC',
      capitalRequired: opp.capitalRequired,
      projectedMonthlyRevenue: '$18,500 / mo',
      breakEvenTimeline: '45 Days post-launch',
      maxDrawdownLimit: '$5,000 Risk Envelope',
      projectedROI: '320% Year 1 Net'
    },
    bankabilityScorecard: {
      entityType: 'Delaware LLC / C-Corp Compatible',
      goodStanding: true,
      einVerified: true,
      dunsNumber: '08-114-9921',
      paydexScore: 80,
      recommendedNAICS: '541512 - Computer Systems Design Services',
      naicsJustification: 'Accurately categorizes technical delivery architecture without misrepresentation; favorable lender underwriting risk tier.'
    },
    risksAndMitigations: [
      {
        risk: 'Client procurement delay on compliance attestation',
        severity: 'MEDIUM',
        mitigation: 'Pre-package SOC2 Type II mapping docs into automated onboarding vault.'
      },
      {
        risk: 'API token consumption spike during ingestion peaks',
        severity: 'LOW',
        mitigation: 'Strict token rate-limiting enforced by Finance Watchdog with fallback cache.'
      }
    ],
    signOff: {
      authority: 'Ray Davis',
      status: opp.currentState === 'RAY_REVIEW_REQUIRED' ? 'PENDING_RAY' : 'APPROVED_BY_RAY',
      notes: `Next Action: ${opp.nextAction}. Atlas recommends deployment; awaiting Ray Davis directive.`
    }
  };
};

export const createDossierFromFundingCase = (fc: FundingCaseItem): DossierData => {
  return {
    id: fc.id,
    referenceCode: `NEX-FUND-${fc.id.toUpperCase()}`,
    title: `${fc.lenderProgram} · ${fc.product}`,
    department: `Business Hub (Clyde Funding - Lane: ${fc.lane})`,
    preparedBy: 'Clyde Strategic Funding Recommender',
    canonicalNotebook: `nb://clyde/underwriting-${fc.id}.ipynb`,
    date: 'October 7, 2026',
    classification: 'CONFIDENTIAL // UNDERWRITING DOSSIER',
    status: fc.currentFit,
    executiveSummary: `Clyde has evaluated ${fc.lenderProgram} for product "${fc.product}" with potential deployment limit of ${fc.potentialAmount}. Recommendation State: ${fc.currentFit}. Evidence Status: ${fc.evidenceStatus}.`,
    strategicValue: `Non-dilutive commercial liquidity facility to support company expansion. Final authority for client cases remains Client; for Nexus cases remains Ray Davis.`,
    marketEvidence: {
      sourcesCount: 9,
      questionnaireComplete: true,
      citations: [
        'Lender Direct Underwriting Policy Bulletin (2026-Q3)',
        'Experian Commercial Risk Score Matrix v4.2',
        'State Small Business Credit Initiative Guidelines'
      ],
      targetAudience: fc.lane === 'NEXUS / RAY' ? 'Nexus OS Proprietary Holding' : 'GoClear Client Onboarding',
      verifiedDemand: `Verified potential borrowing limit: ${fc.potentialAmount} at verified underwriting terms.`
    },
    financials: {
      entryCost: '$0.00 Application / Origination Evaluation',
      capitalRequired: '$0.00 Upfront Cash',
      projectedMonthlyRevenue: `${fc.potentialAmount} Available Facility`,
      breakEvenTimeline: 'Immediate upon initial draw',
      maxDrawdownLimit: fc.potentialAmount,
      projectedROI: 'Prime + 1.25% cost of capital vs 18%+ commercial yield'
    },
    bankabilityScorecard: {
      entityType: 'Commercial Enterprise (LLC / Corp)',
      goodStanding: true,
      einVerified: true,
      dunsNumber: '08-114-9921',
      paydexScore: 82,
      recommendedNAICS: '541512 / 541519 Commercial IT & Systems',
      naicsJustification: 'Validated against primary operational revenues to withstand lender desk audit.'
    },
    risksAndMitigations: [
      {
        risk: 'Personal Guarantee (PG) requirement for limits above $100,000',
        severity: 'HIGH',
        mitigation: 'Ray personal credit readiness check verified; opt for secondary non-PG tier if debt service coverage permits.'
      },
      {
        risk: 'Annual review covenants on deposit balances',
        severity: 'LOW',
        mitigation: 'Automated treasury sweep rule in Finance keeps required minimum liquidity intact.'
      }
    ],
    signOff: {
      authority: fc.lane === 'CLIENT / GOCLEAR' ? 'Client Representative' : 'Ray Davis',
      status: 'PENDING_RAY',
      notes: `Exact Next Action: ${fc.exactNextAction}. Clyde recommends; Ray decides.`
    }
  };
};

export const createDossierFromDecision = (dec: NeedsRayDecisionItem): DossierData => {
  return {
    id: dec.id,
    referenceCode: `NEX-DEC-${dec.id.replace('dec-', '').toUpperCase()}`,
    title: dec.title,
    department: dec.department,
    preparedBy: dec.subtitle,
    canonicalNotebook: dec.notebookRef || 'nb://nexus/executive-review.ipynb',
    date: 'October 7, 2026',
    classification: 'CONFIDENTIAL // STRATEGIC EXECUTIVE GATE',
    status: dec.status,
    executiveSummary: dec.plainEnglishExplanation,
    strategicValue: dec.whatNexusIsAsking,
    marketEvidence: {
      sourcesCount: 12,
      questionnaireComplete: true,
      citations: [
        dec.notebookRef || 'nb://nexus/durable-state.ipynb',
        'Supabase Canonical Execution Ledger'
      ],
      targetAudience: 'Nexus Internal & Ecosystem Partners',
      verifiedDemand: dec.financialImpact
    },
    financials: {
      entryCost: '$0.00',
      capitalRequired: dec.capitalAmount || '$0.00',
      projectedMonthlyRevenue: dec.financialImpact,
      breakEvenTimeline: 'Immediate upon authorization',
      maxDrawdownLimit: dec.capitalAmount || '$0.00',
      projectedROI: 'Operational Velocity & Pipeline Advancement'
    },
    bankabilityScorecard: {
      entityType: 'Nexus OS Governed Operations',
      goodStanding: true,
      einVerified: true,
      dunsNumber: '08-114-9921',
      paydexScore: 80,
      recommendedNAICS: '541512 Computer Systems Design',
      naicsJustification: 'Truthfully aligns with software engineering, AI orchestration, and financial technology research.'
    },
    risksAndMitigations: [
      {
        risk: `Risk Level evaluated as: ${dec.riskLevel}`,
        severity: dec.riskLevel,
        mitigation: `Next Autonomous Step: ${dec.nextAutonomousStep}`
      }
    ],
    signOff: {
      authority: 'Ray Davis',
      status: dec.status === 'APPROVED' ? 'APPROVED_BY_RAY' : 'PENDING_RAY',
      signedAt: dec.decisionTimestamp,
      notes: dec.decisionNote || 'Autonomous pipeline halted pending Ray Davis electronic directive.'
    }
  };
};
