import React, { useCallback, useEffect, useState } from 'react'
import { Activity, Clock3, Compass, RefreshCw, Store, TrendingUp } from 'lucide-react'
import { supabase } from '../lib/supabaseClient'
import './pulseAdminWorkspace.css'

const tabs = ['OVERVIEW', 'LIVE TRENDS', 'TREND NOTEBOOKS', 'COMMERCIAL MATCHES', 'AFFILIATE OPPORTUNITIES', 'MERCH OPPORTUNITIES', 'VIRAL PATTERNS', 'TREND HISTORY', 'RAPID CAMPAIGNS', 'PRINTIFY', 'SOURCE HEALTH', 'SCHEDULE', 'SETTINGS']
const stamp = value => value ? new Date(value).toLocaleString('en-US', { timeZone: 'America/Phoenix' }) : 'Not recorded'

function PulseTable({ rows, columns, empty }) {
  if (!rows?.length) return <div className="pulse-empty">{empty || 'No persisted records yet.'}</div>
  return <div className="pulse-table-wrap"><table className="pulse-table"><thead><tr>{columns.map(column => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.trend_id || row.job_id || row.provider_name || row.handoff_id || row.campaign_id || row.record_id || index}>{columns.map(column => <td key={column.key}>{column.render ? column.render(row[column.key], row) : String(row[column.key] ?? '—')}</td>)}</tr>)}</tbody></table></div>
}

