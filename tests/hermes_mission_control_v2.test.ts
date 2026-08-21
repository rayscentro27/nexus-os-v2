import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import snapshot from '../public/runtime/nexus-mission-control.json';

describe('Mission Control canonical read model', () => {
  it('aggregates the certified runtime stack without becoming an authority', () => {
    expect(snapshot.read_only).toBe(true);
    expect(snapshot.system.core_runtime.status).toBe('HEALTHY');
    expect(snapshot.system.active_operator.status).toBe('HEALTHY');
    expect(snapshot.system.recovery_check.status).toBe('NO_ACTION_REQUIRED');
    expect(snapshot.system.hermes.status).toBe('HEALTHY');
    expect(snapshot.activity.last_continuous_loop.delta_status).toBe('NO_CHANGE');
    expect(snapshot.safety.stripe_autonomy).toBe('DISABLED');
    expect(snapshot.safety.arbitrary_shell).toBe('UNAVAILABLE');
  });

  it('keeps optional integrations separate from core health', () => {
    expect(snapshot.system.overall_status).toBe('HEALTHY');
    expect(snapshot.optional_integrations.alpha.status).toBe('NOT_ENABLED');
    expect(snapshot.optional_integrations.nova.status).toBe('NOT_ENABLED');
  });

  it('does not expose secrets or client-sensitive fields', () => {
    const text = readFileSync('public/runtime/nexus-mission-control.json', 'utf8');
    expect(text).not.toMatch(/STRIPE_SECRET_KEY|TELEGRAM_BOT_TOKEN|runtime\.env|client_profiles/i);
    expect(text).not.toMatch(/client_id|email|phone|ssn|account_number/i);
  });

  it('renders the canonical read-only surface', () => {
    const ui = readFileSync('src/components/command-center/HermesMissionControlV2.tsx', 'utf8');
    expect(ui).toContain('data-testid="hermes-mission-control-v2"');
    expect(ui).toContain('data-testid="mission-card-needs-ray"');
    expect(ui).toContain('data-testid="mission-card-activity"');
    expect(ui).not.toMatch(/insert\(|update\(|delete\(|sendMessage|launchctl/i);
  });
});
