from __future__ import annotations
import json
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


def test_read_only_job_request_capacity_can_be_boundedly_recovered(tmp_path):
    store=store_at(tmp_path)
    job=store.enqueue("RESEARCH_ALPHA","NEXUS_DEPARTMENT_QUERY",job_id="public-research",
        idempotency_key="public-research",max_attempts=3,
        budget_envelope={"max_requests":12,"max_response_bytes":120000,"max_retries":3})
    store.ensure_request_capacity(job.job_id,30)
    assert store.get(job.job_id).budget_envelope["max_requests"]==30
    with store._connect() as db:
        db.execute("UPDATE jobs SET receipt_ref='receipt-done',state='COMPLETED' WHERE job_id=?",(job.job_id,))
    with pytest.raises(JobError,match="JOB_BUDGET_IMMUTABLE"):
        store.ensure_request_capacity(job.job_id,40)
    with pytest.raises(JobError,match="JOB_REQUEST_CAPACITY_OUT_OF_RANGE"):
        store.ensure_request_capacity("public-research",121)


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


def test_supabase_blocked_transition_persists_error_details(monkeypatch):
    from dataclasses import asdict
    from nexus_agent_platform.durable_jobs import Job, SupabaseJobStore

    store = SupabaseJobStore()
    current = Job(job_id="job-synthetic", department="RESEARCH", job_type="NOTEBOOKLM_RESEARCH",
                  state="RUNNING", attempt_count=1, max_attempts=3, claimed_by="worker-test")
    captured = {}

    def request(path, method="GET", body=None, prefer="return=minimal"):
        if method == "PATCH":
            captured.update(path=path, body=body)
            row = asdict(current)
            row.update(body)
            return [row]
        return [asdict(current)]

    monkeypatch.setattr(store, "_request", request)
    result = store.transition("job-synthetic", "BLOCKED", worker_id="worker-test",
                              error_code="NOTEBOOK_ID_REQUIRED", error_summary="No notebook reference")

    assert result.state == "BLOCKED"
    assert captured["body"]["last_error_code"] == "NOTEBOOK_ID_REQUIRED"
    assert captured["body"]["last_error_summary"] == "No notebook reference"
    assert captured["body"]["completed_at"] is not None
    assert captured["body"]["lease_until"] is None
    assert "receipt_ref" not in captured["body"]


def test_supabase_failed_retryable_transition_keeps_retry_fields(monkeypatch):
    from dataclasses import asdict
    from nexus_agent_platform.durable_jobs import Job, SupabaseJobStore

    store = SupabaseJobStore()
    current = Job(job_id="job-synthetic-retry", department="RESEARCH", job_type="NOTEBOOKLM_RESEARCH",
                  state="RUNNING", attempt_count=1, max_attempts=3, claimed_by="worker-test")
    captured = {}

    def request(path, method="GET", body=None, prefer="return=minimal"):
        if method == "PATCH":
            captured.update(path=path, body=body)
            row = asdict(current)
            row.update(body)
            return [row]
        return [asdict(current)]

    monkeypatch.setattr(store, "_request", request)
    result = store.transition("job-synthetic-retry", "FAILED_RETRYABLE", worker_id="worker-test",
                              error_code="TEMPORARY", error_summary="Retry later")

    assert result.state == "FAILED_RETRYABLE"
    assert captured["body"]["last_error_code"] == "TEMPORARY"
    assert captured["body"]["last_error_summary"] == "Retry later"
    assert captured["body"]["scheduled_at"]
    assert captured["body"]["completed_at"] is None


def test_supabase_claim_by_id_never_falls_back_to_unscoped_claim(monkeypatch):
    from nexus_agent_platform.durable_jobs import SupabaseJobStore
    store=SupabaseJobStore(); generic_claim=[]
    monkeypatch.setattr(store,"_request",lambda *args,**kwargs: (_ for _ in ()).throw(
        RuntimeError('SUPABASE_HTTP_404:{"code":"PGRST202"}')))
    monkeypatch.setattr(store,"claim",lambda *args,**kwargs: generic_claim.append(True))
    with pytest.raises(JobError,match="ATOMIC_CLAIM_BY_ID_RPC_REQUIRED"):
        store.claim_by_id("only-this-job","scoped-worker")
    assert generic_claim==[]


