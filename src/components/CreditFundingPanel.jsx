import React, { useState } from 'react'
import { creditReadiness, fundingReadiness, documentChecklist, disputeDraftQueue, bankabilityChecklist } from '../data/creditFundingData'

function DetailDrawer({ title, onClose, children, onAskHermes }) {
  const [receipt, setReceipt] = useState(null)
  return (
    <>
      <div className="nxos-overlay" onClick={onClose} />
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(560px,92vw)',
        background: '#0d1a2c', borderLeft: '1px solid #213650', zIndex: 60,
        overflowY: 'auto', display: 'grid', gridTemplateRows: 'auto 1fr auto', padding: 0
      }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px', borderBottom: '1px solid #20344d' }}>
          <div>
            <small style={{ color: '#8196af' }}>Credit &amp; Funding detail</small>
            <h2 style={{ margin: 0 }}>{title}</h2>
          </div>
          <button type="button" onClick={onClose} style={{ background: 'transparent', border: '1px solid #315176', color: '#dbe9fa', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>×</button>
        </header>
        <div style={{ padding: 20 }}>
          {children}
        </div>
        <div style={{ padding: '14px 20px', borderTop: '1px solid #20344d' }}>
          <div className="nxos-actions">
            <button type="button" className="primary" onClick={() => onAskHermes && onAskHermes(`Review ${title} and suggest next actions`)}>Ask Credit Specialist</button>
            <button type="button" onClick={onClose}>Close</button>
          </div>
          {receipt && <div className="nxos-receipt">{receipt}</div>}
        </div>
      </aside>
    </>
  )
}

function ScoreGauge({ label, score, max = 100 }) {
  const pct = Math.round((score / max) * 100)
  const tone = score >= 70 ? '#67D47A' : score >= 50 ? '#F5A524' : '#EF6461'
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: '#c8d5e7' }}>{label}</span>
        <span style={{ color: tone, fontWeight: 600 }}>{score}/{max}</span>
      </div>
      <div className="nx-mini-progress" style={{ height: 6 }}>
        <span style={{ width: `${pct}%`, background: tone, display: 'block', height: '100%', borderRadius: 99 }} />
      </div>
    </div>
  )
}

