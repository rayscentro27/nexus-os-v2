import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('Admin canonical Nova transport', () => {
  it('uses the same-origin server bridge instead of the protected Nova origin', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/lib/nexusAgentDispatch.ts'), 'utf8')
    expect(source).toContain("const NOVA_ENDPOINT = '/.netlify/functions/admin-nova-chat'")
    expect(source).toContain('Authorization: `Bearer ${accessToken}`')
    expect(source).not.toContain('https://nova.goclearonline.cc/v1/nova/chat')
  })

  it('keeps Access credentials server-side and rejects upstream redirects', () => {
    const source = readFileSync(resolve(process.cwd(), 'netlify/functions/admin-nova-chat.mjs'), 'utf8')
    expect(source).toContain('cf-access-client-id')
    expect(source).toContain('cf-access-client-secret')
    expect(source).toContain("redirect: 'manual'")
    expect(source).toContain('nova_access_redirect_not_allowed')
    expect(source).not.toContain('VITE_')
  })
})
