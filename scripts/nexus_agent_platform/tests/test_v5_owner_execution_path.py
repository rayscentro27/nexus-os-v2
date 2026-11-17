from __future__ import annotations

import json

from nexus_agent_platform.durable_jobs import DurableJobStore, handler_route
from nexus_agent_platform.durable_objective_control import (
    load_active_campaign, recover_after_context_compaction,
)
from nexus_agent_platform.resource_dependency_controller import (
    can_resume_waiting_job, classify_policy, global_stop_allowed, partition_jobs,
)
from nexus_agent_platform.v5_dependency_graph import DEPENDENCY_JOB_TYPES, inspect_graph


def test_v5_campaign_load_survives_worker_restart(tmp_path):
    path=tmp_path/"campaign.json"
    path.write_text(json.dumps({"CERTIFICATION_ID":"NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9",
        "CAMPAIGN_ID":"NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9",
        "OWNER_OBJECTIVE_ID":"ownerobj_nexus_full_owner_real_world_v5_6fb82fd9",
        "MASTER_OBJECTIVE":"NEXUS FULL OWNER-REQUEST REAL-WORLD CERTIFICATION V5",
        "OBJECTIVE_VERSION":"V5","CURRENT_JOB_ID":"job_v5_research_source_review_20261010",
        "CURRENT_JOB_TYPE":"RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY","CHECKPOINT":{},
        "NEXT_REQUIRED_JOB":{},
        "WORKER_ROLE":"DEPARTMENT_EXECUTION","TERMINAL_CONDITION":"COMPLETE_OWNER_EXPERIENCE",
        "TERMINAL_CONDITION_SATISFIED":"NO","CAMPAIGN_STATUS":"ACTIVE"}))
    loaded=load_active_campaign(path)
    resumed=recover_after_context_compaction({},path)
    assert loaded["CURRENT_JOB_ID"]==resumed["current_job_id"]


def test_controller_restores_worker_egress_identity_after_department_job(monkeypatch):
    from scripts.certification import resume_v5_controller as controller
    from nexus_agent_platform import job_worker_once
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID",raising=False)
    monkeypatch.setenv("NEXUS_JOB_BUDGET",'{"max_requests":60}')
    def worker_run(job_id,worker,store):
        import os
        os.environ["NEXUS_DURABLE_JOB_ID"]=job_id
        os.environ["NEXUS_JOB_BUDGET"]='{"max_requests":12}'
        return {"status":"COMPLETED"}
    monkeypatch.setattr(job_worker_once,"run",worker_run)
    assert controller.run_department_job("test-job","test-worker",object())["status"]=="COMPLETED"
    assert "NEXUS_DURABLE_JOB_ID" not in __import__("os").environ
    assert __import__("os").environ["NEXUS_JOB_BUDGET"]=='{"max_requests":60}'


def test_v5_research_job_create_claim_lease_no_duplicate_and_recover(tmp_path):
    store=DurableJobStore(tmp_path/"jobs.sqlite3")
    fields=dict(department="RESEARCH",job_type="RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
        payload_ref="reports/certification/v5/jobs/job_v5_research_source_review_20261010.json",
        correlation_id="corr_4bfc9935c09e534da823278e",idempotency_key="v5:source-review",
        job_id="job_v5_research_source_review_20261010",
        governance_context={"campaign_id":"NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9",
            "owner_objective_id":"ownerobj_nexus_full_owner_real_world_v5_6fb82fd9","objective_version":"V5"})
    first=store.enqueue(**fields); duplicate=store.enqueue(**fields)
    assert first.job_id==duplicate.job_id
    claimed=store.claim_by_id(first.job_id,"worker",lease_seconds=120)
    assert claimed and claimed.state=="CLAIMED" and claimed.lease_until
    assert store.claim_by_id(first.job_id,"other") is None
    assert store.recover_expired() == 0
    assert store.transition(first.job_id,"FAILED_RETRYABLE",worker_id="worker").state=="FAILED_RETRYABLE"