export default function CreditFundingPanel({ onAskHermes }) {
  const [activeSection, setActiveSection] = useState('credit')
  const [selectedItem, setSelectedItem] = useState(null)
  const [draftStatuses, setDraftStatuses] = useState({})

  function handleDraftAction(draftId, action) {
    setDraftStatuses(prev => ({ ...prev, [draftId]: action }))
  }

  function getDraftStatus(id) {
    return draftStatuses[id] || null
  }

  const sections = [
    { id: 'credit', label: 'Credit Readiness', score: creditReadiness.score, tone: 'amber' },
    { id: 'funding', label: 'Funding Readiness', score: fundingReadiness.score, tone: 'amber' },
    { id: 'docs', label: 'Document Checklist', count: documentChecklist.length },
    { id: 'disputes', label: 'Dispute Draft Queue', count: disputeDraftQueue.length },
    { id: 'bankability', label: 'Bankability', count: bankabilityChecklist.length },
  ]

  return (
    <div className="nxos-stack">
      <div className="nxos-metric-grid">
        {sections.map(s => (
          <button
            key={s.id}
            type="button"
            onClick={() => { setActiveSection(s.id); setSelectedItem(null) }}
            style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751', textAlign: 'left', cursor: 'pointer', color: 'inherit', display: 'block', width: '100%' }}
          >
            <small style={{ color: '#8fa3be' }}>{s.label}</small>
            <strong style={{ fontSize: 26, display: 'block', marginTop: 9, color: s.tone === 'amber' ? '#F5A524' : '#dce9f9' }}>
              {s.score !== undefined ? s.score : `${s.count} items`}
            </strong>
          </button>
        ))}
      </div>

      {activeSection === 'credit' && (
        <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
          <h2 style={{ margin: '0 0 12px' }}>Credit Readiness — Score: {creditReadiness.score}</h2>
          <p className="nxos-notice" style={{ marginBottom: 14 }}>{creditReadiness.scoreDisclaimer}</p>
          <ScoreGauge label="Readiness Score" score={creditReadiness.score} />
          <h3 style={{ fontSize: 14, margin: '16px 0 8px' }}>Gaps ({creditReadiness.gaps.length})</h3>
          {creditReadiness.gaps.map(g => (
            <div key={g.id} className="nxos-table-row" style={{ gridTemplateColumns: '1fr auto auto' }}>
              <div>
                <strong style={{ fontSize: 12 }}>{g.label}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>Category: {g.category}</span>
              </div>
              <span className={`pill pill-${g.severity === 'high' ? 'red' : g.severity === 'medium' ? 'amber' : 'green'}`}>{g.severity}</span>
              <span style={{ color: '#91a6c0', fontSize: 11 }}>Impact: {g.estimatedImpact}</span>
            </div>
          ))}
          <h3 style={{ fontSize: 14, margin: '16px 0 8px' }}>Positive factors</h3>
          {creditReadiness.positiveFactors.map((f, i) => (
            <div key={i} style={{ padding: '4px 0', fontSize: 12, color: '#8bedb5' }}>+ {f}</div>
          ))}
          <h3 style={{ fontSize: 14, margin: '16px 0 8px' }}>Negative factors</h3>
          {creditReadiness.negativeFactors.map((f, i) => (
            <div key={i} style={{ padding: '4px 0', fontSize: 12, color: '#ff9daf' }}>- {f}</div>
          ))}
          <div className="nxos-actions" style={{ marginTop: 14 }}>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Analyze credit readiness gaps and suggest dispute priorities')}>Ask Credit Specialist</button>
          </div>
        </section>
      )}

      {activeSection === 'funding' && (
        <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
          <h2 style={{ margin: '0 0 12px' }}>Funding Readiness — Score: {fundingReadiness.score} — {fundingReadiness.status}</h2>
          <ScoreGauge label="Funding Readiness" score={fundingReadiness.score} />
          <p className="nxos-notice">{fundingReadiness.avoidApplicationWarning}</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, margin: '16px 0' }}>
            <div>
              <h3 style={{ fontSize: 13, margin: '0 0 6px' }}>Personal credit blockers</h3>
              {fundingReadiness.personalCreditBlockers.map((b, i) => (
                <div key={i} style={{ padding: '3px 0', fontSize: 12, color: '#ff9daf' }}>• {b}</div>
              ))}
            </div>
            <div>
              <h3 style={{ fontSize: 13, margin: '0 0 6px' }}>Business profile blockers</h3>
              {fundingReadiness.businessProfileBlockers.map((b, i) => (
                <div key={i} style={{ padding: '3px 0', fontSize: 12, color: '#ffd37e' }}>• {b}</div>
              ))}
            </div>
          </div>
          <h3 style={{ fontSize: 14, margin: '16px 0 8px' }}>Funding paths</h3>
          {fundingReadiness.fundingPaths.map(fp => (
            <div key={fp.id} className="nxos-table-row" style={{ gridTemplateColumns: '1fr auto auto' }}>
              <div>
                <strong style={{ fontSize: 12 }}>{fp.name}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>Timeline: {fp.estimatedTimeline}</span>
              </div>
              <span className={`pill pill-${fp.status === 'recommended' ? 'green' : fp.status === 'conditional' ? 'amber' : 'red'}`}>{fp.status}</span>
              <span style={{ color: '#91a6c0', fontSize: 11 }}>Fit: {fp.fitScore}</span>
            </div>
          ))}
          <div className="nxos-actions" style={{ marginTop: 14 }}>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Review funding readiness blockers and recommend next steps')}>Ask Credit Specialist</button>
          </div>
        </section>
      )}

      {activeSection === 'docs' && (
        <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
          <h2 style={{ margin: '0 0 12px' }}>Document Checklist</h2>
          {documentChecklist.map(d => (
            <div key={d.id} className="nxos-table-row" style={{ gridTemplateColumns: '1fr auto auto auto' }}>
              <div>
                <strong style={{ fontSize: 12 }}>{d.name}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>Category: {d.category}{d.dueDate ? ` · Due: ${d.dueDate}` : ''}</span>
              </div>
              {d.required && <span className="pill pill-red">Required</span>}
              <span className={`pill pill-${d.status === 'approved' ? 'green' : d.status === 'uploaded' ? 'blue' : d.status === 'under_review' ? 'amber' : 'red'}`}>{d.status}</span>
            </div>
          ))}
        </section>
      )}

      {activeSection === 'disputes' && (
        <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
          <h2 style={{ margin: '0 0 12px' }}>Dispute Draft Queue</h2>
          <p className="nxos-notice" style={{ marginBottom: 14 }}>No real disputes will be sent. Approve/hold/reject are local status changes only.</p>
          {disputeDraftQueue.map(d => {
            const localStatus = getDraftStatus(d.id)
            return (
              <div key={d.id} className="nxos-table-card" style={{ padding: 14, marginBottom: 10, background: '#0e1c2f', border: '1px solid #223751' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <strong style={{ fontSize: 13 }}>{d.creditor}</strong>
                    <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>{d.accountNumber} · {d.accountType} · {d.disputeReason.replace(/_/g, ' ')}</span>
                    <span style={{ display: 'block', color: '#91a6c0', fontSize: 11 }}>Bureaus: {d.bureaus.join(', ')}</span>
                    <span style={{ display: 'block', color: '#91a6c0', fontSize: 11 }}>Next: {d.nextAction}</span>
                  </div>
                  <span className={`pill pill-${d.draftStatus === 'ready_for_review' ? 'green' : d.draftStatus === 'awaiting_documents' ? 'amber' : 'blue'}`}>{d.draftStatus.replace(/_/g, ' ')}</span>
                </div>
                <div className="nxos-actions" style={{ marginTop: 10 }}>
                  <button type="button" className={localStatus === 'approved' ? 'primary' : ''} onClick={() => handleDraftAction(d.id, 'approved')}>Approve</button>
                  <button type="button" className={localStatus === 'held' ? 'primary' : ''} onClick={() => handleDraftAction(d.id, 'held')}>Hold</button>
                  <button type="button" className={localStatus === 'rejected' ? 'primary' : ''} onClick={() => handleDraftAction(d.id, 'rejected')}>Reject</button>
                  {localStatus && <span className="nxos-receipt" style={{ marginLeft: 8 }}>{localStatus} — receipt {Date.now()}</span>}
                </div>
              </div>
            )
          })}
          <div className="nxos-actions" style={{ marginTop: 14 }}>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Create approval card for dispute draft review')}>Create approval card for dispute draft review</button>
          </div>
        </section>
      )}

      {activeSection === 'bankability' && (
        <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
          <h2 style={{ margin: '0 0 12px' }}>Bankability Checklist</h2>
          {bankabilityChecklist.map(b => (
            <div key={b.id} className="nxos-table-row" style={{ gridTemplateColumns: '1fr auto' }}>
              <strong style={{ fontSize: 12 }}>{b.item}</strong>
              <span className={`pill pill-${b.status === 'complete' ? 'green' : b.status === 'in_progress' ? 'amber' : b.status === 'not_required' ? 'blue' : 'red'}`}>{b.status.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </section>
      )}

      {!activeSection && (
        <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20, textAlign: 'center', color: '#9cafc6' }}>
          <p>Select a section above to view details.</p>
        </section>
      )}

      <div className="nxos-actions">
        <button type="button" onClick={() => onAskHermes && onAskHermes('Review overall credit and funding readiness and recommend priority actions')}>Ask Credit Specialist</button>
      </div>
    </div>
  )
}
