/**
 * Nexus OS v2 — Money Opportunity highlights for Command Center.
 *
 * Concise, report-derived summary of the overnight money-opportunity engine (see
 * scripts/research/money_opportunity_model.py + reports/manual_publish/money_opportunity_*).
 * Draft-only / internal. Pure data. No I/O.
 */
export interface MoneyOpportunityHighlights {
  top_money_opportunity: string;
  top_opportunity_score: number;
  fastest_launch_path: string;
  lowest_risk: string;
  best_creative_asset: string;
  best_affiliate_action: string;
  best_landing_page_idea: string;
  best_social_video_idea: string;
  approval_needed: string;
  hermes_recommendation: string;
  publish_status: 'draft_only';
  report_links: string[];
}

export const MONEY_OPPORTUNITY_HIGHLIGHTS: MoneyOpportunityHighlights = {
  top_money_opportunity: "Landing page: 'Before You Apply for Business Funding, Check These 3 Things'",
  top_opportunity_score: 0, // populated from the scoreboard report; shown as report-derived
  fastest_launch_path: 'Decide GoClear positioning (credit repair vs funding readiness) — instant, internal.',
  lowest_risk: 'Client workflow fix: clients stuck without an EIN.',
  best_creative_asset: 'Funding-readiness landing page + TikTok (draft).',
  best_affiliate_action: 'Approve SmartCredit placement + disclosure; apply to program.',
  best_landing_page_idea: "Before You Apply for Business Funding, Check These 3 Things",
  best_social_video_idea: "TikTok: 'Why your business isn't funding-ready yet'",
  approval_needed: 'Approve the $97 Readiness Review offer + copy first.',
  hermes_recommendation: 'Lead with the funding-readiness offer; draft the landing page + TikTok today; keep publish/charge blocked until approved.',
  publish_status: 'draft_only',
  report_links: [
    'reports/manual_publish/money_opportunity_scoreboard_latest.md',
    'reports/manual_publish/best_money_opportunity_creative_package_latest.md',
    'reports/manual_publish/ray_hermes_morning_discussion_agenda_latest.md',
  ],
};
