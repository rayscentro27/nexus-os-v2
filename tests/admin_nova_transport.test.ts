import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('Admin canonical Nova transport', () => {
  it('uses existing authenticated Admin conversation tables instead of a public Nova origin', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/lib/nexusAgentDispatch.ts'), 'utf8')
    expect(source).toContain("from('admin_ai_messages')")
    expect(source).toContain('Remote Nova transport is not configured.')
    expect(source).not.toContain('nova.goclearonline.cc')
    expect(source).not.toContain('127.0.0.1:8790')
  })

  it('keeps the local bridge on canonical Hermes and requires Admin auth', () => {
    const source = readFileSync(resolve(process.cwd(), 'scripts/nova/nova_admin_server.py'), 'utf8')
    expect(source).toContain('run_oracle_hermes')
    expect(source).toContain('nova_nexus')
    expect(source).toContain('admin_authentication_required')
    expect(source).toContain('Access-Control-Allow-Headers')
  })
})
