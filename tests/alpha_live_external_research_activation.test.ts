import { describe, expect, it } from 'vitest';
import fs from 'node:fs';

describe('Alpha live external research activation', () => {
  const bridge = fs.readFileSync('scripts/telegram/nexus_telegram_bridge.py', 'utf8');
  const live = fs.readFileSync('scripts/alpha/alpha_live_research.py', 'utf8');
  const commandCenter = fs.readFileSync('src/components/CommandCenter.jsx', 'utf8');

  it('routes command and natural language Alpha research to the live provider bridge', () => {
    expect(bridge).toContain('from alpha_live_research import run_alpha_live_research, format_alpha_live_research_response');
    expect(bridge).toContain('def is_alpha_live_research_request');
    expect(bridge).toContain('return _handle_alpha_research(topic)');
    expect(bridge).toContain('ALPHA_RESEARCH_PATTERNS');
    expect(bridge).toContain('business|affiliate|technology|grant|funding|market|competitor|opportun');
    expect(bridge).toContain('run_alpha_live_research(text, source="telegram")');
  });

  it('uses live Brave retrieval and OpenRouter synthesis with source persistence', () => {
    expect(live).toContain('https://api.search.brave.com/res/v1/web/search');
    expect(live).toContain('https://openrouter.ai/api/v1/chat/completions');
    expect(live).toContain('nexus_research_runs');
    expect(live).toContain('nexus_research_results');
    expect(live).toContain('business_opportunities');
    expect(live).toContain('client_data_used');
    expect(live).toContain('provider_query');
    expect(live).not.toContain('print(os.environ');
  });

  it('exposes runtime-backed Alpha evidence in the Command Center', () => {
    expect(commandCenter).toContain('/runtime/alpha-live-research-status.json');
    expect(commandCenter).toContain('executive-alpha-live-research');
    expect(commandCenter).toContain('Brave PASS');
    expect(commandCenter).toContain('OpenRouter PASS');
  });
});
