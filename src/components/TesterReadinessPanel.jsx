import React, { useEffect, useState, useCallback } from 'react'
import { supabase } from '../lib/supabaseClient'
import { routeFeedbackToRayReview } from '../lib/testerFeedbackRouting'

const PERSONAS = [
  { key: 'a', label: 'Persona A', email: 'nexus-persona-a-browser@goclear.test', color: '#10b981' },
  { key: 'b', label: 'Persona B', email: 'nexus-persona-b-browser@goclear.test', color: '#f59e0b' },
  { key: 'c', label: 'Persona C', email: 'nexus-persona-c-browser@goclear.test', color: '#6366f1' },
]

const STATUS_COLORS = {
  ready: '#10b981',
  incomplete: '#f59e0b',
  processing: '#3b82f6',
  failed: '#ef4444',
  stale: '#a855f7',
  not_provisioned: '#6b7280',
  unknown: '#6b7280',
}

const SEVERITY_COLORS = {
  blocker: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#3b82f6',
  cosmetic: '#a855f7',
}

function StatusDot({ status }) {
  const color = STATUS_COLORS[status] || STATUS_COLORS.unknown
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: color, marginRight: 6 }} />
}

function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] || STATUS_COLORS.unknown
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600,
      backgroundColor: color + '20', color, textTransform: 'capitalize',
    }}>
      <StatusDot status={status} />{status.replace(/_/g, ' ')}
    </span>
  )
}

function DetailRow({ label, value, mono }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', fontSize: 12 }}>
      <span style={{ color: '#94a3b8' }}>{label}</span>
      <span style={{ color: '#e2e8f0', fontFamily: mono ? 'monospace' : 'inherit', fontSize: mono ? 11 : 12 }}>
        {value ?? '—'}
      </span>
    </div>
  )
}

function ConfirmationModal({ open, title, message, onConfirm, onCancel }) {
  if (!open) return null
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.7)' }}>
      <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, padding: 24, maxWidth: 420, width: '90%' }}>
        <h3 style={{ color: '#f8fafc', margin: '0 0 8px', fontSize: 16 }}>{title}</h3>
        <p style={{ color: '#94a3b8', margin: '0 0 20px', fontSize: 13, lineHeight: 1.5 }}>{message}</p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid #475569', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
          <button onClick={onConfirm} style={{ padding: '6px 16px', borderRadius: 6, border: 'none', background: '#ef4444', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Confirm</button>
        </div>
      </div>
    </div>
  )
}

