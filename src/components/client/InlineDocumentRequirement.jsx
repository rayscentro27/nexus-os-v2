import React, { useMemo, useState } from 'react'
import InlineDocumentUpload from './InlineDocumentUpload'

function normalize(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '_')
}

function findDocument(existingDocuments = [], category, requirementKey, title) {
  const keys = [category, requirementKey, title].map(normalize).filter(Boolean)
  return existingDocuments.find(doc => {
    const haystack = [
      doc.category,
      doc.doc_type,
      doc.title,
      doc.filename,
      doc.name,
      doc.source_concept,
      doc.summary,
    ].map(normalize).join(' ')
    return keys.some(key => haystack.includes(key))
  })
}

function getStatus(doc, reviewStatus, required) {
  if (!doc) return required ? 'Missing' : 'Optional'
  const status = normalize(reviewStatus || doc.goclear_review_status || doc.status)
  if (status.includes('approved') || status.includes('complete')) return 'Approved'
  if (status.includes('replace') || status.includes('rejected')) return 'Needs Replacement'
  if (status.includes('review') || status.includes('pending')) return 'Pending Review'
  return 'Uploaded'
}

function toneFor(status) {
  if (status === 'Approved' || status === 'Uploaded') return 'green'
  if (status === 'Pending Review' || status === 'Needs Replacement') return 'orange'
  return 'blue'
}

function trackForPage(page) {
  if (/credit-repair|credit-profile|credit-utilization/.test(page || '')) return 'credit_profile'
  if (/business-bankability/.test(page || '')) return 'business_bankability'
  if (/business-setup|profile/.test(page || '')) return 'business_profile'
  if (/funding/.test(page || '')) return 'funding_readiness'
  if (/request-review|dispute-review/.test(page || '')) return 'request_review'
  return 'general'
}

export function InlineDocumentRequirement({
  title,
  description,
  category,
  requirementKey,
  fromPage,
  impactLabel,
  required = true,
  existingDocuments = [],
  reviewStatus,
  onUploaded,
  onOpenUpload,
  compact = false,
  whyItMatters,
}) {
  const [uploadOpen, setUploadOpen] = useState(false)
  const doc = useMemo(() => findDocument(existingDocuments, category, requirementKey, title), [existingDocuments, category, requirementKey, title])
  const status = getStatus(doc, reviewStatus, required)
  const tone = toneFor(status)
  const fileName = doc?.title || doc?.filename || doc?.name || ''

  return (
    <article className={`wc-inlineRequirement ${compact ? 'compact' : ''}`} data-requirement={requirementKey || category}>
      <div className="wc-inlineRequirementMain">
        <div className={`wc-dot ${tone}`}>{status === 'Missing' ? '!' : '✓'}</div>
        <div>
          <div className="wc-inlineRequirementTop">
            <b>{title}</b>
            <span>{status}</span>
          </div>
          <p>{description}</p>
          {whyItMatters && <small>{whyItMatters}</small>}
          {fileName && <em>{fileName}</em>}
          {(reviewStatus || doc?.goclear_review_status) && <em>Review: {reviewStatus || doc.goclear_review_status}</em>}
        </div>
      </div>
      <div className="wc-inlineRequirementActions">
        {impactLabel && <span>{impactLabel}</span>}
        <button onClick={() => onOpenUpload ? onOpenUpload({ title, category, requirementKey, fromPage, description }) : setUploadOpen(open => !open)}>{doc ? 'Replace Upload' : 'Upload'}</button>
        <button disabled title={doc ? 'Uploaded document is under GoClear review. Safe viewing is not implemented yet.' : 'No reviewed document is available yet.'}>{doc ? 'Uploaded - under review' : 'No reviewed document available yet'}</button>
      </div>
      {uploadOpen && (
        <InlineDocumentUpload
          category={category || requirementKey}
          pageContext={fromPage || 'client_portal'}
          track={trackForPage(fromPage)}
          requirementKey={requirementKey || category || 'inline_requirement'}
          onUploaded={onUploaded}
        />
      )}
    </article>
  )
}

export default InlineDocumentRequirement
