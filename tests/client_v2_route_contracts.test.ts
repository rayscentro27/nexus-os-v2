import { describe, expect, it } from 'vitest'
import { V2_ROUTE_CONTRACTS } from '../src/client-v2/routeContracts'
import { resolveRouteAdapter } from '../src/client-v2/adapters/routeAdapters'
import type { V2ViewData } from '../src/client-v2/types/v2-models'

const routePaths = [
  '/client-v2/dashboard',
  '/client-v2/credit',
  '/client-v2/utilization',
  '/client-v2/documents',
  '/client-v2/business',
  '/client-v2/bankability',
  '/client-v2/funding-readiness',
  '/client-v2/recommendations',
  '/client-v2/resources',
  '/client-v2/review',
  '/client-v2/support',
  '/client-v2/account',
  '/client-v2/goals',
] as const

const liveData = {
  mode: 'live',
  isDemo: false,
  loadError: null,
  profile: { name: 'Synthetic Client' },
  scores: { credit: 20, business: 30, funding: 25, overall: 25 },
  readiness: {
    overallScore: 25,
    outstandingRequirements: ['document'],
    stages: { tier1: { requirements: [{ label: 'document' }] } },
  },
  documents: { requiredCount: 1, uploadedCount: 0 },
  creditRepair: { negativeItems: [] },
  flow: { reviewStatus: { status: 'pending' } },
  hermes: { recommendations: [] },
} as unknown as V2ViewData

describe('Client Portal V2 route contracts', () => {
  it('keeps the intended route family finite and explicitly contracted', () => {
    expect(Object.keys(V2_ROUTE_CONTRACTS).sort()).toEqual([...routePaths].sort())
    for (const path of routePaths) {
      const contract = V2_ROUTE_CONTRACTS[path]
      expect(contract.purpose).toBeTruthy()
      expect(contract.backend.length).toBeGreaterThan(0)
      expect(contract.access).toBeTruthy()
      expect(contract.mobile).toBeTruthy()
    }
  })

  it('resolves every route through a named adapter boundary', () => {
    for (const path of routePaths) {
      const adapter = resolveRouteAdapter(path, liveData)
      expect(adapter.adapter).not.toBe('client portal live data')
      expect(adapter.backend).toBeTruthy()
      expect(Array.isArray(adapter.permittedActions)).toBe(true)
    }
  })
})
