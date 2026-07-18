import { describe, expect, it } from 'vitest';
import { classifyIntent, hermesResponseRouter } from '../src/lib/hermesResponseRouter';

describe('Hermes executive intents', () => {
  it('routes daily brief requests to the executive read model', () => {
    expect(classifyIntent('Give me the executive daily brief')).toBe('executive_daily_brief');
    const response = hermesResponseRouter({ message: 'Give me the executive daily brief', pageId: 'command' });
    expect(response.source).toBe('report_context');
    expect(response.text).toMatch(/Facts:/);
    expect(response.text).toMatch(/Recommendations:/);
  });

  it('does not convert executive questions into work creation', () => {
    const response = hermesResponseRouter({ message: 'What should we do first?', pageId: 'command' });
    expect(response.questionType).toBe('executive_priorities');
    expect(response.text).toMatch(/recommendations, not approvals/i);
  });

  it('keeps repo intelligence read-only and writer access disabled', () => {
    const response = hermesResponseRouter({ message: 'What is the GitHub MCP repo intelligence status?', pageId: 'command' });
    expect(response.questionType).toBe('executive_repo_intelligence');
    expect(response.text).toMatch(/No external repository is installed/i);
    expect(response.text).toMatch(/Writer access remains disabled/i);
  });

  it('preserves live Stripe deferral in revenue answers', () => {
    const response = hermesResponseRouter({ message: 'What is the executive revenue status?', pageId: 'command' });
    expect(response.questionType).toBe('executive_revenue_status');
    expect(response.text).toMatch(/LIVE STRIPE CONFIGURATION DEFERRED UNTIL NEXUS 3.0 COMPLETION/);
  });

  it('answers capability questions from the Capability OS read model', () => {
    const response = hermesResponseRouter({ message: 'Which capabilities are active and blocked?', pageId: 'command' });
    expect(response.questionType).toBe('capability_activation');
    expect(response.text).toMatch(/Live Stripe is DEFERRED/);
    expect(response.text).toMatch(/Alpha Supabase access is PROHIBITED/);
  });

  it('explains capability credential requirements without exposing values', () => {
    const response = hermesResponseRouter({ message: 'Which capabilities need credentials?', pageId: 'command' });
    expect(response.questionType).toBe('capability_credentials');
    expect(response.text).toMatch(/Credential metadata stores identifiers only/);
    expect(response.text).not.toMatch(/sk_live_|whsec_|password-value/);
  });
});
