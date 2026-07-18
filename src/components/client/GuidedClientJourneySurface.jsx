import React from 'react'
import InlineDocumentRequirement from './InlineDocumentRequirement'
import { trackEvent } from '../../lib/clientAnalytics'

const stateLabel = value => String(value || 'insufficient_information').replaceAll('_', ' ')
const statusTone = status => status === 'complete' || status === 'ready_to_review' ? 'green' : status === 'processing' ? 'blue' : status === 'attention' ? 'orange' : 'purple'
const categoryLabels = ['Credit Reports', 'Credit Evidence', 'Identity and Authorization', 'Business Formation', 'Banking', 'Revenue and Financials', 'Funding Applications', 'Other']
const resourceGroups = [
  ['Credit education', '/client/credit-profile'],
  ['Report access', '/client/credit-profile'],
  ['Business foundation', '/client/business-setup'],
  ['Business banking', '/client/business-bankability'],
  ['Financial organization', '/client/business-bankability'],
  ['Funding preparation', '/client/funding-readiness'],
]
const contextualOffers = [
  ['SmartCredit', 'Credit education and monitoring', '/client/credit-profile'],
  ['AnnualCreditReport.com', 'Report access education', '/client/credit-profile'],
  ['Northwest Registered Agent', 'Business formation education', '/client/business-setup'],
  ['ZenBusiness', 'Business formation education', '/client/business-setup'],
  ['Bizee', 'Business formation education', '/client/business-setup'],
  ['iPostal1', 'Business address education', '/client/business-setup'],
  ['Mercury', 'Business banking education', '/client/business-bankability'],
  ['Bluevine', 'Business banking education', '/client/business-bankability'],
]

const guidedStageLabel = stageId => stageId?.startsWith('credit') ? 'Credit' : stageId?.startsWith('business') ? 'Business' : stageId === 'funding_readiness' ? 'Funding Readiness' : stageId === 'review_plan' ? 'Request Review' : 'Credit'

function RequirementRows({ stage, existingDocuments, openUploadPanel, onUploaded, navigate }) {
  return <div className="wc-guidedRequirements">{stage.requirements.map(req => (
    req.documentCategory ? <InlineDocumentRequirement
      key={req.id}
      title={req.label}
      description={req.whyItMatters}
      category={req.documentCategory}
      requirementKey={req.id}
      fromPage={req.route.replace('/client/', '')}
      impactLabel={`${req.impact} impact`}
      existingDocuments={existingDocuments}
      onUploaded={onUploaded}
      onOpenUpload={({ title, category, fromPage, description }) => openUploadPanel({ track: stage.id === 'credit_profile' ? 'credit_profile' : stage.id === 'business_foundation' ? 'business_profile' : 'business_funding', pageContext: fromPage || stage.id, suggestedCategory: category, title: `Upload ${title}`, description })}
      whyItMatters={`Why it matters: ${req.whyItMatters}`}
    /> : <div className="wc-guidedRequirement" key={req.id}>
      <div className={`wc-dot ${statusTone(req.status)}`}>{req.status === 'complete' ? '✓' : req.status === 'processing' ? '…' : req.status === 'attention' ? '!' : '?'}</div>
      <div className="wc-guidedRequirementBody"><div className="wc-guidedRequirementTop"><b>{req.label}</b><span>{stateLabel(req.status)}</span></div><p>Why it matters: {req.whyItMatters}</p><small>{req.status === 'complete' ? 'Observed or provided information is available.' : `Missing / next action: ${req.missing}`}</small></div>
      {req.status !== 'complete' && <button onClick={() => navigate(req.route)}>Next action</button>}
    </div>
  ))}</div>
}

function StageCard({ stage, existingDocuments, openUploadPanel, onUploaded, navigate }) {
  return <section className="wc-card wc-guidedStage" data-testid={`guided-stage-${stage.id}`}>
    <div className="wc-sectionHead"><div><h2>{stage.label}</h2><p>{stage.label} contribution: {stage.contribution}/100</p></div><span className={`wc-guidedState ${statusTone(stage.status)}`}>{stateLabel(stage.status)}</span></div>
    <RequirementRows stage={stage} existingDocuments={existingDocuments} openUploadPanel={openUploadPanel} onUploaded={onUploaded} navigate={navigate} />
  </section>
}

