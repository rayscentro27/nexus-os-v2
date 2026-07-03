/**
 * Nexus OS v2 — Readiness Review Scorecard Config.
 *
 * Structured scoring model for the $97 Credit & Funding Readiness Review.
 * Pure config — no I/O, no external calls. Hermes reads this to compute
 * readiness scores and tiers from intake data.
 */

export type ReadinessTier = 'not_ready' | 'needs_cleanup' | 'almost_ready' | 'ready_starter' | 'ready_advanced';

export interface ScoreSection {
  id: string;
  label: string;
  weight: number;
  factors: ScoreFactor[];
}

export interface ScoreFactor {
  key: string;
  label: string;
  maxScore: number;
  tiers: { threshold: number; score: number }[];
}

export interface ReadinessTierDef {
  tier: ReadinessTier;
  label: string;
  range: [number, number];
  description: string;
}

export const SCORE_SECTIONS: ScoreSection[] = [
  {
    id: 'credit_profile',
    label: 'Credit Profile Readiness',
    weight: 0.25,
    factors: [
      { key: 'credit_score_range', label: 'Credit score range', maxScore: 25, tiers: [{ threshold: 500, score: 0 }, { threshold: 600, score: 10 }, { threshold: 700, score: 20 }, { threshold: 999, score: 25 }] },
      { key: 'report_access', label: 'Credit report access', maxScore: 15, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 8 }, { threshold: 2, score: 15 }] },
      { key: 'recency', label: 'Recency of check', maxScore: 10, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 5 }, { threshold: 2, score: 10 }] },
      { key: 'bureau_coverage', label: 'Bureau coverage', maxScore: 10, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 3 }, { threshold: 2, score: 6 }, { threshold: 3, score: 10 }] },
    ],
  },
  {
    id: 'utilization',
    label: 'Utilization Readiness',
    weight: 0.15,
    factors: [
      { key: 'utilization_percent', label: 'Utilization %', maxScore: 40, tiers: [{ threshold: 70, score: 0 }, { threshold: 50, score: 10 }, { threshold: 30, score: 20 }, { threshold: 10, score: 30 }, { threshold: 0, score: 40 }] },
      { key: 'maxed_out', label: 'Maxed-out cards', maxScore: 20, tiers: [{ threshold: 1, score: 0 }, { threshold: 0, score: 20 }] },
      { key: 'balances_trend', label: 'Balances trending', maxScore: 20, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 10 }, { threshold: 2, score: 20 }] },
    ],
  },
  {
    id: 'negative_items',
    label: 'Negative Item Risk',
    weight: 0.20,
    factors: [
      { key: 'late_payments', label: 'Late payments', maxScore: 20, tiers: [{ threshold: 4, score: 0 }, { threshold: 1, score: 10 }, { threshold: 0, score: 20 }] },
      { key: 'collections', label: 'Collections', maxScore: 20, tiers: [{ threshold: 3, score: 0 }, { threshold: 1, score: 10 }, { threshold: 0, score: 20 }] },
      { key: 'chargeoffs', label: 'Charge-offs', maxScore: 20, tiers: [{ threshold: 3, score: 0 }, { threshold: 1, score: 10 }, { threshold: 0, score: 20 }] },
      { key: 'judgments', label: 'Judgments/liens', maxScore: 15, tiers: [{ threshold: 1, score: 0 }, { threshold: 0, score: 15 }] },
      { key: 'bankruptcies', label: 'Bankruptcies', maxScore: 15, tiers: [{ threshold: 1, score: 0 }, { threshold: 0, score: 15 }] },
      { key: 'inaccurate_items', label: 'Inaccurate items', maxScore: 10, tiers: [{ threshold: 0, score: 5 }, { threshold: 1, score: 10 }] },
    ],
  },
  {
    id: 'inquiries',
    label: 'Inquiry Risk',
    weight: 0.05,
    factors: [
      { key: 'hard_inquiries', label: 'Hard inquiries (12mo)', maxScore: 50, tiers: [{ threshold: 6, score: 0 }, { threshold: 3, score: 20 }, { threshold: 0, score: 50 }] },
      { key: 'recent_apps', label: 'Recent applications', maxScore: 50, tiers: [{ threshold: 1, score: 0 }, { threshold: 0, score: 50 }] },
    ],
  },
  {
    id: 'business_foundation',
    label: 'Business Foundation Readiness',
    weight: 0.15,
    factors: [
      { key: 'entity_type', label: 'Entity type', maxScore: 20, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 5 }, { threshold: 2, score: 10 }, { threshold: 3, score: 20 }] },
      { key: 'good_standing', label: 'Good standing', maxScore: 15, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 15 }] },
      { key: 'ein', label: 'EIN status', maxScore: 15, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 8 }, { threshold: 2, score: 15 }] },
      { key: 'duns', label: 'DUNS status', maxScore: 15, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 5 }, { threshold: 2, score: 10 }, { threshold: 3, score: 15 }] },
      { key: 'address', label: 'Business address', maxScore: 10, tiers: [{ threshold: 0, score: 3 }, { threshold: 1, score: 7 }, { threshold: 2, score: 10 }] },
      { key: 'phone', label: 'Business phone', maxScore: 10, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 5 }, { threshold: 2, score: 10 }] },
      { key: 'email', label: 'Business email', maxScore: 10, tiers: [{ threshold: 0, score: 3 }, { threshold: 1, score: 10 }] },
      { key: 'website', label: 'Business website', maxScore: 5, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 2 }, { threshold: 2, score: 5 }] },
    ],
  },
  {
    id: 'bankability',
    label: 'Business Bankability',
    weight: 0.10,
    factors: [
      { key: 'bank_account', label: 'Business bank account', maxScore: 30, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 10 }, { threshold: 2, score: 20 }, { threshold: 3, score: 30 }] },
      { key: 'biz_credit_card', label: 'Business credit card', maxScore: 20, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 20 }] },
      { key: 'dnb_profile', label: 'D&B profile', maxScore: 20, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 5 }, { threshold: 2, score: 20 }] },
      { key: 'paydex', label: 'PAYDEX score', maxScore: 15, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 5 }, { threshold: 2, score: 10 }, { threshold: 3, score: 15 }] },
      { key: 'tradelines', label: 'Vendor tradelines', maxScore: 15, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 8 }, { threshold: 3, score: 15 }] },
    ],
  },
  {
    id: 'funding_docs',
    label: 'Funding Document Readiness',
    weight: 0.05,
    factors: [
      { key: 'doc_count', label: 'Documents available', maxScore: 50, tiers: [{ threshold: 2, score: 0 }, { threshold: 4, score: 10 }, { threshold: 6, score: 20 }, { threshold: 8, score: 35 }, { threshold: 10, score: 50 }] },
      { key: 'key_docs', label: 'Key documents present', maxScore: 50, tiers: [{ threshold: 0, score: 0 }, { threshold: 1, score: 15 }, { threshold: 2, score: 30 }, { threshold: 3, score: 50 }] },
    ],
  },
  {
    id: 'funding_timing',
    label: 'Funding Timing Readiness',
    weight: 0.05,
    factors: [
      { key: 'timeline', label: 'Timeline alignment', maxScore: 40, tiers: [{ threshold: 0, score: 10 }, { threshold: 1, score: 20 }, { threshold: 2, score: 30 }, { threshold: 3, score: 40 }] },
      { key: 'willingness', label: 'Action willingness', maxScore: 30, tiers: [{ threshold: 0, score: 5 }, { threshold: 1, score: 15 }, { threshold: 2, score: 30 }] },
      { key: 'constraint', label: 'Constraint severity', maxScore: 30, tiers: [{ threshold: 0, score: 10 }, { threshold: 1, score: 15 }, { threshold: 2, score: 20 }, { threshold: 3, score: 30 }] },
    ],
  },
];

