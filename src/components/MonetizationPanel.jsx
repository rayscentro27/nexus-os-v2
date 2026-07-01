import React, { useState, useEffect } from 'react'
import { offers, revenueStreams } from '../data/monetizationData'
import { loadSection } from '../lib/liveDataLoader'
import { setPageContext } from '../lib/hermesSourceReasoner'
import SourceBanner from './SourceBanner'

function OfferDetailDrawer({ offer, onClose, onAskHermes, sourceType }) {
  const [status, setStatus] = useState(null)
  const [receipt, setReceipt] = useState(null)
  if (!offer) return null

  function handleAction(action) {
    setStatus(action)
    setReceipt({ id: Date.now(), action, target: offer.name, next: action === 'approved' ? 'Create Stripe test product task or content/landing draft task' : `${action} — local status only` })
  }

  const effectiveStatus = status || offer.status

  return (
    <>
      <div className="nxos-overlay" onClick={onClose} />
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(540px,92vw)',
        background: '#0d1a2c', borderLeft: '1px solid #213650', zIndex: 60,
        overflowY: 'auto', display: 'grid', gridTemplateRows: 'auto 1fr auto', padding: 0
      }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px', borderBottom: '1px solid #20344d' }}>
          <div>
            <small style={{ color: '#8196af' }}>Offer detail</small>
            <h2 style={{ margin: 0 }}>{offer.name}</h2>
          </div>
          <button type="button" onClick={onClose} style={{ background: 'transparent', border: '1px solid #315176', color: '#dbe9fa', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>x</button>
        </header>
        <div style={{ padding: 20 }}>
          <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Price</dt><dd style={{ margin: 3, fontSize: 14, fontWeight: 700 }}>${offer.price}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Status</dt><dd style={{ margin: 3, fontSize: 12 }}><span className={`pill pill-${effectiveStatus === 'approved' ? 'green' : effectiveStatus === 'draft' ? 'blue' : effectiveStatus === 'held' ? 'amber' : 'red'}`}>{effectiveStatus}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Stripe</dt><dd style={{ margin: 3, fontSize: 12 }}><span className={`pill pill-${offer.stripeStatus === 'test_checkout_created' ? 'green' : 'amber'}`}>{offer.stripeStatus.replace(/_/g, ' ')}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Audience</dt><dd style={{ margin: 3, fontSize: 12 }}>{offer.audience}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Data source</dt><dd style={{ margin: 3, fontSize: 12 }}>{sourceType === 'live_supabase' ? 'Live Supabase' : 'Static snapshot'}</dd></div>
          </dl>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Deliverables</h3>
            {(offer.deliverables || []).map((d, i) => (
              <div key={i} style={{ padding: '4px 0', fontSize: 12, color: '#c8d5e7', borderBottom: '1px solid #1d3049' }}>v {d}</div>
            ))}
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Next action</h3>
            <p style={{ fontSize: 12, color: '#c8d5e7' }}>{offer.nextAction}</p>
          </div>
        </div>

        <div style={{ padding: '14px 20px', borderTop: '1px solid #20344d' }}>
          <div className="nxos-actions" style={{ marginBottom: 8 }}>
            <button type="button" className={status === 'approved' ? 'primary' : ''} onClick={() => handleAction('approved')}>Approve</button>
            <button type="button" className={status === 'held' ? 'primary' : ''} onClick={() => handleAction('held')}>Hold</button>
            <button type="button" className={status === 'rejected' ? 'primary' : ''} onClick={() => handleAction('rejected')}>Reject</button>
          </div>
          <div className="nxos-actions" style={{ marginBottom: 8 }}>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Create Stripe test product task for "' + offer.name + '"')}>Create Stripe test product task</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Create content or landing page draft task for "' + offer.name + '"')}>Create content/landing draft task</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Ask Monetization Specialist about offer: ' + offer.name)}>Ask Monetization Specialist</button>
          </div>
          {receipt && <div className="nxos-receipt">{receipt.action} recorded -- {receipt.next}</div>}
        </div>
      </aside>
    </>
  )
}

