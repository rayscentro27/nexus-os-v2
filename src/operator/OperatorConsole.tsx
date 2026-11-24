import { useEffect, useMemo, useState, type ReactNode } from 'react';
import CreativeReviewStudio from '../components/CreativeReviewStudio';
import './operator.css';

type OperatorSection = 'home' | 'nova' | 'review' | 'creative' | 'business' | 'research' | 'trading' | 'operations' | 'finance' | 'system';

const NAV: Array<{ id: OperatorSection; label: string; eyebrow: string }> = [
  { id: 'home', label: 'Home', eyebrow: 'COMMAND' },
  { id: 'nova', label: 'Nova', eyebrow: 'EXECUTIVE' },
  { id: 'review', label: 'Review', eyebrow: 'DECISIONS' },
  { id: 'creative', label: 'Creative', eyebrow: 'PRODUCTION' },
  { id: 'business', label: 'Business', eyebrow: 'OPPORTUNITIES' },
  { id: 'research', label: 'Research', eyebrow: 'ALPHA' },
  { id: 'trading', label: 'Trading', eyebrow: 'PRACTICE ONLY' },
  { id: 'operations', label: 'Operations', eyebrow: 'WORK' },
  { id: 'finance', label: 'Finance', eyebrow: 'CFO / FINOPS' },
  { id: 'system', label: 'System', eyebrow: 'HEALTH' },
];

const FOUNDATIONS: Record<Exclude<OperatorSection, 'home' | 'creative'>, { title: string; description: string; status: string; detail: string }> = {
  nova: { title: 'Nova', description: 'Executive interpretation and morning briefs will live here.', status: 'FOUNDATION', detail: 'Use the existing Nova/Hermes surfaces while this canonical operator area is being connected.' },
  review: { title: 'Review', description: 'A shared decision surface for internal review lanes.', status: 'CREATIVE ACTIVE', detail: 'Creative Review is the first connected lane. Other review types remain intentionally undisplayed until backed by live data.' },
  business: { title: 'Business', description: 'Opportunities, ventures, and performance context.', status: 'FOUNDATION', detail: 'The existing WP8.8 opportunity loop remains authoritative; this console does not duplicate its state.' },
  research: { title: 'Research', description: 'Alpha discovery and evidence chains.', status: 'FOUNDATION', detail: 'Alpha remains the research authority. This route will expose synthesized findings when the read adapter is connected.' },
  trading: { title: 'Trading', description: 'Practice-only market operations and evidence.', status: 'PRACTICE / GOVERNED', detail: 'OANDA authority is unchanged. No execution controls are exposed in this foundation.' },
  operations: { title: 'Operations', description: 'Work orders, queues, and blocked work.', status: 'FOUNDATION', detail: 'No fabricated work count is shown. The live Creative work-order adapter is the next integration seam.' },
  finance: { title: 'Finance', description: 'Cost, resource consumption, revenue truth, and economic preflight.', status: 'CFO / ADVISORY', detail: 'Finance measures and challenges economics; it cannot purchase, pay, change billing, authorize ad spend, or fund live trading.' },
  system: { title: 'System', description: 'Provider health and authority boundaries.', status: 'LIVE STATUS', detail: 'Creative model: gpt-5.5 via existing Hermes route. Creative storage: private Supabase with verified remote objects. Oracle Ollama: degraded optional fallback.' },
};

function sectionFromPath(): OperatorSection {
  const part = window.location.pathname.split('/').filter(Boolean)[1];
  return NAV.some((x) => x.id === part) ? part as OperatorSection : 'home';
}

function Status({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'good' | 'warn' | 'neutral' }) {
  return <span className={`operator-status operator-status-${tone}`}><span aria-hidden="true" />{children}</span>;
}