def test_supabase_renew_extends_only_current_active_worker_lease(monkeypatch):
    from nexus_agent_platform.durable_jobs import SupabaseJobStore
    store = SupabaseJobStore()
    captured = {}
    def request(path, method="GET", body=None, prefer="return=minimal"):
        captured.update(path=path, method=method, body=body)
        return [{"job_id": "job-renew", "lease_until": body["lease_until"]}]
    monkeypatch.setattr(store, "_request", request)
    assert store.renew("job-renew", "rea-worker", lease_seconds=900) is True
    assert captured["method"] == "PATCH"
    assert "claimed_by=eq.rea-worker" in captured["path"]
    assert "state=in.(CLAIMED,RUNNING)" in captured["path"]
    assert "lease_until=gt." in captured["path"]
    assert captured["body"]["lease_until"]


def test_supabase_renew_returns_false_when_worker_lease_is_not_owned(monkeypatch):
    from nexus_agent_platform.durable_jobs import SupabaseJobStore
    store = SupabaseJobStore()
    monkeypatch.setattr(store, "_request", lambda *args, **kwargs: [])
    assert store.renew("job-renew", "another-worker", lease_seconds=900) is False


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


def test_scoped_dispatcher_never_claims_outside_restoration_canary_ids(tmp_path):
    store=store_at(tmp_path)
    allowed=store.enqueue("SYSTEMS","SYSTEMS_INTERNAL_CANARY",idempotency_key="allowed")
    excluded=store.enqueue("RESEARCH","RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",idempotency_key="excluded")
    result=dispatch_once(store,launch=False,worker_id="restoration-canary",allowed_job_ids={allowed.job_id})
    assert result["started"]==1
    assert store.get(allowed.job_id).state=="RUNNING"
    assert store.get(excluded.job_id).state=="READY"


def test_source_scoped_dispatcher_runs_only_nova_created_department_jobs(tmp_path):
    store=store_at(tmp_path)
    allowed=store.enqueue("SYSTEMS","NEXUS_DEPARTMENT_QUERY",idempotency_key="nova-query",
        governance_context={"source":"NOVA_MCP_DEPARTMENT_QUERY"})
    excluded=store.enqueue("RESEARCH","RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
        idempotency_key="owner-campaign",governance_context={"source":"V5_OWNER_CAMPAIGN"})
    result=dispatch_once(store,launch=False,worker_id="source-canary",
        allowed_job_sources={"NOVA_MCP_DEPARTMENT_QUERY"})
    assert result["started"]==1
    assert store.get(allowed.job_id).state=="RUNNING"
    assert store.get(excluded.job_id).state=="READY"


def test_research_and_feeder_routing_is_allowlisted():
    for job_type in {"RESEARCH_GAP_VERIFY","NOTEBOOKLM_RESEARCH","PROACTIVE_DISCOVERY","CONTENT_INTELLIGENCE","MARKET_HEARTBEAT"}:
        assert handler_route(job_type)=="RESEARCH"
    for job_type in {"BUSINESS_OPPORTUNITY_FEEDER","BUSINESS_FUNDING_FEEDER","BUSINESS_CREATION_BANKABILITY_FEEDER","FOREX_INDICATOR_STRATEGY_FEEDER","OPTIONS_STRATEGY_FEEDER","RAY_NOVA_OPPORTUNITY_INTAKE","FEEDER_RESEARCH_CONTINUATION"}:
        assert handler_route(job_type)=="FEEDER"
    assert handler_route("FORMAL_HANDOFF")=="HANDOFF"
    assert handler_route("MARKETING_FINANCE_REVIEW_RESULT")=="MARKETING_CREATIVE"
    assert handler_route("NOVA_RESOURCE_ALERT_RETRY")=="NOVA_COMMUNICATION"
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


