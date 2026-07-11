/**
 * Credit Specialist Workbench — Admin page for reviewing credit reports,
 * identifying dispute items, generating draft letters, and managing DocuPost.
 */

import React, { useEffect, useState } from 'react'
import {
  CheckCircle2, CircleAlert, FileText, Eye, Clock, Send, Upload,
  User, Building2, Mail, AlertTriangle, ChevronRight, Download, Stamp,
} from 'lucide-react'
import {
  loadCreditRepairJourney,
  loadPendingCreditReportReviews,
  createDisputeItem,
  createDisputeLetterDraft,
  generateDisputeLetterBody,
  approveLetterForSpecialistReview,
  specialistApproveLetter,
  createDocuPostSendRequest,
  markMailJobSent,
} from '../lib/creditRepairWorkflow'
import { DISPUTE_REASON_LABELS, OUTCOME_CATEGORIES } from '../lib/disputeStrategyKnowledge'
import { getStrategyResearchBacklog, recommendNextRoundStrategy, summarizeStrategyOutcomes } from '../lib/creditStrategyResearchEngine'
import { CREDIT_REPORT_PARSER_VERSION } from '../lib/creditReportParser'

const DEMO_CLIENT_ID = 'client_test_julius_erving'
const DEMO_TENANT_ID = 'tenant_default'

