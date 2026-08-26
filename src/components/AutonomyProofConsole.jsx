import React, { useEffect, useState } from 'react'

const UNKNOWN = { system: { overall_status: 'UNKNOWN', production_sha: 'UNKNOWN', last_natural_cycle: 'UNKNOWN', next_expected_cycle: 'UNKNOWN' }, proof: { coverage: 0, watchdog: 'UNKNOWN', stalled: [], recovering: [] }, preflight: { registered: 0, attempted: 0, verified: 0, failed: [], ready_tonight: false }, active_jobs: [], campaign: { status: 'UNKNOWN', current_wave: 'UNKNOWN', current_objective: 'UNKNOWN' }, morning_report: { status: 'UNKNOWN' } }

export default function AutonomyProofConsole() {
  const [telemetry, setTelemetry] = useState(UNKNOWN)
  const [source, setSource] = useState('unavailable')
  useEffect(() => {
    let active = true
    fetch('/runtime/nexus-live-telemetry.json', { headers: { accept: 'application/json' }, cache: 'no-store' })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('telemetry unavailable')))
      .then((value) => { if (active) { setTelemetry(value); setSource(value.source || 'canonical runtime') } })
      .catch(() => { if (active) setSource('unavailable — current truth is UNKNOWN') })
    return () => { active = false }
  }, [])
  const system = telemetry.system || UNKNOWN.system
  const proof = telemetry.proof || UNKNOWN.proof
  const preflight = telemetry.preflight || UNKNOWN.preflight
  return <section className="nx2-proof-console" data-testid="autonomy-proof-console">
    <div className="nx2-panel-head"><div><div className="nx2-eyebrow">LIVE OPERATIONAL TRUTH</div><h3>Autonomy / Proof Console</h3></div><span className="nx2-badge">{system.overall_status}</span></div>
    <p className="nx2-muted">Source: {source}. Registry presence and old reports are not runtime proof.</p>
    <div className="nx2-stat-grid">
      <div><span>Production SHA</span><strong>{system.production_sha}</strong></div><div><span>Last natural cycle</span><strong>{system.last_natural_cycle}</strong></div><div><span>Proof coverage</span><strong>{Math.round((proof.coverage || 0) * 100)}%</strong></div><div><span>Watchdog</span><strong>{proof.watchdog}</strong></div>
      <div><span>Preflight</span><strong>{preflight.verified}/{preflight.attempted}</strong></div><div><span>Active jobs</span><strong>{(telemetry.active_jobs || []).filter((job) => job.runtime_state === 'RUNNING').length}</strong></div><div><span>Campaign</span><strong>{(telemetry.campaign || {}).status || 'UNKNOWN'}</strong></div><div><span>Morning report</span><strong>{(telemetry.morning_report || {}).status || 'UNKNOWN'}</strong></div>
    </div>
    {preflight.failed?.length > 0 && <p className="nx2-danger">Failed evidence: {preflight.failed.join(', ')}</p>}
    {(proof.stalled?.length > 0 || proof.recovering?.length > 0) && <p className="nx2-muted">Stalled: {proof.stalled.join(', ') || 'none'} · Recovering: {proof.recovering.join(', ') || 'none'}</p>}
  </section>
}
