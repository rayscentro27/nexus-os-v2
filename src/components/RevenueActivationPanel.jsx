import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { SERVICE_OFFER_CATALOG } from '../config/serviceOfferCatalog'
import { buildReadinessPacketDraft, canTransitionFulfillment, getConsultationEntitlement, summarizeRevenueOrders } from '../lib/revenueActivation'
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient'

function money(cents) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(cents || 0) / 100) }

export default function RevenueActivationPanel() {
  const [orders, setOrders] = useState([])
  const [fulfillments, setFulfillments] = useState([])
  const [packets, setPackets] = useState([])
  const [referrals, setReferrals] = useState([])
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const summary = useMemo(() => summarizeRevenueOrders(orders), [orders])
  const load = useCallback(async () => {
    if (!supabase || !isSupabaseConfigured) { setLoading(false); return }
    setLoading(true)
    const [o, f, p, r] = await Promise.all([
      supabase.from('client_orders').select('*,service_offers(name,slug,tier)').order('created_at', { ascending: false }).limit(100),
      supabase.from('service_fulfillments').select('*').order('updated_at', { ascending: false }).limit(100),
      supabase.from('readiness_packets').select('*').order('created_at', { ascending: false }).limit(100),
      supabase.from('referral_attributions').select('*').order('created_at', { ascending: false }).limit(100),
    ])
    setOrders(o.data || []); setFulfillments(f.data || []); setPackets(p.data || []); setReferrals(r.data || []); setLoading(false)
  }, [])
  useEffect(() => { load() }, [load])
  const update = async (promise, success) => { setMessage(''); const { error } = await promise; if (error) setMessage('Action rejected: controlled transition or authorization failed.'); else { setMessage(success); await load() } }
  const assignReviewer = async (fulfillment) => update(supabase.from('service_fulfillments').update({ assigned_reviewer: 'ray', fulfillment_status: 'admin_review' }).eq('id', fulfillment.id), 'Reviewer assigned. Fulfillment is in admin review.')
  const draftPacket = async (order, fulfillment) => {
    const offer = SERVICE_OFFER_CATALOG.find(item => item.id === order.offer_id) || SERVICE_OFFER_CATALOG[0]
    const current = packets.filter(packet => packet.order_id === order.id).sort((a, b) => Number(b.version) - Number(a.version))[0]
    const version = Number(current?.version || 0) + 1
    const packet = buildReadinessPacketDraft({ offerName: offer.name, orderNumber: order.order_number, readinessState: 'insufficient_information', primaryBlocker: 'Complete paid-service intake and document review.', nextAction: 'Complete onboarding and provide the requested readiness documents.', missingRequirements: ['Paid-service intake', 'Current supporting documents'], completedRequirements: [], reviewerNotes: 'Draft generated for admin review; not delivered.' })
    await update(supabase.from('readiness_packets').insert({ order_id: order.id, client_id: order.client_id, version, status: 'draft', content: packet, approval_status: 'draft', client_visible: false }).select('id').single().then(async ({ data, error }) => { if (error) return { error }; return supabase.from('service_fulfillments').update({ readiness_packet_id: data.id, fulfillment_status: 'admin_review', approval_status: 'pending' }).eq('id', fulfillment.id) }), 'Draft readiness packet created. It remains unavailable to the client.')
  }
  const routeRay = async (order, fulfillment) => {
    const packet = packets.find(item => item.id === fulfillment.readiness_packet_id)
    if (!packet) { setMessage('Generate a draft packet before Ray Review routing.'); return }
    const existing = await supabase.from('task_requests').select('id').eq('task_type', 'readiness_packet_ray_review').contains('payload', { packet_id: packet.id }).limit(1).maybeSingle()
    if (existing.data?.id) { setMessage('Packet is already linked to Ray Review.'); return }
    await update(supabase.from('task_requests').insert({ task_type: 'readiness_packet_ray_review', requested_by: 'revenue_activation', sensitivity: 'funding_sensitive', assigned_worker_type: 'manual_ray_review', hermes_visibility: 'status_only', status: 'requested', allowed_data_scope: ['readiness_packet_summary'], forbidden_data: ['credentials', 'payment_credentials', 'raw_storage_paths'], payload: { order_id: order.id, packet_id: packet.id, requires_ray_review: true, auto_approve: false, auto_execute: false } }), 'Packet routed to Ray Review. No delivery occurred.')
    await supabase.from('readiness_packets').update({ status: 'ray_review', approval_status: 'pending' }).eq('id', packet.id)
    await supabase.from('service_fulfillments').update({ fulfillment_status: 'ray_review' }).eq('id', fulfillment.id)
    await load()
  }
  const approve = async (packet, fulfillment) => {
    setMessage(''); const result = await supabase.from('readiness_packets').update({ status: 'approved_for_delivery', approval_status: 'approved', reviewer_id: 'ray', reviewed_at: new Date().toISOString() }).eq('id', packet.id).eq('status', 'ray_review');
    if (result.error) { setMessage('Approval rejected: only a Ray Review packet can be approved.'); return }
    await supabase.from('service_fulfillments').update({ fulfillment_status: 'approved_for_delivery', approval_status: 'approved', delivery_status: 'ready' }).eq('id', fulfillment.id); setMessage('Ray approved the exact packet version for controlled delivery.'); await load()
  }
  const deliver = async (packet, fulfillment) => {
    setMessage(''); const result = await supabase.from('readiness_packets').update({ status: 'delivered', client_visible: true, delivered_at: new Date().toISOString() }).eq('id', packet.id).eq('status', 'approved_for_delivery');
    if (result.error) { setMessage('Delivery rejected: the packet must be approved first.'); return }
    await supabase.from('service_fulfillments').update({ fulfillment_status: 'delivered', delivery_status: 'delivered' }).eq('id', fulfillment.id); setMessage('Approved packet is now visible to the linked client.'); await load()
  }
  const requestConsultation = async (order, fulfillment) => { const offer = SERVICE_OFFER_CATALOG.find(item => item.id === order.offer_id) || SERVICE_OFFER_CATALOG[0]; const entitlement = getConsultationEntitlement(offer); if (!entitlement.entitled) { setMessage('This tier has no consultation entitlement by default.'); return } const existing = await supabase.from('consultation_requests').select('id').eq('order_id', order.id).maybeSingle(); const operation = existing.data?.id ? supabase.from('consultation_requests').update({ entitlement_type: entitlement.type, allowed_duration_minutes: entitlement.duration_minutes, scheduling_status: 'pending_admin_confirmation' }).eq('id', existing.data.id) : supabase.from('consultation_requests').insert({ order_id: order.id, client_id: order.client_id, entitlement_type: entitlement.type, allowed_duration_minutes: entitlement.duration_minutes, scheduling_status: 'pending_admin_confirmation' }); await update(operation, 'Consultation request recorded for admin confirmation.') }
  return <div className="nxos-stack" data-testid="revenue-activation-panel"><div className="nxos-callout"><strong>TEST MODE ONLY</strong><p>Stripe checkout, webhooks, fulfillment, packet delivery, consultation, and referral attribution remain approval-gated. No live payment, mail, DocuPost, or automatic delivery occurs.</p></div><div className="nxos-metric-grid"><article><small>Orders created</small><strong>{summary.created}</strong></article><article><small>Verified test payments</small><strong>{summary.paid}</strong></article><article><small>Test revenue</small><strong>{money(summary.revenue_cents)}</strong></article><article><small>Pending payment</small><strong>{summary.pending}</strong></article></div>{message && <p className="nxos-callout">{message}</p>}<section className="nxos-table-card"><h2>Offer catalog</h2>{SERVICE_OFFER_CATALOG.map(offer => <div className="nxos-table-row" key={offer.id}><strong>{offer.name}</strong><span>{money(offer.price_cents)} · active test offer</span></div>)}</section><section className="nxos-table-card"><h2>Order and fulfillment operations</h2>{loading && <p>Loading authorized order data…</p>}{!loading && orders.length === 0 && <p>No authorized orders are present. Seed only the synthetic revenue persona for certification.</p>}{orders.map(order => { const f = fulfillments.find(item => item.order_id === order.id); const packet = packets.find(item => item.id === f?.readiness_packet_id); const offer = order.service_offers?.name || order.offer_id; return <article className="nxos-table-row" key={order.id}><div><strong>{offer}</strong><small>{order.order_number} · {order.status} · {order.payment_status} · fulfillment {(f?.fulfillment_status || order.fulfillment_status || 'not_started').replaceAll('_', ' ')}</small></div><div className="nxos-action-row"><button onClick={() => f && assignReviewer(f)} disabled={!f || !canTransitionFulfillment(f.fulfillment_status, 'admin_review')}>Assign reviewer</button><button onClick={() => f && draftPacket(order, f)} disabled={!f}>Generate draft</button><button onClick={() => f && routeRay(order, f)} disabled={!f || !packet}>Ray Review</button><button onClick={() => packet && f && approve(packet, f)} disabled={!packet || packet.status !== 'ray_review'}>Approve</button><button onClick={() => packet && f && deliver(packet, f)} disabled={!packet || packet.status !== 'approved_for_delivery'}>Deliver</button><button onClick={() => f && requestConsultation(order, f)}>Consultation</button></div></article>})}</section><section className="nxos-table-card"><h2>Referral attribution</h2>{referrals.length ? referrals.map(row => <div className="nxos-table-row" key={row.id}><strong>{row.referral_code || 'No referral code'}</strong><span>{row.payment_status} · service-purchase attribution only · commission {row.commission_status}</span></div>) : <p>No referral attribution records in the current test dataset.</p>}</section></div>
}
