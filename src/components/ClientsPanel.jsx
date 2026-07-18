import React, { useState, useEffect } from 'react'
import { clientsList, clientStages } from '../data/clientsData'
import { loadSection } from '../lib/liveDataLoader'
import { setPageContext } from '../lib/hermesSourceReasoner'
import SourceBanner from './SourceBanner'
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient'

function ClientDetailDrawer({ client, onClose, onAskHermes, sourceType }) {
  const [receipt, setReceipt] = useState(null)
  const [storageFiles, setStorageFiles] = useState([])
  const [storageLoading, setStorageLoading] = useState(false)
  const [adminNote, setAdminNote] = useState('')
  const [adminNoteSaved, setAdminNoteSaved] = useState(false)
  const [liveDocuments, setLiveDocuments] = useState([])
  const [liveReviewRequests, setLiveReviewRequests] = useState([])
  const [liveProfileFields, setLiveProfileFields] = useState(null)

  useEffect(() => {
    if (!client || !isSupabaseConfigured) return
    let cancelled = false
    async function loadStorage() {
      setStorageLoading(true)
      try {
        const { data: { user } } = await supabase.auth.getUser()
        if (!user) return
        const targetClientId = client.client_id || client.id
        const [storageResult, docsResult, tasksResult, profileResult] = await Promise.all([
          supabase.storage.from('client-documents').list(targetClientId, { limit: 50 }),
          supabase.from('client_documents').select('title,status,source,created_at,goclear_review_status,category').eq('client_id', targetClientId).limit(20),
          supabase.from('client_tasks').select('title,status,category,source,created_at').eq('client_id', targetClientId).eq('category', 'review_request').limit(10),
          supabase.from('client_profiles').select('legal_name,preferred_name,phone,mailing_address_line1,mailing_address_line2,city,state,postal_code,business_name,entity_type,ein_status,industry,naics_code,business_address_line1,business_address_line2,business_city,business_state,business_postal_code,time_in_business,monthly_revenue_range,funding_goal_range').eq('client_id', targetClientId).maybeSingle(),
        ])
        if (!cancelled) {
          if (!storageResult.error && storageResult.data) setStorageFiles(storageResult.data)
          if (!docsResult.error && docsResult.data) setLiveDocuments(docsResult.data)
          if (!tasksResult.error && tasksResult.data) setLiveReviewRequests(tasksResult.data)
          if (!profileResult.error && profileResult.data) setLiveProfileFields(profileResult.data)
        }
      } catch (e) {
        // silent
      }
      if (!cancelled) setStorageLoading(false)
    }
    loadStorage()
    return () => { cancelled = true }
  }, [client])

  if (!client) return null

  function handleApprove() {
    setReceipt({ id: Date.now(), action: 'approve', target: client.name, next: 'Create Ray Review card for fake customer insert' })
  }
  function handleHold() {
    setReceipt({ id: Date.now(), action: 'hold', target: client.name, next: 'Client placed on hold -- no backend action taken' })
  }

  const stage = clientStages.find(s => s.id === client.stage)

  return (
    <>
      <div className="nxos-overlay" onClick={onClose} />
      <aside data-testid="admin-client-detail-drawer" style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(520px,90vw)',
        background: '#0d1a2c', borderLeft: '1px solid #213650', zIndex: 60,
        overflowY: 'auto', display: 'grid', gridTemplateRows: 'auto 1fr auto', padding: 0
      }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '18px 20px', borderBottom: '1px solid #20344d' }}>
          <div>
            <small style={{ color: '#8196af' }}>Client detail</small>
            <h2 style={{ margin: 0 }}>{client.name}</h2>
          </div>
          <button type="button" onClick={onClose} style={{ background: 'transparent', border: '1px solid #315176', color: '#dbe9fa', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>x</button>
        </header>

        <div style={{ padding: 20 }}>
          <dl style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, margin: '0 0 18px' }}>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Email</dt><dd style={{ margin: 3, fontSize: 12, color: '#dce9f9' }}>{client.email}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Status</dt><dd style={{ margin: 3, fontSize: 12 }}><span className="pill pill-green">{client.status}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Stage</dt><dd style={{ margin: 3, fontSize: 12 }}>{stage ? stage.label : client.stage}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Membership</dt><dd style={{ margin: 3, fontSize: 12 }}>{client.membershipTier}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Payment</dt><dd style={{ margin: 3, fontSize: 12 }}><span className="pill pill-amber">{client.paymentStatus}</span></dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Dashboard live</dt><dd style={{ margin: 3, fontSize: 12 }}>{client.dashboardLiveFlag ? <span className="pill pill-green">Live</span> : <span className="pill pill-red">Off</span>}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Onboarding readiness</dt><dd style={{ margin: 3, fontSize: 12 }}>{client.onboardingReadiness}%</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Advisor</dt><dd style={{ margin: 3, fontSize: 12 }}>{client.advisorName}</dd></div>
            <div><dt style={{ color: '#7f94ae', fontSize: 10 }}>Data source</dt><dd style={{ margin: 3, fontSize: 12 }}>{sourceType === 'live_supabase' ? 'Live Supabase' : 'Static snapshot'}</dd></div>
          </dl>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Readiness Scores</h3>
            {client.readinessScores && Object.entries(client.readinessScores).map(([key, val]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1d3049', fontSize: 12 }}>
                <span style={{ color: '#91a6c0' }}>{key.replace(/([A-Z])/g, ' $1')}</span>
                <span className={val >= 70 ? 'green-text' : val >= 50 ? 'amber-text' : 'red-text'}>{val}</span>
              </div>
            ))}
          </div>

          {liveProfileFields && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Profile & Business Info</h3>
              {[
                ['Legal name', liveProfileFields.legal_name],
                ['Phone', liveProfileFields.phone],
                ['Mailing address', [liveProfileFields.mailing_address_line1, liveProfileFields.city, liveProfileFields.state, liveProfileFields.postal_code].filter(Boolean).join(', ')],
                ['Business name', liveProfileFields.business_name],
                ['Entity type', liveProfileFields.entity_type],
                ['EIN status', liveProfileFields.ein_status],
                ['Industry', liveProfileFields.industry],
                ['NAICS code', liveProfileFields.naics_code],
                ['Time in business', liveProfileFields.time_in_business],
                ['Monthly revenue', liveProfileFields.monthly_revenue_range],
                ['Funding goal', liveProfileFields.funding_goal_range],
              ].filter(([, val]) => val).map(([label, val]) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1d3049', fontSize: 12 }}>
                  <span style={{ color: '#91a6c0' }}>{label}</span>
                  <span style={{ color: '#c8d5e7' }}>{val}</span>
                </div>
              ))}
              {Object.values(liveProfileFields).every(v => !v) && (
                <p style={{ color: '#8fa3be', fontSize: 12 }}>No profile intake data submitted yet.</p>
              )}
            </div>
          )}

          {client.documents && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Documents ({(client.documents.uploadedDocuments || []).length} uploaded, {(client.documents.missingDocuments || []).length} missing)</h3>
              {(client.documents.requiredDocuments || []).map(doc => {
                const isUploaded = (client.documents.uploadedDocuments || []).includes(doc)
                const isMissing = (client.documents.missingDocuments || []).includes(doc)
                return (
                  <div key={doc} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 12, borderBottom: '1px solid #1d3049' }}>
                    <span style={{ color: '#c8d5e7' }}>{doc}</span>
                    <span className={isUploaded ? 'green-text' : isMissing ? 'red-text' : 'amber-text'}>{isUploaded ? 'Uploaded' : isMissing ? 'Missing' : 'Under review'}</span>
                  </div>
                )
              })}
            </div>
          )}

          {client.tasks && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Tasks ({client.tasks.length})</h3>
              {client.tasks.map(t => (
                <div key={t.id} className="nxos-table-row" style={{ gridTemplateColumns: '1fr auto auto' }}>
                  <strong style={{ fontSize: 12 }}>{t.title}</strong>
                  <span className={`pill pill-${t.priority === 'high' ? 'red' : 'amber'}`}>{t.priority}</span>
                  <span className={`pill pill-${t.status === 'open' ? 'blue' : 'violet'}`}>{t.status}</span>
                </div>
              ))}
            </div>
          )}

          {client.messages && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Messages ({client.messages.length})</h3>
              {client.messages.map(m => (
                <div key={m.id} className="nxos-table-row" style={{ gridTemplateColumns: '1fr auto' }}>
                  <div>
                    <strong style={{ fontSize: 12 }}>{m.title}</strong>
                    <p style={{ color: '#8fa3be', fontSize: 11, margin: '2px 0 0' }}>{m.body}</p>
                  </div>
                  <span className={`pill ${m.read ? 'pill-green' : 'pill-amber'}`}>{m.read ? 'Read' : 'Unread'}</span>
                </div>
              ))}
            </div>
          )}

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Live document metadata ({liveDocuments.length}{storageLoading ? ', loading...' : ''})</h3>
            {liveDocuments.length === 0 && !storageLoading && (
              <p style={{ color: '#8fa3be', fontSize: 12 }}>No client_documents rows found.</p>
            )}
            {liveDocuments.map((d, idx) => (
              <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1d3049', fontSize: 12 }}>
                <span style={{ color: '#c8d5e7' }}>{d.category || d.title || 'Untitled document'}</span>
                <span style={{ color: '#91a6c0' }}>{d.status}{d.goclear_review_status ? ` · ${d.goclear_review_status}` : ''}</span>
              </div>
            ))}
          </div>

          {liveReviewRequests.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Pending review requests ({liveReviewRequests.length})</h3>
              {liveReviewRequests.map((r, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1d3049', fontSize: 12 }}>
                  <span style={{ color: '#c8d5e7' }}>{r.title || 'Review request'}</span>
                  <span className={`pill pill-${r.status === 'pending_admin_review' ? 'amber' : 'blue'}`}>{r.status}</span>
                </div>
              ))}
            </div>
          )}

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Storage files {storageLoading && <span style={{ color: '#8fa3be', fontSize: 11 }}>(loading...)</span>}</h3>
            {storageFiles.length === 0 && !storageLoading && (
              <p style={{ color: '#8fa3be', fontSize: 12 }}>No files uploaded yet</p>
            )}
            {storageFiles.map(f => (
              <div key={f.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1d3049', fontSize: 12 }}>
                <span style={{ color: '#c8d5e7' }}>{f.name}</span>
                <span style={{ color: '#91a6c0' }}>{f.metadata?.size ? `${(f.metadata.size / 1024).toFixed(0)}KB` : ''}</span>
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, margin: '0 0 8px' }}>Admin Notes</h3>
            <textarea
              value={adminNote}
              onChange={e => { setAdminNote(e.target.value); setAdminNoteSaved(false) }}
              placeholder="Add internal notes about this client..."
              style={{ width: '100%', minHeight: 60, background: '#0e1c2f', border: '1px solid #213650', borderRadius: 8, color: '#dce9f9', padding: 8, fontSize: 12, resize: 'vertical' }}
            />
            <button
              type="button"
              onClick={() => setAdminNoteSaved(true)}
              style={{ marginTop: 6, background: '#1e3a5f', border: '1px solid #315176', color: '#dbe9fa', borderRadius: 6, padding: '4px 10px', fontSize: 11, cursor: 'pointer' }}
            >
              {adminNoteSaved ? 'Saved' : 'Save Note'}
            </button>
          </div>
        </div>

        <div style={{ padding: '14px 20px', borderTop: '1px solid #20344d' }}>
          <div className="nxos-actions" style={{ marginBottom: 8 }}>
            <button type="button" className="primary" onClick={handleApprove}>Approve</button>
            <button type="button" onClick={handleHold}>Hold</button>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Review client ' + client.name + ' status and suggest next actions')}>
              Ask Hermes
            </button>
          </div>
          {receipt && <div className="nxos-receipt">{receipt.action === 'approve' ? 'Approval recorded' : 'Hold recorded'}: {receipt.next}</div>}
        </div>
      </aside>
    </>
  )
}

