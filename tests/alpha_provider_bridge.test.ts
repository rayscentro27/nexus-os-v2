import { afterEach, describe, expect, it, vi } from 'vitest';
import fs from 'node:fs';
import { alphaProviderActivationSteps, defaultAlphaProviderStatus } from '../src/hermes/alpha/alphaProviderStatus';
import { fetchAlphaProviderStatus, runAlphaProviderBridge } from '../src/hermes/alpha/alphaProviderBridge';

afterEach(() => vi.unstubAllGlobals());

describe('Alpha provider bridge', () => {
  it('always has deterministic fallback and safe disabled defaults', () => {
    expect(defaultAlphaProviderStatus).toMatchObject({
      activeProvider: 'deterministic_local',
      liveWeb: false,
      supabase: false,
      clientData: false,
    });
    expect(defaultAlphaProviderStatus.providers.deterministic_local.available).toBe(true);
    expect(defaultAlphaProviderStatus.providers.groq.available).toBe(false);
    expect(defaultAlphaProviderStatus.providers.openrouter.available).toBe(false);
  });

  it('missing status bridge does not break Alpha', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    expect(await fetchAlphaProviderStatus()).toEqual(defaultAlphaProviderStatus);
  });

  it('does not call bridge for deterministic provider', async () => {
    await expect(runAlphaProviderBridge('deterministic_local', 'hello')).resolves.toMatchObject({
      ok: false,
      error: 'deterministic_provider_uses_local_engine',
    });
  });

  it('contains activation instructions without frontend env names', () => {
    expect(alphaProviderActivationSteps.ollama_local.join(' ')).toMatch(/Ollama/);
    expect(alphaProviderActivationSteps.groq.join(' ')).toMatch(/Groq credential/);
    expect(alphaProviderActivationSteps.openrouter.join(' ')).toMatch(/OpenRouter credential/);
  });

  it('keeps provider keys out of browser bridge code', () => {
    const frontend = [
      'src/hermes/alpha/alphaProviderBridge.ts',
      'src/hermes/alpha/alphaProviderStatus.ts',
      'src/components/HermesAlphaWorkspace.tsx',
    ].map((p) => fs.readFileSync(p, 'utf8')).join('\n');
    expect(frontend).not.toMatch(/GROQ_API_KEY|OPENROUTER_API_KEY|BRAVE_SEARCH_API_KEY|FIRECRAWL_API_KEY|Bearer /);

    const netlifyFunction = fs.readFileSync('netlify/functions/alpha-provider.mjs', 'utf8');
    expect(netlifyFunction).toMatch(/process\.env\.GROQ_API_KEY/);
    expect(netlifyFunction).toMatch(/process\.env\.OPENROUTER_API_KEY/);
  });

  it('allows the local Vite bridge to use hosted providers server-side', () => {
    const viteConfig = fs.readFileSync('vite.config.ts', 'utf8');
    expect(viteConfig).toMatch(/path === '\/api\/alpha\/status'/);
    expect(viteConfig).toMatch(/OPENROUTER_API_KEY/);
    expect(viteConfig).toMatch(/GROQ_API_KEY/);
    expect(viteConfig).toMatch(/historySent/);
    expect(viteConfig).toMatch(/noSupabaseUsed/);
    expect(viteConfig).not.toMatch(/VITE_OPENROUTER_API_KEY|VITE_GROQ_API_KEY/);
  });
});
