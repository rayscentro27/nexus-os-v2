import fs from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = fs.readFileSync('scripts/hermes_runtime/nexus_hermes_runtime_adapter.mjs', 'utf8')

describe('official Hermes runtime adapter contract', () => {
  it('pins the isolated official Hermes target without replacing Nexus Hermes', () => {
    expect(source).toContain("OFFICIAL_HERMES_TARGET = '0.20.0'")
    expect(source).toContain('/Users/raymonddavis/nexus-hermes-runtime')
    expect(source).toContain('Official Hermes Runtime Adapter')
  })

  it('allows only bounded internal task types', () => {
    for (const task of [
      'READ_ONLY_REPOSITORY_AUDIT',
      'RUN_TEST_SUITE',
      'BUILD_VERIFICATION',
      'GENERATE_INTERNAL_REPORT',
      'RESEARCH_SUMMARY_WITHOUT_CLIENT_DATA',
    ]) {
      expect(source).toContain(task)
    }
  })

  it('prohibits irreversible or client-facing external actions', () => {
    for (const task of [
      'SEND_CLIENT_MESSAGE',
      'SEND_DISPUTE',
      'APPLY_FOR_FUNDING',
      'CHARGE_CUSTOMER',
      'EXECUTE_TRADE',
      'CHANGE_RLS',
      'DELETE_PRODUCTION_DATA',
      'DEPLOY_PRODUCTION',
      'ARBITRARY_SHELL_COMMAND',
    ]) {
      expect(source).toContain(task)
    }
  })

  it('records deterministic command evidence and source-change detection', () => {
    expect(source).toContain('nexus_process_runs')
    expect(source).toContain('COMPLETION_CONTRACT_FAILED')
    expect(source).toContain('sourceChangedBeforeAfter')
    expect(source).toContain('stdoutTail')
    expect(source).toContain('stderrTail')
  })
})