def test_resource_circuit_waits_only_dependent_jobs_and_resumes_same_id(tmp_path):
    store=DurableJobStore(tmp_path/"jobs.sqlite3")
    job=store.enqueue("RESEARCH","RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
        job_id="job_a",idempotency_key="job_a",governance_context={"resource_dependencies":["NOTEBOOKLM"]})
    claimed=store.claim_by_id(job.job_id,"worker")
    assert claimed
    context={**claimed.governance_context,"resource_wait":{"resource":"NOTEBOOKLM",
        "resume_condition":"NOTEBOOKLM_POLICY_NORMAL","checkpoint_preserved":True}}
    store.set_governance_context(job.job_id,context)
    store.transition(job.job_id,"WAITING",worker_id="worker")
    waiting=store.get(job.job_id)
    assert waiting.state=="WAITING" and waiting.governance_context["resource_wait"]["checkpoint_preserved"]
    assert can_resume_waiting_job(waiting.governance_context,normalized_resources={"NOTEBOOKLM"})
    store.transition(job.job_id,"READY")
    resumed=store.claim_by_id("job_a","worker-2")
    assert resumed and resumed.job_id=="job_a" and resumed.attempt_count==2
    jobs=[{"id":"a","required_resources":["NOTEBOOKLM"]},
        {"id":"b","required_resources":["MODAL"]},{"id":"c","required_resources":["SYSTEMS"]},
        {"id":"d","required_resources":["HUGGING_FACE"]}]
    executable,resource_waiting=partition_jobs(jobs,paused_resources={"NOTEBOOKLM"})
    assert [x["id"] for x in executable]==["b","c","d"]
    assert resource_waiting[0]["status"]=="WAITING_RESOURCE_WINDOW"
    assert global_stop_allowed(executable) is False
    assert global_stop_allowed([]) is True
    assert classify_policy(provider="NOTEBOOKLM",capability="research_discovery",state="HARD_STOP",
        limits={"usage":{"bytes":500000}},circuit_class="budget")["requires_global_stop"] is False


def test_v5_dag_continues_independent_work_and_research_resumes_same_node():
    graph=inspect_graph(completed=set(),waiting_resources={"NOTEBOOKLM"},
        job_status={"RESEARCH":"WAITING_RESOURCE_WINDOW"})
    rows={row["workstream"]:row for row in graph["workstreams"]}
    assert rows["RESEARCH"]["current_status"]=="WAITING_RESOURCE_WINDOW"
    assert rows["RESEARCH"]["blocking_resource"]=="NOTEBOOKLM"
    for name in ("NEEDLE","MODAL","HUGGING_FACE","SYSTEMS"):
        assert rows[name]["current_status"]=="READY"
        assert rows[name]["can_run_while_research_waiting"] is True
        assert rows[name]["can_run_while_notebooklm_waiting"] is True
    assert graph["runnable_zero_cost_job_count"]>0
    assert graph["global_stop_allowed"] is False
    recovered=inspect_graph(completed=set(),waiting_resources=set(),
        job_status={"RESEARCH":"WAITING_RESOURCE_WINDOW"})
    resumed={row["workstream"]:row for row in recovered["workstreams"]}["RESEARCH"]
    assert resumed["current_status"]=="READY"
    assert resumed["job_type"]==rows["RESEARCH"]["job_type"]