function DashboardSurface({ readiness, journey, navigate }) {
  return <section className="wc-card wc-guidedDashboard" data-testid="guided-dashboard">
    <div className="wc-sectionHead"><div><h2>Funding Readiness</h2><p>One guided path from current evidence to a controlled review request.</p></div><span className="wc-guidedState blue">{stateLabel(readiness.state)}</span></div>
    <div className="wc-guidedMetricGrid"><div><small>Current journey stage</small><b>{guidedStageLabel(journey?.currentStage)}</b></div><div><small>Next best action</small><b>{readiness.nextBestAction}</b></div><div><small>Completed requirements</small><b>{readiness.completedRequirements.length}</b></div><div><small>Outstanding requirements</small><b>{readiness.outstandingRequirements.length}</b></div></div>
    {readiness.primaryBlocker && <div className="wc-guidedBlocker"><b>Primary blocker</b><span>{readiness.primaryBlocker}</span></div>}
    <div className="wc-guidedActions"><button onClick={() => navigate(readiness.nextBestActionRoute)}>Continue where you left off</button><button onClick={() => navigate('/client/funding-readiness')}>View Funding Readiness</button><button onClick={() => navigate('/client/request-review')}>Review eligibility</button></div>
    <div className="wc-guidedColumns"><div><b>Recent activity</b>{(readiness.readinessHistory.length ? readiness.readinessHistory : [{ label: 'Journey state calculated from persisted profile and evidence', status: 'observed', date: '' }]).slice(0, 3).map(item => <p key={`${item.label}-${item.date}`}>• {item.label} · {item.status}</p>)}</div><div><b>Hermes guidance</b><p>Hermes separates Nexus-observed facts, client-provided information, uploaded evidence, uncertainty, and recommendations. Outcomes are not guaranteed.</p></div><div><b>Review eligibility</b><p>{readiness.reviewEligible ? 'Eligible to request a controlled review.' : 'Not yet eligible. Complete outstanding items and wait for processing or specialist review.'}</p></div></div>
  </section>
}

function FundingSurface({ readiness, existingDocuments, openUploadPanel, onUploaded, navigate }) {
  return <section className="wc-guidedFunding" data-testid="guided-funding-readiness"><div className="wc-guidedContributionGrid"><div><small>Credit contribution</small><b>{readiness.stages.credit.contribution}/100</b></div><div><small>Business Foundation contribution</small><b>{readiness.stages.business_foundation.contribution}/100</b></div><div><small>Business Bankability contribution</small><b>{readiness.stages.business_bankability.contribution}/100</b></div><div><small>Current state</small><b>{stateLabel(readiness.state)}</b></div></div><StageCard stage={readiness.stages.funding} existingDocuments={existingDocuments} openUploadPanel={openUploadPanel} onUploaded={onUploaded} navigate={navigate} /><div className="wc-guidedColumns wc-card"><div><b>Tier 1 relevance</b><p>{readiness.tier1.relevance}</p><small>Blockers: {readiness.tier1.blockers.join(', ') || 'None observed'}</small></div><div><b>Tier 2 relevance</b><p>{readiness.tier2.relevance}</p><small>Blockers: {readiness.tier2.blockers.join(', ') || 'None observed'}</small></div><div><b>Readiness history</b>{readiness.readinessHistory.length ? readiness.readinessHistory.map(item => <p key={`${item.label}-${item.date}`}>• {item.label} · {item.status}</p>) : <p>No prior readiness history is persisted yet.</p>}</div></div><div className="wc-card wc-guidedDocumentSummary"><b>Documents in this readiness snapshot</b><span>Complete: {readiness.completedRequirements.length}</span><span>Missing: {readiness.missingDocuments.join(', ') || 'None identified'}</span><span>Processing: {readiness.processingDocuments.join(', ') || 'None'}</span><button onClick={() => navigate('/client/documents')}>Open Documents Vault</button></div></section>
}

function DocumentsSurface({ navigate }) {
  return <section className="wc-card wc-guidedVaultSummary" data-testid="guided-documents-vault"><div className="wc-sectionHead"><div><h2>Documents Vault</h2><p>Protected document organization by category. Preview and download remain controlled by authenticated access.</p></div><button onClick={() => navigate('/client/documents')}>Open vault</button></div><div className="wc-guidedCategoryGrid">{categoryLabels.map(category => <button key={category} onClick={() => navigate('/client/documents')}><b>{category}</b><span>View linked documents</span></button>)}</div></section>
}

function ResourcesSurface({ navigate }) {
  const clickOffer = (title, route) => { trackEvent({ event: 'partner_offer_clicked', route, detail: title }); navigate(route) }
  return <section className="wc-card wc-guidedResources" data-testid="guided-resources"><div className="wc-sectionHead"><div><h2>Resources</h2><p>Education and contextual tools are shown beside the requirement they support.</p></div></div><div className="wc-guidedResourceGroups">{resourceGroups.map(([label, route]) => <button key={label} onClick={() => { trackEvent({ event: 'resource_viewed', route, detail: label }); navigate(route) }}>{label}<span>Open guidance →</span></button>)}</div><h3>Contextual approved offers</h3><div className="wc-guidedOfferGrid">{contextualOffers.map(([title, description, route]) => <button key={title} onClick={() => clickOffer(title, route)}><b>{title}</b><span>{description}</span></button>)}</div></section>
}

