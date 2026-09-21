import React, { useEffect, useState } from 'react'

function value(v) { return String(v || '—').replaceAll('_', ' ') }

export default function MarketingCampaignCertificationPanel({ surface = 'admin' }) {
  const [projection, setProjection] = useState(null)
  const [state, setState] = useState('LOADING')
  useEffect(() => {
    let cancelled = false
    fetch('/runtime/marketing-creative-certification-projection.json', { cache: 'no-store' })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('projection_unavailable')))
      .then((data) => { if (!cancelled) { setProjection(data); setState('LIVE') } })
      .catch(() => { if (!cancelled) setState('UNAVAILABLE') })
    return () => { cancelled = true }
  }, [])
  return <section data-testid="marketing-campaign-certification" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 16, marginTop: 16 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline', flexWrap: 'wrap' }}>
      <div><span className="live-command-eyebrow">MARKETING / CREATIVE CERTIFICATION</span><h3 style={{ margin: '6px 0' }}>{surface === 'nova' ? 'Nova Campaign Monitor' : 'Campaign Operations'}</h3><p style={{ color: '#91a5bf', margin: 0 }}>Canonical read-only projection · {state}</p></div>
      <strong style={{ color: '#83e6b0' }}>{projection ? value(projection.campaign_status) : '—'}</strong>
    </div>
    {state === 'UNAVAILABLE' && <p role="status" style={{ color: '#ffb4b4' }}>Campaign projection is unavailable; no operational claim is made.</p>}
    {state === 'LOADING' && <p style={{ color: '#91a5bf' }}>Loading campaign lineage…</p>}
    {projection && <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(145px,1fr))', gap: 10, marginTop: 14 }}>
        <div><small style={{ color: '#91a5bf' }}>Campaign</small><div>{projection.campaign_id}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Marketing</small><div>Strategy accepted</div></div>
        <div><small style={{ color: '#91a5bf' }}>Creative</small><div>{projection.image?.visual_proof} · {projection.video?.visual_proof}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Landing</small><div>{value(projection.landing_page?.status)}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Cost</small><div>${projection.cost?.observed_cost_usd ?? 'UNKNOWN'}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Bypass</small><div>{projection.worker_routing?.provider_bypass_count ?? 'UNKNOWN'}</div></div>
      </div>
      <p style={{ color: '#91a5bf', marginBottom: 0 }}>Worker routing: {projection.worker_routing?.jobs?.length || 0} receipts · Email {value(projection.distribution?.email?.distribution_status)} · Social held where no approved test surface exists.</p>
    </>}
  </section>
}
