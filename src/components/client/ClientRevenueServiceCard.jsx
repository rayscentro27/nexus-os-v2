import React, { useEffect, useMemo, useState } from 'react'
import { loadClientRevenueState } from '../../lib/revenueActivationClient'

const fallback = { source: 'synthetic', orders: [], fulfillments: [], packets: [], consultations: [] }

export default function ClientRevenueServiceCard({ navigate }) {
  const [state, setState] = useState(fallback)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    loadClientRevenueState().then(result => { if (active) { setState(result); setLoading(false) } }).catch(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  const order = state.orders?.[0]
  const fulfillment = state.fulfillments?.find(item => item.order_id === order?.id)
  const packet = state.packets?.find(item => item.order_id === order?.id)
  const offerName = order?.service_offers?.name || 'Readiness service'
  const nextAction = useMemo(() => {
    if (!order) return 'Choose a controlled readiness service when you are ready.'
    if (order.status !== 'paid') return 'Payment verification is still pending. Your portal will update after the server confirms payment.'
    if (fulfillment?.fulfillment_status === 'onboarding_required') return 'Complete the paid-service intake and confirm your review scope.'
    if (fulfillment?.fulfillment_status === 'awaiting_documents') return 'Upload the documents listed in your readiness checklist.'
    if (fulfillment?.fulfillment_status === 'approved_for_delivery' && !packet) return 'Your approved readiness packet is preparing for portal delivery.'
    if (packet?.status === 'delivered') return 'Review your approved readiness packet and note the next action.'
    return 'Continue your guided readiness journey.'
  }, [order, fulfillment, packet])
  return <section className="wc-card wc-revenue-service" data-testid="client-revenue-service">
    <div className="wc-sectionHead"><h3>Purchased service</h3><span className="wc-statusPill">TEST MODE</span></div>
    {loading ? <p>Loading service status…</p> : order ? <>
      <p><strong>{offerName}</strong> · Order {order.order_number}</p>
      <div className="wc-revenue-grid"><span>Payment <b>{order.status === 'paid' ? 'Verified' : 'Pending verification'}</b></span><span>Fulfillment <b>{(fulfillment?.fulfillment_status || order.fulfillment_status || 'not_started').replaceAll('_', ' ')}</b></span><span>Packet <b>{packet?.status === 'delivered' ? 'Available' : 'Approval gated'}</b></span></div>
      <p className="wc-mutedText">{nextAction}</p>
      <div className="wc-actionRow"><button onClick={() => navigate?.('/client/profile')}>Continue onboarding</button><button onClick={() => navigate?.('/client/documents')}>View documents</button>{packet?.status === 'delivered' && <button onClick={() => navigate?.('/client/funding-readiness')}>Open approved packet</button>}</div>
    </> : <><p>No paid readiness service is linked to this account yet. Public offers remain test-mode and approval-gated.</p><button className="wc-primaryWide" onClick={() => window.location.assign('/pricing')}>View readiness services</button></>}
  </section>
}
