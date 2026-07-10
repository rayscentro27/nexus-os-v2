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

const DEMO_CLIENT_ID = 'client_test_julius_erving'
const DEMO_TENANT_ID = 'tenant_default'

export default function CreditSpecialistWorkbench({ onAskHermes }) {
  const [journey, setJourney] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('queue')
  const [selectedReview, setSelectedReview] = useState(null)
  const [newItemForm, setNewItemForm] = useState({
    bureau: 'experian', furnisherName: '', accountName: '', accountNumberMask: '',
    disputeReason: '', factualBasis: '', requestedAction: 'dispute',
  })
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    loadCreditRepairJourney().then(data => {
      setJourney(data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

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
    { key: 'case_engine', label: 'Case Engine', count: items.length + letters.length },
    { key: 'queue', label: 'Client Queue', count: reviews.length },
    { key: 'items', label: 'Dispute Items', count: items.length },
    { key: 'letters', label: 'Letters', count: letters.length },
    { key: 'mail', label: 'DocuPost', count: mailJobs.length },
  ]

  return <div style={{ padding: 16, color: '#edf5ff' }}>
    <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>Credit Specialist Workbench</h1>
    <p style={{ fontSize: 13, color: '#94a7c3', marginBottom: 16 }}>Review reports, identify dispute items, generate drafts, and move approved letters into DocuPost.</p>

    {loading && <div style={{ color: '#94a7c3', fontSize: 12 }}>Loading...</div>}

    {/* Tabs */}
    <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
      {tabs.map(tab => <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
        padding: '8px 14px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 12,
        background: activeTab === tab.key ? 'linear-gradient(135deg, #1766ff, #7048e8)' : 'rgba(255,255,255,.08)',
        color: activeTab === tab.key ? '#fff' : '#94a7c3',
      }}>{tab.label} <span style={{ marginLeft: 4, opacity: .7 }}>({tab.count})</span></button>)}
    </div>

    {/* Queue Tab */}
    {activeTab === 'queue' && <div>
      {reviews.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: '#94a7c3' }}>No credit report reviews yet.</div>}
      {reviews.map(r => <div key={r.id} onClick={() => setSelectedReview(r)} style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 10,
        border: `1px solid ${selectedReview?.id === r.id ? 'rgba(23,102,255,.4)' : 'rgba(148,163,184,.18)'}`,
        background: selectedReview?.id === r.id ? 'rgba(23,102,255,.08)' : 'transparent',
        cursor: 'pointer', marginBottom: 6,
      }}>
        <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #1766ff, #7048e8)', display: 'grid', placeItems: 'center', color: '#fff', fontWeight: 800, fontSize: 13 }}>
          {r.client_id?.slice(-2).toUpperCase()}
        </div>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 13 }}>{r.client_id}</strong>
          <div style={{ fontSize: 11, color: '#94a7c3' }}>Review #{r.id.slice(0, 8)}</div>
        </div>
        <span style={{ padding: '3px 8px', borderRadius: 12, background: r.status === 'pending_review' ? 'rgba(245,158,11,.15)' : 'rgba(16,185,129,.15)', color: r.status === 'pending_review' ? '#f59e0b' : '#10b981', fontSize: 11, fontWeight: 700 }}>
          {r.status?.replace(/_/g, ' ')}
        </span>
      </div>)}
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
