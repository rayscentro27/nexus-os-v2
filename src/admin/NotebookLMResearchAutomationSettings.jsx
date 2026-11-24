import React, { useEffect, useState } from 'react'
import { supabase } from '../lib/supabaseClient'

const label = value => String(value || 'NOT_CONFIGURED').replaceAll('_', ' ')

export default function NotebookLMResearchAutomationSettings() {
  const [settings, setSettings] = useState(null)
  const [sessions, setSessions] = useState([])
  const [gapCounts, setGapCounts] = useState({})
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    async function load() {
      if (!supabase) return
      const [s, runs, gaps] = await Promise.all([
        supabase.from('research_notebooklm_automation_settings').select('*').eq('settings_id', 'NOTEBOOKLM_RESEARCH').maybeSingle(),
        supabase.from('research_notebooklm_sessions').select('research_session_id,status,automation_path,research_method,started_at,completed_at').order('started_at', { ascending: false }).limit(10),
        supabase.from('nexus_feeder_research_gaps').select('status'),
      ])
      if (!active) return
      if (s.error || runs.error || gaps.error) { setError('NotebookLM automation status is unavailable. Confirm the migration and administrator access.'); return }
      const counts = (gaps.data || []).reduce((result, row) => { result[row.status] = (result[row.status] || 0) + 1; return result }, {})
      setSettings(s.data); setSessions(runs.data || []); setGapCounts(counts)
    }
    void load()
    return () => { active = false }
  }, [])

  const lastSuccess = sessions.find(row => row.status === 'COMPLETED')
  const lastFailure = sessions.find(row => ['BLOCKED_BY_AUTH', 'FAILED_RETRYABLE'].includes(row.status))
  const latestOutcome = sessions[0]
  return <section className="bi-workflows" aria-label="NotebookLM research automation">
    <header><div><span>RESEARCH · NOTEBOOKLM AUTOMATION</span><h2>Bounded public-source research</h2><p>Uses the existing authenticated CLI and Research worker. Sensitive uploads, sharing, and destructive notebook actions are disabled.</p></div><strong>{label(settings?.automation_mode)}</strong></header>
    {error && <p role="status">{error}</p>}
    <div className="bi-bank-grid">
      <article><strong>Active path</strong><small>{label(settings?.preferred_path)} · {settings?.enabled ? 'ENABLED' : 'DISABLED'}</small><small>CLI auth is checked by the worker before each session.</small></article>
      <article><strong>Import limits</strong><small>Sources per pass: {settings?.max_imported_sources_per_pass ?? '—'}</small><small>Passes per gap: {settings?.max_research_passes_per_gap ?? '—'} · Gaps per session: {settings?.max_gaps_per_notebook_session ?? '—'}</small></article>
      <article><strong>Research gap queue</strong><small>Open: {gapCounts.OPEN || 0} · In progress: {gapCounts.IN_PROGRESS || 0}</small><small>Completed: {gapCounts.COMPLETED || 0} · Blocked: {gapCounts.BLOCKED_EXTERNAL || 0}</small></article>
      <article><strong>Latest success</strong><small>{lastSuccess?.completed_at ? new Date(lastSuccess.completed_at).toLocaleString() : 'No completed session'}</small><small>{lastSuccess?.research_session_id || '—'}</small></article>
      <article><strong>Latest failure / recovery</strong><small>{lastFailure ? `${label(lastFailure.status)} · NOTEBOOK_RESEARCH_RECOVERY` : 'No recorded failure'}</small><small>{lastFailure?.started_at ? new Date(lastFailure.started_at).toLocaleString() : '—'}</small></article>
      <article><strong>Latest research outcome</strong><small>{label(latestOutcome?.status)}</small><small>{latestOutcome?.research_session_id || 'No session recorded'}</small></article>
      <article><strong>Privacy and authority</strong><small>Public sources only: {settings?.public_sources_only ? 'YES' : 'NO'}</small><small>Client data / destructive / sharing: NO / NO / NO</small></article>
    </div>
    <div className="bi-section"><div className="bi-section-title"><div><small>RECENT RESEARCH SESSIONS</small><h3>Notebook expansion activity</h3></div></div>
      {sessions.length ? sessions.map(row => <article className="bi-row" key={row.research_session_id}><b>{row.research_method}</b><span>{row.research_session_id} · {label(row.automation_path)}</span><small>{label(row.status)} · {new Date(row.started_at).toLocaleString()}</small></article>) : <p>No NotebookLM research sessions recorded yet.</p>}
    </div>
  </section>
}
