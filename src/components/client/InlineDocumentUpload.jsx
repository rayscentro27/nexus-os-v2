import React, { useState, useRef } from 'react'
import { isSupabaseConfigured, supabase } from '../../lib/supabaseClient'
import { resolveClientContextForCurrentUser } from '../../lib/clientAuthContext'
import { trackEvent } from '../../lib/clientAnalytics'

const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/heic', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
const MAX_SIZE = 10 * 1024 * 1024

function guessCategory(filename, contextCategory) {
  if (contextCategory) return contextCategory
  const lower = filename.toLowerCase()
  if (lower.includes('credit') || lower.includes('transunion') || lower.includes('experian') || lower.includes('equifax')) return 'credit_reports'
  if (lower.includes('bank') || lower.includes('statement')) return 'banking'
  if (lower.includes('ein') || lower.includes('formation') || lower.includes('llc') || lower.includes('inc')) return 'business_formation'
  if (lower.includes('revenue') || lower.includes('invoice') || lower.includes('tax')) return 'revenue_financials'
  if (lower.includes('id') || lower.includes('license') || lower.includes('passport')) return 'identity_authorization'
  if (lower.includes('dispute') || lower.includes('evidence') || lower.includes('letter')) return 'credit_evidence'
  return 'other'
}

const CATEGORY_LABELS = {
  credit_reports: 'Credit Reports',
  credit_report: 'Credit Reports',
  credit_evidence: 'Credit Evidence',
  identity_authorization: 'Identity & Authorization',
  government_id: 'Identity & Authorization',
  identification: 'Identity & Authorization',
  proof_of_address: 'Identity & Authorization',
  business_formation: 'Business Formation',
  business_license: 'Business Formation',
  ein_confirmation: 'Business Formation',
  banking: 'Banking',
  bank_statement: 'Banking',
  revenue_financials: 'Revenue & Financials',
  revenue_summary: 'Revenue & Financials',
  profit_and_loss: 'Revenue & Financials',
  funding_applications: 'Funding Applications',
  funding_support: 'Funding Applications',
  review_support: 'Funding Applications',
  dispute_support: 'Credit Evidence',
  other: 'Other',
  unknown: 'Other',
}

