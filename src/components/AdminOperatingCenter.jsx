import React from 'react'
import CreativeReviewStudio from './CreativeReviewStudio'
import RayReviewCenter from './RayReviewCenter'

export default function AdminOperatingCenter({ mode = 'review' }) {
  if (mode === 'research') return null
  return <div className="nx2-page admin-operating-center" data-testid="admin-review-center">
    <div className="nx2-hero"><div><div className="nx2-eyebrow">ADMIN / REVIEW CENTER</div><h2>Review the work from one place.</h2><p>Private previews, versioned decisions, and governed rework. Approval never publishes by itself.</p></div><span className="nx2-status nx2-status-green">Remote review ready</span></div>
    <div className="nx2-kpi-row"><div className="nx2-kpi"><span>Review source</span><strong className="nx2-blue">Creative library</strong><small>Supabase/private proxy-backed</small></div><div className="nx2-kpi"><span>Decision actions</span><strong className="nx2-green">Approve · Changes · Reject</strong><small>Durable review receipt</small></div><div className="nx2-kpi"><span>Publication</span><strong className="nx2-amber">Gated</strong><small>No external side effect</small></div></div>
    <CreativeReviewStudio />
    <section className="nx2-card" aria-label="Unified review queue"><div className="nx2-card-head"><div><div className="nx2-eyebrow">UNIFIED QUEUE</div><h3>Human review boundaries</h3></div></div><p className="nx2-muted">Creative assets and canonical Ray decisions remain separate records, but are visible from this operating surface.</p><RayReviewCenter /></section>
  </div>
}
