from __future__ import annotations

from pathlib import Path

from nexus_agent_platform.durable_jobs import DurableJobStore


def test_feeder_event_enqueue_is_idempotent_and_correlated(tmp_path,monkeypatch):
    from nexus_agent_platform import durable_jobs, feeder_runtime
    store=DurableJobStore(tmp_path/"jobs.sqlite3")
    monkeypatch.setattr(durable_jobs,"default_store",lambda:store)
    first=feeder_runtime._create_durable_event_job("RESEARCH","RESEARCH_GAP_VERIFY","gap-1","gap:gap-1","source-1")
    again=feeder_runtime._create_durable_event_job("RESEARCH","RESEARCH_GAP_VERIFY","gap-1","gap:gap-1","source-1")
    assert first.job_id==again.job_id
    assert first.payload_ref=="gap-1" and first.correlation_id==again.correlation_id


def test_closed_research_gap_creates_one_feeder_continuation(tmp_path,monkeypatch):
    from nexus_agent_platform import durable_jobs, feeder_runtime, research_work_queue
    store=DurableJobStore(tmp_path/"jobs.sqlite3")
    monkeypatch.setattr(durable_jobs,"default_store",lambda:store)
    class Queue:
        def load(self):
            return {"items":[{"work_id":"gap-1","status":"COMPLETE","last_result":{"gap_state":"COMPLETED","evidence_state":"EVIDENCE_READY"},"artifact_id":"artifact-1","completed_at":"2026-10-08T00:00:00Z"}]}
    monkeypatch.setattr(research_work_queue,"ResearchWorkQueue",Queue)
    paths=[]
    def request(path,method="GET",body=None,prefer="return=minimal"):
        paths.append(path)
        if "question_id=eq.gap-1" in path and method=="GET": return [{"question_id":"gap-1","source_id":"source-1","status":"IN_PROGRESS"}]
        if "status=neq.COMPLETED" in path: return []
        return []
    monkeypatch.setattr(feeder_runtime,"_request",request)
    result=feeder_runtime.continue_research_gap("gap-1")
    assert result["status"]=="SOURCE_GAPS_CLOSED"
    jobs=store.list_ready(10)
    assert len(jobs)==1 and jobs[0].job_type=="FEEDER_RESEARCH_CONTINUATION" and jobs[0].payload_ref=="source-1"
    assert not any("nexus_feeder_research_gaps?status=in." in path for path in paths)


def test_job_worker_targets_one_feeder_source(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform import job_worker_once
    store=DurableJobStore(tmp_path/"jobs.sqlite3")
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(tmp_path/"governor.sqlite3"))
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    governor=LocalGovernorStore(tmp_path/"governor.sqlite3")
    governor.set_policy("SUPABASE","durable_worker","*","DAILY",autonomous_usage_allowed=True,
                        hard_limits={"rate":{},"usage":{"requests":120,"bytes":2_000_000},"money":{"per_job":0,"per_day":0,"per_month":0}})
    job=store.enqueue("FEEDER","BUSINESS_OPPORTUNITY_FEEDER",payload_ref="source-1")
    store.claim("worker")
    calls=[]
    def run(command,**kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0,stdout='{"status":"PASS","count":1,"processed":[{"source_id":"source-1"}]}',stderr="")
    monkeypatch.setattr(job_worker_once.subprocess,"run",run)
    monkeypatch.setattr("nexus_agent_platform.supabase_egress_guard.job_egress_snapshot",lambda job_id:{"request_count":2,"response_bytes":32})
    job_worker_once.run(job.job_id,"worker",store)
    command=calls[0]
    assert command[command.index("--source-id")+1]=="source-1"
    assert store.get(job.job_id).state=="COMPLETED"


def test_feeder_worker_refuses_polling_without_source_reference(monkeypatch):
    from nexus_agent_platform import feeder_runtime
    monkeypatch.setattr(feeder_runtime,"_request",lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("table scan attempted")))
    result=feeder_runtime.process_once()
    assert result=={"status":"BLOCKED","processed":[],"count":0,"reason":"DURABLE_SOURCE_ID_REQUIRED"}


