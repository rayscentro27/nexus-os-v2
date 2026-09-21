import React, { useEffect, useState } from 'react'
import { supabase } from '../lib/supabaseClient'

function status(value) { return String(value || '—').replaceAll('_', ' ') }

export default function GoclearBetaProjectionPanel({ surface = 'admin' }) {
  const [rows, setRows] = useState([])
  const [state, setState] = useState('LOADING')
  useEffect(() => {
    let cancelled = false
    async function load() {
      const { data, error } = await supabase.from('goclear_beta_journey_projection').select('*').order('last_activity_at', { ascending: false })
      if (cancelled) return
      if (error) { setState('UNAVAILABLE'); return }
      setRows(data || []); setState('LIVE')
    }
    load(); const timer = window.setInterval(load, 30000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])
  return <section data-testid="goclear-beta-projection" style={{ background: '#0d1a2c', border: '1px solid #213650', borderRadius: 14, padding: 16, marginTop: 16 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline', flexWrap: 'wrap' }}>
      <div><span className="live-command-eyebrow">GOCLEAR / BETA JOURNEY</span><h3 style={{ margin: '6px 0' }}>{surface === 'nova' ? 'Nova Beta Monitor' : 'Friends-Beta Operations'}</h3><p style={{ color: '#91a5bf', margin: 0 }}>Canonical read-only projection · {state}</p></div>
      <strong style={{ color: '#83e6b0' }}>{rows.filter(row => row.completion_status === 'complete').length}/{rows.length} complete</strong>
    </div>
    {state === 'UNAVAILABLE' && <p role="status" style={{ color: '#ffb4b4' }}>Beta projection is unavailable; no operational claim is made.</p>}
    {state === 'LOADING' && <p style={{ color: '#91a5bf' }}>Loading canonical tester state…</p>}
    {state === 'LIVE' && !rows.length && <p style={{ color: '#91a5bf' }}>No controlled beta tester projection is currently present.</p>}
    {rows.map(row => <article key={row.projection_id} style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #213650' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(130px,1fr))', gap: 10 }}>
        <div><small style={{ color: '#91a5bf' }}>Tester</small><div>{row.tester_display_name || 'Controlled tester'}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Stage</small><div>{status(row.current_stage)}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Report</small><div>{status(row.report_status)}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Follow-up</small><div>{status(row.followup_status)}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Feedback</small><div>{status(row.feedback_status)}</div></div>
        <div><small style={{ color: '#91a5bf' }}>Completion</small><div>{status(row.completion_status)}</div></div>
      </div>
      <p style={{ color: row.blocking_issue ? '#ffd38a' : '#91a5bf', marginBottom: 0 }}>{row.blocking_issue ? `Blocking: ${status(row.blocking_issue)}` : 'No blocking issue recorded.'}{row.ray_action_required ? ' · Ray action required' : ''}</p>
    </article>)}
  </section>
}