def test_nova_trusted_single_ray_chat_is_authorized_without_widening(monkeypatch):
    from nova.nova_telegram_worker import load_runtime_env
    from nexus_agent_platform.provider_enforcement import authorize_telegram_action
    monkeypatch.delenv("NEXUS_TELEGRAM_RAY_CHAT_IDS",raising=False)
    monkeypatch.setattr("nova.nova_telegram_worker.RUNTIME_ENV", "/not-present/runtime.env")
    monkeypatch.setattr("nova.nova_telegram_worker.os.path.exists", lambda _: True)
    monkeypatch.setattr("builtins.open", lambda *_a, **_k: __import__("io").StringIO(
        "HERMES_NOVA_CHAT_ID=1288928049\n"))
    load_runtime_env()
    assert authorize_telegram_action("1288928049")=="RAY_NOTIFICATION"
    try:
        authorize_telegram_action("9999999999")
    except Exception as exc:
        assert getattr(exc,"code",None)=="TELEGRAM_RECIPIENT_NOT_AUTHORIZED"
    else:
        raise AssertionError("non-Ray destination unexpectedly authorized")


def test_v5_dependency_graph_job_types_have_registered_real_worker_routes():
    for job_type in set(DEPENDENCY_JOB_TYPES.values())|{"V5_REMOTE_STACK_HEALTH_CHECK"}:
        assert handler_route(job_type)


def test_daily_resource_circuit_reset_requires_matching_prior_utc_incident(tmp_path):
    from datetime import datetime,timedelta,timezone
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    store=LocalGovernorStore(tmp_path/"governor.sqlite3")
    limits={"usage":{"bytes":500000}}
    store.set_policy("NOTEBOOKLM","research_discovery","V5_DISCOVERY","DAILY",
        autonomous_usage_allowed=True,hard_limits=limits,state="HARD_STOP",approval_required=False)
    yesterday=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    with store.connect() as db:
        db.execute("UPDATE policies SET updated_at=? WHERE provider='NOTEBOOKLM' AND service='research_discovery' AND job_type='V5_DISCOVERY' AND budget_period='DAILY'",(yesterday,))
        db.execute("INSERT INTO incidents VALUES(?,?,?,?,?,?,?,?,?,?)",("inc-v5","NOTEBOOKLM","job_a",None,
            "BUDGET_HARD_LIMIT",json.dumps({"bytes":500000}),json.dumps({"bytes":600000}),"HARD_STOP",None,yesterday))
    assert store.reset_due_daily_budget_hard_stops()==1
    with store.connect() as db:
        row=db.execute("SELECT state FROM policies WHERE provider='NOTEBOOKLM' AND service='research_discovery' AND job_type='V5_DISCOVERY'").fetchone()
    assert row["state"]=="NORMAL"
    store.set_policy("MODAL","research_discovery","V5_DISCOVERY","DAILY",state="HARD_STOP")
    assert store.reset_due_daily_budget_hard_stops()==0


def test_v5_research_router_invokes_registered_department_handler(monkeypatch,tmp_path):
    assert handler_route("RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY")=="V5_OWNER_RESEARCH"
    payload={"campaign_id":"NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9",
        "owner_objective_id":"ownerobj_nexus_full_owner_real_world_v5_6fb82fd9"}
    source=tmp_path/"payload.json"; source.write_text(json.dumps(payload))
    artifact=tmp_path/"notebooklm.json"
    called={}
    def actual_research(job,payload):
        called.update(job_id=job.job_id,payload=payload)
        artifact.write_text(json.dumps({"answer":"NotebookLM source references support candidate models."}))
        return {"status":"COMPLETED","artifact_ref":"notebooklm.json"}
    monkeypatch.setattr("nexus_agent_platform.notebooklm_discovery.execute_import_and_synthesize",actual_research)
    from types import SimpleNamespace
    from nexus_agent_platform.v5_owner_workflow import handle_job
    monkeypatch.setattr("nexus_agent_platform.v5_owner_workflow.ROOT",tmp_path)
    result=handle_job(SimpleNamespace(job_id="job_v5_research_source_review_20261010",payload_ref="payload.json"))
    assert result["status"]=="COMPLETED"
    assert result["evidence_class"]=="NOTEBOOKLM_SOURCE_GROUNDED_RESEARCH"
    assert called["job_id"]=="job_v5_research_source_review_20261010"