def test_supabase_byte_budget_failure_is_job_local_and_other_jobs_remain_claimable(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform import job_worker_once
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    jobs=DurableJobStore(tmp_path/"jobs.sqlite3")
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(tmp_path/"governor.sqlite3"))
    governor=LocalGovernorStore(tmp_path/"governor.sqlite3")
    governor.set_policy("SUPABASE","durable_worker","*","DAILY",autonomous_usage_allowed=True,
        hard_limits={"rate":{},"usage":{"requests":1000,"bytes":10_000_000},"money":{"per_job":0,"per_day":0,"per_month":0}})
    bad=jobs.enqueue("RESEARCH","RESEARCH_GAP_VERIFY",payload_ref="gap-oversized",priority=100)
    other=jobs.enqueue("FEEDER","BUSINESS_OPPORTUNITY_FEEDER",payload_ref="source-safe",priority=0)
    jobs.claim("bounded-worker")
    monkeypatch.setattr(job_worker_once.subprocess,"run",lambda *a,**k:SimpleNamespace(returncode=0,stdout='{}',stderr=''))
    monkeypatch.setattr("nexus_agent_platform.supabase_egress_guard.job_egress_snapshot",
        lambda _job:{"request_count":1,"response_bytes":2_000_001,"budget_exceeded":True})
    monkeypatch.setattr(job_worker_once,"default_store",lambda:jobs)
    monkeypatch.setattr(job_worker_once.sys,"argv",["job_worker_once.py","--job-id",bad.job_id,"--worker-id","bounded-worker"])
    assert job_worker_once.main()==1
    assert jobs.get(bad.job_id).state=="FAILED_RETRYABLE"
    unrelated=jobs.claim("unrelated-worker")
    assert unrelated and unrelated.job_id==other.job_id
    with governor.connect() as db:
        assert db.execute("SELECT count(*) FROM footprints WHERE job_id=?",(bad.job_id,)).fetchone()[0]==1


def test_formal_handoff_enqueues_deduplicated_department_delivery(tmp_path,monkeypatch):
    from nexus_agent_platform import durable_jobs,feeder_runtime
    store=DurableJobStore(tmp_path/"jobs.sqlite3")
    monkeypatch.setattr(durable_jobs,"default_store",lambda:store)
    def request(path,method="GET",body=None,prefer="return=minimal"):
        if path.startswith("nexus_feeder_handoffs?"):
            return [{"handoff_id":"fh-1","to_department":"BUSINESS_OPPORTUNITIES","status":"CREATED","source_id":"source-1","case_id":"case-1"}]
        return []
    monkeypatch.setattr(feeder_runtime,"_request",request)
    one=feeder_runtime.handoff_once("fh-1")
    two=feeder_runtime.handoff_once("fh-1")
    jobs=store.list_ready(10)
    assert one["next_job_id"]==two["next_job_id"]
    assert len(jobs)==1 and jobs[0].job_type=="HANDOFF_DELIVERY" and jobs[0].department=="BUSINESS_OPPORTUNITIES"


def test_pulse_verified_handoff_creates_one_marketing_job(tmp_path,monkeypatch):
    from nexus_agent_platform import durable_jobs
    import research.pulse_runtime as pulse
    store=DurableJobStore(tmp_path/"jobs.sqlite3")
    monkeypatch.setattr(durable_jobs,"default_store",lambda:store)
    monkeypatch.setattr(pulse,"_upsert",lambda *args,**kwargs:(True,{}))
    trend={"trend_id":"trend-1","status":"VERIFIED","title":"Verified public trend","topic":"operations",
        "notebook_id":"notebook-1","confidence":0.9,"expected_half_life":"DAYS",
        "observed_data":{"video":{"url":"https://www.youtube.com/watch?v=abc","views":1000,"published_at":"2026-10-08"},"sources":[]}}
    one=pulse._make_campaign(trend)
    two=pulse._make_campaign(trend)
    jobs=store.list_ready(10)
    assert one["downstream_job_id"]==two["downstream_job_id"]
    assert len(jobs)==1 and jobs[0].job_type=="PULSE_HANDOFF" and jobs[0].department=="MARKETING"


def test_handoff_types_have_bounded_worker_route():
    from nexus_agent_platform.durable_jobs import handler_route
    assert handler_route("PULSE_HANDOFF")=="HANDOFF"
    assert handler_route("HANDOFF_DELIVERY")=="HANDOFF"


