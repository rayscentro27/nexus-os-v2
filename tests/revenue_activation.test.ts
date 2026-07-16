import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { SERVICE_OFFER_CATALOG, SERVICE_OFFER_DISCLAIMERS, getServiceOffer } from '../src/config/serviceOfferCatalog'
import { buildReadinessPacketDraft, canTransitionFulfillment, canTransitionOrder, hasUnsafePacketContent, resolveTrustedPrice, summarizeRevenueOrders, validateCheckoutInput } from '../src/lib/revenueActivation'
import { isStripeTestSecret, isStripeTestWebhookSecret, reconcileVerifiedPaymentEvent, shouldCreateFulfillment, verifyStripeTestSignature } from '../src/lib/stripeTestMode'

describe('Phase 6 — controlled revenue activation', () => {
  const migration = readFileSync(resolve(import.meta.dirname, '../supabase/migrations/20260715180000_revenue_activation_test_mode.sql'), 'utf8')
  const revenueRoleFixMigration = readFileSync(resolve(import.meta.dirname, '../supabase/migrations/20260716100000_fix_revenue_service_role_trigger.sql'), 'utf8')
  const checkoutFunction = readFileSync(resolve(import.meta.dirname, '../supabase/functions/create-stripe-checkout/index.ts'), 'utf8')
  const webhookFunction = readFileSync(resolve(import.meta.dirname, '../supabase/functions/stripe-webhook/index.ts'), 'utf8')

  it('adds the required tables and owner/admin access boundaries', () => {
    for (const table of ['service_offers', 'client_orders', 'payment_events', 'service_fulfillments', 'readiness_packets', 'consultation_requests', 'referral_attributions']) expect(migration).toContain(`create table if not exists public.${table}`)
    expect(migration).toContain('client_orders_owner_select')
    expect(migration).toContain('service_fulfillments_owner_select')
    expect(migration).toContain('readiness_packets_owner_select')
    expect(migration).toContain('payment_state_is_server_verified')
    expect(migration).toContain('delivered_packet_is_immutable')
    expect(revenueRoleFixMigration).toContain("current_user <> 'service_role'")
  })

  it('keeps provider secrets and payment writes server-side', () => {
    expect(checkoutFunction).toContain('STRIPE_SECRET_KEY')
    expect(checkoutFunction).toContain('price_cents')
    expect(checkoutFunction).toContain('sk_test_')
    expect(checkoutFunction).toContain('checkout_persistence_failed')
    expect(webhookFunction).toContain('Stripe-Signature')
    expect(webhookFunction).toContain('provider_event_id')
    expect(webhookFunction).toContain('processed_status')
    expect(webhookFunction).toContain('verifiedPaymentMatchesOrder')
    expect(webhookFunction).toContain('amount_total')
    expect(webhookFunction).not.toContain('console.log(raw)')
  })

  it('defines the approved one-time service offers', () => {
    expect(SERVICE_OFFER_CATALOG.map(offer => offer.slug)).toEqual(['readiness-review-97', 'readiness-action-plan-297', 'funding-readiness-concierge-497', 'invited-readiness-test'])
    expect(SERVICE_OFFER_CATALOG.map(offer => offer.price_cents)).toEqual([9700, 29700, 49700, 100])
    expect(SERVICE_OFFER_CATALOG.filter(offer => ['readiness-review-97', 'readiness-action-plan-297', 'funding-readiness-concierge-497'].includes(offer.slug)).every(offer => offer.active && offer.currency === 'usd')).toBe(true)
    expect(SERVICE_OFFER_CATALOG.find(offer => offer.slug === 'invited-readiness-test')?.active).toBe(false)
  })

  it('resolves trusted server-side price and rejects tampering', () => {
    const offer = getServiceOffer('readiness-review-97')!
    expect(resolveTrustedPrice(offer)).toEqual({ ok: true, amount_cents: 9700, currency: 'usd' })
    expect(resolveTrustedPrice(offer, 1)).toEqual({ ok: false, error: 'client_price_not_accepted' })
  })

  it('requires the catalog terms version before checkout', () => {
    const offer = getServiceOffer('readiness-action-plan-297')!
    expect(validateCheckoutInput({ offerSlug: offer.slug, termsAccepted: true, termsVersion: offer.terms_version }, offer).ok).toBe(true)
    expect(validateCheckoutInput({ offerSlug: offer.slug, termsAccepted: true, termsVersion: 'old' }, offer).ok).toBe(false)
  })

  it('enforces controlled order and fulfillment transitions', () => {
    expect(canTransitionOrder('draft', 'checkout_created')).toBe(true)
    expect(canTransitionOrder('draft', 'paid')).toBe(false)
    expect(canTransitionOrder('paid', 'refunded')).toBe(true)
    expect(canTransitionFulfillment('admin_review', 'ray_review')).toBe(true)
    expect(canTransitionFulfillment('admin_review', 'delivered')).toBe(false)
  })

  it('builds a draft packet with source labels and no unsafe data', () => {
    const packet = buildReadinessPacketDraft({ offerName: 'Credit & Funding Readiness Review', orderNumber: 'GC-TEST', readinessState: 'action_needed', primaryBlocker: 'Missing documents', nextAction: 'Upload documents', missingRequirements: ['Proof of address'], completedRequirements: ['Intake'] })
    expect(packet.status).toBe('draft')
    expect(packet.source_labels.uploaded_evidence).toContain('Uploaded')
    expect(hasUnsafePacketContent(packet)).toBe(false)
    expect(hasUnsafePacketContent({ text: 'guaranteed funding approval' })).toBe(true)
  })

  it('keeps delivered packet access approval-gated', () => {
    const packet = buildReadinessPacketDraft({ offerName: 'Test', orderNumber: 'GC-TEST' })
    expect(packet.sections.some(section => section.key === 'reviewer')).toBe(true)
    expect(SERVICE_OFFER_DISCLAIMERS.join(' ')).toMatch(/does not guarantee/i)
  })

  it('summarizes test revenue without treating pending orders as revenue', () => {
    const summary = summarizeRevenueOrders([{ status: 'paid', amount_cents: 9700, offer_id: 'offer_readiness_review_97' }, { status: 'payment_pending', amount_cents: 29700, offer_id: 'offer_readiness_action_plan_297' }])
    expect(summary.revenue_cents).toBe(9700)
    expect(summary.pending).toBe(1)
    expect(summary.paid).toBe(1)
  })

  it('accepts only test-mode provider secrets and verifies signed webhook bytes', async () => {
    expect(isStripeTestSecret('sk_test_fixture')).toBe(true)
    expect(isStripeTestSecret(['sk', 'live', 'fixture'].join('_'))).toBe(false)
    expect(isStripeTestWebhookSecret('whsec_fixture')).toBe(true)
    expect(isStripeTestWebhookSecret('')).toBe(false)
    const body = '{"id":"evt_fixture"}'
    const timestamp = 1700000000
    const key = await crypto.subtle.importKey('raw', new TextEncoder().encode('whsec_fixture'), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
    const digest = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${timestamp}.${body}`))
    const signature = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
    expect(await verifyStripeTestSignature(body, `t=${timestamp},v1=${signature}`, 'whsec_fixture', timestamp)).toBe(true)
    expect(await verifyStripeTestSignature(body, `t=${timestamp},v1=${signature}`, 'whsec_fixture', timestamp + 301)).toBe(false)
  })

  it('reconciles only verified event types and creates fulfillment once', () => {
    expect(reconcileVerifiedPaymentEvent('checkout.session.completed', 'payment_pending')).toEqual({ orderStatus: 'paid', paymentStatus: 'verified_paid' })
    expect(reconcileVerifiedPaymentEvent('payment_intent.payment_failed', 'payment_pending')).toEqual({ orderStatus: 'payment_failed', paymentStatus: 'failed' })
    expect(reconcileVerifiedPaymentEvent('checkout.session.completed', 'payment_pending')).not.toBeNull()
    expect(reconcileVerifiedPaymentEvent('unknown.client.claim', 'payment_pending')).toBeNull()
    expect(shouldCreateFulfillment(0)).toBe(true)
    expect(shouldCreateFulfillment(1)).toBe(false)
  })
})
