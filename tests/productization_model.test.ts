import { describe, expect, it } from 'vitest'
import { CAPABILITY_ENTITLEMENTS, PRODUCT_OPTIONS, capabilityPolicy, provisioningPlan, readinessMatrix, sameTenantAccess } from '../src/lib/productizationModel'

describe('governed productization model', () => {
  it('keeps product options explicitly dependency and validation gated', () => {
    expect(PRODUCT_OPTIONS).toHaveLength(6)
    expect(PRODUCT_OPTIONS.find(option => option.model === 'WHITE_LABEL_BUSINESS_OS')?.readiness).toBe('NOT_READY')
    expect(PRODUCT_OPTIONS.find(option => option.model === 'CLIENT_PORTAL_PLUS_AI')?.knownGaps.length).toBeGreaterThan(0)
  })
  it('enforces tenant boundaries and safe entitlements', () => {
    expect(sameTenantAccess('tenant-a', 'tenant-a')).toBe(true)
    expect(sameTenantAccess('tenant-a', 'tenant-b')).toBe(false)
    expect(CAPABILITY_ENTITLEMENTS.FREE_GUEST.fundingExecution).toBe(false)
    expect(CAPABILITY_ENTITLEMENTS.FREE_GUEST.admin).toBe(false)
  })
  it('provisions only a synthetic bounded plan', () => {
    expect(provisioningPlan('synthetic-tenant-a', 'FREE_GUEST')).toMatchObject({ syntheticOnly: true, realCustomerProvisioned: false, externalSideEffect: false })
  })
  it('does not let product settings grant external authority', () => {
    expect(capabilityPolicy('payment').enabled).toBe(false)
    expect(capabilityPolicy('bank transfer').requiresApproval).toBe(true)
    expect(capabilityPolicy('readiness').authorityClass).toBe('READ_ONLY')
    expect(readinessMatrix().WHITE_LABEL_PRODUCT.production).toBe('NOT_READY')
  })
})