export const READINESS_TIERS: ReadinessTierDef[] = [
  { tier: 'not_ready', label: 'Not Ready', range: [0, 25], description: 'Significant gaps in credit and/or business foundation. Must address basics before funding applications.' },
  { tier: 'needs_cleanup', label: 'Needs Cleanup First', range: [26, 45], description: 'Partial foundation exists but negative items, utilization, or missing setup items block progress. Focus on cleanup.' },
  { tier: 'almost_ready', label: 'Almost Ready', range: [46, 65], description: 'Core foundation in place. Address specific gaps and timing issues. 3-6 months of preparation recommended.' },
  { tier: 'ready_starter', label: 'Ready for Starter Funding Path', range: [66, 80], description: 'Solid foundation. Pursue starter funding options (business credit cards, small lines of credit).' },
  { tier: 'ready_advanced', label: 'Ready for Advanced Funding Review', range: [81, 100], description: 'Strong profile. Pursue advanced funding options (SBA loans, larger lines of credit).' },
];

export function getReadinessTier(score: number): ReadinessTierDef {
  for (const tier of READINESS_TIERS) {
    if (score >= tier.range[0] && score <= tier.range[1]) return tier;
  }
  return READINESS_TIERS[0];
}

export function scoreFactorValue(factor: ScoreFactor, value: number): number {
  let bestScore = 0;
  for (const tier of factor.tiers) {
    if (value >= tier.threshold) bestScore = tier.score;
  }
  return Math.min(bestScore, factor.maxScore);
}

export function scoreSection(section: ScoreSection, answers: Record<string, number>): number {
  let total = 0;
  for (const factor of section.factors) {
    total += scoreFactorValue(factor, answers[factor.key] ?? 0);
  }
  const maxPossible = section.factors.reduce((s, f) => s + f.maxScore, 0);
  return maxPossible > 0 ? Math.round((total / maxPossible) * 100) : 0;
}

export function calculateOverallScore(answers: Record<string, number>): number {
  let weighted = 0;
  for (const section of SCORE_SECTIONS) {
    const sectionScore = scoreSection(section, answers);
    weighted += sectionScore * section.weight;
  }
  return Math.round(weighted);
}