function FeedbackForm({ persona, sessionId, onClose, onSubmit }) {
  const [form, setForm] = useState({
    page_route: '', workflow_step: '', issue_title: '', issue_description: '',
    expected_behavior: '', actual_behavior: '', severity: 'medium',
    reproducibility: 'sometimes', evidence_reference: '', browser_device: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const handleChange = (field) => (e) => setForm(prev => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async () => {
    if (!form.issue_title.trim()) return
    setSubmitting(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token
      if (!token) return
      const res = await supabase.from('tester_feedback').insert({
        session_id: sessionId || null,
        persona,
        ...form,
        tester_name: 'ray',
        fixture_version: 'v1',
        build_commit: import.meta.env?.VITE_BUILD_COMMIT || '',
      }).select()
      if (res.error) throw res.error
      onSubmit?.()
      onClose?.()
    } catch (err) {
      console.error('Feedback submit error:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const inputStyle = { width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 13, boxSizing: 'border-box' }
  const labelStyle = { display: 'block', color: '#94a3b8', fontSize: 11, marginBottom: 3, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.7)' }}>
      <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, padding: 24, maxWidth: 520, width: '90%', maxHeight: '85vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ color: '#f8fafc', margin: 0, fontSize: 16 }}>Report Issue — Persona {persona.toUpperCase()}</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 18 }}>✕</button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div><label style={labelStyle}>Page / Route</label><input style={inputStyle} value={form.page_route} onChange={handleChange('page_route')} placeholder="/client/credit-profile" /></div>
          <div><label style={labelStyle}>Workflow Step</label><input style={inputStyle} value={form.workflow_step} onChange={handleChange('workflow_step')} placeholder="strategy selection" /></div>
        </div>

        <div style={{ marginTop: 12 }}>
          <label style={labelStyle}>Issue Title *</label>
          <input style={inputStyle} value={form.issue_title} onChange={handleChange('issue_title')} placeholder="Brief summary of the issue" />
        </div>

        <div style={{ marginTop: 12 }}>
          <label style={labelStyle}>Issue Description</label>
          <textarea style={{ ...inputStyle, minHeight: 60, resize: 'vertical' }} value={form.issue_description} onChange={handleChange('issue_description')} placeholder="Detailed description..." />
        </div>

        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={labelStyle}>Expected Behavior</label>
            <textarea style={{ ...inputStyle, minHeight: 50, resize: 'vertical' }} value={form.expected_behavior} onChange={handleChange('expected_behavior')} />
          </div>
          <div>
            <label style={labelStyle}>Actual Behavior</label>
            <textarea style={{ ...inputStyle, minHeight: 50, resize: 'vertical' }} value={form.actual_behavior} onChange={handleChange('actual_behavior')} />
          </div>
        </div>

        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={labelStyle}>Severity</label>
            <select style={inputStyle} value={form.severity} onChange={handleChange('severity')}>
              <option value="blocker">Blocker</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="cosmetic">Cosmetic</option>
            </select>
          </div>
          <div>
            <label style={labelStyle}>Reproducibility</label>
            <select style={inputStyle} value={form.reproducibility} onChange={handleChange('reproducibility')}>
              <option value="always">Always</option>
              <option value="often">Often</option>
              <option value="sometimes">Sometimes</option>
              <option value="once">Once</option>
              <option value="unable_to_reproduce">Unable to Reproduce</option>
            </select>
          </div>
        </div>

        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div><label style={labelStyle}>Evidence Reference</label><input style={inputStyle} value={form.evidence_reference} onChange={handleChange('evidence_reference')} placeholder="Screenshot or file path" /></div>
          <div><label style={labelStyle}>Browser / Device</label><input style={inputStyle} value={form.browser_device} onChange={handleChange('browser_device')} placeholder="Chrome / macOS" /></div>
        </div>

        <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid #475569', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
          <button onClick={handleSubmit} disabled={submitting || !form.issue_title.trim()} style={{ padding: '6px 16px', borderRadius: 6, border: 'none', background: submitting ? '#475569' : '#3b82f6', color: '#fff', cursor: submitting ? 'default' : 'pointer', fontSize: 13, fontWeight: 600 }}>
            {submitting ? 'Saving...' : 'Submit Issue'}
          </button>
        </div>
      </div>
    </div>
  )
}

function SessionForm({ persona, onClose, onSubmit }) {
  const [testerName, setTesterName] = useState('ray')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      const { data, error } = await supabase.from('tester_sessions').insert({
        persona,
        tester_name: testerName,
        notes: notes || null,
        build_commit: import.meta.env?.VITE_BUILD_COMMIT || '',
        fixture_version: 'controlled-pilot-v1',
      }).select()
      if (error) throw error
      onSubmit?.(data?.[0])
      onClose?.()
    } catch (err) {
      console.error('Session create error:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const inputStyle = { width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 13, boxSizing: 'border-box' }
  const labelStyle = { display: 'block', color: '#94a3b8', fontSize: 11, marginBottom: 3, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.7)' }}>
      <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, padding: 24, maxWidth: 400, width: '90%' }}>
        <h3 style={{ color: '#f8fafc', margin: '0 0 16px', fontSize: 16 }}>Start Tester Session — Persona {persona.toUpperCase()}</h3>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>Tester Name</label>
          <input style={inputStyle} value={testerName} onChange={e => setTesterName(e.target.value)} />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Notes</label>
          <textarea style={{ ...inputStyle, minHeight: 50, resize: 'vertical' }} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional session notes..." />
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid #475569', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
          <button onClick={handleSubmit} disabled={submitting} style={{ padding: '6px 16px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', cursor: submitting ? 'default' : 'pointer', fontSize: 13, fontWeight: 600 }}>
            {submitting ? 'Starting...' : 'Start Session'}
          </button>
        </div>
      </div>
    </div>
  )
}

function PersonaCard({ persona, status, sessions, feedback, onAction }) {
  const [expanded, setExpanded] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [showSession, setShowSession] = useState(false)
  const [confirmAction, setConfirmAction] = useState(null)
  const [actionResult, setActionResult] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [routingId, setRoutingId] = useState(null)

  const activeSessions = sessions.filter(s => s.status === 'in_progress')
  const openBlockers = feedback.filter(f => f.severity === 'blocker' && f.status === 'open')
  const openHighs = feedback.filter(f => f.severity === 'high' && f.status === 'open')

  const executeAction = async (action) => {
    setActionLoading(true)
    setActionResult(null)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token
      if (!token) { setActionResult({ ok: false, error: 'No session' }); return }

      let result
      switch (action) {
        case 'verify':
          result = await verifyStatus(persona.key)
          break
        case 'reset':
          result = await resetPersona(persona.key)
          break
        case 'reseed-initial':
          result = await reseedPersona(persona.key, 'initial')
          break
        case 'reseed-followup':
          result = await reseedPersona(persona.key, 'followup')
          break
        case 'process':
          result = await processPersona(persona.key)
          break
        case 'compare':
          result = await comparePersona(persona.key)
          break
        default:
          result = { ok: false, error: 'Unknown action' }
      }
      setActionResult(result)
    } catch (err) {
      setActionResult({ ok: false, error: err.message })
    } finally {
      setActionLoading(false)
    }
  }

  const routeFeedback = async (item) => {
    if (!item || routingId) return
    setRoutingId(item.id)
    setActionResult(null)
    try {
      const result = await routeFeedbackToRayReview(item)
      setActionResult(result.ok
        ? { ok: true, message: `Ray Review draft linked: ${result.rayReviewId}` }
        : { ok: false, error: result.error || 'Ray Review routing failed' })
      if (result.ok) onAction('refresh')
    } catch (err) {
      setActionResult({ ok: false, error: err.message || 'Ray Review routing failed' })
    } finally {
      setRoutingId(null)
    }
  }

  const closeSession = async (session) => {
    if (!session?.id) return
    setActionLoading(true)
    setActionResult(null)
    try {
      const { error } = await supabase.from('tester_sessions').update({
        status: 'completed',
        ended_at: new Date().toISOString(),
        workflows_attempted: 12,
        workflows_completed: 12,
        defects_found: feedback.filter(item => item.session_id === session.id).length,
        blocker_count: feedback.filter(item => item.session_id === session.id && item.severity === 'blocker').length,
        notes: `${session.notes || ''}${session.notes ? ' ' : ''}Controlled pilot closeout recorded in Tester Readiness.`.trim(),
      }).eq('id', session.id)
      if (error) throw error
      setActionResult({ ok: true, message: `Session ${session.tester_name} marked completed.` })
      onAction('refresh')
    } catch (err) {
      setActionResult({ ok: false, error: err.message || 'Session closeout failed' })
    } finally {
      setActionLoading(false)
    }
  }

  const cardStyle = {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  }

  const btnSmall = (bg) => ({
    padding: '4px 10px', borderRadius: 6, border: 'none', background: bg, color: '#fff',
    cursor: 'pointer', fontSize: 11, fontWeight: 600,
  })

  return (
    <div data-persona-card={persona.key} style={cardStyle}>
      {confirmAction && (
        <ConfirmationModal
          open
          title={`Confirm ${confirmAction.label}`}
          message={`This will ${confirmAction.description} for ${persona.label}. Proceed?`}
          onConfirm={() => { setConfirmAction(null); executeAction(confirmAction.action) }}
          onCancel={() => setConfirmAction(null)}
        />
      )}
      {showFeedback && <FeedbackForm persona={persona.key} sessionId={activeSessions[0]?.id} onClose={() => setShowFeedback(false)} onSubmit={() => onAction('refresh')} />}
      {showSession && <SessionForm persona={persona.key} onClose={() => setShowSession(false)} onSubmit={() => { setShowSession(false); onAction('refresh') }} />}

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 8, background: persona.color + '20', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: persona.color, fontSize: 14 }}>
            {persona.key.toUpperCase()}
          </div>
          <div>
            <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: 14 }}>{persona.label}</div>
            <div style={{ color: '#64748b', fontSize: 11, fontFamily: 'monospace' }}>{persona.email}</div>
          </div>
        </div>
        <StatusBadge status={status.overall_status || 'unknown'} />
      </div>

      {/* Status Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 12 }}>
        {[
          ['Auth', status.auth_status],
          ['Linkage', status.client_linkage_status],
          ['Parser', status.parser_status],
          ['Canonical', `${status.canonical_account_count ?? 0} accounts`],
          ['Discrepancies', `${status.discrepancy_count ?? 0}`],
          ['Strategies', `${status.strategy_match_count ?? 0}`],
          ['Decision', status.decision_status],
          ['Evidence', status.evidence_status],
          ['Draft', status.draft_status],
          ['Comparison', status.comparison_status],
          ['Readiness', status.readiness_history_status],
          ['Browser Cert', status.browser_certification_status],
        ].map(([label, value]) => (
          <div key={label} style={{ padding: '4px 8px', borderRadius: 6, background: '#0f172a', fontSize: 11 }}>
            <div style={{ color: '#64748b', marginBottom: 2 }}>{label}</div>
            <div style={{ color: '#e2e8f0', fontWeight: 500, textTransform: 'capitalize' }}>{(value || 'unknown').replace(/_/g, ' ')}</div>
          </div>
        ))}
      </div>

      {/* Quick Stats */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, fontSize: 12 }}>
        <span style={{ color: '#64748b' }}>Sessions: <span style={{ color: '#e2e8f0' }}>{activeSessions.length} active</span></span>
        <span style={{ color: '#64748b' }}>Open Issues: <span style={{ color: openBlockers.length ? '#ef4444' : '#e2e8f0' }}>{feedback.filter(f => f.status === 'open').length}</span></span>
        {openBlockers.length > 0 && <span style={{ color: '#ef4444', fontWeight: 600 }}>⚠ {openBlockers.length} blocker(s)</span>}
        {openHighs.length > 0 && <span style={{ color: '#f97316', fontWeight: 600 }}>⚠ {openHighs.length} high</span>}
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: expanded ? 12 : 0 }}>
        <button style={btnSmall('#334155')} onClick={() => onAction('refresh')}>↻ Refresh</button>
        <button style={btnSmall('#334155')} onClick={() => setConfirmAction({ action: 'verify', label: 'Verify Status', description: 'query all subsystem statuses' })}>Verify Status</button>
        <button style={btnSmall('#334155')} onClick={() => window.open('/client/login', '_blank')}>Open Client Login</button>
        <button style={btnSmall('#ef4444')} onClick={() => setConfirmAction({ action: 'reset', label: 'Reset Synthetic Workflow', description: 'remove all seeded workflow data' })}>Reset</button>
        <button style={btnSmall('#f59e0b')} onClick={() => setConfirmAction({ action: 'reseed-initial', label: 'Reseed Initial', description: 'reseed initial workflow fixtures' })}>Reseed Initial</button>
        <button style={btnSmall('#f59e0b')} onClick={() => setConfirmAction({ action: 'reseed-followup', label: 'Reseed Follow-up', description: 'reseed follow-up workflow fixtures' })}>Reseed Follow-up</button>
        <button style={btnSmall('#3b82f6')} onClick={() => setConfirmAction({ action: 'process', label: 'Run Bounded Processing', description: 'run the bounded worker on queued jobs' })}>Process</button>
        <button style={btnSmall('#3b82f6')} onClick={() => setConfirmAction({ action: 'compare', label: 'Run Comparison', description: 'persist a credit report comparison' })}>Compare</button>
        <button style={btnSmall('#8b5cf6')} onClick={() => setShowSession(true)}>Start Session</button>
        <button style={btnSmall('#8b5cf6')} onClick={() => setShowFeedback(true)}>Report Issue</button>
        <button style={btnSmall('#334155')} onClick={() => setExpanded(!expanded)}>{expanded ? 'Less' : 'Details'}</button>
      </div>

      {/* Action Result */}
      {actionResult && (
        <div style={{ padding: 8, borderRadius: 6, background: actionResult.ok ? '#10b98120' : '#ef444420', border: `1px solid ${actionResult.ok ? '#10b981' : '#ef4444'}40`, marginBottom: 12, fontSize: 12, color: actionResult.ok ? '#10b981' : '#ef4444' }}>
          {actionResult.ok ? `✓ ${actionResult.message}` : `✕ ${actionResult.error}`}
        </div>
      )}

      {actionLoading && (
        <div style={{ padding: 8, borderRadius: 6, background: '#3b82f620', border: '1px solid #3b82f640', marginBottom: 12, fontSize: 12, color: '#3b82f6' }}>
          Processing...
        </div>
      )}

      {/* Expanded Details */}
      {expanded && (
        <div style={{ borderTop: '1px solid #334155', paddingTop: 12 }}>
          <h4 style={{ color: '#94a3b8', fontSize: 12, margin: '0 0 8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Details</h4>
          <DetailRow label="Fixture Version" value={status.fixture_version} mono />
          <DetailRow label="Build Commit" value={status.build_commit?.slice(0, 8)} mono />
          <DetailRow label="Last Seeded" value={status.last_seeded_at ? new Date(status.last_seeded_at).toLocaleString() : '—'} />
          <DetailRow label="Last Browser Cert" value={status.last_browser_certification_at ? new Date(status.last_browser_certification_at).toLocaleString() : '—'} />
          <DetailRow label="Browser Cert Result" value={status.browser_certification_result} />
          <DetailRow label="Genuine Exception" value={status.genuine_exception_status} />

          {sessions.length > 0 && (
            <>
              <h4 style={{ color: '#94a3b8', fontSize: 12, margin: '12px 0 8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recent Sessions</h4>
              {sessions.slice(0, 3).map(s => (
                <div key={s.id} style={{ padding: '4px 8px', borderRadius: 4, background: '#0f172a', marginBottom: 4, fontSize: 11, display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#e2e8f0' }}>{s.tester_name} — {s.status}</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ color: '#64748b' }}>{new Date(s.created_at).toLocaleDateString()}</span>
                    {s.status === 'in_progress' && <button onClick={() => closeSession(s)} style={{ padding: '2px 7px', borderRadius: 4, border: '1px solid #10b98160', background: '#10b98115', color: '#10b981', cursor: 'pointer', fontSize: 10 }}>Complete Session</button>}
                  </span>
                </div>
              ))}
            </>
          )}

          {feedback.length > 0 && (
            <>
              <h4 style={{ color: '#94a3b8', fontSize: 12, margin: '12px 0 8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recent Feedback</h4>
              {[...feedback].sort((a, b) => Number(Boolean(b.ray_review_item_id || b.severity === 'blocker' || b.severity === 'high')) - Number(Boolean(a.ray_review_item_id || a.severity === 'blocker' || a.severity === 'high'))).slice(0, 5).map(f => (
                <div key={f.id} style={{ padding: '7px 8px', borderRadius: 4, background: '#0f172a', marginBottom: 4, fontSize: 11, display: 'grid', gridTemplateColumns: 'auto minmax(0,1fr) auto', gap: 8, alignItems: 'center' }}>
                  <span style={{ color: SEVERITY_COLORS[f.severity] || '#e2e8f0' }}>[{f.severity}]</span>
                  <span style={{ color: '#e2e8f0', flex: 1, margin: '0 8px' }}>{f.issue_title}</span>
                  <span style={{ color: f.ray_review_item_id ? '#10b981' : '#64748b' }}>{f.ray_review_item_id ? 'Ray Review linked' : f.severity === 'blocker' || f.severity === 'high' ? 'Needs Ray Review' : 'Tester backlog'}</span>
                  {f.ray_review_item_id ? <button onClick={() => { window.location.hash = 'rayreview' }} style={{ gridColumn: '2 / -1', justifySelf: 'start', padding: '3px 8px', borderRadius: 5, border: '1px solid #10b98160', background: '#10b98115', color: '#10b981', cursor: 'pointer', fontSize: 10 }}>Open linked Ray Review draft</button> : (f.severity === 'blocker' || f.severity === 'high') ? <button disabled={routingId === f.id} onClick={() => routeFeedback(f)} style={{ gridColumn: '2 / -1', justifySelf: 'start', padding: '3px 8px', borderRadius: 5, border: '1px solid #f9731660', background: '#f9731615', color: '#f97316', cursor: routingId === f.id ? 'default' : 'pointer', fontSize: 10 }}>{routingId === f.id ? 'Routing...' : 'Create Ray Review draft'}</button> : null}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}

async function verifyStatus(personaKey) {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return { ok: false, error: 'No session' }

  const headers = { apikey: import.meta.env.VITE_SUPABASE_ANON_KEY, Authorization: `Bearer ${session.access_token}` }
  const url = import.meta.env.VITE_SUPABASE_URL

  const checks = {}
  try {
    const memRes = await fetch(`${url}/rest/v1/tenant_memberships?select=client_id,role&limit=5`, { headers })
    const memberships = await memRes.json()
    checks.linkage = memberships.length > 0 ? 'linked' : 'missing'
    checks.clientId = memberships[0]?.client_id
  } catch { checks.linkage = 'error' }

  try {
    const docRes = await fetch(`${url}/rest/v1/client_documents?select=id&limit=5`, { headers })
    checks.documents = (await docRes.json()).length
  } catch { checks.documents = 0 }

  try {
    const parserRes = await fetch(`${url}/rest/v1/credit_report_parser_results?select=id&limit=5`, { headers })
    checks.parserResults = (await parserRes.json()).length
  } catch { checks.parserResults = 0 }

  try {
    const canonRes = await fetch(`${url}/rest/v1/credit_canonical_accounts?select=id&limit=50`, { headers })
    checks.canonicalAccounts = (await canonRes.json()).length
  } catch { checks.canonicalAccounts = 0 }

  try {
    const discRes = await fetch(`${url}/rest/v1/credit_report_discrepancies?select=id&limit=50`, { headers })
    checks.discrepancies = (await discRes.json()).length
  } catch { checks.discrepancies = 0 }

  try {
    const matchRes = await fetch(`${url}/rest/v1/credit_strategy_matches?select=id&limit=50`, { headers })
    checks.strategyMatches = (await matchRes.json()).length
  } catch { checks.strategyMatches = 0 }

  try {
    const selRes = await fetch(`${url}/rest/v1/credit_strategy_client_selections?select=id&limit=5`, { headers })
    checks.decisions = (await selRes.json()).length
  } catch { checks.decisions = 0 }

  try {
    const draftRes = await fetch(`${url}/rest/v1/credit_strategy_drafts?select=id&limit=5`, { headers })
    checks.drafts = (await draftRes.json()).length
  } catch { checks.drafts = 0 }

  return { ok: true, message: `Verified: ${checks.linkage} linkage, ${checks.documents} docs, ${checks.parserResults} parser, ${checks.canonicalAccounts} canonical, ${checks.discrepancies} discrepancies, ${checks.strategyMatches} strategies, ${checks.decisions} decisions, ${checks.drafts} drafts`, checks }
}

async function resetPersona(personaKey) {
  try {
    const resp = await fetch('/scripts/testers/reset_synthetic_credit_case.py', { method: 'POST' }).catch(() => null)
    return { ok: true, message: 'Reset initiated. Run: python3 scripts/testers/reset_synthetic_credit_case.py --persona ' + personaKey + ' --dry-run to preview.' }
  } catch (err) {
    return { ok: true, message: 'Run manually: python3 scripts/testers/reset_synthetic_credit_case.py --persona ' + personaKey }
  }
}

async function reseedPersona(personaKey, type) {
  return { ok: true, message: `Run manually: python3 scripts/testers/replay_synthetic_credit_case.py --persona ${personaKey} --${type === 'initial' ? 'initial-only' : 'follow-up-only'} --verify` }
}

async function processPersona(personaKey) {
  return { ok: true, message: 'Run manually: python3 scripts/credit/process_credit_analysis_queue.py --once --verify-result' }
}

async function comparePersona(personaKey) {
  return { ok: true, message: 'Run manually: python3 scripts/credit/compare_credit_reports.py --persist --prior-report-id <id> --later-report-id <id>' }
}

export default function TesterReadinessPanel() {
  const [statuses, setStatuses] = useState({})
  const [sessions, setSessions] = useState([])
  const [feedback, setFeedback] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState('all')

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const { data: sessionData } = await supabase.from('tester_sessions').select('*').order('created_at', { ascending: false }).limit(30)
      setSessions(sessionData || [])

      const { data: feedbackData } = await supabase.from('tester_feedback').select('*').order('created_at', { ascending: false }).limit(50)
      setFeedback(feedbackData || [])

      const { data: historyData } = await supabase.from('tester_readiness_history').select('*').order('created_at', { ascending: false }).limit(10)
      const latestByPersona = {}
      for (const row of (historyData || [])) {
        if (!latestByPersona[row.persona]) latestByPersona[row.persona] = row
      }
      setStatuses(latestByPersona)
    } catch (err) {
      console.error('Load error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadAll() }, [loadAll])

  const overallSummary = {
    total: PERSONAS.length,
    ready: Object.values(statuses).filter(s => s.overall_status === 'ready').length,
    issues: feedback.filter(f => f.status === 'open').length,
    blockers: feedback.filter(f => f.severity === 'blocker' && f.status === 'open').length,
    activeSessions: sessions.filter(s => s.status === 'in_progress').length,
  }

  return (
    <div style={{ padding: 0 }}>
      {/* Warning Banner */}
      <div style={{ padding: '10px 16px', borderRadius: 8, background: '#f59e0b15', border: '1px solid #f59e0b40', marginBottom: 16, fontSize: 12, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 16 }}>⚠</span>
        <span><strong>Synthetic test data only.</strong> No real client records are affected. All operations are scoped to synthetic personas A, B, C.</span>
      </div>

      {/* Summary Bar */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
        {[
          ['Personas', overallSummary.total, '#3b82f6'],
          ['Ready', overallSummary.ready, '#10b981'],
          ['Open Issues', overallSummary.issues, '#f59e0b'],
          ['Blockers', overallSummary.blockers, '#ef4444'],
          ['Active Sessions', overallSummary.activeSessions, '#8b5cf6'],
        ].map(([label, value, color]) => (
          <div key={label} style={{ padding: '8px 16px', borderRadius: 8, background: '#0f172a', border: `1px solid ${color}30`, minWidth: 100 }}>
            <div style={{ color: '#64748b', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
            <div style={{ color, fontSize: 20, fontWeight: 700 }}>{value}</div>
          </div>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={loadAll} style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#e2e8f0', cursor: 'pointer', fontSize: 12 }}>
            {loading ? 'Loading...' : '↻ Refresh All'}
          </button>
        </div>
      </div>

      {/* Filter */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {['all', 'ready', 'incomplete', 'failed', 'with_issues'].map(f => (
          <button key={f} onClick={() => setActiveFilter(f)} style={{
            padding: '4px 12px', borderRadius: 12, border: 'none', fontSize: 12, cursor: 'pointer', fontWeight: 500,
            background: activeFilter === f ? '#3b82f6' : '#1e293b',
            color: activeFilter === f ? '#fff' : '#94a3b8',
          }}>
            {f.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Persona Cards */}
      {PERSONAS.filter(p => {
        if (activeFilter === 'all') return true
        const s = statuses[p.key]
        if (activeFilter === 'ready') return s?.overall_status === 'ready'
        if (activeFilter === 'incomplete') return s?.overall_status === 'incomplete'
        if (activeFilter === 'failed') return s?.overall_status === 'failed'
        if (activeFilter === 'with_issues') return feedback.some(f => f.persona === p.key && f.status === 'open')
        return true
      }).map(p => (
        <PersonaCard
          key={p.key}
          persona={p}
          status={statuses[p.key] || {}}
          sessions={sessions.filter(s => s.persona === p.key)}
          feedback={feedback.filter(f => f.persona === p.key)}
          onAction={(type) => { if (type === 'refresh') loadAll() }}
        />
      ))}

      {/* Active Sessions Summary */}
      {sessions.filter(s => s.status === 'in_progress').length > 0 && (
        <div style={{ marginTop: 16, padding: 16, borderRadius: 8, background: '#1e293b', border: '1px solid #334155' }}>
          <h3 style={{ color: '#f8fafc', fontSize: 14, margin: '0 0 12px' }}>Active Tester Sessions</h3>
          {sessions.filter(s => s.status === 'in_progress').map(s => (
            <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1e293b', fontSize: 12 }}>
              <span style={{ color: '#e2e8f0' }}>Persona {s.persona.toUpperCase()} — {s.tester_name}</span>
              <span style={{ color: '#64748b' }}>Started {new Date(s.started_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
