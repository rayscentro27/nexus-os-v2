import React, { useState, useEffect } from 'react'
import { businessOpportunities } from '../data/businessOpportunitiesData'
import { loadSection, SECTION_CONFIGS } from '../lib/liveDataLoader'
import { setPageContext } from '../lib/hermesSourceReasoner'
import SourceBanner from './SourceBanner'

function OpportunityDetailDrawer({ opportunity, onClose, onAskHermes, sourceType }) {
  const [status, setStatus] = useState(null)
  const [receipt, setReceipt] = useState(null)
  if (!opportunity) return null

  function handleAction(action) {
    setStatus(action)
    setReceipt({ id: Date.now(), action, target: opportunity.title, next: action === 'approved' ? 'Convert to Ray Review card or offer/content draft' : `${action} — local status only` })
  }

  const laneColors = { credit_readiness: 'blue', funding_readiness: 'amber', monetization: 'violet', saas_builds: 'red', marketing: 'green', business_readiness: 'blue', grants: 'green' }

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
            <small style={{ color: '#8196af' }}>Opportunity detail</small>
            <h2 style={{ margin: 0 }}>{opportunity.title}</h2>
          </div>
          <button type="button" onClick={onClose} style={{ background: 'transparent', border: '1px solid #315176', color: '#dbe9fa', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>x</button>
        </header>
        <div style={{ padding: 20 }}>
          <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Category</dt><dd style={{ margin: 3, fontSize: 12 }}><span className={`pill pill-${laneColors[opportunity.lane] || 'blue'}`}>{opportunity.category}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Score</dt><dd style={{ margin: 3, fontSize: 12 }}><strong style={{ color: opportunity.score >= 70 ? '#67D47A' : opportunity.score >= 50 ? '#F5A524' : '#EF6461' }}>{opportunity.score}</strong></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Revenue range</dt><dd style={{ margin: 3, fontSize: 12 }}>{opportunity.revenueRange}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Confidence</dt><dd style={{ margin: 3, fontSize: 12 }}><span className={`pill pill-${opportunity.confidence === 'high' ? 'green' : opportunity.confidence === 'medium' ? 'amber' : 'red'}`}>{opportunity.confidence}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Lane</dt><dd style={{ margin: 3, fontSize: 12 }}>{opportunity.lane.replace(/_/g, ' ')}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Status</dt><dd style={{ margin: 3, fontSize: 12 }}>{status || opportunity.status}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Data source</dt><dd style={{ margin: 3, fontSize: 12 }}>{sourceType === 'live_supabase' ? 'Live Supabase' : 'Static snapshot'}</dd></div>
          </dl>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Reason</h3>
            <p style={{ fontSize: 12, color: '#c8d5e7', lineHeight: 1.5 }}>{opportunity.reason}</p>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Next action</h3>
            <p style={{ fontSize: 12, color: '#c8d5e7' }}>{opportunity.nextAction}</p>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Convert options</h3>
            <div className="nxos-actions">
              {(opportunity.convertOptions || []).map(opt => (
                <span key={opt} className="pill pill-blue" style={{ textTransform: 'capitalize' }}>{opt}</span>
              ))}
            </div>
          </div>
        </div>

        <div style={{ padding: '14px 20px', borderTop: '1px solid #20344d' }}>
          <div className="nxos-actions" style={{ marginBottom: 8 }}>
            <button type="button" className={status === 'approved' ? 'primary' : ''} onClick={() => handleAction('approved')}>Approve</button>
            <button type="button" className={status === 'held' ? 'primary' : ''} onClick={() => handleAction('held')}>Hold</button>
            <button type="button" className={status === 'rejected' ? 'primary' : ''} onClick={() => handleAction('rejected')}>Reject</button>
          </div>
          <div className="nxos-actions" style={{ marginBottom: 8 }}>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Convert opportunity "' + opportunity.title + '" to Ray Review card')}>Convert to Ray Review card</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Convert opportunity "' + opportunity.title + '" to content or offer draft')}>Convert to content/offer draft</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Ask Hermes about opportunity: ' + opportunity.title)}>Ask Hermes</button>
          </div>
          {receipt && <div className="nxos-receipt">{receipt.action} recorded -- {receipt.next}</div>}
        </div>
      </aside>
    </>
  )
}

export default function BusinessOpportunitiesPanel({ onAskHermes }) {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('all')
  const [statusOverrides, setStatusOverrides] = useState({})
  const [sectionResult, setSectionResult] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      const result = await loadSection('business_opportunities', businessOpportunities)
      if (!cancelled) {
        setSectionResult(result)
        setPageContext('business_opportunities', {
          sectionId: 'business_opportunities',
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

  const items = sectionResult ? sectionResult.records : businessOpportunities

  function getEffectiveStatus(opp) {
    return statusOverrides[opp.id] || opp.status
  }

  const filtered = items.filter(opp => {
    const effective = getEffectiveStatus(opp)
    if (filter === 'all') return true
    return effective === filter
  })

  const counts = {
    all: items.length,
    scored: items.filter(o => getEffectiveStatus(o) === 'scored').length,
    approved: items.filter(o => getEffectiveStatus(o) === 'approved').length,
    held: items.filter(o => getEffectiveStatus(o) === 'held').length,
    rejected: items.filter(o => getEffectiveStatus(o) === 'rejected').length,
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
      <div className="nxos-toolbar">
        <div className="nxos-chiprow">
          {['all', 'scored', 'approved', 'held', 'rejected'].map(f => (
            <button
              key={f}
              type="button"
              className={filter === f ? 'active' : ''}
              onClick={() => setFilter(f)}
              style={{ textTransform: 'capitalize' }}
            >
              {f} ({counts[f] || 0})
            </button>
          ))}
        </div>
        <span style={{ color: '#8fa3be', fontSize: 12 }}>{filtered.length} shown</span>
      </div>

      <div style={{ maxHeight: 600, overflowY: 'auto', display: 'grid', gap: 8 }}>
        {filtered.map(opp => {
          const effective = getEffectiveStatus(opp)
          return (
            <button
              key={opp.id}
              type="button"
              onClick={() => setSelected(opp)}
              style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto auto auto', gap: 12, alignItems: 'center', padding: '12px 16px', background: '#0e1c2f', border: '1px solid #223751', borderRadius: 10, cursor: 'pointer', color: 'inherit', textAlign: 'left', width: '100%' }}
            >
              <div style={{ minWidth: 0 }}>
                <strong style={{ fontSize: 13 }}>{opp.title}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>{opp.category} · {(opp.lane || '').replace(/_/g, ' ')}</span>
              </div>
              <span style={{ fontWeight: 700, color: opp.score >= 70 ? '#67D47A' : opp.score >= 50 ? '#F5A524' : '#EF6461', fontSize: 14 }}>{opp.score}</span>
              <span style={{ color: '#91a6c0', fontSize: 11 }}>{opp.revenueRange}</span>
              <span className={`pill pill-${effective === 'approved' ? 'green' : effective === 'held' ? 'amber' : effective === 'rejected' ? 'red' : 'blue'}`}>{effective}</span>
            </button>
          )
        })}
      </div>

      <div className="nxos-actions">
        <button type="button" onClick={() => onAskHermes && onAskHermes('Review all business opportunities and recommend priority approvals')}>Ask Hermes</button>
      </div>

      <OpportunityDetailDrawer opportunity={selected} onClose={() => setSelected(null)} onAskHermes={onAskHermes} sourceType={sectionResult ? sectionResult.sourceType : 'static_fallback'} />
    </div>
  )
}