def test_resource_pressure_process_match_ignores_chrome_remote_desktop():
    from nexus_agent_platform.durable_jobs import _resource_heavy_process
    assert not _resource_heavy_process(
        "remoting_me2me_host",
        "/Library/PrivilegedHelperTools/ChromeRemoteDesktopHost.app/Contents/MacOS/remoting_me2me_host "
        "--host-config=/Library/PrivilegedHelperTools/org.chromium.chromoting.json",
    )
    assert _resource_heavy_process(
        "Google Chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-pipe "
        "--user-data-dir=/tmp/playwright_chromiumdev_profile-test",
    )


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


def test_repaired_job_gets_a_fresh_bounded_egress_allowance_per_attempt(tmp_path,monkeypatch):
    from nexus_agent_platform import supabase_egress_guard as guard
    monkeypatch.setattr(guard,"JOB_EGRESS_DIR",tmp_path/"job-egress")
    monkeypatch.setattr(guard,"SYSTEMS_INCIDENTS",tmp_path/"systems.jsonl")
    monkeypatch.setattr(guard,"JOB_MAX_REQUESTS",2)
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job-retry-egress-test")
    monkeypatch.setenv("NEXUS_JOB_BUDGET",json.dumps({"max_requests":2,"max_response_bytes":1000}))
    monkeypatch.setenv("NEXUS_DURABLE_EXECUTION_ID","attempt-one")
    for _ in range(2):
        guard.preflight_request("GET","nexus_durable_jobs?select=job_id&limit=1")
        guard.record_request("GET","nexus_durable_jobs?select=job_id&limit=1",200,16,trace=False)
    with pytest.raises(guard.JobEgressBudgetExceeded):
        guard.preflight_request("GET","nexus_durable_jobs?select=job_id&limit=1")
    monkeypatch.setenv("NEXUS_DURABLE_EXECUTION_ID","attempt-two")
    guard.preflight_request("GET","nexus_durable_jobs?select=job_id&limit=1")
    guard.record_request("GET","nexus_durable_jobs?select=job_id&limit=1",200,16,trace=False)
    snapshot=guard.job_egress_snapshot("job-retry-egress-test")
    assert snapshot["request_count"]==3
    assert snapshot["attempt_request_count"]==1
    assert snapshot["response_bytes"]==48
    assert snapshot["attempt_response_bytes"]==16


def test_full_research_canary_gets_only_its_scoped_request_ceiling(tmp_path,monkeypatch):
    from nexus_agent_platform import supabase_egress_guard as guard
    monkeypatch.setattr(guard,"JOB_EGRESS_DIR",tmp_path/"job-egress")
    monkeypatch.setattr(guard,"SYSTEMS_INCIDENTS",tmp_path/"systems.jsonl")
    monkeypatch.setattr(guard,"STATE",tmp_path/"egress.json")
    monkeypatch.setattr(guard,"JOB_MAX_REQUESTS",120)
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job_full_research_canary_test")
    monkeypatch.setenv("NEXUS_JOB_BUDGET",json.dumps({"max_requests":300,"max_response_bytes":2_000_000}))
    for _ in range(121):
        guard.preflight_request("GET","nexus_resource_policies?select=job_type&limit=1")
        guard.record_request("GET","nexus_resource_policies?select=job_type&limit=1",200,16,trace=False)
    assert guard.job_egress_snapshot("job_full_research_canary_test")["attempt_request_count"]==121
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job_other_research_test")
    monkeypatch.setenv("NEXUS_DURABLE_EXECUTION_ID","other-job-attempt")
    for _ in range(120):
        guard.preflight_request("GET","nexus_resource_policies?select=job_type&limit=1")
        guard.record_request("GET","nexus_resource_policies?select=job_type&limit=1",200,16,trace=False)
    with pytest.raises(guard.JobEgressBudgetExceeded):
        guard.preflight_request("GET","nexus_resource_policies?select=job_type&limit=1")


