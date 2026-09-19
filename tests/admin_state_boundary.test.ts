import { describe, expect, it } from 'vitest'
import { normalizeAdminState } from '../src/admin/adminStateBoundary'

describe('Admin live state boundary', () => {
  it('keeps incomplete research projections render-safe without fabricating metrics', () => {
    const state = normalizeAdminState({ system_health: 'DEGRADED', seo: {} }, { provenance: 'live', research: {} })
    expect(state.seo).toEqual({})
    expect(state.seo.signals_found).toBeUndefined()
    expect(state.research).toEqual({})
    expect(state.ray_decisions.items).toEqual([])
  })

  it('preserves populated live metrics', () => {
    const state = normalizeAdminState({ seo: { signals_found: 1 } }, { seo: { signals_found: 7 } })
    expect(state.seo.signals_found).toBe(7)
  })
})
