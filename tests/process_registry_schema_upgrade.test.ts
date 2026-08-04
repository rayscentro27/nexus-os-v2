import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('authoritative process registry schema', () => {
  const migration = fs.readFileSync(path.join(process.cwd(), 'supabase/migrations/20260803120000_authoritative_process_run_registry.sql'), 'utf8');

  it('creates process definitions and run lifecycle tables with required states', () => {
    expect(migration).toContain('create table if not exists public.nexus_process_definitions');
    expect(migration).toContain('create table if not exists public.nexus_process_runs');
    for (const state of ['QUEUED', 'RUNNING', 'SUCCEEDED', 'PARTIAL', 'FAILED', 'BLOCKED', 'CANCELLED', 'TIMED_OUT', 'SIMULATED', 'UNKNOWN']) {
      expect(migration).toContain(state);
    }
  });

  it('keeps operational and research tables admin-only via existing active-admin function', () => {
    expect(migration).toContain('alter table public.nexus_process_definitions enable row level security');
    expect(migration).toContain('alter table public.nexus_research_results enable row level security');
    expect(migration.match(/public\.nexus_is_active_admin\(\)/g)?.length ?? 0).toBeGreaterThanOrEqual(5);
    expect(migration).not.toMatch(/to anon/i);
  });
});
