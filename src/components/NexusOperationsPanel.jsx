import React from 'react'

const sections = [
  ['System Status','Local operational cycle available; prohibited external actions blocked.'],
  ['Hermes Nexus Operator','Local/operator brain for status, GoClear, reports, health, review, and blockers.'],
  ['Hermes Alpha Opportunity Brain','Separate no-Supabase brain for SEO, marketing, business, affiliate, and trading research.'],
  ['Research Engine Status','Local sources and reports; safe scan cadence every two working-day hours.'],
  ['SEO / Money Opportunity Engine','Local-report fallback active; GSC and Analytics needed for measured validation.'],
  ['GoClear Readiness Internal Workflow','Hypothetical-profile testing only; draft and Ray Review required.'],
  ['Trading Research / Demo Pipeline','Strategy-to-backtest/demo plan only; no orders or performance claims.'],
  ['Marketing Asset Studio','Four local HTML previews; not published or client-facing approved.'],
  ['Affiliate / API Setup Center','Presence-only connector registry and placeholder link inputs.'],
  ['Ray Review Queue','Draft decisions prepared; approval does not execute an external action.'],
  ['Scheduler / Automation Status','Level 1 local jobs enabled in runner; launchd not loaded.'],
  ['Reports Needed / Generated','Operational evidence is indexed under reports/operations and reports/alpha.'],
  ['Blockers to Full Automation','Credentials, approved accounts, production gates, real-data workflow, and external-action approvals.'],
  ['Next Best Actions','Run the local cycle, review blockers, test dual-brain routing, then inspect marketing previews.']
]

export default function NexusOperationsPanel({ onNavigate }) {
  return <section className="page active simple-page" aria-label="Nexus Operations">
    <div className="page-title"><div><h2>Nexus Operations</h2><p>One internal screen for safe operation, evidence, and blockers</p></div></div>
    <div className="note">INTERNAL OPERATIONS · DRAFT ONLY · RAY REVIEW REQUIRED · CLIENT-FACING DISABLED · NO REAL CLIENT DATA · EXTERNAL ACTIONS APPROVAL-GATED</div>
    <div className="metrics-grid" style={{gridTemplateColumns:'repeat(4, 1fr)'}}>
      <div className="glass panel"><strong>Operational mode</strong><h3>Local / internal</h3></div><div className="glass panel"><strong>External actions</strong><h3>0 enabled</h3></div><div className="glass panel"><strong>Marketing previews</strong><h3>4 drafts</h3></div><div className="glass panel"><strong>Live trading</strong><h3>Blocked</h3></div>
    </div>
    <div style={{display:'grid',gridTemplateColumns:'repeat(2, minmax(0,1fr))',gap:10}}>{sections.map(([title,detail])=><article className="glass panel" key={title}><h3>{title}</h3><p>{detail}</p></article>)}</div>
    <section className="glass panel"><h3>Safe controls</h3><div className="action-row">
      <button type="button" onClick={()=>onNavigate('health')}>View latest status</button><button type="button" onClick={()=>onNavigate('reports')}>View reports</button><button type="button" onClick={()=>onNavigate('hermes')}>View Nexus Hermes brief</button><button type="button" onClick={()=>onNavigate('alpha')}>View Alpha brief</button><button type="button" onClick={()=>onNavigate('rayreview')}>Create Ray Review draft</button><a href="/marketing-previews/index.html" target="_blank" rel="noreferrer">View marketing samples</a>
    </div></section>
    <section className="glass panel"><h3>Disabled controls</h3><div className="action-row">{['Send','Publish','Charge','Trade live','Submit dispute','Submit lender application','Submit grant application','Approve client-facing','Use real client data'].map(x=><button type="button" disabled key={x}>{x}</button>)}</div></section>
  </section>
}
