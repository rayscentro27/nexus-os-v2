import React, { useState } from 'react'
import { createJob } from '../lib/ledger'

const REQUESTS = [
  ['MAKE_FUNNY', 'Make it funny'],
  ['MAKE_PREMIUM', 'Make it premium'],
  ['MAKE_POV', 'Make it POV'],
  ['MAKE_EDUCATIONAL', 'Make it educational'],
  ['ADD_FACT', 'Add a verified fact'],
  ['CHANGE_CTA', 'Change the CTA'],
]

export default function CreativeVariationActions({ campaign }) {
  const [status, setStatus] = useState('')
  async function revise(label, request) {
    setStatus(`Queueing ${label}…`)
    const id = await createJob({ lane: 'creative', job_type: 'creative_natural_language_revision', status: 'queued', input: { campaign_id: campaign?.campaign_strategy?.campaign_id || campaign?.campaign_id, revision_request: request, preserved_context: campaign?.campaign_strategy || campaign, requested_at: new Date().toISOString() } })
    setStatus(id ? `${label} queued · ${id}` : 'Not queued: authenticated ledger unavailable. No fake revision was recorded.')
  }
  return <section className="nx2-card creative-variation-actions" aria-label="Creative variation actions"><div className="nx2-card-head"><div><div className="nx2-eyebrow">CONVERSATIONAL CREATIVE</div><h3>Revise this campaign in plain language.</h3></div><span className="nx2-status nx2-status-green">Context preserved</span></div><p className="nx2-muted">Each request keeps campaign, audience, stage, outcome, offer, compliance boundaries, and funnel destination.</p><div className="nx2-link-grid">{REQUESTS.map(([key, label]) => <button key={key} type="button" onClick={() => revise(label, label)}>{label}</button>)}<button type="button" onClick={() => revise('Fact + comment FUNDING', 'Use an interesting fact and tell them to comment FUNDING')}>Fact + comment FUNDING</button><button type="button" onClick={() => revise('Create variant', 'Create a materially different creative variant')}>Create variant</button></div>{status && <small>{status}</small>}</section>
}