export default function InlineDocumentUpload({ category, onUploaded, compact, label, className, pageContext = 'client_portal', track = 'general', requirementKey = '' }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(category || '')
  const inputRef = useRef(null)

  const handleFile = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    if (f.size > MAX_SIZE) {
      setResult({ ok: false, message: `File too large (max ${MAX_SIZE / 1024 / 1024}MB)` })
      return
    }
    setFile(f)
    setResult(null)
    if (!selectedCategory) setSelectedCategory(guessCategory(f.name, category))
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setProgress(0)
    setResult(null)
    trackEvent({ event: 'upload_started', stage: track, requirement: requirementKey, route: pageContext })

    try {
      if (!isSupabaseConfigured || !supabase) throw new Error('Supabase is not configured')
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { setResult({ ok: false, message: 'Not authenticated' }); return }

      const context = await resolveClientContextForCurrentUser()
      if (!context) throw new Error('Could not resolve your client profile')
      const timestamp = Date.now()
      const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_')
      const path = `${session.user.id}/${timestamp}_${safeName}`

      setProgress(30)

      const { error: uploadError } = await supabase.storage
        .from('client-documents')
        .upload(path, file, { cacheControl: '3600', upsert: false })

      if (uploadError) throw uploadError
      setProgress(70)

      const cat = selectedCategory || guessCategory(file.name, category)

      const docMeta = {
        id: `${context.authUserId}_${timestamp}_${safeName}`,
        tenant_id: context.tenantId,
        client_id: context.clientId,
        category: cat,
        title: file.name,
        summary: `Uploaded via inline upload — ${CATEGORY_LABELS[cat] || cat}`,
        status: 'uploaded',
        score: 0,
        priority: 'normal',
        risk_level: 'low',
        automation_level: cat === 'credit_reports' ? 'automatic_analysis_queue' : 'manual',
        client_visible: true,
        approval_required: true,
        goclear_review_status: cat === 'credit_reports' ? 'not_required' : 'pending_review',
        source: 'client_portal_upload',
        source_concept: `inline_${track}`,
        recommended_next_action: cat === 'credit_reports' ? 'Analysis queues automatically after upload' : 'Admin review uploaded document',
        created_at: new Date().toISOString(),
        payload: {
          storage_path: path,
          file_size: file.size,
          mime_type: file.type,
          uploaded_via: 'inline_upload',
          document_category: cat,
          journey_stage: track,
          requirement_key: requirementKey || null,
          page_context: pageContext,
        },
      }

      const { error: metaError } = await supabase.from('client_documents').upsert(docMeta, { onConflict: 'id' })
      if (metaError) throw metaError

      setProgress(100)
      setResult({ ok: true, message: `Uploaded to ${CATEGORY_LABELS[cat] || cat}` })
      setFile(null)
      onUploaded?.({ documentId: docMeta.id, fileName: file.name, category: cat, requirementKey, stage: track })
      trackEvent({ event: 'upload_completed', stage: track, requirement: requirementKey, route: pageContext, detail: cat })

      if (cat === 'credit_reports' || cat === 'credit_report') {
        const { error: jobError } = await supabase.from('credit_analysis_jobs').insert({
          tenant_id: docMeta.tenant_id,
          client_id: docMeta.client_id,
          document_id: docMeta.id,
          status: 'queued',
          requested_by: 'inline_upload',
        })
        if (jobError) console.warn('Failed to queue analysis job:', jobError)
      }
    } catch (err) {
      setResult({ ok: false, message: err?.message || 'Upload failed' })
      trackEvent({ event: 'upload_failed', stage: track, requirement: requirementKey, route: pageContext, detail: err?.message || 'Upload failed' })
    } finally {
      setUploading(false)
    }
  }

  if (compact) {
    return (
      <div className={className} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <input ref={inputRef} type="file" accept={ALLOWED_TYPES.join(',')} onChange={handleFile} style={{ display: 'none' }} />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          style={{
            padding: '4px 10px', borderRadius: 6, border: '1px solid #334155',
            background: '#1e293b', color: '#e2e8f0', cursor: 'pointer', fontSize: 11,
          }}
        >
          {uploading ? `Uploading ${progress}%` : (label || 'Upload')}
        </button>
        {result && (
          <span style={{ fontSize: 11, color: result.ok ? '#10b981' : '#ef4444' }}>
            {result.message}
          </span>
        )}
      </div>
    )
  }

  return (
    <div className={className} style={{
      padding: 12, borderRadius: 8, background: '#0f172a', border: '1px solid #334155',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600 }}>📎 {label || 'Upload Document'}</span>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <select
          value={selectedCategory}
          onChange={e => setSelectedCategory(e.target.value)}
          style={{
            padding: '4px 8px', borderRadius: 6, border: '1px solid #334155',
            background: '#1e293b', color: '#e2e8f0', fontSize: 12,
          }}
        >
          <option value="">Select category...</option>
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>

        <input ref={inputRef} type="file" accept={ALLOWED_TYPES.join(',')} onChange={handleFile} style={{ display: 'none' }} />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          style={{
            padding: '4px 12px', borderRadius: 6, border: '1px solid #475569',
            background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 12,
          }}
        >
          Choose File
        </button>

        {file && (
          <span style={{ color: '#e2e8f0', fontSize: 12, flex: 1 }}>
            {file.name} ({Math.round(file.size / 1024)}KB)
          </span>
        )}

        {file && (
          <button
            onClick={handleUpload}
            disabled={uploading || !selectedCategory}
            style={{
              padding: '4px 12px', borderRadius: 6, border: 'none',
              background: uploading ? '#475569' : '#3b82f6', color: '#fff',
              cursor: uploading ? 'default' : 'pointer', fontSize: 12, fontWeight: 600,
            }}
          >
            {uploading ? `${progress}%` : 'Upload'}
          </button>
        )}
      </div>

      {uploading && (
        <div style={{ marginTop: 8, height: 3, background: '#1e293b', borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${progress}%`, background: '#3b82f6', transition: 'width 0.3s' }} />
        </div>
      )}

      {result && (
        <div style={{
          marginTop: 8, padding: '6px 10px', borderRadius: 6,
          background: result.ok ? '#10b98115' : '#ef444415',
          border: `1px solid ${result.ok ? '#10b981' : '#ef4444'}30`,
          fontSize: 12, color: result.ok ? '#10b981' : '#ef4444',
        }}>
          {result.ok ? '✓' : '✕'} {result.message}
        </div>
      )}
    </div>
  )
}