export default function MonetizationPanel({ onAskHermes }) {
  const [selected, setSelected] = useState(null)
  const [statusOverrides, setStatusOverrides] = useState({})
  const [sectionResult, setSectionResult] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      const result = await loadSection('monetization', offers)
      if (!cancelled) {
        setSectionResult(result)
        setPageContext('monetization', {
          sectionId: 'monetization',
          sourceType: result.sourceType,
          liveData: result.liveData,
          rowCount: result.rowCount,
          staticCount: result.staticCount,
          mismatch: result.mismatch,
          tableNamesUsed: result.tableNamesUsed,
          records: result.records,
        })
        setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const items = sectionResult ? sectionResult.records : offers

  function getEffectiveStatus(offer) {
    return statusOverrides[offer.id] || offer.status
  }

  return (
    <div className="nxos-stack">
      {sectionResult && (
        <SourceBanner
          sourceType={sectionResult.sourceType}
          liveData={sectionResult.liveData}
          rowCount={sectionResult.rowCount}
          staticCount={sectionResult.staticCount}
          mismatch={sectionResult.mismatch}
          limitations={sectionResult.limitations}
          tableNamesUsed={sectionResult.tableNamesUsed}
          error={sectionResult.error}
        />
      )}
      {loading && <div style={{ color: '#8fa3be', fontSize: 12, padding: 8 }}>Loading live data...</div>}
      <div className="nxos-metric-grid">
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Total offers</small>
          <strong style={{ fontSize: 26 }}>{items.length}</strong>
        </article>
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Approved</small>
          <strong style={{ fontSize: 26, color: '#67D47A' }}>{items.filter(o => getEffectiveStatus(o) === 'approved').length}</strong>
        </article>
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Drafts</small>
          <strong style={{ fontSize: 26, color: '#3BA3FF' }}>{items.filter(o => getEffectiveStatus(o) === 'draft').length}</strong>
        </article>
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Projected monthly</small>
          <strong style={{ fontSize: 26 }}>${revenueStreams.find(r => r.id === 'rev-001')?.projectedMonthlyRevenue || 0}</strong>
        </article>
      </div>

      <section style={{ display: 'grid', gap: 8 }}>
        <h2 style={{ fontSize: 17, margin: '0 0 8px' }}>Offers</h2>
        {items.map(offer => {
          const effective = getEffectiveStatus(offer)
          return (
            <button
              key={offer.id}
              type="button"
              onClick={() => setSelected(offer)}
              style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto auto auto', gap: 12, alignItems: 'center', padding: '14px 16px', background: '#0e1c2f', border: '1px solid #223751', borderRadius: 10, cursor: 'pointer', color: 'inherit', textAlign: 'left', width: '100%' }}
            >
              <div style={{ minWidth: 0 }}>
                <strong style={{ fontSize: 13 }}>{offer.name}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>{offer.audience}</span>
              </div>
              <span style={{ fontWeight: 700, fontSize: 14, color: '#dce9f9' }}>${offer.price}</span>
              <span className={`pill pill-${offer.stripeStatus === 'test_checkout_created' ? 'green' : 'amber'}`} style={{ fontSize: 10 }}>
                {offer.stripeStatus === 'test_checkout_created' ? 'Stripe test' : 'Stripe TBD'}
              </span>
              <span className={`pill pill-${effective === 'approved' ? 'green' : effective === 'draft' ? 'blue' : effective === 'held' ? 'amber' : 'red'}`}>{effective}</span>
            </button>
          )
        })}
      </section>

      <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
        <h2 style={{ margin: '0 0 12px' }}>Revenue details</h2>
        {revenueStreams.map(r => (
          <div key={r.id} className="nxos-table-row" style={{ gridTemplateColumns: '1fr auto auto' }}>
            <div>
              <strong style={{ fontSize: 12 }}>{r.name}</strong>
              <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>{r.description}</span>
            </div>
            <span className={`pill pill-${r.status === 'awaiting_first_sale' ? 'amber' : r.status === 'concept_phase' ? 'red' : 'blue'}`}>{r.status.replace(/_/g, ' ')}</span>
            <span style={{ fontSize: 12, color: '#67D47A' }}>${r.projectedMonthlyRevenue}/mo</span>
          </div>
        ))}
      </section>

      <div className="nxos-actions">
        <button type="button" onClick={() => onAskHermes && onAskHermes('Review monetization offers and revenue projections, recommend priority actions')}>Ask Monetization Specialist</button>
      </div>

      <OfferDetailDrawer offer={selected} onClose={() => setSelected(null)} onAskHermes={onAskHermes} sourceType={sectionResult ? sectionResult.sourceType : 'static_fallback'} />
    </div>
  )
}