def test_egress_guard_allows_bounded_reservation_release_cleanup_after_budget(tmp_path,monkeypatch):
    from nexus_agent_platform import supabase_egress_guard as guard
    monkeypatch.setattr(guard,"JOB_EGRESS_DIR",tmp_path/"job-egress")
    monkeypatch.setattr(guard,"SYSTEMS_INCIDENTS",tmp_path/"systems.jsonl")
    monkeypatch.setattr(guard,"JOB_MAX_REQUESTS",1)
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","job-release-cleanup")
    monkeypatch.setenv("NEXUS_JOB_BUDGET",json.dumps({"max_requests":1,"max_response_bytes":1000}))
    guard.preflight_request("GET","nexus_resource_policies?select=state&limit=1")
    guard.record_request("GET","nexus_resource_policies?select=state&limit=1",200,16,trace=False)
    release_path="nexus_resource_reservations?reservation_id=eq.reserve-one&status=eq.ACTIVE"
    release_body={"status":"RELEASED","reconciled_at":"2026-10-12T00:00:00Z"}
    guard.preflight_request("PATCH",release_path,release_body)
    guard.record_request("PATCH",release_path,200,16,trace=False)
    with pytest.raises(guard.JobEgressBudgetExceeded):
        guard.preflight_request("GET","nexus_resource_policies?select=state&limit=1")


def test_job_worker_exits_and_persists_one_receipt(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform import job_worker_once
    from nexus_agent_platform import stability_supervisor
    monkeypatch.setattr(stability_supervisor,"get_host_execution_gate",lambda:{
        "heavy_work_allowed":True,"research_execution_allowed":True})
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(tmp_path/"governor.sqlite3"))
    store=store_at(tmp_path); job=store.enqueue("RESEARCH","RESEARCH_GAP_VERIFY",payload_ref="work-ref")
    store.claim("test-worker")
    from nexus_agent_platform import research_work_queue
    monkeypatch.setattr(research_work_queue,"default_queue",lambda:SimpleNamespace(load=lambda:{"items":[{"work_id":"work-ref","question":"bounded test assignment"}]}))
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
    assert len(purposes)==1 and purposes[0].startswith("durable-job-envelope:run-")
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


def test_retry_capacity_can_recover_same_job_after_preexecution_auth_block(tmp_path):
    store=store_at(tmp_path)
    job=store.enqueue("NOVA","NOVA_RESOURCE_ALERT_RETRY",job_id="retained-alert",
        idempotency_key="retained-alert",max_attempts=1,budget_envelope={"max_retries":1})
    assert store.claim_by_id(job.job_id,"worker")
    store.transition(job.job_id,"BLOCKED",worker_id="worker",error_code="ACTIVE_CAMPAIGN_IDENTITY_MISMATCH")
    store.ensure_retry_capacity(job.job_id,2)
    recovered=store.transition(job.job_id,"READY")
    assert recovered.job_id==job.job_id and recovered.max_attempts==2


def test_reopen_after_repair_retains_same_job_and_records_bounded_window(tmp_path):
    store=store_at(tmp_path)
    job=store.enqueue("RESEARCH","NEXUS_NOTEBOOKLM_RUNTIME_CANARY",job_id="same-canary",
        idempotency_key="same-canary",max_attempts=1,
        budget_envelope={"max_requests":120,"max_response_bytes":2_000_000})
    store.claim_by_id(job.job_id,"worker-a")
    store.transition(job.job_id,"BLOCKED",worker_id="worker-a",error_code="CHECKPOINT_RECONCILIATION")
    reopened=store.reopen_after_repair(job.job_id,reason="recover local answer statuses",
        budget_updates={"max_requests":300,"max_response_bytes":4_000_000})
    assert reopened.job_id==job.job_id and reopened.state=="READY" and reopened.attempt_count==0
    assert reopened.budget_envelope["max_requests"]==300
    assert reopened.governance_context["repair_attempt_total"]==1
    assert reopened.governance_context["repair_retry_windows"][0]["attempt_count"]==1
