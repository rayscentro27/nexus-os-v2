import { describe, expect, it } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '..')
const read = (relativePath: string) => readFileSync(resolve(ROOT, relativePath), 'utf8')

describe('Phase 5 — controlled synthetic pilot safety', () => {
  it('reset script fails closed to one exact synthetic persona', () => {
    const code = read('scripts/testers/reset_synthetic_credit_case.py')
    expect(code).toContain('/auth/v1/admin/users')
    expect(code).toContain('PERSONA_EMAILS')
    expect(code).toContain('nexus-persona-a-browser@goclear.test')
    expect(code).toContain('gc_[0-9a-f]{32}')
    expect(code).toContain('if len(matches) != 1')
    expect(code).toContain('if args.dry_run and not args.verify')
    expect(code).not.toContain('fallback')
    expect(code).toContain('delete_pair')
    expect(code).toContain('protected storage objects: untouched')
  })

  it('replay is persona-scoped, bounded, and supports explicit follow-up mode', () => {
    const code = read('scripts/testers/replay_synthetic_credit_case.py')
    expect(code).toContain("choices=['a', 'b', 'c']")
    expect(code).toContain('--follow-up-only')
    expect(code).toContain('--initial-only')
    expect(code).toContain('"--persona", persona')
    expect(code).toContain('seed_credit_workflow_fixtures.py')
    expect(code).toContain('no active duplicate jobs')
    expect(code).not.toContain('args.follow-up_only')
  })

  it('tester readiness closeout is persisted and scoped to a persona card', () => {
    const panel = read('src/components/TesterReadinessPanel.jsx')
    expect(panel).toContain("fixture_version: 'controlled-pilot-v1'")
    expect(panel).toContain("status: 'completed'")
    expect(panel).toContain('Complete Session')
    expect(panel).toContain('data-persona-card={persona.key}')
  })

  it('controlled pilot suite has required coverage and no skipped tests', () => {
    const suitePath = resolve(ROOT, 'tests/e2e/controlled-tester-pilot.spec.ts')
    expect(existsSync(suitePath)).toBe(true)
    const suite = readFileSync(suitePath, 'utf8')
    expect(suite).toContain('Persona A completes the guided checklist')
    expect(suite).toContain('Persona B keeps the genuine exception')
    expect(suite).toContain('Persona C completes the purchased-debt documentation path')
    expect(suite).toContain('Synthetic admin creates, reviews, routes, and closes')
    expect(suite).toContain('Client sessions cannot access admin tester controls')
    expect(suite).toContain('pilot viewport keeps actions and navigation accessible')
    expect(suite).not.toMatch(/test\.skip|test\.only|describe\.skip|describe\.only/)
  })
})
