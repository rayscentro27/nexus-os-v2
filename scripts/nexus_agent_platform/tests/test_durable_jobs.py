from __future__ import annotations
import threading
from datetime import timedelta
from pathlib import Path

import pytest

from nexus_agent_platform.durable_jobs import (
    DurableJobStore, JobError, create_next_job, dispatch_once, handler_route,
    resource_pressure, utcnow, HEAVY_MARKERS,
)


def store_at(tmp_path: Path) -> DurableJobStore:
    return DurableJobStore(tmp_path / "queue.sqlite3")


def test_atomic_claim_and_duplicate_claim_rejection(tmp_path):
    store = store_at(tmp_path); job = store.enqueue("RESEARCH", "RESEARCH_GAP_VERIFY")
    barrier = threading.Barrier(2); results = []
    def claimant(name):
        barrier.wait(); results.append(store.claim(name))
    threads = [threading.Thread(target=claimant,args=(f"worker-{n}",)) for n in range(2)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sum(value is not None for value in results) == 1
    with store._connect() as db: assert db.execute("select count(*) from jobs where job_id=? and state='CLAIMED'",(job.job_id,)).fetchone()[0] == 1


def test_lease_recovery_backoff_reclaim_and_single_receipt(tmp_path):
    store=store_at(tmp_path); job=store.enqueue("RESEARCH","RESEARCH_GAP_VERIFY",max_attempts=3); now=utcnow()
    claimed=store.claim("worker-a",lease_seconds=15,now=now); store.transition(job.job_id,"RUNNING",worker_id="worker-a",lease_seconds=15)
    assert store.recover_expired(now+timedelta(seconds=20)) == 1
    assert store.get(job.job_id).state == "FAILED_RETRYABLE"
    assert store.claim("worker-b",now=now+timedelta(seconds=20)) is None
    retry_time=now+timedelta(seconds=100); reclaimed=store.claim("worker-b",now=retry_time)
    assert reclaimed and reclaimed.attempt_count == 2
    store.transition(job.job_id,"RUNNING",worker_id="worker-b")
    receipt=store.complete(job.job_id,"worker-b",{"ok":True})
    assert store.complete(job.job_id,"worker-b",{"ok":True}) == receipt
    assert store.get(job.job_id).state == "COMPLETED"
    with store._connect() as db: assert db.execute("select count(*) from receipts where job_id=?",(job.job_id,)).fetchone()[0] == 1
    assert store.claim("worker-c") is None


def test_bounded_retry_becomes_blocked(tmp_path):
    store=store_at(tmp_path); job=store.enqueue("RESEARCH","RESEARCH_GAP_VERIFY",max_attempts=1)
    claim=store.claim("w"); result=store.transition(job.job_id,"FAILED_RETRYABLE",worker_id="w",error_code="X")
    assert claim and result.state=="BLOCKED"


def test_scheduler_deduplicates_and_is_one_shot(tmp_path):
    store=store_at(tmp_path); now=utcnow()
    store.add_schedule("once","RESEARCH","MARKET_HEARTBEAT",next_run_at=(now-timedelta(seconds=1)).isoformat())
    assert store.scheduler_once(now)==1
    assert store.scheduler_once(now)==0
    assert len(store.list_ready())==1


def test_supabase_ready_filter_url_encodes_utc_offset(monkeypatch):
    from nexus_agent_platform.durable_jobs import SupabaseJobStore
    requests=[]
    store=SupabaseJobStore()
    monkeypatch.setattr(store,"_request",lambda path,*args: requests.append(path) or [])
    assert store.list_ready(7)==[]
    assert len(requests)==1
    assert "scheduled_at=lte." in requests[0]
    assert "%2B00%3A00" in requests[0]
    assert "+00:00" not in requests[0]


def test_next_job_is_event_created_and_idempotent(tmp_path):
    store=store_at(tmp_path); parent=store.enqueue("FEEDER","BUSINESS_OPPORTUNITY_FEEDER")
    first=create_next_job(store,parent,department="RESEARCH",job_type="RESEARCH_GAP_VERIFY",payload_ref="artifact:gap",event_id="gap-opened")
    again=create_next_job(store,parent,department="RESEARCH",job_type="RESEARCH_GAP_VERIFY",payload_ref="artifact:gap",event_id="gap-opened")
    assert first.job_id==again.job_id and first.parent_job_id==parent.job_id


def test_credit_upload_job_contract_is_durable_and_governance_metadata_is_non_authorizing(tmp_path):
    store=store_at(tmp_path)
    context={"source":"client_documents_insert_trigger","paid_provider_authorized":False,"external_actions_authorized":False}
    job=store.enqueue("CREDIT_BUSINESS_FUNDING","CREDIT_REPORT_ANALYSIS",payload_ref="document-123",
        tenant_id="tenant-test",client_id="client-test",source_document_id="document-123",
        correlation_id="correlation-test",idempotency_key="credit-report-upload:document-123",governance_context=context)
    assert handler_route(job.job_type)=="DOCUMENT_ANALYSIS"
    assert job.tenant_id=="tenant-test" and job.client_id=="client-test"
    assert job.source_document_id==job.payload_ref=="document-123"
    assert job.correlation_id=="correlation-test"
    assert job.governance_context==context
    assert "CREDIT_REPORT_ANALYSIS" in HEAVY_MARKERS


def test_credit_upload_migration_uses_existing_queue_without_legacy_enqueue():
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]
    migration=(root/"supabase/migrations/20261021170000_credit_upload_durable_job_transition.sql").read_text()
    assert "insert into public.nexus_durable_jobs" in migration.lower()
    assert "insert into public.credit_analysis_jobs" not in migration.lower()
    assert "credit-report-upload:" in migration
    assert "paid_provider_authorized',false" in migration
    assert "external_actions_authorized',false" in migration
    upload=(root/"src/components/client/InlineDocumentUpload.jsx").read_text()
    assert "from('credit_analysis_jobs').insert" not in upload
    rerun_privileges=(root/"supabase/migrations/20261021180000_revoke_anon_credit_rerun.sql").read_text().lower()
    assert "revoke all on function public.request_credit_analysis_rerun(text,text) from public,anon" in rerun_privileges
    assert "to authenticated,service_role" in rerun_privileges


