import React, { useState } from 'react'
import { researchCandidates } from '../data/researchEngineData'

function ResearchCandidateDrawer({ candidate, onClose, onAskHermes }) {
  const [status, setStatus] = useState(null)
  const [receipt, setReceipt] = useState(null)
  if (!candidate) return null

  function handleAction(action) {
    setStatus(action)
    setReceipt({ id: Date.now(), action, target: candidate.title, next: action === 'approved' ? 'Convert to opportunity, content draft, or automation task' : `${action} — local status only` })
  }

  const laneColors = { credit_readiness: 'blue', funding_readiness: 'amber', monetization: 'violet', saas_builds: 'red', marketing: 'green', business_readiness: 'blue', grants: 'green' }

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
            <small style={{ color: '#8196af' }}>Research candidate detail</small>
            <h2 style={{ margin: 0, fontSize: 16 }}>{candidate.title}</h2>
          </div>
          <button type="button" onClick={onClose} style={{ background: 'transparent', border: '1px solid #315176', color: '#dbe9fa', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>×</button>
        </header>
        <div style={{ padding: 20 }}>
          <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Source</dt><dd style={{ margin: 3, fontSize: 12 }}><span className="pill pill-blue">{candidate.source}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Score</dt><dd style={{ margin: 3, fontSize: 12 }}><strong style={{ color: candidate.score >= 70 ? '#67D47A' : candidate.score >= 50 ? '#F5A524' : '#EF6461' }}>{candidate.score}</strong></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Type</dt><dd style={{ margin: 3, fontSize: 12 }}>{candidate.type}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Lane</dt><dd style={{ margin: 3, fontSize: 12 }}><span className={`pill pill-${laneColors[candidate.lane] || 'blue'}`}>{candidate.lane.replace(/_/g, ' ')}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Status</dt><dd style={{ margin: 3, fontSize: 12 }}>{status || candidate.status}</dd></div>
          </dl>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Reason</h3>
            <p style={{ fontSize: 12, color: '#c8d5e7', lineHeight: 1.5 }}>{candidate.reason}</p>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Next action</h3>
            <p style={{ fontSize: 12, color: '#c8d5e7' }}>{candidate.nextAction}</p>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Convert options</h3>
            <div className="nxos-actions">
              {candidate.convertOptions.map(opt => (
                <span key={opt} className="pill pill-violet" style={{ textTransform: 'capitalize' }}>{opt}</span>
              ))}
            </div>
          </div>

          <div className="nxos-notice" style={{ marginBottom: 16 }}>
            <strong>How approval works:</strong> Approving a candidate marks it as approved locally. From there you can convert it to an opportunity, content draft, or automation task. No backend action is taken until a specialist or Hermes processes the conversion.
          </div>
        </div>

        <div style={{ padding: '14px 20px', borderTop: '1px solid #20344d' }}>
          <div className="nxos-actions" style={{ marginBottom: 8 }}>
            <button type="button" className={status === 'approved' ? 'primary' : ''} onClick={() => handleAction('approved')}>Approve</button>
            <button type="button" className={status === 'held' ? 'primary' : ''} onClick={() => handleAction('held')}>Hold</button>
            <button type="button" className={status === 'rejected' ? 'primary' : ''} onClick={() => handleAction('rejected')}>Reject</button>
          </div>
          <div className="nxos-actions" style={{ marginBottom: 8 }}>
            <button type="button" onClick={() => onAskHermes && onAskHermes(`Convert research candidate "${candidate.title}" to opportunity`)}>Convert to opportunity</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes(`Convert research candidate "${candidate.title}" to content draft`)}>Convert to content draft</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes(`Convert research candidate "${candidate.title}" to automation task`)}>Convert to automation task</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes(`Send research candidate "${candidate.title}" to Hermes or specialist for review`)}>Send to Hermes/Specialist</button>
          </div>
          {receipt && <div className="nxos-receipt">{receipt.action} recorded — {receipt.next}</div>}
        </div>
      </aside>
    </>
  )
}

export default function ResearchEnginePanel({ onAskHermes }) {
  const [selected, setSelected] = useState(null)
  const [laneFilter, setLaneFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [statusOverrides, setStatusOverrides] = useState({})

  function getEffectiveStatus(c) {
    return statusOverrides[c.id] || c.status
  }

  const lanes = [...new Set(researchCandidates.map(c => c.lane))].sort()
  const statuses = [...new Set(researchCandidates.map(c => c.status))].sort()

  const filtered = researchCandidates.filter(c => {
    const effective = getEffectiveStatus(c)
    if (laneFilter !== 'all' && c.lane !== laneFilter) return false
    if (statusFilter !== 'all' && effective !== statusFilter) return false
    return true
  })

  return (
    <div className="nxos-stack">
      <div className="nxos-toolbar">
        <div className="nxos-chiprow">
          <button type="button" className={laneFilter === 'all' ? 'active' : ''} onClick={() => setLaneFilter('all')}>All lanes ({researchCandidates.length})</button>
          {lanes.map(l => (
            <button key={l} type="button" className={laneFilter === l ? 'active' : ''} onClick={() => setLaneFilter(l)} style={{ textTransform: 'capitalize' }}>
              {l.replace(/_/g, ' ')} ({researchCandidates.filter(c => c.lane === l).length})
            </button>
          ))}
        </div>
      </div>
      <div className="nxos-toolbar">
        <div className="nxos-chiprow">
          <button type="button" className={statusFilter === 'all' ? 'active' : ''} onClick={() => setStatusFilter('all')}>All statuses</button>
          {statuses.map(s => (
            <button key={s} type="button" className={statusFilter === s ? 'active' : ''} onClick={() => setStatusFilter(s)} style={{ textTransform: 'capitalize' }}>
              {s}
            </button>
          ))}
        </div>
        <span style={{ color: '#8fa3be', fontSize: 12 }}>{filtered.length} candidates</span>
      </div>

      <div style={{ maxHeight: 600, overflowY: 'auto', display: 'grid', gap: 6 }}>
        {filtered.map(c => {
          const effective = getEffectiveStatus(c)
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => setSelected(c)}
              style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.4fr) auto auto auto', gap: 10, alignItems: 'center', padding: '10px 14px', background: '#0e1c2f', border: '1px solid #223751', borderRadius: 8, cursor: 'pointer', color: 'inherit', textAlign: 'left', width: '100%' }}
            >
              <div style={{ minWidth: 0 }}>
                <strong style={{ fontSize: 12 }}>{c.title}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 10 }}>{c.source} · {c.type} · {c.lane.replace(/_/g, ' ')}</span>
              </div>
              <span style={{ fontWeight: 700, color: c.score >= 70 ? '#67D47A' : c.score >= 50 ? '#F5A524' : '#EF6461', fontSize: 13 }}>{c.score}</span>
              <span className="pill pill-blue" style={{ textTransform: 'capitalize', fontSize: 10 }}>{c.lane.replace(/_/g, ' ')}</span>
              <span className={`pill pill-${effective === 'scored' ? 'blue' : effective === 'approved' ? 'green' : effective === 'held' ? 'amber' : 'red'}`} style={{ fontSize: 10 }}>{effective}</span>
            </button>
          )
        })}
      </div>

      <div className="nxos-actions">
        <button type="button" onClick={() => onAskHermes && onAskHermes('Review all research candidates and recommend top approvals')}>Ask Hermes</button>
      </div>

      <ResearchCandidateDrawer candidate={selected} onClose={() => setSelected(null)} onAskHermes={onAskHermes} />
    </div>
  )
}
