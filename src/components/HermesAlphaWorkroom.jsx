import React from 'react'
import { runAlphaPhase1Evaluations, summarizeAlphaEvaluations } from '../hermes/alpha/alphaEvaluationHarness'

const roomCards = [
  ['Opportunity Desk', 'Score mock opportunity fixtures and propose reversible experiments.'],
  ['Marketing Asset Studio', 'Preview draft-only campaign and creative concepts.'],
  ['Affiliate / Offer Lab', 'Evaluate mock referral ideas with disclosure requirements.'],
  ['Newsletter Studio', 'Prepare evaluation-only newsletter drafts.'],
  ['Landing Page Studio', 'Prepare evaluation-only landing-page drafts.'],
  ['Social Content Studio', 'Prepare Facebook/social drafts with publishing disabled.'],
  ['Trading Research Lab', 'Score strategy research, backtest plans, and risk reviews.'],
  ['Oanda Demo Trading Desk', 'Future / disabled — no connection and no trades.'],
]

const reports = [
  'alpha_phase_1_preflight_status.md',
  'alpha_phase_1_evaluation_harness_report.md',
  'alpha_phase_1_evaluation_summary.md',
  'alpha_phase_1_workroom_ui_report.md',
  'alpha_research_file_adapter_v1_foundation.md',
  'alpha_research_file_adapter_allowed_sources.md',
  'alpha_research_file_adapter_validation_report.md',
  'alpha_ray_review_bridge_contract.md',
  'alpha_safety_guard_result.md',
  'no_supabase_guard_result.md',
  'alpha_next_step_recommendation.md',
]

function Badge({ children, tone = 'blue' }) {
  return <span className={`pill pill-${tone}`} style={{ marginRight: 6, marginBottom: 6 }}>{children}</span>
}

export default function HermesAlphaWorkroom({ onOpenReports }) {
  const results = runAlphaPhase1Evaluations()
  const summary = summarizeAlphaEvaluations(results)
  return <div className="nxos-stack" data-testid="hermes-alpha-workroom">
    <section className="glass panel" style={{ borderColor: '#7857d8' }}>
      <div className="between">
        <div>
          <p className="nx-muted" style={{ margin: 0 }}>SEPARATE FROM NEXUS HERMES</p>
          <h2 style={{ margin: '4px 0' }}>Hermes Alpha Workroom</h2>
          <p>Offline research, opportunity, marketing, and trading-research evaluation workspace.</p>
        </div>
        <Badge tone="violet">Phase 1 Evaluation</Badge>
      </div>
      <div>
        <Badge tone="amber">Offline</Badge><Badge tone="amber">Draft Only</Badge><Badge tone="green">No Supabase</Badge>
        <Badge tone="blue">Mock Provider Only</Badge><Badge tone="red">External Actions Disabled</Badge>
        <Badge tone="amber">No Oanda Connected</Badge><Badge tone="red">No Publishing / Sending / Charging / Trading</Badge>
      </div>
    </section>

    <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
      <article className="metric glass"><div><div className="muted">Evaluation fixtures</div><div className="metric-value">{summary.total}</div><small>Mock/evaluation-only</small></div></article>
      <article className="metric glass"><div><div className="muted">Passed</div><div className="metric-value green-text">{summary.passed}</div><small>{summary.failed} failed</small></div></article>
      <article className="metric glass"><div><div className="muted">Safety blocks</div><div className="metric-value">{summary.blocked}</div><small>Expected refusal</small></div></article>
      <article className="metric glass"><div><div className="muted">External adapters</div><div className="metric-value">0</div><small>None touched</small></div></article>
    </div>

    <section className="glass panel">
      <h3>Alpha Rooms — Preview Only</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: 10 }}>
        {roomCards.map(([title, description]) => <article className="nx-soft" key={title} style={{ padding: 12 }}>
          <div className="between"><strong>{title}</strong><Badge tone={title.includes('Oanda') ? 'red' : 'blue'}>{title.includes('Oanda') ? 'Disabled' : 'Preview'}</Badge></div>
          <p className="nx-muted">{description}</p>
          <button type="button" disabled title="Phase 1 preview only">No execution available</button>
        </article>)}
      </div>
    </section>

    <div className="command-layout">
      <section className="glass panel">
        <h3>Evaluation Results</h3>
        {results.map((result) => <div className="nx-soft feedback-row" key={result.fixtureName} data-testid="alpha-evaluation-result">
          <div><strong>{result.fixtureName}</strong><small>{result.inputCategory} · {result.routeSelected} · {String(result.scoreOrRating)}</small></div>
          <Badge tone={result.pass ? 'green' : 'red'}>{result.pass ? 'Pass' : 'Fail'}</Badge>
        </div>)}
      </section>
      <aside className="side-stack">
        <section className="glass panel">
          <h3>Ray Review Draft Proposal</h3>
          <p><strong>Status:</strong> Conversation draft only</p>
          <p>Alpha may propose a scored experiment. It cannot save, submit, approve, or execute it.</p>
          <button type="button" disabled>Draft preview only</button>
        </section>
        <section className="glass panel">
          <h3>Alpha Reports</h3>
          {reports.map((name) => <button type="button" key={name} onClick={onOpenReports} className="nx-soft" style={{ display: 'block', width: '100%', marginBottom: 5, textAlign: 'left' }} title={`reports/hermes_alpha/${name}`}>{name}</button>)}
        </section>
      </aside>
    </div>
  </div>
}
