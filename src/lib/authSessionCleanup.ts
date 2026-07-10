import { supabase } from './supabaseClient'

type StorageName = 'localStorage' | 'sessionStorage'

export type AuthCleanupResult = {
  reason?: string
  signOut: 'skipped' | 'global' | 'local' | 'failed'
  removedKeys: Array<{ storage: StorageName; key: string }>
  errors: string[]
}

const AUTH_KEY_PATTERNS = [
  'supabase',
  'sb-',
  'nexus',
  'client_profile',
  'clientprofile',
  'tenant_membership',
  'tenantmembership',
  'admin_user',
  'adminuser',
  'goclear',
]

function shouldRemoveStorageKey(key: string) {
  const lower = key.toLowerCase()
  return AUTH_KEY_PATTERNS.some(pattern => lower.includes(pattern))
}

function getStorage(name: StorageName): Storage | null {
  if (typeof window === 'undefined') return null
  try {
    return name === 'localStorage' ? window.localStorage : window.sessionStorage
  } catch {
    return null
  }
}

function storageKeys(storage: Storage | null) {
  if (!storage) return []
  const keys: string[] = []
  for (let i = 0; i < storage.length; i += 1) {
    const key = storage.key(i)
    if (key) keys.push(key)
  }
  return keys
}

function clearMatchingStorageKeys(name: StorageName, result: AuthCleanupResult) {
  const storage = getStorage(name)
  if (!storage) return
  for (const key of storageKeys(storage)) {
    if (!shouldRemoveStorageKey(key)) continue
    try {
      storage.removeItem(key)
      result.removedKeys.push({ storage: name, key })
    } catch (error) {
      result.errors.push(`Unable to remove ${name}:${key}: ${error instanceof Error ? error.message : 'unknown error'}`)
    }
  }
}

export async function clearNexusAuthSession(reason?: string): Promise<AuthCleanupResult> {
  const result: AuthCleanupResult = { reason, signOut: 'skipped', removedKeys: [], errors: [] }

  if (supabase) {
    try {
      const globalResult = await supabase.auth.signOut({ scope: 'global' })
      if (globalResult.error) {
        const localResult = await supabase.auth.signOut()
        result.signOut = localResult.error ? 'failed' : 'local'
        if (localResult.error) result.errors.push(localResult.error.message)
      } else {
        result.signOut = 'global'
      }
    } catch (error) {
      try {
        const fallback = await supabase.auth.signOut()
        result.signOut = fallback.error ? 'failed' : 'local'
        if (fallback.error) result.errors.push(fallback.error.message)
      } catch (fallbackError) {
        result.signOut = 'failed'
        result.errors.push(fallbackError instanceof Error ? fallbackError.message : 'Supabase sign out failed')
      }
      if (error instanceof Error) result.errors.push(error.message)
    }
  }

  clearMatchingStorageKeys('localStorage', result)
  clearMatchingStorageKeys('sessionStorage', result)

  try {
    window.dispatchEvent(new CustomEvent('nexus-auth-session-cleared', { detail: { reason, removedKeyCount: result.removedKeys.length } }))
  } catch {
    // Browser-only event.
  }

  return result
}

export async function forceAuthResetAndRedirect(path: string) {
  await clearNexusAuthSession(`redirect:${path}`)
  if (typeof window !== 'undefined') window.location.assign(path)
}

export async function getAuthDebugSnapshot() {
  const matchingKeys = [
    ...storageKeys(getStorage('localStorage')).filter(shouldRemoveStorageKey).map(key => ({ storage: 'localStorage' as const, key })),
    ...storageKeys(getStorage('sessionStorage')).filter(shouldRemoveStorageKey).map(key => ({ storage: 'sessionStorage' as const, key })),
  ]

  let hasSession = false
  let userEmail: string | null = null
  if (supabase) {
    try {
      const { data } = await supabase.auth.getSession()
      hasSession = Boolean(data.session)
      userEmail = data.session?.user?.email ?? null
    } catch {
      hasSession = false
    }
  }

  return { hasSession, userEmail, storageKeys: matchingKeys }
}
