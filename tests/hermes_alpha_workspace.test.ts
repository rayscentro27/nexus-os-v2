import { describe, expect, it } from 'vitest';
import fs from 'node:fs';

const workspace = () => fs.readFileSync('src/components/HermesAlphaWorkspace.tsx', 'utf8');

describe('Alpha workspace UI', () => {
  it('is direct and shows provider, memory, cost, search, and safety controls', () => {
    const s = workspace();
    for (const x of [
      'Conversation',
      'Opportunity Canvas',
      'Provider & Cost Controls',
      'Usage Today',
      'Memory & Sources',
      'Action Draft',
      'Handoff / export',
      'Clear conversation',
      'Send to Alpha',
      'ALPHA IS SEPARATE FROM NEXUS HERMES',
      'No Supabase',
      'No client data',
      'alpha-sticky-composer',
      "gridTemplateRows:'auto minmax(0,1fr) auto'",
    ]) expect(s).toContain(x);
    expect(s).not.toMatch(/import .*hermes\/nexus/i);
  });

  it('migrates stale local-only preferences to a healthy hosted provider in model-first pilot', () => {
    const s = workspace();
    for (const x of [
      'PREF_VERSION_KEY',
      'staleLocal',
      "localStorage.getItem(PROVIDER_KEY)==='deterministic_local'||getAlphaCostMode()==='cheap'",
      'localStorage.setItem(PROVIDER_KEY,preferred)',
      "setAlphaCostMode(preferred==='openrouter'?'strategy':'fast')",
      'Migrated obsolete local-only Alpha preferences',
    ]) expect(s).toContain(x);
  });

  it('exposes selected and actual provider plus stable composer controls', () => {
    const s = workspace();
    for (const x of [
      'const actualProvider=',
      'Selected: {provider}',
      'Actual: {actualProvider}',
      'data-testid="alpha-conversation-panel"',
      'data-testid="alpha-composer"',
      'data-testid="alpha-transcript"',
      'data-testid="alpha-composer-input"',
      'data-testid="alpha-composer-send"',
      'minHeight:84',
      'Composer: mounted',
    ]) expect(s).toContain(x);
  });

  it('offers all modes', () => {
    const s = fs.readFileSync('src/hermes/alpha/hermesAlphaModeRouter.ts', 'utf8');
    expect((s.match(/"[A-Za-z /]+"/g) || []).length).toBeGreaterThanOrEqual(12);
  });
});
