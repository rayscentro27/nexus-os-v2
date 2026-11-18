import { afterEach, describe, expect, it, vi } from 'vitest'

const originalEnv = { ...process.env }
const response = (body, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { 'content-type': 'application/json' },
})

describe('requireAdmin role resolution', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    process.env = { ...originalEnv }
  })

  it('requires an authenticated bearer session', async () => {
    const { requireAdmin } = await import('../netlify/functions/_admin-auth.mjs')
    const result = await requireAdmin({ headers: {} })
    expect(result).toMatchObject({ ok: false, statusCode: 401, error: 'AUTH_FAILED' })
  })

  it('checks the exact authenticated user against live role rows with the server key', async () => {
    process.env.VITE_SUPABASE_URL = 'https://iqjwgpnujbeoyaeuwehj.supabase.co'
    process.env.VITE_SUPABASE_ANON_KEY = 'test-anon'
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-server-secret'
    const calls = []
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
      calls.push({ url: String(url), options })
      if (String(url).includes('/auth/v1/user')) return response({ id: 'user-ray' })
      if (String(url).includes('/admin_users?')) return response([{ role: 'admin', active: true }])
      throw new Error('unexpected request')
    }))

    const { requireAdmin } = await import('../netlify/functions/_admin-auth.mjs')
    const result = await requireAdmin({ headers: { authorization: 'Bearer test-session' } })
    expect(result).toMatchObject({ ok: true, userId: 'user-ray', role: 'admin', projectRef: 'iqjwgpnujbeoyaeuwehj' })
    expect(calls).toHaveLength(2)
    expect(calls[0].options.headers.authorization).toBe('Bearer test-session')
    expect(calls[1].options.headers.authorization).toBe('Bearer test-server-secret')
  })

  it('reports an admin query failure instead of converting it into a false 403', async () => {
    process.env.VITE_SUPABASE_URL = 'https://iqjwgpnujbeoyaeuwehj.supabase.co'
    process.env.VITE_SUPABASE_ANON_KEY = 'test-anon'
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-server-secret'
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn(async (url) => String(url).includes('/auth/v1/user')
      ? response({ id: 'user-ray' })
      : response({ message: 'private raw failure' }, 500)))

    const { requireAdmin } = await import('../netlify/functions/_admin-auth.mjs')
    const result = await requireAdmin({ headers: { authorization: 'Bearer test-session' } })
    expect(result).toMatchObject({
      ok: false,
      statusCode: 503,
      error: 'ADMIN_QUERY_ERROR',
      projectRef: 'iqjwgpnujbeoyaeuwehj',
    })
    expect(JSON.stringify(result)).not.toContain('private raw failure')
  })

  it('accepts an active administrator membership when the direct allowlist row is inactive', async () => {
    process.env.VITE_SUPABASE_URL = 'https://iqjwgpnujbeoyaeuwehj.supabase.co'
    process.env.VITE_SUPABASE_ANON_KEY = 'test-anon'
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-server-secret'
    vi.spyOn(console, 'info').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      if (String(url).includes('/auth/v1/user')) return response({ id: 'user-ray' })
      if (String(url).includes('/admin_users?')) return response([{ role: 'admin', active: false }])
      return response([{ role: 'operator' }])
    }))

    const { requireAdmin } = await import('../netlify/functions/_admin-auth.mjs')
    const result = await requireAdmin({ headers: { authorization: 'Bearer test-session' } })
    expect(result).toMatchObject({ ok: true, userId: 'user-ray', role: 'operator' })
  })

  it('denies users absent from both role sources with a bounded diagnostic', async () => {
    process.env.VITE_SUPABASE_URL = 'https://iqjwgpnujbeoyaeuwehj.supabase.co'
    process.env.VITE_SUPABASE_ANON_KEY = 'test-anon'
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-server-secret'
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      if (String(url).includes('/auth/v1/user')) return response({ id: 'user-non-admin' })
      return response([])
    }))

    const { requireAdmin } = await import('../netlify/functions/_admin-auth.mjs')
    const result = await requireAdmin({ headers: { authorization: 'Bearer test-session' } })
    expect(result).toMatchObject({
      ok: false,
      statusCode: 403,
      error: 'TENANT_MEMBERSHIP_NOT_FOUND',
      projectRef: 'iqjwgpnujbeoyaeuwehj',
    })
  })
})
