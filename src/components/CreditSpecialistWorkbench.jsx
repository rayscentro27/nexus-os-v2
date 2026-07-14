/**
 * Credit & Funding Readiness Review — admin report and documentation review.
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
  loadSystemReviewForDocument,
  queueCreditReportAnalysis,
  loadLatestAnalysisJob,
} from '../lib/creditRepairWorkflow'
import { DISPUTE_REASON_LABELS, OUTCOME_CATEGORIES } from '../lib/disputeStrategyKnowledge'
import { getStrategyResearchBacklog, recommendNextRoundStrategy, summarizeStrategyOutcomes } from '../lib/creditStrategyResearchEngine'
import { CREDIT_REPORT_PARSER_VERSION } from '../lib/creditReportParser'
import { createManualReportItem, getOrCreateCreditRepairCaseForDocument, listCreditReportItems } from '../lib/creditRepairCaseEngine'
import { loadParserResultForDocument } from '../lib/creditRepairWorkflow'
import { supabase } from '../lib/supabaseClient'

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
  const [actionMessage, setActionMessage] = useState('')
  const [actionError, setActionError] = useState('')
  const [reviewPanelOpen, setReviewPanelOpen] = useState(false)
  const [parserPanelOpen, setParserPanelOpen] = useState(false)
  const [manualItemFormOpen, setManualItemFormOpen] = useState(false)
  const [selectedCase, setSelectedCase] = useState(null)
  const [caseItems, setCaseItems] = useState([])
  const [manualItemForm, setManualItemForm] = useState({
    bureau: 'experian',
    item_type: 'collection',
    furnisher_name: '',
    account_name: '',
    account_number_masked: '',
    reason: 'verify_or_validate',
    notes: '',
    evidence_needed: 'yes',
  })
  const [parserResult, setParserResult] = useState(null)
  const [parserResultLoading, setParserResultLoading] = useState(false)
  const [systemReview, setSystemReview] = useState(null)
  const [analysisJob, setAnalysisJob] = useState(null)
  const [recommendationDecisions, setRecommendationDecisions] = useState({})
  const [automationMetrics, setAutomationMetrics] = useState({ cards: 0, choices: 0, exceptions: 0, research: 0, failed: 0 })

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

  useEffect(() => {
    if (!supabase) return
    Promise.all([
      supabase.from('credit_strategy_recommendations').select('id,status', { count: 'exact' }).limit(100),
      supabase.from('credit_strategy_client_decisions').select('id', { count: 'exact' }).limit(1),
      supabase.from('credit_strategy_sources').select('id', { count: 'exact' }).in('review_status', ['needs_verification','needs_approval']).limit(1),
      supabase.from('credit_analysis_jobs').select('id', { count: 'exact' }).eq('status', 'failed').limit(1),
    ]).then(([cards, choices, research, failed]) => setAutomationMetrics({ cards: cards.count || 0, choices: choices.count || 0, exceptions: (cards.data || []).filter(x => x.status === 'exception_required').length, research: research.count || 0, failed: failed.count || 0 })).catch(() => {})
  }, [analysisJob?.status])

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

  function selectPendingReview(doc) {
    if (!doc) {
      setSelectedPending(null)
      setSelectedReview(null)
      setReviewPanelOpen(false)
      setParserPanelOpen(false)
      return
    }
    setSelectedPending(doc)
    setSelectedReview({ id: doc.reviewId, client_id: doc.clientId, tenant_id: doc.tenantId, document_id: doc.documentId, status: doc.status })
    setActionMessage('')
    setActionError('')
  }

  function handleReviewReport(doc = selectedPending) {
    if (!doc) {
      setActionError('Select a pending report first.')
      return
    }
    selectPendingReview(doc)
    setReviewPanelOpen(true)
    setParserPanelOpen(false)
    setActionMessage(`Review panel opened for ${doc.fileName}.`)
  }

  function handleRunParserPreview(doc = selectedPending) {
    if (!doc) {
      setActionError('Select a pending report first.')
      return
    }
    selectPendingReview(doc)
    setParserPanelOpen(true)
    setReviewPanelOpen(true)
    setParserResultLoading(true)
    setParserResult(null)

    // Try to load existing parser result from database
    Promise.all([loadParserResultForDocument(doc.documentId), loadSystemReviewForDocument(doc.documentId), loadLatestAnalysisJob(doc.documentId)]).then(([result, review, job]) => {
      setParserResult(result)
      setSystemReview(review)
      setAnalysisJob(job)
      setParserResultLoading(false)
      if (result) {
        setActionMessage(`Report analysis loaded: ${result.accountsCount} accounts, ${result.negativeCandidatesCount} funding-impact items, ${result.inquiriesCount} inquiries.`)
      } else {
        setActionMessage('No parser result found for this document. Run the local parser worker to generate results.')
      }
    }).catch(() => {
      setParserResultLoading(false)
      setActionMessage('Could not load parser results. Run the local parser worker to generate results.')
    })
  }

  async function handleQueueAnalysis(doc = selectedPending) {
    if (!doc) return setActionError('Select a pending report first.')
    setActionError(''); setActionMessage('Queuing bounded server-side report analysis job...')
    const result = await queueCreditReportAnalysis({ tenantId: doc.tenantId, clientId: doc.clientId, documentId: doc.documentId })
    if (!result.ok) return setActionError(result.error || 'Could not queue analysis.')
    setAnalysisJob(result.job)
    setActionMessage(result.duplicatePrevented ? 'An analysis job is already queued or processing.' : 'Analysis queued. Run the bounded Mac queue worker, then refresh analysis.')
  }

  async function handleRefreshParserResults(doc = selectedPending) {
    if (!doc) return
    setParserResultLoading(true)
    try {
      const [result, review, job] = await Promise.all([loadParserResultForDocument(doc.documentId), loadSystemReviewForDocument(doc.documentId), loadLatestAnalysisJob(doc.documentId)])
      setParserResult(result)
      setSystemReview(review)
      setAnalysisJob(job)
      if (result) {
        setActionMessage(`Report analysis refreshed: ${result.accountsCount} accounts, ${result.negativeCandidatesCount} funding-impact items.`)
      } else {
        setActionMessage('No parser result found yet. Run the local parser worker first.')
      }
    } catch {
      setActionMessage('Failed to refresh parser results.')
    }
    setParserResultLoading(false)
  }

  async function handleConfirmParserItem(parserItem) {
    if (!selectedPending) {
      setActionError('Select a pending report first.')
      return
    }
    setActionError('')
    setActionMessage('Confirming parser item as case item...')
    let activeCase = selectedCase
    if (!activeCase) {
      const caseResult = await getOrCreateCreditRepairCaseForDocument({
        clientId: selectedPending.clientId,
        tenantId: selectedPending.tenantId,
        documentId: selectedPending.documentId,
        source: selectedPending.source || 'client_documents',
        createdBy: 'admin_credit_specialist_workbench',
      })
      if (!caseResult.ok) {
        setActionError(`Cannot confirm item: case creation failed — ${caseResult.error || 'unknown error'}`)
        return
      }
      activeCase = caseResult.case
      setSelectedCase(caseResult.case)
    }
    const { confirmParserItemAsCaseItem } = await import('../lib/creditReportParserToCaseEngine')
    const ctx = { authUserId: 'admin_credit_specialist', tenantId: selectedPending.tenantId, clientId: selectedPending.clientId }
    const result = await confirmParserItemAsCaseItem(ctx, activeCase.id, parserItem, { notes: 'Confirmed from parser result in workbench.' })
    if (result.ok) {
      setActionMessage(`Parser item confirmed as case item. Dispute strategy must be selected by specialist or client.`)
      const items = await listCreditReportItems(ctx, activeCase.id)
      setCaseItems(items)
    } else {
      setActionError(`Failed to confirm item: ${result.error || 'unknown error'}`)
    }
  }

  async function handleCreateCreditRepairCase(doc = selectedPending) {
    if (!doc) {
      setActionError('Select a pending report first.')
      return
    }
    setActionError('')
    const result = await getOrCreateCreditRepairCaseForDocument({
      clientId: doc.clientId,
      tenantId: doc.tenantId,
      documentId: doc.documentId,
      source: doc.source || 'client_documents',
      createdBy: 'admin_credit_specialist_workbench',
    })
    if (!result.ok) {
      setActionError(`Case creation needs database support or permissions. ${result.error || 'Use manual review for now.'}`)
      return
    }
    setSelectedCase(result.case)
    const ctx = { authUserId: 'admin_credit_specialist', tenantId: doc.tenantId, clientId: doc.clientId }
    const itemsForCase = await listCreditReportItems(ctx, result.case.id).catch(() => [])
    setCaseItems(itemsForCase)
    setActiveTab('case_engine')
    setActionMessage(`${result.openedExisting ? 'Profile review case opened' : 'Profile review case created'} for this report.`)
  }

  function handleAddManualItem(doc = selectedPending) {
    if (!doc) {
      setActionError('Select a pending report first.')
      return
    }
    selectPendingReview(doc)
    setManualItemFormOpen(true)
    setReviewPanelOpen(true)
    setActionMessage('Manual item form opened. Use masked last four only; do not enter SSN, full DOB, full account numbers, or bureau credentials.')
  }

  async function handleSubmitManualItem(e) {
    e.preventDefault()
    if (!selectedPending) {
      setActionError('Select a pending report first.')
      return
    }
    setActionError('')
    let activeCase = selectedCase
    if (!activeCase) {
      const result = await getOrCreateCreditRepairCaseForDocument({
        clientId: selectedPending.clientId,
        tenantId: selectedPending.tenantId,
        documentId: selectedPending.documentId,
        source: selectedPending.source || 'client_documents',
        createdBy: 'admin_credit_specialist_workbench',
      })
      if (!result.ok) {
        setActionError(`Manual item draft could not be saved because case creation failed: ${result.error || 'unknown error'}`)
        return
      }
      activeCase = result.case
      setSelectedCase(result.case)
    }
    const ctx = { authUserId: 'admin_credit_specialist', tenantId: selectedPending.tenantId, clientId: selectedPending.clientId }
    const item = await createManualReportItem(ctx, activeCase.id, {
      bureau: manualItemForm.bureau,
      item_type: manualItemForm.item_type,
      furnisher_name: manualItemForm.furnisher_name,
      account_name: manualItemForm.account_name,
      account_number_masked: manualItemForm.account_number_masked,
      reported_status: 'specialist_review',
      raw_notes: [
        'Specialist-entered item from uploaded credit report review.',
        `Selected reason: ${manualItemForm.reason}.`,
        `Evidence needed: ${manualItemForm.evidence_needed}.`,
        manualItemForm.notes,
      ].filter(Boolean).join('\n'),
      client_wants_challenged: true,
    })
    if (!item.ok) {
      setActionError(`Manual item draft could not be saved: ${item.error || 'unknown error'}`)
      return
    }
    const itemsForCase = await listCreditReportItems(ctx, activeCase.id).catch(() => [])
    setCaseItems(itemsForCase)
    setManualItemFormOpen(false)
    setActiveTab('items')
    setActionMessage('Manual item saved for specialist review. No letters were created.')
    setManualItemForm({ bureau: 'experian', item_type: 'collection', furnisher_name: '', account_name: '', account_number_masked: '', reason: 'verify_or_validate', notes: '', evidence_needed: 'yes' })
  }

  async function handleMarkNeedsInfo(doc = selectedPending) {
    if (!doc) {
      setActionError('Select a pending report first.')
      return
    }
    if (!supabase) {
      setActionError('Mark Needs Info requires Supabase.')
      return
    }
    const { error } = await supabase
      .from('client_documents')
      .update({
        goclear_review_status: 'needs_info',
        status: 'needs_info',
        updated_at: new Date().toISOString(),
      })
      .eq('id', doc.documentId)
    if (error) {
      setActionError(`Unable to mark needs info: ${error.message}`)
      return
    }
    setActionMessage('Marked report as Needs Info. Client document status can reflect this where displayed.')
    await refreshQueue()
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
    { key: 'queue', label: 'Review Queue', count: pendingReviews.length },
    { key: 'case_engine', label: 'Profile Review Cases', count: items.length + letters.length },
    { key: 'parser_preview', label: 'Report Analysis', count: 0 },
    { key: 'items', label: 'Report Items', count: items.length },
    { key: 'letters', label: 'Draft Letters', count: letters.length },
    { key: 'mail', label: 'Mail Queue', count: mailJobs.length },
  ]

  return <div style={{ padding: 16, color: '#edf5ff' }}>
    <h1 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>Credit & Funding Readiness Review</h1>
    <p style={{ fontSize: 13, color: '#94a7c3', marginBottom: 10 }}>Nexus performs the first-pass report comparison and approved strategy matching automatically. GoClear handles low-confidence, safety, identity-theft, legal, complaint, or system exceptions.</p>
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(140px,1fr))',gap:8,marginBottom:16}}>{[['Strategy Cards generated',automationMetrics.cards],['Client selections',automationMetrics.choices],['Low-confidence exceptions',automationMetrics.exceptions],['Research awaiting approval',automationMetrics.research],['Failed analysis jobs',automationMetrics.failed]].map(([label,value])=><div key={label} style={{padding:8,borderRadius:8,background:'rgba(255,255,255,.06)'}}><small>{label}</small><strong style={{display:'block'}}>{value}</strong></div>)}</div>

    {loading && <div style={{ color: '#94a7c3', fontSize: 12 }}>Loading...</div>}
    {actionMessage && <div style={{ padding: 10, borderRadius: 8, background: 'rgba(16,185,129,.12)', color: '#10b981', fontSize: 12, marginBottom: 10 }}>{actionMessage}</div>}
    {actionError && <div style={{ padding: 10, borderRadius: 8, background: 'rgba(239,68,68,.12)', color: '#ef4444', fontSize: 12, marginBottom: 10 }}>{actionError}</div>}

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
          <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 2 }}>Review Queue</h3>
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

      {pendingReviews.map(doc => <div key={doc.reviewId} onClick={() => selectPendingReview(selectedPending?.reviewId === doc.reviewId ? null : doc)} style={{
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
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }} onClick={e => e.stopPropagation()}>
          <button onClick={() => handleReviewReport(doc)} style={{ padding: '5px 8px', borderRadius: 6, border: 'none', background: '#1766ff', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Review Report</button>
          <button onClick={() => handleRunParserPreview(doc)} style={{ padding: '5px 8px', borderRadius: 6, border: 'none', background: '#7048e8', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Run Report Analysis</button>
          <button onClick={() => handleQueueAnalysis(doc)} style={{ padding: '5px 8px', borderRadius: 6, border: 'none', background: '#0ea5e9', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Queue Analysis</button>
          <button onClick={() => handleCreateCreditRepairCase(doc)} style={{ padding: '5px 8px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Create Profile Review Case</button>
          <button onClick={() => handleAddManualItem(doc)} style={{ padding: '5px 8px', borderRadius: 6, border: 'none', background: '#f59e0b', color: '#101e32', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Add Manual Item</button>
          <button onClick={() => handleMarkNeedsInfo(doc)} style={{ padding: '5px 8px', borderRadius: 6, border: '1px solid rgba(148,163,184,.22)', background: 'rgba(255,255,255,.06)', color: '#edf5ff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Mark Needs Info</button>
        </div>
      </div>)}

      {/* Detail panel */}
      {selectedPending && reviewPanelOpen && <div style={{ marginTop: 12, padding: 14, borderRadius: 10, border: '1px solid rgba(23,102,255,.25)', background: 'rgba(23,102,255,.06)' }}>
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
          <button onClick={() => setActionMessage('Safe file preview is not available yet. Use metadata review and manual item entry for now.')} style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #1766ff, #7048e8)', color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}>Review Report</button>
          <button onClick={() => handleRunParserPreview()} style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: '#7048e8', color: '#fff', fontSize: 12, cursor: 'pointer' }}>Run Report Analysis</button>
          <button onClick={() => handleQueueAnalysis()} style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: '#0ea5e9', color: '#fff', fontSize: 12, cursor: 'pointer' }}>Queue Analysis</button>
          <button onClick={() => handleCreateCreditRepairCase()} style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: '#10b981', color: '#fff', fontSize: 12, cursor: 'pointer' }}>Create Profile Review Case</button>
          <button onClick={() => handleAddManualItem()} style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: '#f59e0b', color: '#101e32', fontSize: 12, cursor: 'pointer' }}>Add Manual Item</button>
          <button onClick={() => handleMarkNeedsInfo()} style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(148,163,184,.2)', background: 'rgba(255,255,255,.06)', color: '#edf5ff', fontSize: 12, cursor: 'pointer' }}>Mark Needs Info</button>
        </div>
        <p style={{ marginTop: 10, color: '#94a7c3', fontSize: 12 }}>Safe file preview is not available yet. Use metadata review and manual item entry for now.</p>
        {parserPanelOpen && <div style={{ marginTop: 10, padding: 10, borderRadius: 8, border: '1px solid rgba(112,72,232,.28)', background: 'rgba(112,72,232,.08)', color: '#d8ccff', fontSize: 12 }}>
          <strong>Report Analysis</strong>
          <p style={{ margin: '6px 0 0', fontSize: 11 }}>Status: {analysisJob?.status?.replace(/_/g, ' ') || (parserResult ? 'analysis complete' : 'ready for analysis')}</p>
          {parserResultLoading && <p style={{ margin: '6px 0 0' }}>Loading parser results...</p>}
          {!parserResultLoading && !parserResult && <div>
            <p style={{ margin: '6px 0 0' }}>No parser result found for this document. Run the local admin parser worker to generate results:</p>
            <code style={{ display: 'block', margin: '8px 0', padding: 8, borderRadius: 6, background: 'rgba(0,0,0,.3)', fontSize: 11, whiteSpace: 'pre-wrap' }}>source .venv-credit/bin/activate
python3 scripts/credit/parse_uploaded_credit_report.py --document-id {selectedPending?.documentId}</code>
            <button onClick={() => handleRefreshParserResults()} style={{ padding: '6px 12px', borderRadius: 6, border: 'none', background: '#7048e8', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer', marginTop: 4 }}>Refresh Parser Results</button>
          </div>}
          {!parserResultLoading && parserResult && <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, margin: '8px 0' }}>
              <div style={{ padding: 6, borderRadius: 6, background: 'rgba(0,0,0,.2)' }}>Accounts: <strong>{parserResult.accountsCount}</strong></div>
              <div style={{ padding: 6, borderRadius: 6, background: 'rgba(0,0,0,.2)' }}>Funding-impact candidates: <strong>{parserResult.reviewCandidatesCount}</strong></div>
              <div style={{ padding: 6, borderRadius: 6, background: 'rgba(0,0,0,.2)' }}>Inquiries: <strong>{parserResult.inquiriesCount}</strong></div>
            </div>
            <div style={{ fontSize: 11, margin: '4px 0' }}>
              Extraction: {parserResult.extractionMode} · Confidence: {parserResult.confidence} · Bureaus: {parserResult.bureausDetected.join(', ') || 'None'}
            </div>
            {parserResult.warnings.length > 0 && <div style={{ margin: '6px 0', fontSize: 11 }}>
              Warnings: {parserResult.warnings.map(w => w.message).join('; ')}
            </div>}
            <div style={{ fontSize: 11, margin: '4px 0', color: '#f59e0b' }}>
              Suggested extraction — Needs GoClear specialist review. Not verified yet.
            </div>
            {parserResult.accountsCount === 0 && parserResult.textLength > 0 && <div style={{ margin: '8px 0', padding: 8, borderRadius: 6, background: 'rgba(239,68,68,.15)', color: '#ef4444', fontSize: 11 }}>
              Parser result data mismatch detected. Refresh analysis or inspect the latest result.
            </div>}
            {parserResult.structuredItemDraftsCount > 0 && <div style={{ margin: '8px 0', fontSize: 11 }}>
              {parserResult.structuredItemDraftsCount} suggested items ready for specialist review. Confirm, edit, or reject each item before creating case items.
            </div>}
            {parserResult.accountsCount > 0 && <div style={{ margin: '8px 0', fontSize: 11, color: '#94a7c3' }}>
              {parserResult.accountsCount} accounts · {parserResult.inquiriesCount} inquiries · {parserResult.negativeCandidatesCount} funding-impact items detected.
            </div>}
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <button onClick={() => handleRefreshParserResults()} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: '#7048e8', color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>Refresh</button>
              <button disabled={!parserResult || parserResult.structuredItemDraftsCount === 0} title={parserResult?.structuredItemDraftsCount > 0 ? "Confirm all suggested parser items as case items" : "No parser items to confirm"} onClick={() => handleConfirmParserItem({})} style={{ padding: '4px 10px', borderRadius: 6, border: 'none', background: parserResult?.structuredItemDraftsCount > 0 ? '#10b981' : 'rgba(255,255,255,.1)', color: parserResult?.structuredItemDraftsCount > 0 ? '#fff' : '#94a7c3', fontSize: 11, fontWeight: 700, cursor: parserResult?.structuredItemDraftsCount > 0 ? 'pointer' : 'not-allowed' }}>Confirm Items</button>
            </div>
          </div>}
          {systemReview && <div style={{ marginTop: 10, padding: 10, borderRadius: 8, background: 'rgba(16,185,129,.08)' }}>
            <h4 style={{ margin: '0 0 8px' }}>System First-Pass Review</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 6 }}>
              {[['Accounts analyzed', systemReview.summary.accountsAnalyzed || parserResult?.accountsCount || 0], ['Funding-impact items', systemReview.fundingImpactItems.length], ['Utilization actions', systemReview.utilizationActions.length], ['Inquiries reviewed', systemReview.inquiryReviews.length], ['Report items needing review', systemReview.reportItemReviews.length], ['Client evidence requests', systemReview.evidenceNeeded.length], ['Specialist exceptions', systemReview.specialistExceptions.length], ['Credit Profile status', systemReview.summary.creditProfileStatus || 'pending review']].map(([label,value]) => <div key={label} style={{ padding: 6, borderRadius: 6, background: 'rgba(0,0,0,.2)' }}><small>{label}</small><strong style={{ display: 'block' }}>{String(value)}</strong></div>)}
            </div>
            {systemReview.fundingImpactItems.slice(0, 12).map(item => <div key={item.id} style={{ marginTop: 8, padding: 8, border: '1px solid rgba(148,163,184,.18)', borderRadius: 7 }}>
              <strong>{item.creditorFurnisher || 'Report item'} · {item.maskedAccountReference || 'masked reference unavailable'}</strong>
              <div>{item.bureau || 'other'} · {String(item.category || '').replace(/_/g,' ')} · confidence: {item.confidence || 'low'}</div>
              <div style={{ color: '#94a7c3' }}>{item.issueDetected} {item.fundingImpact}</div>
              <div>Suggested next step: {item.suggestedNextStep}</div>
              <div>Tier 1: {item.tier1Impact} · Tier 2: {item.tier2Impact}</div>
              <div style={{ display: 'flex', gap: 5, marginTop: 6, flexWrap: 'wrap' }}>
                {['Confirm Recommendation','Edit','Reject','Request Client Evidence'].map(action => <button key={action} onClick={() => setRecommendationDecisions(p => ({...p,[item.id]:action}))} style={{ padding: '3px 7px', fontSize: 10 }}>{action}</button>)}
                <button disabled={!item.letterEligible || recommendationDecisions[item.id] !== 'Confirm Recommendation'} title="Draft letter requires a confirmed, letter-eligible report-review recommendation" style={{ padding: '3px 7px', fontSize: 10 }}>Prepare Draft Letter</button>
              </div>
              {recommendationDecisions[item.id] && <small>Decision: {recommendationDecisions[item.id]} · Client-facing action remains gated.</small>}
            </div>)}
          </div>}
          <p style={{ margin: '6px 0 0', fontSize: 11 }}>No letters are created automatically. No DocuPost is sent.</p>
        </div>}
        {manualItemFormOpen && <form onSubmit={handleSubmitManualItem} style={{ marginTop: 12, padding: 12, borderRadius: 8, background: 'rgba(255,255,255,.05)', display: 'grid', gap: 8 }}>
          <h4 style={{ margin: 0, fontSize: 13 }}>Add Manual Item</h4>
          <p style={{ margin: 0, color: '#94a7c3', fontSize: 11 }}>Specialist-entered item. Do not enter SSN, full DOB, full account numbers, or bureau credentials.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <label style={{ fontSize: 11, color: '#94a7c3' }}>Bureau<select value={manualItemForm.bureau} onChange={e => setManualItemForm(p => ({ ...p, bureau: e.target.value }))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, background: '#101e32', color: '#edf5ff', border: '1px solid rgba(148,163,184,.18)' }}><option value="experian">Experian</option><option value="equifax">Equifax</option><option value="transunion">TransUnion</option><option value="unknown">Multiple/Unknown</option></select></label>
            <label style={{ fontSize: 11, color: '#94a7c3' }}>Item type<select value={manualItemForm.item_type} onChange={e => setManualItemForm(p => ({ ...p, item_type: e.target.value }))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, background: '#101e32', color: '#edf5ff', border: '1px solid rgba(148,163,184,.18)' }}><option value="collection">Collection</option><option value="charge_off">Charge-off</option><option value="late_payment">Late payment</option><option value="inquiry">Inquiry</option><option value="incorrect_balance">Incorrect balance</option><option value="personal_info">Personal information</option><option value="other">Other</option></select></label>
            <label style={{ fontSize: 11, color: '#94a7c3' }}>Furnisher/account name<input value={manualItemForm.furnisher_name} onChange={e => setManualItemForm(p => ({ ...p, furnisher_name: e.target.value, account_name: e.target.value }))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, background: '#101e32', color: '#edf5ff', border: '1px solid rgba(148,163,184,.18)' }} /></label>
            <label style={{ fontSize: 11, color: '#94a7c3' }}>Masked account last 4 only<input value={manualItemForm.account_number_masked} onChange={e => setManualItemForm(p => ({ ...p, account_number_masked: e.target.value }))} maxLength={4} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, background: '#101e32', color: '#edf5ff', border: '1px solid rgba(148,163,184,.18)' }} /></label>
            <label style={{ fontSize: 11, color: '#94a7c3' }}>Reason<select value={manualItemForm.reason} onChange={e => setManualItemForm(p => ({ ...p, reason: e.target.value }))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, background: '#101e32', color: '#edf5ff', border: '1px solid rgba(148,163,184,.18)' }}>{['not_mine','incorrect_balance','incorrect_dates','duplicate','paid_or_settled_wrong','late_payment_wrong','unauthorized_inquiry','personal_info_error','verify_or_validate','outdated','not_sure'].map(reason => <option key={reason} value={reason}>{reason.replace(/_/g, ' ')}</option>)}</select></label>
            <label style={{ fontSize: 11, color: '#94a7c3' }}>Evidence needed<select value={manualItemForm.evidence_needed} onChange={e => setManualItemForm(p => ({ ...p, evidence_needed: e.target.value }))} style={{ width: '100%', marginTop: 4, padding: 6, borderRadius: 6, background: '#101e32', color: '#edf5ff', border: '1px solid rgba(148,163,184,.18)' }}><option value="yes">Yes</option><option value="no">No</option></select></label>
          </div>
          <textarea value={manualItemForm.notes} onChange={e => setManualItemForm(p => ({ ...p, notes: e.target.value }))} placeholder="Specialist notes. Do not enter sensitive full identifiers." style={{ minHeight: 70, padding: 8, borderRadius: 6, background: '#101e32', color: '#edf5ff', border: '1px solid rgba(148,163,184,.18)' }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: '#10b981', color: '#fff', fontWeight: 700 }}>Save Manual Item</button>
            <button type="button" onClick={() => setManualItemFormOpen(false)} style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(148,163,184,.2)', background: 'rgba(255,255,255,.06)', color: '#edf5ff' }}>Cancel</button>
          </div>
        </form>}
        <div style={{ marginTop: 10, padding: 10, borderRadius: 8, background: 'rgba(245,158,11,.12)', color: '#f59e0b', fontSize: 11 }}>
          Suggested next steps and report items require GoClear confirmation before draft letters or DocuPost can proceed. No letters are generated automatically.
        </div>
      </div>}
    </div>}

    {activeTab === 'case_engine' && <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 12 }}>
      <section style={{ padding: 12, borderRadius: 10, border: '1px solid rgba(148,163,184,.18)' }}>
        <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Profile Review Cases</h3>
        <p style={{ fontSize: 12, color: '#94a7c3', marginBottom: 10 }}>Specialist reviews selected items, client reasons, evidence, and letter options before sending anything to client approval.</p>
        {items.length === 0 && caseItems.length === 0 && <p style={{ fontSize: 12, color: '#94a7c3' }}>No client-selected report items yet. Create a case from Client Queue.</p>}
        {selectedCase && <div style={{ padding: 10, borderRadius: 8, border: '1px solid rgba(16,185,129,.25)', marginBottom: 8, color: '#94a7c3', fontSize: 12 }}>Selected case: {selectedCase.id} · status: {selectedCase.status}</div>}
        {caseItems.map(item => <div key={item.id} style={{ padding: 10, borderRadius: 8, border: '1px solid rgba(148,163,184,.18)', marginBottom: 8 }}>
          <strong style={{ fontSize: 13 }}>{item.furnisher_name || item.account_name || 'Manual report item'}</strong>
          <div style={{ fontSize: 11, color: '#94a7c3' }}>{item.bureau?.toUpperCase()} · {item.item_type || 'credit item'} · specialist-entered item</div>
        </div>)}
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
      {caseItems.length === 0 && items.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: '#94a7c3' }}>Add Manual Item from Client Queue.</div>}
      {caseItems.map(item => <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 8, border: '1px solid rgba(148,163,184,.18)', marginBottom: 4 }}>
        <div style={{ width: 28, height: 28, borderRadius: 6, background: 'rgba(245,158,11,.12)', display: 'grid', placeItems: 'center', color: '#f59e0b' }}><AlertTriangle size={14} /></div>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 12 }}>{item.furnisher_name || item.account_name || 'Manual item'}</strong>
          <div style={{ fontSize: 10, color: '#94a7c3' }}>{item.bureau?.toUpperCase()} · {item.item_type} · specialist-entered item</div>
        </div>
        <span style={{ padding: '2px 6px', borderRadius: 8, background: 'rgba(245,158,11,.12)', color: '#f59e0b', fontSize: 10, fontWeight: 700 }}>specialist review</span>
      </div>)}
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
        <p style={{ fontSize: 11, color: '#94a7c3' }}>Draft Letter Tool · Documentation Preparation · Client Review Required · GoClear Review Required · Mailing only after approval.</p>
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
        <div style={{ marginTop: 8, fontSize: 10, color: '#f59e0b' }}>Draft preview only. This document requires review and approval before use. Nexus does not guarantee deletion, a credit score change, or a specific reporting outcome.</div>
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
      <h3 style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>Credit Report Analysis</h3>
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