function ReviewSurface({ readiness, existingDocuments, openUploadPanel, onUploaded, navigate }) {
  const focusReviewForm = () => {
    const submitButton = document.querySelector('.wc-panel-review .wc-submitBtn')
    if (submitButton) {
      submitButton.scrollIntoView({ behavior: 'smooth', block: 'center' })
      submitButton.focus()
    } else navigate('/client/request-review')
  }
  return <section className="wc-card wc-guidedReview" data-testid="guided-request-review"><div className="wc-sectionHead"><div><h2>Request Review</h2><p>Submit a controlled review request with a readiness snapshot. No email, DocuPost, or automatic approval is triggered.</p></div><span className={`wc-guidedState ${readiness.reviewEligible ? 'green' : 'orange'}`}>{readiness.reviewEligible ? 'eligible' : 'not eligible'}</span></div><div className="wc-guidedReviewGrid"><div><b>Current readiness state</b><p>{stateLabel(readiness.state)}</p><b>Missing requirements</b><p>{readiness.outstandingRequirements.join(', ') || 'None'}</p></div><div><b>Documents still processing</b><p>{readiness.processingDocuments.join(', ') || 'None'}</p><b>Unresolved blockers</b><p>{readiness.primaryBlocker || 'None observed'}</p></div><div><b>Review deliverable</b><p>Readiness snapshot, documented gaps, client questions, and specialist follow-up where required.</p><p className="wc-guidedNoGuarantee">Review eligibility is not a guarantee of approval or funding.</p></div></div><InlineDocumentRequirement title="Request Review Support" description="Attach a missing or clarifying document without leaving the request workflow." category="review_support" requirementKey="review_support" fromPage="request-review" impactLabel="Optional" required={false} existingDocuments={existingDocuments} onUploaded={onUploaded} onOpenUpload={({ title, category, fromPage, description }) => openUploadPanel({ track: 'request_review', pageContext: fromPage, suggestedCategory: category, title: `Upload ${title}`, description })} whyItMatters="A support attachment gives the review team context without sending anything externally." /><button className="wc-primaryWide" onClick={() => readiness.reviewEligible ? focusReviewForm() : navigate(readiness.nextBestActionRoute)}>{readiness.reviewEligible ? 'Continue to submit review request' : 'Complete requirements first'}</button></section>
}

export default function GuidedClientJourneySurface({ routeKey, readiness, journey, existingDocuments, openUploadPanel, onUploaded, navigate }) {
  if (!readiness) return null
  if (routeKey === 'home') return <DashboardSurface readiness={readiness} journey={journey} navigate={navigate} />
  if (routeKey === 'credit') return <div className="wc-guidedStageStack"><StageCard stage={readiness.stages.credit} existingDocuments={existingDocuments} openUploadPanel={openUploadPanel} onUploaded={onUploaded} navigate={navigate} /><div className="wc-card wc-guidedCreditNote"><h2>Credit stage guidance</h2><p>Credit Profile and Credit Utilization are one guided stage. Utilization, discrepancies, strategies, evidence, and safe drafts stay connected here.</p><button onClick={() => navigate('/client/dispute-review')}>Open safe draft review</button></div></div>
  if (routeKey === 'business') return <div className="wc-guidedStageStack"><StageCard stage={readiness.stages.business_foundation} existingDocuments={existingDocuments} openUploadPanel={openUploadPanel} onUploaded={onUploaded} navigate={navigate} /><StageCard stage={readiness.stages.business_bankability} existingDocuments={existingDocuments} openUploadPanel={openUploadPanel} onUploaded={onUploaded} navigate={navigate} /></div>
  if (routeKey === 'funding') return <FundingSurface readiness={readiness} existingDocuments={existingDocuments} openUploadPanel={openUploadPanel} onUploaded={onUploaded} navigate={navigate} />
  if (routeKey === 'documents') return <DocumentsSurface navigate={navigate} />
  if (routeKey === 'resources') return <ResourcesSurface navigate={navigate} />
  if (routeKey === 'review') return <ReviewSurface readiness={readiness} existingDocuments={existingDocuments} openUploadPanel={openUploadPanel} onUploaded={onUploaded} navigate={navigate} />
  return null
}