export default function CreditSpecialistWorkbench({ onAskHermes }) {
  const [journey, setJourney] = useState(null)
  const [pendingReviews, setPendingReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('queue')
  const [selectedReview, setSelectedReview] = useState(null)
  const [selectedPending, setSelectedPending] = useState(null)
  const [newItemForm, setNewItemForm] = useState({
    bureau: 'experian', furnisherName: '', accountName: '', accountNumberMask: '',
    disputeReason: '', factualBasis: '', requestedAction: 'dispute',
  })
  const [generating, setGenerating] = useState(false)
  const [queueCheckedAt, setQueueCheckedAt] = useState(null)
  const [queueError, setQueueError] = useState(null)

  useEffect(() => {
    Promise.all([
      loadCreditRepairJourney(),
      loadPendingCreditReportReviews(),
    ]).then(([journeyData, pending]) => {
      setJourney(journeyData)
      setPendingReviews(pending)
      setQueueCheckedAt(new Date().toISOString())
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  async function refreshQueue() {
    try {
      const pending = await loadPendingCreditReportReviews()
      setPendingReviews(pending)
      setQueueCheckedAt(new Date().toISOString())
      setQueueError(null)
    } catch (e) {
      setQueueError(e?.message || 'Failed to load queue')
    }
  }

  async function handleCreateItem() {
    if (!newItemForm.disputeReason) return
    await createDisputeItem({
      clientId: DEMO_CLIENT_ID,
      tenantId: DEMO_TENANT_ID,
      reviewId: selectedReview?.id,
      bureau: newItemForm.bureau,
      furnisherName: newItemForm.furnisherName || undefined,
      accountName: newItemForm.accountName || undefined,
      accountNumberMask: newItemForm.accountNumberMask || undefined,
      disputeReason: newItemForm.disputeReason,
      factualBasis: newItemForm.factualBasis,
      requestedAction: newItemForm.requestedAction,
    })
    const updated = await loadCreditRepairJourney()
    setJourney(updated)
    setNewItemForm({ bureau: 'experian', furnisherName: '', accountName: '', accountNumberMask: '', disputeReason: '', factualBasis: '', requestedAction: 'dispute' })
  }

  async function handleGenerateLetter() {
    if (!journey?.disputeItems?.length) return
    setGenerating(true)
    const items = journey.disputeItems.map(d => ({
      furnisherName: d.furnisher_name,
      accountName: d.account_name,
      accountNumberMask: d.account_number_mask,
      disputeReason: d.dispute_reason,
      factualBasis: d.factual_basis,
      requestedAction: d.requested_action,
    }))
    const body = generateDisputeLetterBody({
      clientName: 'Julius Erving (Demo)',
      clientAddress: '[Client Address on File]',
      recipientName: 'Experian',
      recipientAddress: 'P.O. Box 4500\nAllen, TX 75013',
      bureau: 'Experian',
      items,
    })
    await createDisputeLetterDraft({
      tenantId: DEMO_TENANT_ID,
      clientId: DEMO_CLIENT_ID,
      disputeItemIds: journey.disputeItems.map(d => d.id),
      recipientType: 'bureau',
      recipientName: 'Experian',
      letterBody: body,
    })
    const updated = await loadCreditRepairJourney()
    setJourney(updated)
    setGenerating(false)
  }

  async function handleApproveLetter(letterId) {
    await specialistApproveLetter(letterId)
    const updated = await loadCreditRepairJourney()
    setJourney(updated)
  }

  async function handleSendToDocuPost(letterId) {
    await createDocuPostSendRequest(letterId)
    const updated = await loadCreditRepairJourney()
    setJourney(updated)
  }

  const reviews = journey?.reviews ?? []
  const items = journey?.disputeItems ?? []
  const letters = journey?.letters ?? []
  const mailJobs = journey?.mailJobs ?? []
  const strategySummary = summarizeStrategyOutcomes([])

  const tabs = [
    { key: 'queue', label: 'Client Queue', count: pendingReviews.length },
    { key: 'case_engine', label: 'Case Engine', count: items.length + letters.length },
    { key: 'parser_preview', label: 'Parser Preview', count: 0 },
    { key: 'items', label: 'Dispute Items', count: items.length },
    { key: 'letters', label: 'Letters', count: letters.length },
    { key: 'mail', label: 'DocuPost', count: mailJobs.length },
  ]

  return <div style={{ padding: 16, color: '#edf5ff' }}>
    <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>Credit Specialist Workbench</h1>
    <p style={{ fontSize: 13, color: '#94a7c3', marginBottom: 16 }}>Review reports, identify dispute items, generate drafts, and move approved letters into DocuPost.</p>

    {loading && <div style={{ color: '#94a7c3', fontSize: 12 }}>Loading...</div>}

    {/* Tabs */}
    <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
      {tabs.map(tab => <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
        padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 12,
        background: activeTab === tab.key ? 'linear-gradient(135deg, #1766ff, #7048e8)' : 'rgba(255,255,255,.08)',
        color: activeTab === tab.key ? '#fff' : '#94a7c3',
      }}>{tab.label} <span style={{ marginLeft: 4, opacity: .7 }}>({tab.count})</span></button>)}
    </div>

    {activeTab === 'parser_preview' && <ParserPreviewPanel pendingReviews={pendingReviews} />}

    {/* Queue Tab — wired to client_documents pending credit reports */}
    {activeTab === 'queue' && <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 2 }}>Client Queue</h3>
          <p style={{ fontSize: 12, color: '#94a7c3' }}>Pending credit report uploads from client portal. Queue source: client_documents pending credit_report uploads.</p>
        </div>
        <button onClick={refreshQueue} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid rgba(148,163,184,.2)', background: 'rgba(255,255,255,.06)', color: '#94a7c3', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Refresh</button>
      </div>

      {queueCheckedAt && <div style={{ fontSize: 10, color: '#6b7b94', marginBottom: 8 }}>Last checked: {new Date(queueCheckedAt).toLocaleTimeString()}</div>}
      {queueError && <div style={{ padding: 8, borderRadius: 6, background: 'rgba(239,68,68,.12)', color: '#ef4444', fontSize: 11, marginBottom: 8 }}>Queue load error: {queueError}</div>}

      {pendingReviews.length === 0 && !loading && <div style={{ padding: 20, textAlign: 'center', color: '#94a7c3' }}>
        <div style={{ marginBottom: 6 }}>No credit report reviews yet.</div>
        <div style={{ fontSize: 11, color: '#6b7b94' }}>When a client uploads a credit report from /client/documents, it will appear here.</div>
      </div>}

      {pendingReviews.map(doc => <div key={doc.reviewId} onClick={() => setSelectedPending(selectedPending?.reviewId === doc.reviewId ? null : doc)} style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderRadius: 10,
        border: `1px solid ${selectedPending?.reviewId === doc.reviewId ? 'rgba(23,102,255,.4)' : 'rgba(148,163,184,.18)'}`,
        background: selectedPending?.reviewId === doc.reviewId ? 'rgba(23,102,255,.08)' : 'transparent',
        cursor: 'pointer', marginBottom: 8,
      }}>
        <div style={{ width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg, #1766ff, #7048e8)', display: 'grid', placeItems: 'center', color: '#fff', flexShrink: 0 }}>
          <FileText size={18} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <strong style={{ fontSize: 13 }}>{doc.fileName}</strong>
          <div style={{ fontSize: 11, color: '#94a7c3', marginTop: 2 }}>
            {doc.clientName || doc.clientId} {doc.clientEmail ? `(${doc.clientEmail})` : ''} · {doc.uploadedAt ? new Date(doc.uploadedAt).toLocaleDateString() : 'Unknown date'}
          </div>
          <div style={{ fontSize: 10, color: '#6b7b94', marginTop: 2 }}>
            Category: {doc.category || 'credit_report'} · Source: {doc.source || 'client_portal'} · Parser: {doc.parserStatus?.replace(/_/g, ' ')}
          </div>
        </div>
        <span style={{ padding: '3px 8px', borderRadius: 12, background: 'rgba(245,158,11,.15)', color: '#f59e0b', fontSize: 11, fontWeight: 700, flexShrink: 0 }}>
          {doc.reviewStatusLabel}
        </span>
      </div>)}

      {/* Detail panel */}
      {selectedPending && <div style={{ marginTop: 12, padding: 14, borderRadius: 10, border: '1px solid rgba(23,102,255,.25)', background: 'rgba(23,102,255,.06)' }}>
        <h4 style={{ fontSize: 13, fontWeight: 800, marginBottom: 8 }}>Report Detail</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 12, color: '#94a7c3', marginBottom: 12 }}>
          <div><strong>File:</strong> {selectedPending.fileName}</div>
          <div><strong>Client:</strong> {selectedPending.clientName || selectedPending.clientId}</div>
          <div><strong>Status:</strong> {selectedPending.reviewStatusLabel}</div>
          <div><strong>Parser:</strong> {selectedPending.parserStatus?.replace(/_/g, ' ')}</div>
          <div><strong>Source:</strong> {selectedPending.source || 'client_portal'}</div>
          <div><strong>Uploaded:</strong> {selectedPending.uploadedAt ? new Date(selectedPending.uploadedAt).toLocaleString() : 'Unknown'}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #1766ff, #7048e8)', color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}>Review Report</button>
          <button disabled style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(148,163,184,.2)', background: 'rgba(255,255,255,.06)', color: '#6b7b94', fontSize: 12, cursor: 'not-allowed' }} title="Live parser requires backend file extraction worker. Use manual review or test fixtures for parser preview.">Run Parser Preview</button>
          <button disabled style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(148,163,184,.2)', background: 'rgba(255,255,255,.06)', color: '#6b7b94', fontSize: 12, cursor: 'not-allowed' }} title="Create case only after parser preview or manual item identification.">Create Credit Repair Case</button>
          <button disabled style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(148,163,184,.2)', background: 'rgba(255,255,255,.06)', color: '#6b7b94', fontSize: 12, cursor: 'not-allowed' }}>Add Manual Item</button>
          <button disabled style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(148,163,184,.2)', background: 'rgba(255,255,255,.06)', color: '#6b7b94', fontSize: 12, cursor: 'not-allowed' }}>Mark Needs Info</button>
        </div>
        <div style={{ marginTop: 10, padding: 10, borderRadius: 8, background: 'rgba(245,158,11,.12)', color: '#f59e0b', fontSize: 11 }}>
          Parser suggestions and dispute items require specialist confirmation before letters or DocuPost can proceed. No letters are generated automatically.
        </div>
      </div>}
    </div>}

    {activeTab === 'case_engine' && <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 12 }}>
      <section style={{ padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,.18)' }}>
        <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Credit Repair Case Engine Review</h3>
        <p style={{ fontSize: 12, color: '#94a7c3', marginBottom: 10 }}>Specialist reviews selected items, client reasons, evidence, and letter options before sending anything to client approval.</p>
        {items.length === 0 && <p style={{ fontSize: 12, color: '#94a7c3' }}>No client-selected report items yet.</p>}
        {items.map(item => <div key={item.id} style={{ padding: 10, borderRadius: 8, border: '1px solid rgba(148,163,184,.18)', marginBottom: 8 }}>
          <strong style={{ fontSize: 13 }}>{item.furnisher_name || item.account_name || 'Report item'}</strong>
          <div style={{ fontSize: 11, color: '#94a7c3' }}>{item.bureau?.toUpperCase()} · {item.item_type || 'credit item'} · reason: {item.dispute_reason || 'client selection pending'}</div>
          <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
            <button type="button" onClick={() => onAskHermes && onAskHermes('Review selected dispute item and recommend compliant letter option')} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#1766ff', color: '#fff', fontSize: 11, fontWeight: 700 }}>Review strategy</button>
            <button type="button" onClick={() => setActiveTab('letters')} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', fontSize: 11, fontWeight: 700 }}>Review drafts</button>
            <button type="button" onClick={() => setActiveTab('mail')} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#7048e8', color: '#fff', fontSize: 11, fontWeight: 700 }}>DocuPost gate</button>
          </div>
        </div>)}
      </section>
      <section style={{ padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,.18)' }}>
        <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Supported Reasons & Outcome Learning</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 12 }}>
          {Object.values(DISPUTE_REASON_LABELS).slice(0, 12).map(reason => <span key={reason} style={{ fontSize: 11, color: '#94a7c3', padding: '5px 7px', borderRadius: 8, background: 'rgba(255,255,255,.06)' }}>{reason}</span>)}
        </div>
        <p style={{ fontSize: 12, color: '#94a7c3', marginBottom: 8 }}>Record outcomes after bureau/furnisher responses. Nexus should learn what worked and what did not without promising outcomes.</p>
        <p style={{ fontSize: 12, color: '#94a7c3', marginBottom: 8 }}>Backend strategy summary: {strategySummary.summary}. Next-round rule: {recommendNextRoundStrategy({ response_result: 'verified' })}</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {OUTCOME_CATEGORIES.map(result => <span key={result} style={{ fontSize: 11, color: '#edf5ff', padding: '5px 8px', borderRadius: 999, background: 'rgba(23,102,255,.18)' }}>{result.replace(/_/g, ' ')}</span>)}
        </div>
        <div style={{ marginTop: 10, display: 'grid', gap: 5 }}>{getStrategyResearchBacklog().slice(0, 3).map(item => <span key={item} style={{ fontSize: 11, color: '#94a7c3' }}>• {item}</span>)}</div>
      </section>
    </div>}

    {/* Dispute Items Tab */}
    {activeTab === 'items' && <div>
      <div style={{ marginBottom: 12, padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,.18)' }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Add Dispute Item</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
          <select value={newItemForm.bureau} onChange={e => setNewItemForm(p => ({ ...p, bureau: e.target.value }))} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(148,163,184,.18)', background: '#101e32', color: '#edf5ff', fontSize: 12 }}>
            <option value="experian">Experian</option>
            <option value="equifax">Equifax</option>
            <option value="transunion">TransUnion</option>
          </select>
          <input placeholder="Furnisher name" value={newItemForm.furnisherName} onChange={e => setNewItemForm(p => ({ ...p, furnisherName: e.target.value }))} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(148,163,184,.18)', background: '#101e32', color: '#edf5ff', fontSize: 12 }} />
          <input placeholder="Account name" value={newItemForm.accountName} onChange={e => setNewItemForm(p => ({ ...p, accountName: e.target.value }))} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(148,163,184,.18)', background: '#101e32', color: '#edf5ff', fontSize: 12 }} />
          <input placeholder="Account # (last 4 only)" value={newItemForm.accountNumberMask} onChange={e => setNewItemForm(p => ({ ...p, accountNumberMask: e.target.value }))} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(148,163,184,.18)', background: '#101e32', color: '#edf5ff', fontSize: 12 }} />
        </div>
        <input placeholder="Dispute reason" value={newItemForm.disputeReason} onChange={e => setNewItemForm(p => ({ ...p, disputeReason: e.target.value }))} style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(148,163,184,.18)', background: '#101e32', color: '#edf5ff', fontSize: 12, marginBottom: 8 }} />
        <input placeholder="Factual basis" value={newItemForm.factualBasis} onChange={e => setNewItemForm(p => ({ ...p, factualBasis: e.target.value }))} style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(148,163,184,.18)', background: '#101e32', color: '#edf5ff', fontSize: 12, marginBottom: 8 }} />
        <button onClick={handleCreateItem} style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #1766ff, #7048e8)', color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}>Add Item</button>
      </div>
      {items.map(item => <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 8, border: '1px solid rgba(148,163,184,.18)', marginBottom: 4 }}>
        <div style={{ width: 28, height: 28, borderRadius: 6, background: 'rgba(245,158,11,.12)', display: 'grid', placeItems: 'center', color: '#f59e0b' }}><AlertTriangle size={14} /></div>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 12 }}>{item.furnisher_name || item.account_name || 'Item'}</strong>
          <div style={{ fontSize: 10, color: '#94a7c3' }}>{item.bureau?.toUpperCase()} · {item.dispute_reason}</div>
        </div>
        <span style={{ padding: '2px 6px', borderRadius: 8, background: 'rgba(245,158,11,.12)', color: '#f59e0b', fontSize: 10, fontWeight: 700 }}>{item.status}</span>
      </div>)}
    </div>}

    {/* Letters Tab */}
    {activeTab === 'letters' && <div>
      <div style={{ marginBottom: 12 }}>
        <button onClick={handleGenerateLetter} disabled={generating || items.length === 0} style={{
          padding: '8px 16px', borderRadius: 8, border: 'none', background: generating ? '#374151' : 'linear-gradient(135deg, #1766ff, #7048e8)',
          color: '#fff', fontWeight: 700, fontSize: 12, cursor: generating ? 'not-allowed' : 'pointer',
        }}>{generating ? 'Generating...' : 'Generate Draft Letter'}</button>
      </div>
      {letters.map(letter => <div key={letter.id} style={{ padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,.18)', marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div>
            <strong style={{ fontSize: 13 }}>Letter to {letter.recipient_name || letter.recipient_type}</strong>
            <div style={{ fontSize: 11, color: '#94a7c3' }}>Status: {letter.status?.replace(/_/g, ' ')}</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {letter.status === 'draft' && <button onClick={() => approveLetterForSpecialistReview(letter.id).then(() => loadCreditRepairJourney().then(setJourney))} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Send to Review</button>}
            {letter.status === 'specialist_review' && <button onClick={() => handleApproveLetter(letter.id)} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Approve for Client</button>}
            {letter.status === 'client_approved' && <button onClick={() => handleSendToDocuPost(letter.id)} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#7048e8', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Send to DocuPost</button>}
          </div>
        </div>
        <div style={{ fontSize: 11, color: '#94a7c3', maxHeight: 120, overflow: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'Georgia, serif', lineHeight: 1.5 }}>
          {letter.letter_body?.slice(0, 500)}...
        </div>
      </div>)}
    </div>}

    {/* DocuPost Tab */}
    {activeTab === 'mail' && <div>
      {mailJobs.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: '#94a7c3' }}>No mail jobs yet.</div>}
      {mailJobs.map(job => <div key={job.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(148,163,184,.18)', marginBottom: 6 }}>
        <div style={{ width: 28, height: 28, borderRadius: 6, background: job.status === 'mailed' ? 'rgba(16,185,129,.12)' : 'rgba(245,158,11,.12)', display: 'grid', placeItems: 'center', color: job.status === 'mailed' ? '#10b981' : '#f59e0b' }}><Mail size={14} /></div>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 12 }}>Mail to {job.recipient_name || 'Recipient'}</strong>
          <div style={{ fontSize: 10, color: '#94a7c3' }}>{job.status?.replace(/_/g, ' ')} {job.tracking_number ? `· ${job.tracking_number}` : ''}</div>
        </div>
        {job.status === 'approved_to_send' && <button onClick={() => markMailJobSent(job.id, `TRK-${Date.now()}`).then(() => loadCreditRepairJourney().then(setJourney))} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Mark Sent</button>}
      </div>)}
    </div>}
  </div>
}

