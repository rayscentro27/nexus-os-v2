import { describe, expect, it } from 'vitest'
import fs from 'node:fs'

const adapter = fs.readFileSync('src/lib/clientPortalDataAdapter.ts', 'utf8')
const v2Data = fs.readFileSync('src/client-v2/hooks/useV2ClientData.ts', 'utf8')

describe('GoClear authenticated client live-data boundary', () => {
  it('does not substitute the demo profile for an empty configured Supabase result', () => {
    expect(adapter).toContain("return { data: null, source: 'supabase' as const, error: 'No client profile found' }")
  })

  it('does not substitute demo documents for an empty configured Supabase result', () => {
    expect(adapter).toContain("return { data: [], source: 'supabase' as const };")
    expect(adapter).toContain('Keep configured/live mode empty when RLS returns no documents')
  })

  it('keeps preview demo mode separate from authenticated V2 live mode', () => {
    expect(v2Data).toContain('const shouldLoadLive = clientDataMode.liveSupabaseTestClientEnabled && isSupabaseConfigured')
    expect(v2Data).toContain('const isDemo = mode !== \'live\'')
  })
})
