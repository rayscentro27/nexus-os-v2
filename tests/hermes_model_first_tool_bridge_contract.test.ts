import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

const edgeSource = readFileSync(new URL('../supabase/functions/hermes-chat/index.ts', import.meta.url), 'utf8');

describe('Hermes model-first Edge tool bridge contract', () => {
  it('uses native conversational text-or-tool calling as the model-first path', () => {
    expect(edgeSource).toContain('runConversationalOpenRouter');
    expect(edgeSource).toContain('callOpenRouterNative');
    expect(edgeSource).toContain('payload.tools = tools');
    expect(edgeSource).toContain("payload.tool_choice = 'auto'");
    expect(edgeSource).toContain("source: 'GENERAL_MODEL'");
  });

  it('registers the approved model-facing Nexus tools centrally', () => {
    [
      'get_current_time',
      'get_hermes_identity',
      'get_nexus_version',
      'get_project_status',
      'get_system_health',
      'list_reports',
      'summarize_report',
      'get_client_aggregate',
      'get_approval_summary',
      'get_department_status',
      'get_revenue_status',
      'get_repo_intelligence_status',
      'get_answer_provenance',
      'draft_task',
      'draft_ray_review',
      'draft_schedule',
    ].forEach((toolName) => {
      expect(edgeSource).toContain(`${toolName}:`);
    });
  });

  it('keeps tool execution server-side and denies unsafe tool requests', () => {
    expect(edgeSource).toContain('validateToolRequest');
    expect(edgeSource).toContain('UNKNOWN_TOOL');
    expect(edgeSource).toContain('INVALID_ARGUMENTS');
    expect(edgeSource).toContain('UNAUTHORIZED_ACTOR');
    expect(edgeSource).toContain('SELF_APPROVAL_PROHIBITED');
    expect(edgeSource).toContain('executeToolRequest');
    expect(edgeSource).toContain("actionClass: 'DRAFT_ONLY'");
    expect(edgeSource).toContain("executionStatus: 'NOT_EXECUTED'");
  });

  it('uses the bridge only for model-first mode and preserves legacy direct chat outside the pilot path', () => {
    expect(edgeSource).toContain("mode === 'model_first_conversation'");
    expect(edgeSource).toContain('runConversationalOpenRouter');
    expect(edgeSource).toContain('body: JSON.stringify({ model: m, messages, max_tokens: MAX_OUTPUT_TOKENS })');
  });

  it('does not expose provider or service credentials through Vite variables', () => {
    expect(edgeSource).not.toMatch(/VITE_.*OPENROUTER/i);
    expect(edgeSource).not.toMatch(/VITE_.*SERVICE/i);
    expect(edgeSource).toContain("Deno.env.get('OPENROUTER_API_KEY')");
    expect(edgeSource).toContain("Deno.env.get('SUPABASE_ANON_KEY')");
  });
});