export default function PulseAdminWorkspace() {
  const [active, setActive] = useState('OVERVIEW')
  const [data, setData] = useState({ schedules: [], providers: [], trends: [], handoffs: [], campaigns: [], shops: [], banks: [], notebooks: [], history: [] })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(async () => {
    setLoading(true); setError('')
    const queries = await Promise.all([
      supabase.from('pulse_schedule_registry').select('job_id,cadence_seconds,enabled,last_started_at,last_success_at,last_status,next_run_at').order('next_run_at').limit(10),
      supabase.from('pulse_provider_registry').select('provider_name,source_type,current_status,automation_mode,nexus_tested,last_tested_at').order('provider_name').limit(50),
      supabase.from('pulse_trends').select('trend_id,title,topic,platform,current_views,velocity,status,last_observed_at,trend_class,source_quality,updated_at').order('updated_at', { ascending: false }).limit(100),
      supabase.from('pulse_handoffs').select('handoff_id,to_department,summary,status,created_at').order('created_at', { ascending: false }).limit(30),
      supabase.from('pulse_campaign_briefs').select('campaign_id,campaign_type,state,publish_state,ray_approval_required,created_at').order('created_at', { ascending: false }).limit(30),
      supabase.from('pulse_printify_shops').select('shop_id,shop_title,sales_channel,store_status,last_tested_at').order('last_tested_at', { ascending: false }).limit(10),
      supabase.from('pulse_shared_intelligence_bank').select('bank_name,record_id,trend_id,evidence_state,confidence,updated_at').order('updated_at', { ascending: false }).limit(100),
      supabase.from('research_notebooks').select('id,title,owner_department,status,updated_at').eq('owner_department', 'PULSE').order('updated_at', { ascending: false }).limit(50),
      supabase.from('trend_history_bank').select('trend_id,views,velocity,platform_count,status,observed_at').order('observed_at', { ascending: false }).limit(100),
    ])
    const failed = queries.find(result => result.error)
    if (failed) setError('Pulse data is unavailable to this authenticated admin session.')
    setData({ schedules: queries[0].data || [], providers: queries[1].data || [], trends: queries[2].data || [], handoffs: queries[3].data || [], campaigns: queries[4].data || [], shops: queries[5].data || [], banks: queries[6].data || [], notebooks: queries[7].data || [], history: queries[8].data || [] })
    setLoading(false)
  }, [])
  useEffect(() => { refresh() }, [refresh])
  const latest = data.schedules.map(row => row.last_success_at).filter(Boolean).sort().at(-1)
  const next = data.schedules.map(row => row.next_run_at).filter(Boolean).sort()[0]
  const view = active === 'OVERVIEW' ? <>
    <div className="pulse-metrics"><article><Activity /><span>Persisted trends</span><strong>{data.trends.length}</strong></article><article><Clock3 /><span>Last successful scan</span><strong>{stamp(latest)}</strong></article><article><Clock3 /><span>Next scheduled scan</span><strong>{stamp(next)}</strong></article><article><Store /><span>Printify connection</span><strong>{data.providers.find(x => x.provider_name === 'PRINTIFY_SHOPS')?.current_status || 'NOT_TESTED'}</strong></article></div>
    <div className="pulse-grid"><section><h2>Top rising trends</h2><PulseTable rows={data.trends.slice(0, 8)} columns={[{ key: 'title', label: 'Signal' }, { key: 'platform', label: 'Platform' }, { key: 'trend_class', label: 'Class' }, { key: 'status', label: 'Status' }, { key: 'source_quality', label: 'Evidence' }]} /></section><section><h2>Active schedule</h2><PulseTable rows={data.schedules} columns={[{ key: 'job_id', label: 'Job' }, { key: 'cadence_seconds', label: 'Cadence (s)' }, { key: 'last_status', label: 'Status' }, { key: 'next_run_at', label: 'Next run', render: stamp }]} /></section></div>
    <section className="pulse-panel"><h2>Recent handoffs</h2><PulseTable rows={data.handoffs.slice(0, 6)} columns={[{ key: 'to_department', label: 'Owner' }, { key: 'summary', label: 'Summary' }, { key: 'status', label: 'Status' }, { key: 'created_at', label: 'Created', render: stamp }]} /></section>
  </> : active === 'LIVE TRENDS' ? <section className="pulse-panel"><h2>Live trends</h2><PulseTable rows={data.trends} columns={[{ key: 'title', label: 'Trend' }, { key: 'topic', label: 'Topic' }, { key: 'platform', label: 'Platform' }, { key: 'current_views', label: 'Views' }, { key: 'velocity', label: 'Views/hour' }, { key: 'status', label: 'State' }, { key: 'last_observed_at', label: 'Observed', render: stamp }]} /></section>
    : active === 'TREND NOTEBOOKS' ? <section className="pulse-panel"><h2>Trend notebooks · Pulse ownership</h2><PulseTable rows={data.notebooks} columns={[{ key: 'title', label: 'Notebook' }, { key: 'owner_department', label: 'Owner' }, { key: 'status', label: 'Status' }, { key: 'updated_at', label: 'Updated', render: stamp }]} /></section>
      : active === 'SCHEDULE' ? <section className="pulse-panel"><h2>Schedule · shared continuous daemon</h2><PulseTable rows={data.schedules} columns={[{ key: 'job_id', label: 'Scheduled job' }, { key: 'cadence_seconds', label: 'Seconds' }, { key: 'enabled', label: 'Enabled' }, { key: 'last_started_at', label: 'Last started', render: stamp }, { key: 'last_status', label: 'Last result' }, { key: 'next_run_at', label: 'Next', render: stamp }]} /></section>
        : active === 'SOURCE HEALTH' ? <section className="pulse-panel"><h2>Source health</h2><PulseTable rows={data.providers} columns={[{ key: 'provider_name', label: 'Provider' }, { key: 'source_type', label: 'Type' }, { key: 'current_status', label: 'Status' }, { key: 'automation_mode', label: 'Mode' }, { key: 'nexus_tested', label: 'Tested' }, { key: 'last_tested_at', label: 'Tested at', render: stamp }]} /></section>
          : active === 'PRINTIFY' ? <section className="pulse-panel"><h2>Printify · read-only capability</h2><p className="pulse-note">No product creation, publishing, order placement, or spend is enabled.</p><PulseTable rows={data.shops} columns={[{ key: 'shop_id', label: 'Shop ID' }, { key: 'shop_title', label: 'Store' }, { key: 'sales_channel', label: 'Sales channel' }, { key: 'store_status', label: 'Status' }, { key: 'last_tested_at', label: 'Last test', render: stamp }]} empty="Shop list requires authenticated Printify access." /></section>
            : active === 'RAPID CAMPAIGNS' ? <section className="pulse-panel"><h2>Rapid campaigns · approval required</h2><PulseTable rows={data.campaigns} columns={[{ key: 'campaign_id', label: 'Campaign' }, { key: 'campaign_type', label: 'Type' }, { key: 'state', label: 'State' }, { key: 'publish_state', label: 'Publish' }, { key: 'ray_approval_required', label: 'Ray approval' }]} /></section>
              : active === 'TREND HISTORY' ? <section className="pulse-panel"><h2>Trend history</h2><PulseTable rows={data.history} columns={[{ key: 'trend_id', label: 'Trend' }, { key: 'views', label: 'Views' }, { key: 'velocity', label: 'Velocity' }, { key: 'platform_count', label: 'Platforms' }, { key: 'status', label: 'Status' }, { key: 'observed_at', label: 'Observed', render: stamp }]} /></section>
                : <section className="pulse-panel"><h2>{active.replaceAll('_', ' ').toLowerCase()}</h2><PulseTable rows={data.banks.filter(row => active === 'COMMERCIAL MATCHES' ? ['TREND_TO_REVENUE_BANK', 'PRODUCT_TREND_BANK'].includes(row.bank_name) : active === 'AFFILIATE OPPORTUNITIES' ? row.bank_name === 'AFFILIATE_OPPORTUNITY_BANK' : active === 'MERCH OPPORTUNITIES' ? row.bank_name === 'MERCHANDISE_OPPORTUNITY_BANK' : active === 'VIRAL PATTERNS' ? row.bank_name === 'VIRAL_PATTERN_BANK' : true)} columns={[{ key: 'bank_name', label: 'Bank' }, { key: 'record_id', label: 'Record' }, { key: 'evidence_state', label: 'Evidence' }, { key: 'confidence', label: 'Confidence' }, { key: 'updated_at', label: 'Updated', render: stamp }]} empty="No evidence-qualified matches have been recorded." /></section>
  return <main className="pulse-admin"><header className="pulse-header"><div><span>TREND & MARKET INTELLIGENCE / PULSE</span><h1>What is changing now?</h1><p>Live signals, evidence, commercial matches, and governed handoffs.</p></div><button type="button" onClick={refresh} disabled={loading}><RefreshCw size={15} />{loading ? 'Refreshing' : 'Refresh'}</button></header><nav className="pulse-tabs" aria-label="Pulse workspace tabs">{tabs.map(tab => <button type="button" className={active === tab ? 'active' : ''} onClick={() => setActive(tab)} key={tab}>{tab}</button>)}</nav>{error && <p role="status" className="pulse-error">{error}</p>}{loading ? <p className="pulse-note">Loading persisted Pulse state…</p> : view}</main>
}
