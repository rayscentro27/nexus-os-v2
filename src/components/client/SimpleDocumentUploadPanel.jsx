import React, { useMemo, useState } from 'react'
import { DocumentUploadZone } from './DocumentUploadZone'
import {
  DOCUMENT_CLASSIFICATION_DISCLOSURE,
  getDocumentUsageLabels,
  getNextRecommendedDocument,
  inferDocumentCategoryFromContext,
} from '../../lib/documentClassification'

const sourceByTrack = {
  credit_profile: 'client_portal_credit_profile_upload',
  business_profile: 'client_portal_business_profile_upload',
  business_funding: 'client_portal_business_funding_upload',
  request_review: 'client_portal_request_review_upload',
  credit_repair: 'client_portal_credit_repair_upload',
  general: 'client_portal_general_upload',
  documents: 'client_portal_general_upload',
}

export function SimpleDocumentUploadPanel({
  isOpen,
  onClose,
  pageContext = 'client_portal',
  track = 'general',
  suggestedCategory,
  title = 'Upload One Document',
  description = 'Upload one document and Clyde will organize it for GoClear review.',
  existingDocuments = [],
  missingRequirements = [],
  onUploaded,
  onViewVault,
}) {
  const [uploaded, setUploaded] = useState(null)
  const predictedCategory = useMemo(() => inferDocumentCategoryFromContext({ pageContext, track, suggestedCategory }), [pageContext, track, suggestedCategory])
  const nextDocument = getNextRecommendedDocument({ track, uploadedDocuments: existingDocuments, missingRequirements })
  const usage = getDocumentUsageLabels(uploaded?.category || predictedCategory)

  if (!isOpen) return null

  const handleUploadComplete = (details) => {
    const category = inferDocumentCategoryFromContext({
      fileName: details?.fileName,
      pageContext,
      track,
      suggestedCategory: details?.category || suggestedCategory,
    })
    setUploaded({
      fileName: details?.fileName || 'Uploaded document',
      category,
      source: sourceByTrack[track] || sourceByTrack.general,
    })
    onUploaded?.(details)
  }

  return (
    <div className="wc-uploadPanelOverlay" role="dialog" aria-modal="true" aria-label={title}>
      <div className="wc-uploadPanel">
        <div className="wc-uploadPanelHead">
          <div className="wc-softIcon">☁</div>
          <div>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
          <button onClick={onClose} aria-label="Close upload panel">×</button>
        </div>
        <div className="wc-uploadPanelNotice">
          <b>One document at a time</b>
          <p>{DOCUMENT_CLASSIFICATION_DISCLOSURE}</p>
        </div>
        <DocumentUploadZone
          compact
          maxFiles={1}
          category={predictedCategory}
          sourceConcept={sourceByTrack[track] || sourceByTrack.general}
          fromPage={pageContext}
          onUploadComplete={handleUploadComplete}
        />
        {uploaded ? (
          <div className="wc-uploadPanelResult">
            <b>{uploaded.fileName}</b>
            <span>Suggested category: {String(uploaded.category).replaceAll('_', ' ')}</span>
            <span>Pending GoClear Review</span>
            <span>Attached to: {pageContext.replaceAll('_', ' ')}</span>
            <p>Clyde is organizing this document for GoClear review.</p>
            {(uploaded.category === 'credit_report' || predictedCategory === 'credit_report') && (
              <p>Your report is uploaded and pending GoClear review. It should appear in the Credit Specialist Workbench for review. If parser preview is enabled, GoClear may use it to suggest items, but a specialist must confirm them before dispute options or letters move forward.</p>
            )}
            <p>Next recommended document: <strong>{nextDocument}</strong></p>
            <div>{usage.map(label => <em key={label}>{label}</em>)}</div>
          </div>
        ) : (
          <div className="wc-uploadPanelResult muted">
            <span>Suggested category: {String(predictedCategory).replaceAll('_', ' ')}</span>
            <span>Next recommended document: {nextDocument}</span>
          </div>
        )}
        <div className="wc-uploadPanelActions">
          <button onClick={() => setUploaded(null)}>Upload another document</button>
          <button onClick={onViewVault}>View Documents Vault</button>
        </div>
      </div>
    </div>
  )
}

export default SimpleDocumentUploadPanel
