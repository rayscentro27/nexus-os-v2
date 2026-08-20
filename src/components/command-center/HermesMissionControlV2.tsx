import { hermesMissionControlData as data } from '../../data/hermesMissionControlData';

type SectionCardProps = {
  title: string;
  status: string;
  what: string;
  changed: string;
  blocked: string;
  next: string;
  decision: string;
  children?: React.ReactNode;
};

function Status({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const tone = ['PASS', 'HEALTHY', 'AVAILABLE', 'SUCCESS'].includes(normalized) ? 'good' : ['BLOCKED', 'AUTH_BLOCKED', 'PARTIAL', 'UNKNOWN', 'UNAVAILABLE', 'INSTALLED_UNPROVEN', 'RATE_LIMITED', 'NOT_INSTALLED'].includes(normalized) ? 'warn' : 'info';
  return <span className={`hermes-mc-status ${tone}`}>{value}</span>;
}

function SectionCard({ title, status, what, changed, blocked, next, decision, children }: SectionCardProps) {
  return (
    <article className="hermes-mc-card" data-testid={`mission-card-${title.toLowerCase()}`}>
      <header className="hermes-mc-card-head"><h3>{title}</h3><Status value={status} /></header>
      <div className="hermes-mc-answers">
        <div><b>What is this?</b><span>{what}</span></div>
        <div><b>What changed?</b><span>{changed}</span></div>
        <div><b>What is blocked?</b><span>{blocked}</span></div>
        <div><b>What happens next?</b><span>{next}</span></div>
        <div><b>Ray decision?</b><span>{decision}</span></div>
      </div>
      {children && <div className="hermes-mc-card-detail">{children}</div>}
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="hermes-mc-metric"><span>{label}</span><strong>{String(value)}</strong></div>;
}

export function HermesMissionControlV2() {
  const workers = data.workers;
  const workerRows = ['codex', 'opencode', 'mimo', 'openhands', 'local_python'].map((id) => workers.find((worker) => worker.id === id) ?? { id, status: 'UNKNOWN', reason: 'No current record' });
  return (
    <section className="hermes-mc-v2" data-testid="hermes-mission-control-v2">
      <div className="hermes-mc-hero">
        <div>
          <div className="hermes-mc-eyebrow">Hermes modernization · read-only evidence view</div>
          <h1>Mission Control V2</h1>
          <p>Actual Phase 9 pipeline records, runtime loop evidence, worker health, cost, and blockers. No provider actions are available here.</p>
        </div>
        <div className="hermes-mc-hero-state"><Status value={data.finalStatus} /><span>Resume: {data.resumePoint}</span></div>
      </div>

      <div className="hermes-mc-overview">
        <Metric label="Current phase" value={data.phase} />
        <Metric label="Active opportunities" value={data.activeOpportunityCount} />
        <Metric label="Opportunity status" value={data.opportunity.status} />
        <Metric label="Base score" value={data.opportunity.base_score} />
        <Metric label="Pending approvals" value={data.approvals.pending} />
        <Metric label="System health" value={data.loops.systemStatus} />
        <Metric label="Scheduler" value={data.runtimeSnapshot.scheduler_health.status} />
        <Metric label="Last dispatch" value={data.runtimeSnapshot.scheduler_health.last_dispatch} />
        <Metric label="Next dispatch" value={data.runtimeSnapshot.scheduler_health.next_dispatch} />
        <Metric label="Morning Brief" value={data.runtimeSnapshot.morning_brief.status} />
      </div>

      <div className="hermes-mc-grid-v2">
        <SectionCard title="TODAY" status={data.finalStatus} what="The current modernization checkpoint and the one proven opportunity slice." changed={`Phase 9 recorded ${data.opportunity.title}; Mission Control is the next resume point.`} blocked={data.builder.status === 'PARTIAL' ? 'Real coding-provider authentication is not proven.' : 'UNKNOWN'} next="Review this evidence surface, then continue with visibility improvements only." decision="No approval is requested to view these records." />

        <SectionCard title="OPPORTUNITIES" status={data.opportunity.status} what={`${data.activeOpportunityCount} canonical active opportunity: ${data.opportunity.title} (${data.opportunity.category}).`} changed={`Base score ${data.opportunity.base_score}; confidence ${data.opportunity.confidence}; risk ${data.opportunity.risk}.`} blocked="No approval to advance beyond PILOT_PROPOSED is recorded." next={data.opportunity.recommended_next_action} decision="Yes — authorize any future pilot advancement explicitly." />

        <SectionCard title="RESEARCH" status={data.research.status} what="Alpha’s Nexus-first public-information evidence set." changed={`${data.research.source_records_collected} source records normalized; ${data.research.duplicates_removed} duplicates removed; ${data.research.evidence_count} compact evidence retained.`} blocked="No live re-research is represented in this view." next="Reuse unchanged evidence until a material delta appears." decision="No — the evidence is already classified and provenance-linked." >
          <div className="hermes-mc-metrics"><Metric label="AI calls" value={data.research.ai_calls} /><Metric label="Evidence" value={data.research.evidence_count} /><Metric label="Dedupe" value={data.research.duplicates_removed} /></div>
        </SectionCard>

        <SectionCard title="CREATIVE" status={data.creative.status} what="Evidence-driven Creative Lab output for the selected opportunity." changed={`${data.creative.territory_count} distinct territories were generated; selected territory is ${data.creative.selected_territory}.`} blocked="Production marketing assets and publishing remain out of scope." next="Use the selected territory only as an internal build direction." decision="No — creative exploration is complete for this pilot." />

        <SectionCard title="BUILDERS" status={data.builder.status} what="Provider-neutral builder routing and the internal proof artifact." changed={`Worker used: ${data.builder.workerUsed}; verification ${data.builder.verification}; ${data.builder.testsPassed} tests passed.`} blocked="Real worker leg is blocked; no provider login/configuration was attempted." next="Obtain separate authorization before proving a real coding worker." decision="Yes — decide whether to authorize a future provider-auth proof." >
          <div className="hermes-mc-worker-table">{workerRows.map((worker) => <div className="hermes-mc-worker-row" key={worker.id}><b>{worker.id === 'local_python' ? 'Internal worker' : worker.id}</b><Status value={worker.status} /><span>{worker.reason}</span></div>)}</div>
        </SectionCard>

        <SectionCard title="LOOPS" status={data.loops.systemHealth} what="The existing deterministic system-health loop and four controlled Phase 14 business loops." changed={`Last recorded run ${data.loops.lastUpdated}; ${data.loops.businessLoops.filter((loop) => loop.status === 'PASS' || loop.status === 'NO_CHANGE').length} business loop proofs are verified; ${data.loops.activeRuns} active run(s), ${data.loops.failedRuns} failed run(s).`} blocked="Unchanged inputs stop with NO_CHANGE; external actions, publishing, outreach, and paid actions remain blocked." next="Wait for a material source delta or the next eligible bounded schedule, then review the internal recommendation." decision="No — this card is observational; Ray approval is required for external action." >
          <div className="hermes-mc-worker-table">{data.loops.businessLoops.map((loop) => <div className="hermes-mc-worker-row" key={loop.loopId}><b>{loop.loopId}</b><Status value={loop.status} /><span>value {JSON.stringify(loop.value)} · cost {String(loop.cost)} · AI calls {String(loop.aiCalls)} · verifier {String(loop.verifier)}</span></div>)}</div>
        </SectionCard>

        <SectionCard title="APPROVALS" status={String(data.approvals.pending)} what="Pending approval count reported by system_health_loop." changed={`${data.approvals.pending} pending approval(s) are visible from ${data.approvals.source}.`} blocked="This page cannot approve, reject, or execute anything." next="Open the existing Ray Review flow if a decision is required." decision="Yes — only Ray can decide pending governed actions." />

        <SectionCard title="COST" status="$0.00" what="Phase 9 token, provider-cost, and local-compute accounting." changed={`Deterministic execution ${data.execution.deterministicRatio}; AI execution ${data.execution.aiRatio}.`} blocked="Provider usage is absent because no AI/provider call was made." next="Continue compact structured deltas and deterministic-first processing." decision="No — no spend occurred." >
          <div className="hermes-mc-metrics"><Metric label="Zero-token executions" value={data.execution.zeroTokenExecutions} /><Metric label="Input tokens" value={data.execution.inputTokens} /><Metric label="Output tokens" value={data.execution.outputTokens} /><Metric label="Provider USD" value={`$${data.execution.providerCostUsd.toFixed(2)}`} /><Metric label="Local compute" value={data.execution.localComputeExecutions} /></div>
        </SectionCard>

        <SectionCard title="SYSTEM" status={data.loops.systemStatus} what="Read-only modernization system and pipeline health summary." changed={`Verification ${data.builder.verification}; protected paths PASS; client portal and production Telegram unchanged.`} blocked={data.builder.status === 'PARTIAL' ? 'Real worker authentication remains blocked.' : 'UNKNOWN'} next={`Resume at ${data.resumePoint}.`} decision="No — Mission Control only visualizes proven records." />
      </div>
      <div className="hermes-mc-source">Source of truth: <code>reports/hermes_modernization/end_to_end_pilot.json</code>, <code>reports/hermes_modernization/state.json</code>, and <code>data/runtime/nexus_loops/loop_state.json</code>. Source commit: {data.sourceCommit}.</div>
    </section>
  );
}