function Home({ assetCount, provider, onOpenCreative }: { assetCount: number; provider: string; onOpenCreative: () => void }) {
  return <>
    <div className="operator-page-head"><div><div className="operator-eyebrow">NEXUS OPERATOR CONSOLE</div><h1>Keep the system moving.</h1><p>One calm surface for attention, decisions, review, and next actions.</p></div><Status tone="good">Internal operations · governed</Status></div>
    <section className="operator-attention" aria-labelledby="attention-title"><div className="operator-section-heading"><div><span className="operator-eyebrow">RIGHT NOW</span><h2 id="attention-title">Needs your attention</h2></div><span className="operator-muted">No fabricated alerts</span></div><div className="operator-attention-grid"><article className="operator-card operator-card-focus"><span className="operator-card-label">CREATIVE REVIEW</span><strong>{assetCount} remote assets indexed</strong><p>Supabase-backed Creative artifacts are available for internal review. Open the queue to inspect proxies, screenshots, and version history.</p><button className="operator-primary" onClick={onOpenCreative}>Open Creative Review</button></article><article className="operator-card"><span className="operator-card-label">MODEL ROUTE</span><strong>Available</strong><p>gpt-5.5 through the active Hermes runtime completed the last bounded Creative loop.</p><Status tone="good">Working route</Status></article><article className="operator-card"><span className="operator-card-label">STORAGE</span><strong>{provider === 'supabase_storage' ? 'Remote verified' : 'Review path available'}</strong><p>Private media uses proxy-first review. Approval remains separate from publication.</p><Status tone={provider === 'supabase_storage' ? 'good' : 'warn'}>{provider === 'supabase_storage' ? 'Supabase Storage' : 'Degraded'}</Status></article></div></section>
    <section className="operator-columns"><article className="operator-panel"><div className="operator-section-heading"><div><span className="operator-eyebrow">OPERATING PULSE</span><h2>Active work</h2></div></div><div className="operator-empty"><strong>Live work-order feed not connected</strong><span>The console will show real assignments here once the read adapter is connected.</span></div></article><article className="operator-panel"><div className="operator-section-heading"><div><span className="operator-eyebrow">NEXT</span><h2>Recommended actions</h2></div></div><ol className="operator-action-list"><li><b>Review Creative outputs</b><span>Decide which internal asset needs revision or approval.</span></li><li><b>Keep Oracle fallback degraded</b><span>Do not spend or reconfigure while the proven Hermes route is healthy.</span></li><li><b>Connect review aggregation</b><span>Expose other governed review lanes only when backed by live state.</span></li></ol></article></section>
  </>;
}

function Foundation({ section }: { section: Exclude<OperatorSection, 'home' | 'creative'> }) {
  const item = FOUNDATIONS[section];
  return <div className="operator-foundation"><div className="operator-eyebrow">{item.status}</div><h1>{item.title}</h1><p className="operator-lede">{item.description}</p><div className="operator-foundation-note"><Status tone={section === 'trading' ? 'warn' : 'neutral'}>{item.status}</Status><p>{item.detail}</p></div><div className="operator-boundary"><b>Operator principle</b><span>Show what Nexus knows, what is blocked, and what decision is next. Never fill a missing feed with demo production data.</span></div></div>;
}