function ParserPreviewPanel({ pendingReviews = [] }) {
  const fixtureRows = [
    { name: '3-bureau tradeline PDF', status: 'Suggested extraction ready', action: 'Confirm selected item' },
    { name: 'Annual report style PDF', status: 'Suggested extraction ready', action: 'Edit item before creating case item' },
    { name: 'Credit monitoring export', status: 'Suggested extraction ready', action: 'Reject or request full report' },
    { name: 'Scanned/screenshot PDF', status: 'OCR required', action: 'Manual review or backend OCR worker' },
    { name: 'Mixed credit/funding bundle', status: 'Needs specialist split/verify', action: 'Classify before creating items' },
  ]
  return <div style={{ display: 'grid', gridTemplateColumns: '1fr .9fr', gap: 12 }}>
    <section style={{ padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,.18)' }}>
      <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Credit Report Parser Preview</h3>
      <div style={{ padding: 10, borderRadius: 8, background: 'rgba(245,158,11,.12)', color: '#f59e0b', fontSize: 12, marginBottom: 10 }}>
        Parser preview can read text-based fixtures. Live uploaded file parsing requires a backend extraction worker or storage file access integration.
      </div>
      <p style={{ fontSize: 12, color: '#94a7c3', marginBottom: 10 }}>
        Parser preview is available for test fixtures/local validation. Live report parsing requires backend extraction worker.
        Parser output is a suggested extraction, needs GoClear specialist review, and is not verified yet.
      </p>
      {pendingReviews.length > 0 && <div style={{ marginBottom: 12 }}>
        <h4 style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Uploaded Reports Needing Review</h4>
        {pendingReviews.map(doc => <div key={doc.reviewId} style={{ padding: 8, borderRadius: 6, border: '1px solid rgba(148,163,184,.18)', marginBottom: 4, fontSize: 12 }}>
          <strong>{doc.fileName}</strong>
          <span style={{ marginLeft: 8, color: '#f59e0b', fontSize: 11 }}>{doc.reviewStatusLabel}</span>
        </div>)}
      </div>}
      <div style={{ display: 'grid', gap: 8 }}>
        {fixtureRows.map(row => <div key={row.name} style={{ padding: 10, borderRadius: 8, border: '1px solid rgba(148,163,184,.18)', background: 'rgba(255,255,255,.04)' }}>
          <strong style={{ fontSize: 12 }}>{row.name}</strong>
          <div style={{ fontSize: 11, color: '#94a7c3', marginTop: 3 }}>Status: {row.status}</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
            <button type="button" disabled title="Preview only. Run local fixture parser and confirm in specialist workflow before creating case items." style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: 'rgba(23,102,255,.28)', color: '#edf5ff', fontSize: 11, fontWeight: 700, cursor: 'not-allowed' }}>{row.action}</button>
            <button type="button" disabled title="Parser suggestions cannot create letters automatically." style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: 'rgba(245,158,11,.18)', color: '#f59e0b', fontSize: 11, fontWeight: 700, cursor: 'not-allowed' }}>No auto letters</button>
          </div>
        </div>)}
      </div>
    </section>
    <section style={{ padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,.18)' }}>
      <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Specialist Confirmation Gate</h3>
      <p style={{ fontSize: 12, color: '#94a7c3', marginBottom: 8 }}>Version: {CREDIT_REPORT_PARSER_VERSION}</p>
      <ol style={{ color: '#94a7c3', fontSize: 12, lineHeight: 1.7, paddingLeft: 18 }}>
        <li>Run the local fixture parser against fake reports.</li>
        <li>Review confidence, warnings, suggested items, and suggested reasons.</li>
        <li>Confirm selected item or edit before creating a case item.</li>
        <li>Create report item only after specialist confirmation.</li>
        <li>Choose reason before letter options are generated.</li>
        <li>Keep specialist review, client approval, and DocuPost gates in place.</li>
      </ol>
      <div style={{ marginTop: 10, padding: 10, borderRadius: 8, background: 'rgba(245,158,11,.12)', color: '#f59e0b', fontSize: 12 }}>
        Uploaded credit reports remain Pending GoClear Review until a specialist confirms parser suggestions or manually creates report items.
      </div>
    </section>
  </div>
}