def test_mocked_multi_department_dispatch_creates_next_jobs_and_receipts(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from datetime import timedelta
    from nexus_agent_platform import job_worker_once
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    from nexus_agent_platform.durable_jobs import utcnow
    jobs=DurableJobStore(tmp_path/"jobs.sqlite3")
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(tmp_path/"governor.sqlite3"))
    gov=LocalGovernorStore(tmp_path/"governor.sqlite3")
    gov.set_policy("SUPABASE","durable_worker","*","DAILY",autonomous_usage_allowed=True,
        hard_limits={"rate":{},"usage":{"requests":500,"bytes":10_000_000},"money":{"per_job":0,"per_day":0,"per_month":0}})
    gov.set_policy("OPENROUTER","mock_completion","E2E_RESEARCH","DAILY",autonomous_usage_allowed=True,
        hard_limits={"rate":{},"usage":{"requests":2,"tokens":20},"money":{"per_job":0,"per_day":0,"per_month":0}})
    jobs.add_schedule("e2e-request","RESEARCH","RESEARCH_GAP_VERIFY",
        next_run_at=(utcnow()-timedelta(seconds=1)).isoformat(),payload_ref="gap-1")
    assert jobs.scheduler_once()==1
    root=jobs.list_ready(1)[0]
    transitions=[]
    def fake_run(command,**kwargs):
        text=" ".join(map(str,command))
        if "run_dispatched_research_job.py" in text:
            from nexus_agent_platform.provider_enforcement import execute
            execute("OPENROUTER","mock_completion","COMPLETION",{"requests":1,"tokens":3,"cost":0,"billable":False},
                lambda:{"usage":{"total_tokens":3}},job_id="e2e-mock-provider",job_type="E2E_RESEARCH")
            job=jobs.enqueue("FEEDER","FEEDER_RESEARCH_CONTINUATION",payload_ref="source-1",parent_job_id=root.job_id,idempotency_key="e2e:continuation")
            transitions.append(job)
            out={"status":"PASS","evidence":"mock"}
        elif "continue-source" in text:
            job=jobs.enqueue("SYSTEMS","FORMAL_HANDOFF",payload_ref="handoff-1",parent_job_id=continuation.job_id,idempotency_key="e2e:formal")
            transitions.append(job)
            out={"status":"FORMAL_HANDOFF_CREATED","handoff_id":"handoff-1"}
        elif "handoff-once" in text:
            job=jobs.enqueue("BUSINESS_OPPORTUNITIES","HANDOFF_DELIVERY",payload_ref="nexus_feeder_handoffs:handoff-1",parent_job_id=formal.job_id,idempotency_key="e2e:delivery")
            transitions.append(job)
            out={"status":"FORMAL_HANDOFF_PERSISTED","next_job_id":job.job_id}
        else:
            out={"status":"HANDOFF_DELIVERED","to_department":"BUSINESS_OPPORTUNITIES"}
        return SimpleNamespace(returncode=0,stdout=json.dumps(out),stderr="")
    import json
    monkeypatch.setattr(job_worker_once.subprocess,"run",fake_run)
    monkeypatch.setattr("nexus_agent_platform.supabase_egress_guard.job_egress_snapshot",lambda _job:{"request_count":2,"response_bytes":128})
    def run_next(job):
        claimed=jobs.claim("mock-worker")
        assert claimed and claimed.job_id==job.job_id
        return job_worker_once.run(job.job_id,"mock-worker",jobs)
    run_next(root)
    continuation=transitions[-1]
    run_next(continuation)
    formal=transitions[-1]
    run_next(formal)
    delivery=transitions[-1]
    run_next(delivery)
    assert len(transitions)==3
    assert all(jobs.get(j.job_id).state=="COMPLETED" for j in [root,continuation,formal,delivery])
    assert all(jobs.get(j.job_id).result_hash for j in [root,continuation,formal,delivery])
    with gov.connect() as db:
        assert db.execute("SELECT count(*) FROM footprints WHERE job_id IN (?,?,?,?)",(root.job_id,continuation.job_id,formal.job_id,delivery.job_id)).fetchone()[0]==4
