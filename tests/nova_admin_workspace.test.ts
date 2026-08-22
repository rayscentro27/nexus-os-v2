import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(resolve(process.cwd(), 'src/components/NovaWorkspace.jsx'), 'utf8')

describe('Nova Admin workspace transport', () => {
  it('uses the browser-only Nova endpoint and canonical response presentation', () => {
    expect(source).toContain('VITE_NEXUS_NOVA_ENDPOINT')
    expect(source).toContain('nova.goclearonline.cc/v1/nova/chat')
    expect(source).toContain('credentials: \'include\'')
    expect(source).toContain('<SafeMarkdown>')
    expect(source).not.toContain('runHermesConversation')
    expect(source).not.toContain('NOT_CONNECTED')
  })
})