function ResearchCases() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState(false);
  useEffect(() => { fetch('/runtime/research-cases.json').then((r) => r.ok ? r.json() : Promise.reject()).then(setData).catch(() => setError(true)); }, []);
  const cases = Array.isArray(data?.cases) ? data.cases : [];
  return <div className="operator-research">
    <div className="operator-page-head"><div><div className="operator-eyebrow">RESEARCH / OBJECTIVE DEVELOPMENT</div><h1>What is Nexus trying to figure out?</h1><p>Evidence accumulates around an objective. Missing evidence stays visible as a question and a next step.</p></div><Status tone={error ? 'warn' : 'good'}>{error ? 'Case read model unavailable' : `${cases.length} active cases`}</Status></div>
    {data?.metrics && <div className="operator-research-metrics">{[
      ['Cases advanced', data.metrics.cases_advanced], ['Recommendations ready', data.metrics.cases_recommendation_ready],
      ['Follow-up questions answered', data.metrics.followup_questions_answered], ['Multi-source syntheses', data.metrics.multi_source_syntheses],
      ['Fully specified strategies', data.metrics.strategies_fully_specified], ['Opportunities developed', data.metrics.business_opportunities_developed],
    ].map(([label, value]) => <article key={String(label)}><span>{label}</span><b>{value ?? 'UNKNOWN'}</b></article>)}</div>}
    {error ? <div className="operator-foundation-note"><p>The Research case read model has not been published yet. The live Research runtime remains authoritative.</p></div> : !cases.length ? <div className="operator-foundation-note"><p>No active objective cases are in the current bounded read model.</p></div> : <div className="operator-research-list">{cases.map((item: any) => {
      const latestRecommendation = item.recommendations?.[item.recommendations.length - 1];
      return <article className="operator-research-case" key={item.case_id}>
        <div className="operator-research-case-head"><div><span className="operator-eyebrow">{item.objective_family || 'RESEARCH OBJECTIVE'}</span><h2>{item.objective || item.primary_question || item.case_id}</h2></div><Status tone={item.requires_ray ? 'warn' : 'neutral'}>{item.status || 'UNKNOWN'}</Status></div>
        <div className="operator-research-meta"><span>Owner <b>{item.owner_department || 'RESEARCH'}</b></span><span>Promise <b>{item.promise_score ?? 'UNASSESSED'}</b></span><span>Evidence <b>{item.source_count ?? 0} sources · {item.source_class_count ?? 0} classes</b></span><span>Ray <b>{item.requires_ray ? 'REQUIRED' : 'NOT REQUIRED'}</b></span></div>
        {item.business_or_nexus_goal && <p className="operator-research-goal">Company goal: {item.business_or_nexus_goal}</p>}
        {item.primary_question && <section><h3>Primary question</h3><p>{item.primary_question}</p></section>}
        {item.notebook_playbook && <section><h3>Notebook playbook · {item.notebook_playbook.case_type}</h3><p>Notebook {item.notebook_playbook.notebook_id || item.notebook_workspace?.notebook_id || 'UNBOUND'} · {item.notebook_playbook.questions_asked ?? 0} asked · {item.notebook_playbook.questions_answered ?? 0} answered · {item.notebook_playbook.questions_open ?? 0} open · {item.notebook_playbook.new_sources_added ?? 0} new sources</p>{item.notebook_playbook.current_gaps?.length > 0 && <><b>Current gaps</b><ul>{item.notebook_playbook.current_gaps.map((gap: string) => <li key={gap}>{gap}</li>)}</ul></>}<p>Recommendation: {item.notebook_playbook.current_recommendation || 'PENDING'} · handoff packet: {item.notebook_playbook.handoff_packet_status || 'PENDING'} · destination: {item.notebook_playbook.handoff_destination || 'UNASSIGNED'}</p><p>Development packet ready: {item.notebook_playbook.ready_for_handoff ? 'YES' : 'NO'} (department review only)</p><b>Next research action</b><p>{item.next_research_action || 'UNAVAILABLE'}</p></section>}
        <div className="operator-research-columns"><section><h3>Open questions <small>{item.open_questions?.length || 0}</small></h3>{item.open_questions?.length ? <ul>{item.open_questions.map((q: any) => <li key={q.question_id || q.question}><b>{q.question}</b>{q.why_it_matters && <small>{q.why_it_matters}</small>}</li>)}</ul> : <p>No open questions.</p>}</section><section><h3>What is known <small>{item.answered_questions?.length || 0} answered</small></h3>{item.answered_questions?.length ? <ul>{item.answered_questions.map((q: any) => <li key={q.question_id || q.question}><b>{q.question}</b><small>{q.answer}</small></li>)}</ul> : <p>No case questions have been closed by direct evidence yet.</p>}</section></div>
        {item.hypotheses?.length > 0 && <section><h3>Current hypotheses</h3><ul>{item.hypotheses.map((h: any) => <li key={h.hypothesis_id}><b>{h.statement}</b><small>{h.status || 'PROPOSED'} · {h.complete_rules ? 'complete rules' : 'incomplete; needs departmental development'}</small></li>)}</ul></section>}
        {item.development_profile?.required_before_independent_test?.length > 0 && <section><h3>Required before independent testing</h3><p>{item.development_profile.required_before_independent_test.join(' · ')}</p></section>}
        {latestRecommendation && <section className="operator-research-recommendation"><h3>Recommendation · {latestRecommendation.recommendation}</h3><p>{latestRecommendation.recommendation_reason}</p><small>Next: {latestRecommendation.next_action} · confidence {latestRecommendation.confidence ?? 'UNKNOWN'}</small></section>}
        {item.sources?.length > 0 && <section><h3>Evidence sources</h3><ul className="operator-research-sources">{item.sources.map((source: any) => <li key={source.identity || source.source_id || source.url}><a href={source.url || source.source_url} target="_blank" rel="noreferrer">{source.title || source.url || source.source_id}</a><small>{source.source_class || 'UNKNOWN'} · {source.evidence_role || source.extraction_status || 'source attached'}</small></li>)}</ul></section>}
        <div className="operator-research-next"><b>Next action</b><span>{item.next_research_action || 'UNAVAILABLE'}</span><small>Depth used {JSON.stringify(item.depth_used || {})} / budget {JSON.stringify(item.depth_budget || {})}</small></div>
      </article>;
    })}</div>}
    <div className="operator-boundary"><b>Research boundaries</b><span>Findings and recommendations are evidence-linked. Department handoff does not close a case. Live trading, external spend, and production actions remain governed elsewhere.</span></div>
  </div>;
}