def test_twenty_ready_jobs_respect_total_worker_limit(tmp_path):
    store=store_at(tmp_path)
    for index in range(20): store.enqueue("SYSTEMS",f"MOCK_{index}",idempotency_key=f"mock-{index}")
    result=dispatch_once(store,launch=False,worker_id="bounded-test")
    assert result["started"]==2 and result["active"]==2 and len(store.list_ready(100))==18


def test_research_and_feeder_routing_is_allowlisted():
    for job_type in {"RESEARCH_GAP_VERIFY","NOTEBOOKLM_RESEARCH","PROACTIVE_DISCOVERY","CONTENT_INTELLIGENCE","MARKET_HEARTBEAT"}:
        assert handler_route(job_type)=="RESEARCH"
    for job_type in {"BUSINESS_OPPORTUNITY_FEEDER","BUSINESS_FUNDING_FEEDER","BUSINESS_CREATION_BANKABILITY_FEEDER","FOREX_INDICATOR_STRATEGY_FEEDER","OPTIONS_STRATEGY_FEEDER","RAY_NOVA_OPPORTUNITY_INTAKE","FEEDER_RESEARCH_CONTINUATION"}:
        assert handler_route(job_type)=="FEEDER"
    assert handler_route("FORMAL_HANDOFF")=="HANDOFF"
    assert handler_route("MARKETING_FINANCE_REVIEW_RESULT")=="MARKETING_CREATIVE"
    with pytest.raises(JobError): handler_route("UNLISTED")


def test_internal_canary_is_strictly_local_and_failure_is_once():
    from types import SimpleNamespace
    from nexus_agent_platform.internal_canary import execute_internal_canary
    context={"purpose":"staged_activation_canary","external_actions_authorized":False,"paid_provider_authorized":False}
    job=SimpleNamespace(job_type="SYSTEMS_INTERNAL_CANARY",governance_context=context,job_id="job-test",correlation_id="corr-test",payload_ref=None,max_attempts=1,attempt_count=1)
    assert handler_route(job.job_type)=="INTERNAL_CANARY"
    assert execute_internal_canary(job)=={"status":"COMPLETED","canary":"staged-activation","deterministic_value":140,"check":True}
    failure=SimpleNamespace(**{**job.__dict__,"job_type":"SYSTEMS_FAILURE_CANARY","max_attempts":2,"attempt_count":1})
    with pytest.raises(RuntimeError,match="CONTROLLED_CANARY_FAILURE_ONCE"):
        execute_internal_canary(failure)
    failure.attempt_count=2
    assert execute_internal_canary(failure)=={"status":"COMPLETED","canary":"failure-recovery","attempt":2,"check":True}
    invalid=SimpleNamespace(**{**job.__dict__,"payload_ref":"external-ref"})
    with pytest.raises(ValueError,match="INTERNAL_CANARY_CONTEXT_INVALID"):
        execute_internal_canary(invalid)


def test_internal_canary_worker_completes_with_receipt(tmp_path,monkeypatch):
    from nexus_agent_platform import job_worker_once
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    from nexus_agent_platform import supabase_egress_guard
    governor_path=tmp_path/"governor.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(governor_path))
    monkeypatch.setattr(supabase_egress_guard,"job_egress_snapshot",lambda _job_id:{"request_count":0,"response_bytes":0})
    context={"purpose":"staged_activation_canary","external_actions_authorized":False,"paid_provider_authorized":False}
    store=store_at(tmp_path); job=store.enqueue("SYSTEMS","SYSTEMS_INTERNAL_CANARY",max_attempts=1,governance_context=context)
    assert store.claim("canary-worker")
    LocalGovernorStore(governor_path).set_policy(
        "SUPABASE","durable_worker","SYSTEMS_INTERNAL_CANARY","DAILY",autonomous_usage_allowed=True,
        hard_limits={"rate":{},"usage":{"requests":120,"bytes":2_000_000},"money":{"per_job":0,"per_day":0,"per_month":0}},
    )
    result=job_worker_once.run(job.job_id,"canary-worker",store)
    assert result["status"]=="COMPLETED"
    assert store.get(job.job_id).state=="COMPLETED"
    with store._connect() as db:
        assert db.execute("select count(*) from receipts where job_id=?",(job.job_id,)).fetchone()[0]==1
    with LocalGovernorStore(governor_path).connect() as db:
        assert db.execute("select count(*) from footprints where job_id=?",(job.job_id,)).fetchone()[0]==1