export default function ClientsPanel({ onAskHermes }) {
  const [selected, setSelected] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [sectionResult, setSectionResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [clientCounts, setClientCounts] = useState({})

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      const result = await loadSection('clients', clientsList)
      if (!cancelled) {
        setSectionResult(result)
        setPageContext('clients', {
          sectionId: 'clients',
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

  useEffect(() => {
    if (!sectionResult || !isSupabaseConfigured) return
    let cancelled = false
    async function fetchCounts() {
      const counts = {}
      for (const client of sectionResult.records) {
        const clientId = client.client_id || client.id
        if (!clientId) continue
        try {
          const [docsResult, tasksResult] = await Promise.all([
            supabase.from('client_documents').select('id', { count: 'exact', head: true }).eq('client_id', clientId),
            supabase.from('client_tasks').select('id', { count: 'exact', head: true }).eq('client_id', clientId).eq('category', 'review_request').eq('status', 'pending_admin_review'),
          ])
          if (!cancelled) {
            counts[clientId] = {
              documentCount: docsResult.count ?? 0,
              pendingReviewCount: tasksResult.count ?? 0,
            }
          }
        } catch { /* silent */ }
      }
      if (!cancelled) setClientCounts(counts)
    }
    fetchCounts()
    return () => { cancelled = true }
  }, [sectionResult])

  const items = sectionResult ? sectionResult.records : clientsList
  const filteredItems = searchQuery
    ? items.filter(c => {
        const q = searchQuery.toLowerCase()
        return (c.name || '').toLowerCase().includes(q) || (c.email || '').toLowerCase().includes(q) || (c.client_id || c.id || '').toLowerCase().includes(q)
      })
    : items

  function handleRowClick(client) {
    setSelected(client)
    setDrawerOpen(true)
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
          <small style={{ color: '#8fa3be' }}>Total clients</small>
          <strong style={{ fontSize: 26 }}>{items.length}</strong>
        </article>
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Avg readiness</small>
          <strong style={{ fontSize: 26 }}>{items.length > 0 ? Math.round(items.reduce((a, c) => a + (c.onboardingReadiness || 0), 0) / items.length) : 0}%</strong>
        </article>
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Open tasks</small>
          <strong style={{ fontSize: 26 }}>{items.reduce((a, c) => a + (c.tasks || []).filter(t => t.status === 'open').length, 0)}</strong>
        </article>
        <article style={{ padding: 18, borderRadius: 14, background: '#0e1c2f', border: '1px solid #223751' }}>
          <small style={{ color: '#8fa3be' }}>Dashboard live</small>
          <strong style={{ fontSize: 26 }}>{items.filter(c => c.dashboardLiveFlag).length}</strong>
        </article>
      </div>

      <section className="nxos-table-card" data-testid="admin-client-list" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Client status (test/fake customer)</h2>
          <input
            type="text"
            placeholder="Search clients by name, email, or ID..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ background: '#0e1c2f', border: '1px solid #213650', borderRadius: 8, color: '#dbe9fa', padding: '6px 12px', fontSize: 12, width: 280 }}
          />
        </div>
        {filteredItems.length === 0 && <p style={{ color: '#8fa3be', fontSize: 12 }}>No clients match the search.</p>}
        {filteredItems.map(client => {
          const stage = clientStages.find(s => s.id === client.stage)
          const clientId = client.client_id || client.id
          const counts = clientCounts[clientId] || {}
          return (
            <button
              key={client.id}
              type="button"
              className="nxos-table-row"
              data-testid="admin-client-row"
              style={{ gridTemplateColumns: '1.2fr auto auto auto auto auto', background: 'transparent', border: 'none', width: '100%', textAlign: 'left', cursor: 'pointer', color: 'inherit' }}
              onClick={() => handleRowClick(client)}
            >
              <div>
                <strong>{client.name}</strong>
                <span style={{ display: 'block', color: '#8fa3be', fontSize: 11 }}>{client.email}</span>
              </div>
              <span className="pill pill-green">{client.status}</span>
              <span className="pill pill-amber">{stage ? stage.label : client.stage}</span>
              <span style={{ color: '#91a6c0', fontSize: 12 }}>{client.onboardingReadiness || 0}% ready</span>
              <span style={{ color: counts.documentCount > 0 ? '#10b981' : '#91a6c0', fontSize: 11 }}>{counts.documentCount || 0} docs</span>
              <span style={{ color: (counts.pendingReviewCount || 0) > 0 ? '#f59e0b' : '#91a6c0', fontSize: 11 }}>{counts.pendingReviewCount || 0} reviews</span>
            </button>
          )
        })}
      </section>

      <div className="nxos-actions">
        <button type="button" className="primary" onClick={() => onAskHermes && onAskHermes('Create Ray Review card for fake customer insert')}>
          Create Ray Review card for fake customer insert
        </button>
        <button type="button" onClick={() => onAskHermes && onAskHermes('Review all client onboarding readiness and suggest priority actions')}>
          Ask Hermes
        </button>
      </div>

      <ClientDetailDrawer
        client={drawerOpen ? selected : null}
        onClose={() => { setDrawerOpen(false); setSelected(null) }}
        onAskHermes={onAskHermes}
        sourceType={sectionResult ? sectionResult.sourceType : 'static_fallback'}
      />
    </div>
  )
}
