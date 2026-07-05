/**
 * Nexus OS v2 — Alpha Research Intake / Decision Packets
 * Prompt 2: Phase K
 *
 * Processes independent research items and generates decision packets
 * with scoring, recommendations, and Ray Review routing.
 */

export type SourceType =
  | 'youtube_video'
  | 'tiktok_video'
  | 'github_repo'
  | 'business_idea'
  | 'tool_software'
  | 'grant_page'
  | 'credit_card_offer'
  | 'affiliate_opportunity'
  | 'landing_page_example'
  | 'trading_strategy'
  | 'payment_infrastructure'
  | 'marketing_automation'
  | 'app_idea';

export interface DecisionPacket {
  packet_id: string;
  source_type: SourceType;
  source_url: string;
  title: string;
  summary: string;
  what_it_is: string;
  why_it_matters: string;
  money_angle: string;
  nexus_fit: string;
  department: string;
  activation_mode: string;
  score: number;
  risk: string;
  hype_check: string;
  recommended_action: string;
  branch_recommendation: string;
  ray_review_required: boolean;
  evidence: string[];
  next_test: string;
  created_at: string;
}

let packetCounter = 0;

export function generatePacketId(): string {
  packetCounter++;
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 6);
  return `packet_${ts}_${rand}_${packetCounter}`;
}

export function scoreDecisionPacket(packet: Omit<DecisionPacket, 'score' | 'ray_review_required'>): DecisionPacket {
  let score = 0;

  // Content Quality (0-30)
  if (packet.what_it_is.length > 50) score += 10;
  if (packet.why_it_matters.length > 50) score += 10;
  if (packet.evidence.length > 0) score += 10;

  // Relevance (0-25)
  const relevantDepartments = ['research', 'marketing', 'trading', 'billing_referral', 'app'];
  if (relevantDepartments.includes(packet.department)) score += 15;
  if (packet.nexus_fit.length > 30) score += 10;

  // Monetization Potential (0-25)
  if (packet.money_angle.length > 30) score += 15;
  if (packet.recommended_action.length > 20) score += 10;

  // Actionability (0-20)
  if (packet.next_test.length > 20) score += 10;
  if (packet.branch_recommendation.length > 10) score += 10;

  score = Math.min(100, Math.max(0, score));

  const ray_review_required = score >= 80;

  return {
    ...packet,
    score,
    ray_review_required,
  };
}

export function classifySourceType(input: string): SourceType {
  const lower = input.toLowerCase();
  if (/youtube\.com|youtu\.be/.test(lower)) return 'youtube_video';
  if (/tiktok\.com/.test(lower)) return 'tiktok_video';
  if (/github\.com/.test(lower)) return 'github_repo';
  if (/grant|apply.*fund/.test(lower)) return 'grant_page';
  if (/credit.*card|offer.*card/.test(lower)) return 'credit_card_offer';
  if (/affiliate|referral|partner/.test(lower)) return 'affiliate_opportunity';
  if (/landing.*page|squeeze|funnel/.test(lower)) return 'landing_page_example';
  if (/trade|backtest|strategy|oanda/.test(lower)) return 'trading_strategy';
  if (/stripe|payment|billing|checkout/.test(lower)) return 'payment_infrastructure';
  if (/email|newsletter|automation/.test(lower)) return 'marketing_automation';
  if (/app|build.*app|feature/.test(lower)) return 'app_idea';
  if (/tool|software|saas/.test(lower)) return 'tool_software';
  return 'business_idea';
}

export function createDecisionPacket(
  sourceType: SourceType,
  url: string,
  title: string,
  summary: string,
  overrides: Partial<DecisionPacket> = {}
): DecisionPacket {
  const now = new Date().toISOString();
  const base: Omit<DecisionPacket, 'score' | 'ray_review_required'> = {
    packet_id: generatePacketId(),
    source_type: sourceType,
    source_url: url,
    title,
    summary,
    what_it_is: '',
    why_it_matters: '',
    money_angle: '',
    nexus_fit: '',
    department: 'research',
    activation_mode: 'DRY_RUN',
    risk: '',
    hype_check: '',
    recommended_action: '',
    branch_recommendation: '',
    evidence: [],
    next_test: '',
    created_at: now,
    ...overrides,
  };
  return scoreDecisionPacket(base);
}

export function getScoreClassification(score: number): {
  classification: string;
  action: string;
  visibility: string;
  ray_review: boolean;
} {
  if (score >= 80) return { classification: 'high_value', action: 'ray_review_required', visibility: 'ray_review_queue', ray_review: true };
  if (score >= 60) return { classification: 'opportunity_candidate', action: 'weekly_review', visibility: 'alpha_hermes', ray_review: false };
  if (score >= 40) return { classification: 'medium_value', action: 'archive_with_summary', visibility: 'research_archive', ray_review: false };
  return { classification: 'low_value', action: 'metadata_only', visibility: 'hidden', ray_review: false };
}