def test_resource_pressure_defers_heavy_job(tmp_path,monkeypatch):
    store=store_at(tmp_path); store.enqueue("RESEARCH","NOTEBOOKLM_RESEARCH")
    monkeypatch.setenv("NEXUS_RESOURCE_PRESSURE","true")
    assert resource_pressure()
    result=dispatch_once(store,launch=False)
    assert result["started"]==0 and len(store.list_ready())==1


def test_job_scoped_egress_budget_aborts_only_excessive_job(tmp_path,monkeypatch):
    from nexus_agent_platform import supabase_egress_guard as guard
    monkeypatch.setattr(guard,"JOB_EGRESS_DIR",tmp_path/"job-egress")
    monkeypatch.setattr(guard,"SYSTEMS_INCIDENTS",tmp_path/"systems.jsonl")
    monkeypatch.setattr(guard,"STATE",tmp_path/"egress.json")
    monkeypatch.setattr(guard,"JOB_MAX_REQUESTS",2)
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job-egress-test")
    guard.preflight_request("GET","nexus_durable_jobs?select=job_id&limit=1")
    guard.record_request("GET","nexus_durable_jobs?select=job_id&limit=1",200,16,trace=False)
    guard.preflight_request("GET","nexus_durable_jobs?select=job_id&limit=1")
    with pytest.raises(guard.JobEgressBudgetExceeded):
        guard.preflight_request("GET","nexus_durable_jobs?select=job_id&limit=1")
    assert guard.job_egress_snapshot("job-egress-test")["request_count"]==2


def test_job_worker_exits_and_persists_one_receipt(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform import job_worker_once
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(tmp_path/"governor.sqlite3"))
    store=store_at(tmp_path); job=store.enqueue("RESEARCH","RESEARCH_GAP_VERIFY",payload_ref="work-ref")
    store.claim("test-worker")
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    governor=LocalGovernorStore(tmp_path/"governor.sqlite3")
    governor.set_policy("SUPABASE","durable_worker","*","DAILY",autonomous_usage_allowed=True,
                        hard_limits={"rate":{},"usage":{"requests":120,"bytes":2_000_000},"money":{"per_job":0,"per_day":0,"per_month":0}})
    original_reserve=LocalGovernorStore.reserve
    purposes=[]
    def tracked_reserve(self,*args,**kwargs):
        purposes.append(kwargs.get("purpose"))
        return original_reserve(self,*args,**kwargs)
    monkeypatch.setattr(LocalGovernorStore,"reserve",tracked_reserve)
    monkeypatch.setattr(job_worker_once.subprocess,"run",lambda *a,**k:SimpleNamespace(returncode=0,stdout="bounded result",stderr=""))
    monkeypatch.setattr("nexus_agent_platform.supabase_egress_guard.job_egress_snapshot",lambda job_id:{"request_count":1,"response_bytes":100})
    result=job_worker_once.run(job.job_id,"test-worker",store)
    assert result["status"]=="COMPLETED" and store.get(job.job_id).state=="COMPLETED"
    assert purposes==["durable-job-envelope:attempt-1"]
    with store._connect() as db: assert db.execute("select count(*) from receipts where job_id=?",(job.job_id,)).fetchone()[0]==1


def test_worker_defers_transient_governor_throttle_with_bounded_backoff(tmp_path,monkeypatch):
    from nexus_agent_platform import job_worker_once, resource_spend_governor
    store=store_at(tmp_path); job=store.enqueue("MARKETING","FINANCE_CAMPAIGN_REVIEW",payload_ref="unused")
    claimed=store.claim("throttle-worker")
    assert claimed

    class ThrottledGovernor:
        def reserve(self,*args,**kwargs):
            raise resource_spend_governor.GovernanceDenied("THROTTLED","RATE_LIMIT")
        def record_footprint(self,footprint):
            assert footprint["final_state"]=="FAILED_RETRYABLE"
            return "receipt-hash"

    monkeypatch.setattr(resource_spend_governor,"default_store",lambda:ThrottledGovernor())
    outcome=job_worker_once.run(job.job_id,"throttle-worker",store)
    updated=store.get(job.job_id)
    assert outcome["status"]=="FAILED_RETRYABLE"
    assert updated.state=="FAILED_RETRYABLE"
    assert updated.last_error_code=="RATE_LIMIT"
    assert updated.scheduled_at>updated.created_at