def test_v5_notebooklm_restart_reuses_checkpoint_without_reimport(monkeypatch,tmp_path):
    import sys
    from types import ModuleType, SimpleNamespace
    from nexus_agent_platform import notebooklm_discovery as discovery
    source_url="https://example.test/market"
    discovery.ROOT=tmp_path
    evidence=tmp_path/"reports/certification/v5/research/job_e33989d3e27e4dc89b1c976aabd9d5da_notebooklm_discovery.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps({"sources":[{"url":source_url,"title":"Public source"}]}))
    class Adapter:
        def __init__(self,*args,**kwargs): pass
        def _run_json(self,args,**kwargs):
            if args[0]=="source": return {"sources":[{"id":"source-1","url":source_url,"title":"Public source"}]}
            return {"answer":"Evidence-backed summary","references":[{"source_id":"source-1"}]}
        def _turn_receipt(self,notebook_id,query,answer):
            return {"answer":answer["answer"],"references":answer["references"],
                "response_reference":"response-1","conversation_id":"conversation-1"}
    adapter_module=ModuleType("research.notebooklm_research_adapter")
    adapter_module.AdapterConfig=lambda **kwargs: object()
    adapter_module.NotebookLMResearchAdapter=Adapter
    research_module=ModuleType("research")
    research_module.__path__=[]
    monkeypatch.setitem(sys.modules,"research",research_module)
    monkeypatch.setitem(sys.modules,"research.notebooklm_research_adapter",adapter_module)
    calls=[]
    def execute(provider,service,action,estimate,callback,**kwargs):
        calls.append(action)
        if action=="NOTEBOOKLM_SOURCE_SCOPED_SYNTHESIS" and calls.count(action)==1:
            from nexus_agent_platform.resource_spend_governor import GovernanceDenied
            raise GovernanceDenied("HARD_STOP","BUDGET_HARD_LIMIT")
        return callback()
    monkeypatch.setattr("nexus_agent_platform.provider_enforcement.execute",execute)
    monkeypatch.setenv("NEXUS_DEPARTMENT","RESEARCH")
    job=SimpleNamespace(job_id="job_v5_research_source_review_20261010",job_type="RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
        attempt_count=2,correlation_id="corr-v5")
    payload={"operation":"IMPORT_AND_SYNTHESIZE","query":"Summarize cited evidence.",
        "notebook_id":"e0657f43-bf4e-4241-8336-7854739e942d","campaign_id":"campaign","project_id":"project"}
    first=discovery.execute_import_and_synthesize(job,payload)
    assert first["status"]=="WAITING_RESOURCE_WINDOW",first
    assert "NOTEBOOKLM_RESEARCH_IMPORT" not in calls
    checkpoint_path=tmp_path/"reports/certification/v5/jobs/job_v5_research_source_review_20261010_notebooklm_checkpoint.json"
    checkpoint=json.loads(checkpoint_path.read_text())
    assert checkpoint["last_completed_step"]=="NOTEBOOKLM_SOURCE_LIST_RESUME_RECONCILIATION"
    job.attempt_count=3
    resumed=discovery.execute_import_and_synthesize(job,payload)
    assert resumed["status"]=="COMPLETED",resumed
    assert calls==["NOTEBOOKLM_SOURCE_LIST_RESUME_RECONCILIATION",
        "NOTEBOOKLM_SOURCE_SCOPED_SYNTHESIS","NOTEBOOKLM_SOURCE_SCOPED_SYNTHESIS"]
    assert "NOTEBOOKLM_RESEARCH_IMPORT" not in calls
    checkpoint=json.loads(checkpoint_path.read_text())
    assert checkpoint["last_completed_step"]=="NOTEBOOKLM_SOURCE_SCOPED_SYNTHESIS"
    assert resumed["checkpoint_ref"].endswith("_notebooklm_checkpoint.json")

