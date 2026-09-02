import React, { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabaseClient'

export default function CreativeReviewStudio() {
  const [library, setLibrary] = useState({ assets: [] })
  const [selected, setSelected] = useState(null)
  const [compare, setCompare] = useState(false)
  const [decision, setDecision] = useState('READY_FOR_REVIEW')
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function authHeaders() {
    const { data } = await supabase?.auth.getSession() || { data: {} }
    return data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}
  }
  useEffect(() => {
    Promise.all([
      fetch('/creative-library/index.json').then(r => r.ok ? r.json() : { assets: [] }),
      authHeaders().then(headers => fetch('/.netlify/functions/creative-review-write', { credentials: 'include', headers })).then(r => r.ok ? r.json() : { reviews: [] }).catch(() => ({ reviews: [] }))
    ]).then(([nextLibrary, reviewData]) => {
      const reviews = reviewData.reviews || []
      const byAsset = new Map(reviews.map(review => [review.payload?.asset_id, review]))
      setLibrary({ ...nextLibrary, assets: (nextLibrary.assets || []).map(asset => ({ ...asset, review_state: byAsset.get(asset.asset_id)?.status || asset.review_state })) })
    }).catch(() => setLibrary({ assets: [] }))
  }, [])
  const assets = library.assets || []
  const current = selected || assets[0]
  const related = useMemo(() => current ? assets.filter(x => x.channel === current.channel && x.asset_type === current.asset_type) : [], [assets, current])
  const act = async (next) => {
    if (!current || busy) return
    setBusy(true); setError('')
    const requestId = `${current.asset_id}:v${current.version}:${next}:${feedback.trim()}`
    try {
      const auth = await authHeaders()
      const response = await fetch('/.netlify/functions/creative-review-write', {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', ...auth },
        body: JSON.stringify({ asset_id: current.asset_id, version: current.version, action: next, feedback, request_id: requestId })
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.error || 'The review could not be saved.')
      setDecision(payload.review?.status || next)
      setLibrary(previous => ({ ...previous, assets: (previous.assets || []).map(asset => asset.asset_id === current.asset_id ? { ...asset, review_state: payload.review?.status || next } : asset) }))
    } catch (err) { setError(err.message || 'The review could not be saved.') }
    finally { setBusy(false) }
  }
  return <section className="creative-review-studio" aria-label="Creative Asset Library">
    <div className="creative-review-header"><div><div className="nx2-eyebrow">CREATIVE / REVIEW STUDIO</div><h2>Review the work without hunting for files.</h2><p>Proxy-first internal review · {assets.length} verified artifacts · publication blocked</p></div><span className="creative-review-health">{library.provider || 'Loading'} · VERIFIED INDEX</span></div>
    <nav className="creative-review-tabs" aria-label="Creative asset filters">{['Overview', 'Review Queue', 'Landing Pages', 'Images', 'Videos', 'Nova', 'Archive'].map(x => <span key={x}>{x}</span>)}</nav>
    <div className="creative-review-layout"><div className="creative-review-grid">{assets.map(asset => <button type="button" key={asset.asset_id} className={`creative-review-card ${current?.asset_id === asset.asset_id ? 'selected' : ''}`} onClick={() => setSelected(asset)}><div className="creative-review-thumb">{asset.mime_type?.startsWith('video') ? <img src={asset.review_urls?.poster_object_ref || asset.review_urls?.thumbnail_object_ref} alt="Video poster" /> : <img src={asset.review_urls?.thumbnail_object_ref || asset.review_urls?.review_object_ref} alt={`${asset.channel} preview`} />}</div><strong>{asset.asset_type.replaceAll('_', ' ')}</strong><small>{asset.channel} · {asset.version}</small><em>{asset.review_state}</em></button>)}</div>
      {current && <aside className="creative-review-detail"><div className="creative-review-detail-top"><div><div className="nx2-eyebrow">{current.channel} / {current.version}</div><h3>{current.asset_type.replaceAll('_', ' ')}</h3></div><button type="button" onClick={() => setCompare(v => !v)}>{compare ? 'Exit comparison' : 'Compare versions'}</button></div>{current.mime_type?.startsWith('video') ? <video controls poster={current.review_urls?.poster_object_ref} src={current.review_urls?.review_object_ref} /> : <img className="creative-review-large" src={current.review_urls?.review_object_ref} alt="Creative review artifact" />}<dl><dt>Territory</dt><dd>{current.territory_id}</dd><dt>Storage</dt><dd>Verified object · master available explicitly</dd><dt>Provenance</dt><dd>{current.source_provenance}</dd></dl><textarea aria-label="Review feedback" value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="Concise review note" /><div className="creative-review-actions"><button type="button" disabled={busy} onClick={() => act('APPROVE')}>Approve</button><button type="button" disabled={busy} onClick={() => act('REQUEST_REVISION')}>Request revision</button><button type="button" disabled={busy} onClick={() => act('REJECT')}>Reject</button></div><small className="creative-review-decision">{busy ? 'Saving durable review…' : `${decision} · no publication triggered`}</small>{error && <small role="alert" className="creative-review-error">{error}</small>}{compare && <div className="creative-review-compare"><strong>Version comparison</strong><span>{related.length} related artifact(s) indexed; choose another card to compare side by side.</span></div>}</aside>}
    </div>
  </section>
}
