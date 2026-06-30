import React, { useState } from 'react'
import { marketingDrafts } from '../data/marketingDraftsData'

function MarketingDraftDetailDrawer({ draft, onClose, onAskHermes }) {
  const [status, setStatus] = useState(null)
  const [receipt, setReceipt] = useState(null)
  const [copied, setCopied] = useState(false)
  if (!draft) return null

  function handleAction(action) {
    setStatus(action)
    setReceipt({ id: Date.now(), action, target: draft.title, next: action === 'approved' ? 'Create Ray Review card for final approval' : `${action} — local status only, no publishing` })
  }

  function handleCopy() {
    navigator.clipboard.writeText(draft.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => setCopied(true))
  }

  const effectiveStatus = status || draft.status

  return (
    <>
      <div className="nxos-overlay" onClick={onClose} />
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(580px,94vw)',
        background: '#0d1a2c', borderLeft: '1px solid #213650', zIndex: 60,
        overflowY: 'auto', display: 'grid', gridTemplateRows: 'auto 1fr auto', padding: 0
      }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px', borderBottom: '1px solid #20344d' }}>
          <div>
            <small style={{ color: '#8196af' }}>Marketing draft detail</small>
            <h2 style={{ margin: 0, fontSize: 16 }}>{draft.title}</h2>
          </div>
          <button type="button" onClick={onClose} style={{ background: 'transparent', border: '1px solid #315176', color: '#dbe9fa', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>×</button>
        </header>
        <div style={{ padding: 20 }}>
          <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Category</dt><dd style={{ margin: 3, fontSize: 12 }}><span className="pill pill-blue">{draft.category}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Type</dt><dd style={{ margin: 3, fontSize: 12 }}><span className="pill pill-violet">{draft.type}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Status</dt><dd style={{ margin: 3, fontSize: 12 }}><span className={`pill pill-${effectiveStatus === 'draft' ? 'blue' : effectiveStatus === 'approved' ? 'green' : effectiveStatus === 'held' ? 'amber' : 'red'}`}>{effectiveStatus}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Next action</dt><dd style={{ margin: 3, fontSize: 12 }}>{draft.nextAction}</dd></div>
          </dl>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, margin: '0 0 6px', color: '#8fa3be' }}>Content</h3>
            <div style={{ background: '#081525', border: '1px solid #28425f', borderRadius: 8, padding: 14, whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.6, color: '#c8d5e7', maxHeight: 400, overflowY: 'auto' }}>
              {draft.content}
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
            <button type="button" onClick={handleCopy}>{copied ? 'Copied!' : 'Copy draft'}</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes(`Create Ray Review card for marketing draft: ${draft.title}`)}>Create Ray Review card</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes(`Ask Marketing Specialist about draft: ${draft.title}`)}>Ask Marketing Specialist</button>
          </div>
          <p className="nxos-notice">Publishing is disabled. All approvals are local only — no content will be published from this panel.</p>
          {receipt && <div className="nxos-receipt">{receipt.action} recorded — {receipt.next}</div>}
        </div>
      </aside>
    </>
  )
}

export default function MarketingDraftsPanel({ onAskHermes }) {
  const [selected, setSelected] = useState(null)
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [statusOverrides, setStatusOverrides] = useState({})

  function getEffectiveStatus(draft) {
    return statusOverrides[draft.id] || draft.status
  }

  const categories = [...new Set(marketingDrafts.map(d => d.category))].sort()
  const grouped = {}
  marketingDrafts.forEach(d => {
    if (!grouped[d.category]) grouped[d.category] = []
    grouped[d.category].push(d)
  })

  const filteredDrafts = categoryFilter === 'all'
    ? marketingDrafts
    : marketingDrafts.filter(d => d.category === categoryFilter)

  const categoryCounts = {}
  categories.forEach(c => {
    categoryCounts[c] = marketingDrafts.filter(d => d.category === c).length
  })

  return (
    <div className="nxos-stack">
      <div className="nxos-metric-grid">
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Total drafts</small>
          <strong style={{ fontSize: 26 }}>{marketingDrafts.length}</strong>
        </article>
        {categories.slice(0, 3).map(cat => (
          <article key={cat} style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
            <small style={{ color: '#8fa3be', textTransform: 'capitalize' }}>{cat}</small>
            <strong style={{ fontSize: 26 }}>{categoryCounts[cat]}</strong>
          </article>
        ))}
      </div>

      <div className="nxos-toolbar">
        <div className="nxos-chiprow">
          <button type="button" className={categoryFilter === 'all' ? 'active' : ''} onClick={() => setCategoryFilter('all')}>
            All ({marketingDrafts.length})
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              type="button"
              className={categoryFilter === cat ? 'active' : ''}
              onClick={() => setCategoryFilter(cat)}
              style={{ textTransform: 'capitalize' }}
            >
              {cat} ({categoryCounts[cat]})
            </button>
          ))}
        </div>
        <span style={{ color: '#8fa3be', fontSize: 12 }}>{filteredDrafts.length} shown</span>
      </div>

      <section className="nxos-table-card" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
        <h2 style={{ margin: '0 0 12px' }}>Drafts</h2>
        {filteredDrafts.map(draft => {
          const effective = getEffectiveStatus(draft)
          return (
            <button
              key={draft.id}
              type="button"
              onClick={() => setSelected(draft)}
              style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto auto', gap: 12, alignItems: 'center', padding: '10px 0', background: 'transparent', border: 'none', borderBottom: '1px solid #1d3049', cursor: 'pointer', color: 'inherit', textAlign: 'left', width: '100%' }}
            >
              <div style={{ minWidth: 0 }}>
                <strong style={{ fontSize: 12 }}>{draft.title}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 10 }}>{draft.category} · {draft.type}</span>
              </div>
              <span className="pill pill-blue" style={{ textTransform: 'capitalize', fontSize: 10 }}>{draft.category}</span>
              <span className={`pill pill-${effective === 'draft' ? 'blue' : effective === 'approved' ? 'green' : effective === 'held' ? 'amber' : 'red'}`} style={{ fontSize: 10 }}>{effective}</span>
            </button>
          )
        })}
      </section>

      <div className="nxos-actions">
        <button type="button" onClick={() => onAskHermes && onAskHermes('Review all marketing drafts and recommend priority approvals')}>Ask Marketing Specialist</button>
      </div>

      <MarketingDraftDetailDrawer draft={selected} onClose={() => setSelected(null)} onAskHermes={onAskHermes} />
    </div>
  )
}
