import { describe, expect, it } from 'vitest';
import { hermesDailyBrief, renderHermesDailyBrief } from '../src/data/hermesDailyBriefData';

describe('Hermes Phase 11 Daily Brief', () => {
  it('uses the canonical report-backed opportunity and cost facts', () => {
    expect(hermesDailyBrief.opportunity_updates[0].title).toBe('Crawl4AI');
    expect(hermesDailyBrief.opportunity_updates[0].status).toBe('PILOT_PROPOSED');
    expect(hermesDailyBrief.revenue_status.confirmed_revenue_usd).toBe(0);
    expect(hermesDailyBrief.cost_summary.provider_cost_usd).toBe(0);
    expect(hermesDailyBrief.freshness.live_supabase_read).toBe('NOT_AVAILABLE');
  });

  it('renders worker health, unknowns, decisions, and next action', () => {
    const rendered = renderHermesDailyBrief();
    expect(rendered).toContain('codex: AVAILABLE');
    expect(rendered).toContain('opencode: UNAVAILABLE');
    expect(rendered).toContain('mimo: INSTALLED_UNPROVEN');
    expect(rendered).toContain('trend UNKNOWN');
    expect(rendered).toContain('Ray decisions:');
    expect(rendered).toContain('$97 Stripe test Checkout');
  });
});
