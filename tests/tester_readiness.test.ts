import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '..')

describe('tester readiness system', () => {
  describe('database migration', () => {
    const migrationPath = resolve(ROOT, 'supabase/migrations/20260715160000_tester_readiness_system.sql')

    it('migration file exists', () => {
      expect(existsSync(migrationPath)).toBe(true)
    })

    it('creates tester_sessions table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.tester_sessions')
      expect(sql).toContain('persona text not null')
      expect(sql).toContain('tester_name text not null')
      expect(sql).toContain('status text not null default')
    })

    it('creates tester_feedback table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.tester_feedback')
      expect(sql).toContain('issue_title text not null')
      expect(sql).toContain('severity text not null default')
      expect(sql).toContain('reproducibility text default')
    })

    it('creates tester_readiness_history table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.tester_readiness_history')
      expect(sql).toContain('overall_status text default')
    })

    it('enables RLS on all tables', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      const rlsCount = (sql.match(/alter table public\.tester_\w+ enable row level security/g) || []).length
      expect(rlsCount).toBe(3)
    })

    it('creates admin-only policies', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('nexus_is_active_admin()')
      const policyCount = (sql.match(/create policy "tester_/g) || []).length
      expect(policyCount).toBeGreaterThanOrEqual(9)
    })

    it('has proper check constraints', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain("check (persona in ('a', 'b', 'c'))")
      expect(sql).toContain("check (severity in ('blocker', 'high', 'medium', 'low', 'cosmetic'))")
      expect(sql).toContain("check (status in ('in_progress', 'completed', 'blocked', 'abandoned'))")
    })

    it('creates indexes', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create index if not exists idx_tester_sessions_persona')
      expect(sql).toContain('create index if not exists idx_tester_feedback_severity')
      expect(sql).toContain('create index if not exists idx_tester_readiness_persona')
    })
  })

  describe('reset script', () => {
    const scriptPath = resolve(ROOT, 'scripts/testers/reset_synthetic_credit_case.py')

    it('reset script exists', () => {
      expect(existsSync(scriptPath)).toBe(true)
    })

    it('has --persona flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--persona'")
    })

    it('has --dry-run flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--dry-run'")
    })

    it('has --verify flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--verify'")
    })

    it('does not delete Auth users', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).not.toContain('DELETE FROM auth')
      expect(script).not.toContain('DELETE FROM public.auth')
    })

    it('does not target non-synthetic clients', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain('Never deletes')
    })

    it('RESET_TABLES uses FK-safe ordering', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("'credit_strategy_selection_history'")
      expect(script).toContain("'credit_strategy_client_selections'")
      expect(script).toContain("'client_documents'")
      const selectionIdx = script.indexOf("'credit_strategy_client_selections'")
      const draftIdx = script.indexOf("'credit_strategy_drafts'")
      expect(selectionIdx).toBeLessThan(draftIdx)
    })
  })

  describe('replay script', () => {
    const scriptPath = resolve(ROOT, 'scripts/testers/replay_synthetic_credit_case.py')

    it('replay script exists', () => {
      expect(existsSync(scriptPath)).toBe(true)
    })

    it('has --full flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--full'")
    })

    it('has --initial-only flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--initial-only'")
    })

    it('has --follow-up-only flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--follow-up-only'")
    })

    it('has --verify flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--verify'")
    })

    it('has --dry-run flag', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("add_argument('--dry-run'")
    })

    it('verifies parser results', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain('credit_report_parser_results')
    })

    it('verifies canonical accounts', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain('credit_canonical_accounts')
    })

    it('verifies strategy matches', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain('credit_strategy_matches')
    })
  })

  describe('readiness report generator', () => {
    const scriptPath = resolve(ROOT, 'scripts/testers/generate_tester_readiness_report.py')

    it('report script exists', () => {
      expect(existsSync(scriptPath)).toBe(true)
    })

    it('outputs markdown', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain('tester_readiness_latest.md')
    })

    it('outputs json', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain('tester_readiness_latest.json')
    })

    it('does not include credentials', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).not.toContain('password =')
      expect(script).not.toContain('api_key =')
      expect(script).not.toContain('token =')
    })

    it('includes all personas', () => {
      const script = readFileSync(scriptPath, 'utf8')
      expect(script).toContain("'a':")
      expect(script).toContain("'b':")
      expect(script).toContain("'c':")
    })
  })

  describe('admin panel component', () => {
    const componentPath = resolve(ROOT, 'src/components/TesterReadinessPanel.jsx')

    it('panel component exists', () => {
      expect(existsSync(componentPath)).toBe(true)
    })

    it('defines all three personas', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).toContain("key: 'a'")
      expect(component).toContain("key: 'b'")
      expect(component).toContain("key: 'c'")
    })

    it('has status badges', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).toContain('StatusBadge')
      expect(component).toContain('ready')
      expect(component).toContain('incomplete')
      expect(component).toContain('failed')
    })

    it('has persona cards', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).toContain('PersonaCard')
    })

    it('has feedback form', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).toContain('FeedbackForm')
      expect(component).toContain('issue_title')
      expect(component).toContain('severity')
      expect(component).toContain('reproducibility')
    })

    it('has session form', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).toContain('SessionForm')
      expect(component).toContain('tester_sessions')
    })

    it('has confirmation modal', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).toContain('ConfirmationModal')
    })

    it('has warning banner', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).toContain('Synthetic test data only')
    })

    it('does not expose passwords', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).not.toContain('E2E_PERSONA_A_PASSWORD')
      expect(component).not.toContain('E2E_PERSONA_B_PASSWORD')
      expect(component).not.toContain('E2E_PERSONA_C_PASSWORD')
    })

    it('does not expose service role key', () => {
      const component = readFileSync(componentPath, 'utf8')
      expect(component).not.toContain('SUPABASE_SERVICE_ROLE_KEY')
    })
  })

  describe('admin UI integration', () => {
    const adminPath = resolve(ROOT, 'src/admin/NexusAdminUI.jsx')

    it('imports TesterReadinessPanel', () => {
      const admin = readFileSync(adminPath, 'utf8')
      expect(admin).toContain("import TesterReadinessPanel from")
    })

    it('has tester-readiness nav item', () => {
      const admin = readFileSync(adminPath, 'utf8')
      expect(admin).toContain("id: 'tester-readiness'")
      expect(admin).toContain('Tester Readiness')
    })

    it('has tester-readiness page mapping', () => {
      const admin = readFileSync(adminPath, 'utf8')
      expect(admin).toContain("'tester-readiness':")
      expect(admin).toContain('<TesterReadinessPanel')
    })

    it('has modeLabel for tester-readiness', () => {
      const admin = readFileSync(adminPath, 'utf8')
      expect(admin).toContain("'tester-readiness': 'Tester Readiness")
    })
  })
})