function FinanceOverview() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { fetch('/runtime/finance-preflight.json').then(r => r.ok ? r.json() : null).then(setData).catch(() => setData(null)); }, []);
  const ledger = data?.daily_ledger;
  return <div className="operator-foundation finance-overview"><div className="operator-eyebrow">CFO / ADVISORY GOVERNANCE</div><h1>Know what Nexus costs.</h1><p className="operator-lede">Actual receipts, explicit estimates, and bounded preflight before optional consumption.</p><div className="finance-authority-strip"><Status tone="good">Read / measure / recommend</Status><Status tone="warn">No purchase, payment, billing, or live-capital authority</Status></div><div className="operator-finance-grid">{[['Cash spent', ledger?.cash_spent ?? 'UNKNOWN', 'ACTUAL RECEIPTS'], ['Revenue received', ledger?.revenue_received ?? 'UNKNOWN', 'RECEIVED ONLY'], ['Free credit', ledger?.free_credit_consumed ?? 'UNKNOWN', 'MEASURED / UNKNOWN'], ['Net contribution', ledger?.net_contribution ?? 'UNKNOWN', 'NOT PROFIT ACCOUNTING']].map(([label, value, note]) => <article className="operator-finance-metric" key={label}><span className="operator-card-label">{label}</span><strong>{typeof value === 'number' ? `$${value.toFixed(2)}` : value}</strong><small className="operator-finance-note">{note}</small></article>)}</div><div className="operator-foundation-note"><Status tone="warn">Campaign preflight</Status><p>{data?.campaign?.recommendation || 'No preflight artifact is available yet.'} · mobile-detailing demand, CAC, conversion, and retention remain UNKNOWN; no revenue is fabricated.</p></div><div className="operator-foundation-note"><Status tone="warn">Trading preflight</Status><p>{data?.trading?.economic_state || 'INSUFFICIENT_DATA'} · gross/net expectancy and capital remain explicit; win rate is not used alone.</p></div><div className="operator-foundation-note"><Status tone="neutral">Resource inventory</Status><p>{(data?.resource_inventory || []).map((item: any) => `${item.provider}: ${item.state} (${item.scarcity})`).join(' · ') || 'No current inventory artifact.'}</p></div></div>;
}

export default function OperatorConsole({ email }: { email: string | null }) {
  const [section, setSection] = useState<OperatorSection>(sectionFromPath);
  const [library, setLibrary] = useState<{ assets?: Array<{ asset_id: string }>; provider?: string }>({});
  useEffect(() => { fetch('/creative-library/index.json').then((r) => r.ok ? r.json() : {}).then(setLibrary).catch(() => setLibrary({})); const onPop = () => setSection(sectionFromPath()); window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  const assetCount = library.assets?.length || 0;
  const active = useMemo(() => NAV.find((x) => x.id === section) || NAV[0], [section]);
  function navigate(next: OperatorSection) { setSection(next); window.history.pushState({}, '', next === 'home' ? '/operator' : `/operator/${next}`); window.scrollTo({ top: 0, behavior: 'smooth' }); }
  return <div className="operator-shell"><aside className="operator-sidebar"><div className="operator-brand"><span className="operator-mark">N</span><div><b>NEXUS</b><small>OPERATOR CONSOLE</small></div></div><div className="operator-side-label">OPERATE</div><nav aria-label="Operator console navigation">{NAV.map((item) => <button key={item.id} className={section === item.id ? 'active' : ''} onClick={() => navigate(item.id)}><span className="operator-nav-glyph" aria-hidden="true">{item.id === 'home' ? '⌂' : item.id === 'system' ? '◌' : item.id === 'finance' ? '$' : '•'}</span><span><b>{item.label}</b><small>{item.eyebrow}</small></span></button>)}</nav><div className="operator-sidebar-foot"><Status tone="good">Internal only</Status><small>Publication, spend, and outreach remain governed elsewhere.</small></div></aside><main className="operator-main"><header className="operator-topbar"><div><span className="operator-breadcrumb">NEXUS / {active.label.toUpperCase()}</span><span className="operator-topbar-title">{active.label}</span></div><div className="operator-topbar-right"><span className="operator-user">{email || 'Approved operator'}</span><Status tone="good">Session protected</Status></div></header><div className="operator-content">{section === 'home' && <Home assetCount={assetCount} provider={library.provider || 'local_review_path'} onOpenCreative={() => navigate('creative')} />}{section === 'creative' && <><div className="operator-page-head operator-page-head-compact"><div><div className="operator-eyebrow">PRODUCTION / CREATIVE</div><h1>Choose the next move.</h1><p>Review remote-backed Creative assets, compare versions, and record the next internal decision.</p></div><Status tone={library.provider === 'supabase_storage' ? 'good' : 'warn'}>{library.provider === 'supabase_storage' ? 'Remote media verified' : 'Review path degraded'}</Status></div><CreativeReviewStudio /></>}{section === 'research' ? <ResearchCases /> : section === 'finance' ? <FinanceOverview /> : section !== 'home' && section !== 'creative' && <Foundation section={section} />}</div></main></div>;
}
