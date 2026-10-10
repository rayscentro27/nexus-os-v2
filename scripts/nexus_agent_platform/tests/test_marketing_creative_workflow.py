from __future__ import annotations

import json

import pytest

from nexus_agent_platform import durable_jobs as jobs
from nexus_agent_platform import marketing_creative_workflow as workflow


@pytest.fixture
def local_workflow(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_MARKETING_CREATIVE_DIR", str(tmp_path / "workflow"))
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    monkeypatch.setenv("NEXUS_DURABLE_JOBS_LOCAL", "1")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("VITE_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    store = jobs.DurableJobStore(tmp_path / "jobs.sqlite3")
    root = tmp_path / "workflow"
    monkeypatch.setattr(workflow, "RUNTIME", root)
    monkeypatch.setattr(workflow, "PAYLOADS", root / "payloads")
    monkeypatch.setattr(workflow, "REVIEWS", root / "campaigns")
    monkeypatch.setattr(workflow, "ARTIFACTS", root / "artifacts")
    monkeypatch.setattr(workflow, "default_store", lambda: store)
    return store


def _execute_next(store, parent_id, worker_id):
    job = store.claim(worker_id)
    assert job and job.job_id == parent_id
    store.transition(job.job_id, "RUNNING", worker_id=worker_id)
    result = workflow.handle_job(job, store)
    if result.get("status") == "BLOCKED":
        store.transition(job.job_id, "BLOCKED", worker_id=worker_id, error_code=result["reason"])
    else:
        store.complete(job.job_id, worker_id, result)
    return result


def test_goclear_campaign_runs_marketing_creative_and_explicit_ray_review(local_workflow, tmp_path, monkeypatch):
    store = local_workflow
    created = workflow.create_request({
        "campaign_id": "goclear-local-cert", "project_id": "goclear", "business_id": "goclear",
        "target_audience": "small business owners preparing for funding",
        "problem": "owners are unsure what records to prepare", "offer": "readiness review",
        "objective": "help owners prepare", "channels": ["landing page"], "cta": "Review readiness",
        "evidence_refs": ["fixture:research-1"], "required_assets": ["copy", "storyboard"],
    }, source="ATLAS")

    result = _execute_next(store, created["job_id"], "test-worker-1")
    assert result["state"] == "WAITING_CREATIVE"
    assert result["next_job_id"]
    brief_job = store.get(result["next_job_id"])
    store.claim("test-worker-2")
    store.transition(brief_job.job_id, "RUNNING", worker_id="test-worker-2")
    result = workflow.handle_job(brief_job, store)
    store.complete(brief_job.job_id, "test-worker-2", result)

    asset_job = store.claim("test-worker-3")
    assert asset_job.job_type == "CREATIVE_ASSET_GENERATE"
    store.transition(asset_job.job_id, "RUNNING", worker_id="test-worker-3")
    result = workflow.handle_job(asset_job, store)
    store.complete(asset_job.job_id, "test-worker-3", result)

    review_job = store.claim("test-worker-4")
    assert review_job.job_type == "MARKETING_ASSET_REVIEW"
    store.transition(review_job.job_id, "RUNNING", worker_id="test-worker-4")
    result = workflow.handle_job(review_job, store)
    store.complete(review_job.job_id, "test-worker-4", result)

    state = workflow.health("goclear-local-cert")
    assert state["state"] == "RAY_REVIEW_REQUIRED"
    assert state["approval_state"] == "READY_FOR_RAY_REVIEW"
    package = workflow.REVIEWS / workflow._hash("goclear-local-cert")[:24] / "review"
    assert (package / "copy_variants.md").exists()
    assert (package / "approval_status.json").exists()
    with pytest.raises(ValueError, match="EXPLICIT_RAY_COMMAND_REQUIRED"):
        workflow.explicit_ray_decision("goclear-local-cert", "casual discussion")
    revision = workflow.explicit_ray_decision("goclear-local-cert", "REQUEST_REVISION", feedback="Tighten the CTA")
    revision_job = store.get(revision["revision_job_id"])
    store.claim("test-worker-revision")
    store.transition(revision_job.job_id, "RUNNING", worker_id="test-worker-revision")
    revised = workflow.handle_job(revision_job, store)
    store.complete(revision_job.job_id, "test-worker-revision", revised)
    revised_review = store.claim("test-worker-revision-review")
    store.transition(revised_review.job_id, "RUNNING", worker_id="test-worker-revision-review")
    review_result = workflow.handle_job(revised_review, store)
    store.complete(revised_review.job_id, "test-worker-revision-review", review_result)
    approved = workflow.explicit_ray_decision("goclear-local-cert", "APPROVE_CAMPAIGN")
    assert approved["approval_state"] == "APPROVED_BY_RAY"
    assert approved["publish_job_id"]
    publish_job = store.get(approved["publish_job_id"])
    store.claim("test-worker-5")
    store.transition(publish_job.job_id, "RUNNING", worker_id="test-worker-5")
    prep = workflow.handle_job(publish_job, store)
    store.complete(publish_job.job_id, "test-worker-5", prep)
    monkeypatch.setenv("NEXUS_CERTIFICATION_MODE", "1")
    measure = workflow.publication_result_event("goclear-local-cert", publish_job.job_id, result_ref="mock-publication:1", mock=True)
    duplicate = workflow.publication_result_event("goclear-local-cert", publish_job.job_id, result_ref="mock-publication:1")
    assert measure["next_job_id"] == duplicate["next_job_id"]
    collect_job = store.get(measure["next_job_id"])
    store.claim("test-worker-6")
    store.transition(collect_job.job_id, "RUNNING", worker_id="test-worker-6")
    collected = workflow.handle_job(collect_job, store)
    store.complete(collect_job.job_id, "test-worker-6", collected)
    analyze_job = store.get(collected["next_job_id"])
    store.claim("test-worker-7")
    store.transition(analyze_job.job_id, "RUNNING", worker_id="test-worker-7")
    analyzed = workflow.handle_job(analyze_job, store)
    store.complete(analyze_job.job_id, "test-worker-7", analyzed)
    assert workflow.health("goclear-local-cert")["state"] == "COMPLETE"


def test_event_jobs_are_deduplicated_and_atlas_never_skips_marketing(local_workflow):
    store = local_workflow
    request = workflow.create_request({"campaign_id": "atlas-campaign", "target_audience": "a"}, source="ATLAS")
    first = store.get(request["job_id"])
    ref = workflow.store_payload({"campaign_id": "atlas-campaign", "event": "strategy-ready"}, payload_id="fixed-event")
    a = jobs.create_next_job(store, first, department="CREATIVE", job_type="CREATIVE_BRIEF_BUILD", payload_ref=ref, event_id="strategy-ready")
    b = jobs.create_next_job(store, first, department="CREATIVE", job_type="CREATIVE_BRIEF_BUILD", payload_ref=ref, event_id="strategy-ready")
    assert a.job_id == b.job_id
    assert first.job_type == "MARKETING_STRATEGY"


def test_nova_routing_and_revision_limit(local_workflow):
    assert workflow.classify_nova_request("Create a GoClear business funding campaign") == "CREATE_CAMPAIGN"
    assert workflow.classify_nova_request("Research why it is not working") == "SEND_TO_RESEARCH"
    assert workflow.classify_nova_request("Make another version") == "DISCUSS"
    assert workflow.classify_nova_request("Make another version", existing_campaign_id="c1") == "REVISE_ASSET"
    assert workflow.MAX_AUTONOMOUS_CREATIVE_REVISIONS == 2


def test_ray_nova_request_starts_marketing_and_research_gap_returns_event(local_workflow, monkeypatch):
    store = local_workflow
    payload = {"campaign_id": "nova-marketing", "target_audience": "small businesses", "problem": "unclear readiness", "offer": "review", "objective": "explain readiness", "cta": "Learn", "channels": ["landing page"]}
    intake = workflow.ray_nova_intake("Create a GoClear business-funding campaign", strategy_inputs=payload)
    assert intake["classification"] == "CREATE_CAMPAIGN"
    assert store.get(intake["job_id"]).job_type == "MARKETING_STRATEGY"
    strategy_job = store.get(intake["job_id"])
    store.claim("research-parent")
    store.transition(strategy_job.job_id, "RUNNING", worker_id="research-parent")
    result = workflow.handle_job(strategy_job, store)
    store.complete(strategy_job.job_id, "research-parent", result)

    from nexus_agent_platform.research_work_queue import ResearchWorkQueue
    monkeypatch.setattr(ResearchWorkQueue, "enqueue", lambda self, **fields: fields)
    requested = workflow.request_research("nova-marketing", strategy_job.job_id, question="Verify channel fit", evidence_gap_id="channel-fit")
    assert store.get(requested["job_id"]).job_type == "MARKETING_RESEARCH_GAP_VERIFY"
    research_job = store.get(requested["job_id"])
    resumed = workflow.research_completed_event(research_job, result_ref="research-result:fixture")
    assert store.get(resumed["next_job_id"]).job_type == "MARKETING_STRATEGY"


def test_campaign_spend_proposal_routes_to_finance_without_authorizing_spend(local_workflow, tmp_path, monkeypatch):
    store = local_workflow
    request = workflow.create_request({"campaign_id": "finance-campaign", "target_audience": "owners", "problem": "gap", "offer": "review", "objective": "educate", "cta": "learn", "channels": [], "paid_ad_budget": 25})
    parent = store.claim("strategy-worker")
    store.transition(parent.job_id, "RUNNING", worker_id="strategy-worker")
    strategy_result = workflow.handle_job(parent, store)
    store.complete(parent.job_id, "strategy-worker", strategy_result)
    finance = store.get(workflow.campaign("finance-campaign")["finance_review_job_id"])
    assert finance.department == "FINANCE"
    assert jobs.handler_route(finance.job_type) == "FINANCE"
    with store._connect() as db:
        db.execute("UPDATE jobs SET priority=200 WHERE job_id=?", (finance.job_id,))
    claimed_finance = store.claim("finance-worker")
    assert claimed_finance.job_id == finance.job_id
    store.transition(claimed_finance.job_id, "RUNNING", worker_id="finance-worker")
    from nexus_agent_platform import resource_spend_governor

    class Governor:
        def summary(self):
            return {"active_reservations": 0, "providers": [
                {"provider": "SOCIAL_MEDIA_EXTERNAL_ACTIONS", "service": "*", "state": "DISABLED",
                 "autonomous_usage_allowed": False, "autonomous_spend_allowed": False,
                 "approval_required": True, "daily_usage": {"estimated_cost": 0},
                 "monthly_usage": {"estimated_cost": 0}, "reserved_usage": {"estimated_cost": 0},
                 "active_paid_jobs": 0}
            ]}

    monkeypatch.setattr(resource_spend_governor, "default_store", lambda: Governor())
    from nexus_agent_platform import marketing_supabase_state
    remote_writes = []
    monkeypatch.setattr(marketing_supabase_state, "configured", lambda: True)
    monkeypatch.setattr("nexus_agent_platform.feeder_runtime._request", lambda *args: remote_writes.append(args) or [])
    from nexus_agent_platform.finance.job_handlers import handle_campaign_review
    out = handle_campaign_review(claimed_finance, store)
    assert out["spend_authorized"] is False
    assert out["finance_request_id"]
    assert out["recommendation"] == "DEFER_NO_SPEND_AUTHORITY"
    assert out["available_budget"] == "UNKNOWN"
    assert out["resource_budget_state"]["providers"][0]["state"] == "DISABLED"
    finance_event = next(call for call in remote_writes if call[0] == "nexus_events?on_conflict=id")
    assert finance_event[2]["payload"]["spend_authorized"] is False
    assert finance_event[2]["payload"]["recommendation"] == "DEFER_NO_SPEND_AUTHORITY"
    store.complete(claimed_finance.job_id, "finance-worker", out)
    marketing_result = store.get(out["next_job_id"])
    assert marketing_result.department == "MARKETING"
    assert marketing_result.job_type == "MARKETING_FINANCE_REVIEW_RESULT"
    with store._connect() as db:
        db.execute("UPDATE jobs SET priority=250 WHERE job_id=?", (marketing_result.job_id,))
    claimed_result = store.claim("marketing-result-worker")
    assert claimed_result and claimed_result.job_id == marketing_result.job_id
    store.transition(claimed_result.job_id, "RUNNING", worker_id="marketing-result-worker")
    result = workflow.handle_job(claimed_result, store)
    store.complete(claimed_result.job_id, "marketing-result-worker", result)
    state = workflow.campaign("finance-campaign")
    assert state["finance_review_state"] == "REVIEW_COMPLETE"
    assert state["spend_authorized"] is False
    assert state["state"] == "WAITING_CREATIVE"


def test_local_artifact_metadata_and_r2_default_off(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_MARKETING_CREATIVE_DIR", str(tmp_path / "workflow"))
    monkeypatch.setattr(workflow, "ARTIFACTS", tmp_path / "workflow" / "artifacts")
    ref = workflow.LocalArtifactStore().put_json({"asset_id": "a", "content": "local"}, "campaign", "asset")
    assert ref["storage_provider"] == "LOCAL_WORKING"
    assert ref["sha256"] and ref["size_bytes"] > 0
    assert workflow.R2ArtifactStore.available({}) is False
    assert workflow.R2ArtifactStore.available({"R2_ACCOUNT_ID": "a", "R2_ACCESS_KEY_ID": "b", "R2_SECRET_ACCESS_KEY": "c", "R2_BUCKET": "d"})


def test_creative_guardrail_text_is_not_misread_as_campaign_claim():
    from nexus_agent_platform.creative.studio import build_creative_brief_from_growth, validate_creative_brief

    brief = build_creative_brief_from_growth({"growth_id": "cert", "objective": "Explain readiness", "target_offer": "readiness review"})
    brief["brand_constraints"] = ["No guaranteed approval or funding claims"]
    assert "prohibited_claim" not in validate_creative_brief(brief)
    brief["target_offer"] = "Guaranteed funding"
    assert "prohibited_claim" in validate_creative_brief(brief)


def test_durable_internal_campaign_revision_approval_performance_loop(local_workflow):
    store = local_workflow
    created = workflow.create_test_campaign(store=store, campaign_id="marketing-creative-full-canary")
    completed_types = []
    while True:
        job = store.claim("marketing-canary-worker")
        if not job:
            break
        assert job.governance_context["test_campaign"] is True
        assert job.governance_context["providers_allowed"] == []
        assert job.governance_context["external_actions_allowed"] is False
        assert job.correlation_id == created["correlation_id"]
        assert "heavy" not in jobs.classify(job)
        store.transition(job.job_id, "RUNNING", worker_id="marketing-canary-worker")
        result = workflow.handle_job(job, store)
        receipt = store.complete(job.job_id, "marketing-canary-worker", result)
        workflow.record_job_receipt(job, receipt)
        completed_types.append(job.job_type)
    state = workflow.campaign(created["campaign_id"])
    assert completed_types == [
        "RESEARCH_MARKETING_TEST_HANDOFF", "MARKETING_STRATEGY", "CREATIVE_BRIEF_BUILD",
        "CREATIVE_ASSET_GENERATE", "MARKETING_ASSET_REVIEW", "CREATIVE_ASSET_REVISE",
        "MARKETING_ASSET_REVIEW", "PERFORMANCE_COLLECT", "MARKETING_PERFORMANCE_ANALYZE",
    ]
    assert state["workflow_stage"] == "ITERATION"
    assert state["approval_state"] == "PENDING_RAY_APPROVAL"
    assert state["publish_execution"] == "BLOCKED_BY_APPROVAL"
    assert state["publication_attempts"] == 0
    assert state["revision_count"] == 1
    assert state["review_decisions"] == ["REVISE", "ACCEPT"]
    assert len(state["asset_ids"]) == 2
    assert len(set(state["asset_ids"])) == 2
    assert state["performance_ref"] and state["analysis_ref"]
    assert store.health()["active_worker_count"] == 0
    assert store.list_ready(20) == []
    handoffs = sorted((workflow.RUNTIME / "handoffs").glob("*.json"))
    assert len(handoffs) >= 6
    for path in handoffs:
        handoff = json.loads(path.read_text())
        assert handoff["campaign_id"] == created["campaign_id"]
        assert handoff["correlation_id"] == created["correlation_id"]
        assert handoff["handoff_id"] and handoff["job_id"]
        assert handoff["receipt_id"]
    assert store.get(created["job_id"]).receipt_ref
    assert workflow.load_payload(state["performance_ref"])["data_class"] == "TEST"
    assert workflow.load_payload(state["analysis_ref"])["data_class"] == "TEST"


def test_supabase_campaign_projection_is_compact_and_asset_projection_omits_content(monkeypatch):
    from nexus_agent_platform import marketing_supabase_state as remote

    calls = []
    monkeypatch.setenv("SUPABASE_URL", "https://unit.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "unit-test-only")
    monkeypatch.setattr("nexus_agent_platform.feeder_runtime._request", lambda *args: calls.append(args) or [])
    remote.save_campaign({
        "campaign_id": "campaign-test", "project_id": "project-test", "state": "ASSETS_READY",
        "creative_state": "READY_FOR_MARKETING", "approval_state": "PENDING",
        "request_ref": "request-ref", "asset_ids": ["asset-1"],
        "secret_token": "must-not-persist", "brief_body": "large body must not persist",
    })
    remote.record_asset_metadata(
        asset_id="asset-1", campaign_id="campaign-test", project_id="project-test",
        asset_type="VIDEO_STORYBOARD", artifact_ref="local://artifact.json", sha256="a" * 64,
        size_bytes=123, mime_type="application/json", status="REVIEW_REQUIRED",
        approval_state="PENDING",
    )
    assert calls[0][0] == "creative_campaigns?on_conflict=campaign_key"
    assert "secret_token" not in json.dumps(calls[0][2])
    assert "brief_body" not in json.dumps(calls[0][2])
    assert calls[1][0] == "creative_assets?on_conflict=id"
    assert calls[1][2]["content"] is None
    assert "artifact_ref" in json.dumps(calls[1][2]["payload"])


def test_campaign_remote_fallback_uses_compact_projection(monkeypatch):
    from nexus_agent_platform import marketing_supabase_state as remote

    monkeypatch.setenv("SUPABASE_URL", "https://unit.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "unit-test-only")
    calls = []
    monkeypatch.setattr("nexus_agent_platform.feeder_runtime._request", lambda path, *args: calls.append(path) or [{"campaign_key": "campaign-test", "status": "RAY_REVIEW_REQUIRED", "goal": "test goal", "audience": "test audience", "offer": "test offer", "metadata": {"approval_state": "READY_FOR_RAY_REVIEW"}}])
    result = remote.get_campaign("campaign-test")
    assert result["approval_state"] == "READY_FOR_RAY_REVIEW"
    assert "select=campaign_key,status,metadata" in calls[0]
    assert "limit=1" in calls[0]


def test_worker_router_accepts_campaign_job_types():
    assert jobs.handler_route("MARKETING_STRATEGY") == "MARKETING_CREATIVE"
    assert jobs.handler_route("CREATIVE_ASSET_GENERATE") == "MARKETING_CREATIVE"


def test_one_shot_worker_persists_result_and_footprint(local_workflow, monkeypatch):
    from nexus_agent_platform import job_worker_once, resource_spend_governor, supabase_egress_guard

    class Governor:
        def __init__(self):
            self.footprints = []
            self.reconciled = []

        def reserve(self, *args, **kwargs):
            return {"reservation_id": "local-reservation"}

        def reconcile(self, reservation_id, usage):
            self.reconciled.append((reservation_id, usage))

        def record_footprint(self, footprint):
            self.footprints.append(footprint)
            return footprint

        def record_incident(self, *args, **kwargs):
            self.incidents.append((args, kwargs))

        incidents = []

    governor = Governor()
    monkeypatch.setattr(resource_spend_governor, "default_store", lambda: governor)
    monkeypatch.setattr(supabase_egress_guard, "job_egress_snapshot", lambda _job_id: {"request_count": 0, "response_bytes": 0, "budget_exceeded": False})
    monkeypatch.setenv("NEXUS_MARKETING_CREATIVE_DIR", str(workflow.RUNTIME))
    created = workflow.create_request({"campaign_id": "worker-campaign", "target_audience": "customers", "problem": "need help", "offer": "review", "objective": "explain", "cta": "learn", "channels": []})
    claimed = local_workflow.claim("one-shot-worker")
    out = job_worker_once.run(claimed.job_id, "one-shot-worker", local_workflow)
    assert out["status"] == "COMPLETED"
    assert local_workflow.get(claimed.job_id).state == "COMPLETED"
    assert len(governor.reconciled) == 1
    assert governor.footprints[0]["campaign_id"] == "worker-campaign"
    assert governor.footprints[0]["final_state"] == "COMPLETED"


def test_external_action_denial_isolated_and_incident_recorded(local_workflow, monkeypatch):
    from nexus_agent_platform import job_worker_once, resource_spend_governor, supabase_egress_guard

    class Governor:
        def __init__(self):
            self.incidents, self.footprints, self.reconciled = [], [], []

        def reserve(self, *args, **kwargs): return {"reservation_id": "deny-reservation"}
        def reconcile(self, reservation_id, usage): self.reconciled.append((reservation_id, usage))
        def record_incident(self, *args, **kwargs): self.incidents.append((args, kwargs))
        def record_footprint(self, footprint): self.footprints.append(footprint); return footprint

    governor = Governor()
    monkeypatch.setattr(resource_spend_governor, "default_store", lambda: governor)
    monkeypatch.setattr(supabase_egress_guard, "job_egress_snapshot", lambda _job_id: {"request_count": 0, "response_bytes": 0, "budget_exceeded": False})
    campaign = {"campaign_id": "blocked-email", "approval_state": "APPROVED_BY_RAY"}
    workflow._save_campaign({**campaign, "project_id": "goclear", "state": "READY_FOR_CONTROLLED_PUBLISH", "job_id": "parent", "asset_ids": [], "revision_count": 0})
    ref = workflow.store_payload({"campaign_id": "blocked-email", "channel": "EMAIL", "approval_state": "APPROVED_BY_RAY", "action_classification": "TEST"}, payload_id="blocked-email-action")
    blocked = local_workflow.enqueue("MARKETING", "CONTROLLED_EMAIL_SEND", payload_ref=ref, priority=200)
    unrelated = local_workflow.enqueue("SYSTEMS", "MOCK_SAFE_WORK", priority=10)
    claim = local_workflow.claim("external-action-worker")
    out = job_worker_once.run(claim.job_id, "external-action-worker", local_workflow)
    assert out["status"] == "BLOCKED"
    assert local_workflow.get(blocked.job_id).state == "BLOCKED"
    assert local_workflow.get(unrelated.job_id).state == "READY"
    assert governor.incidents and governor.footprints and governor.reconciled


def test_canary_controller_waits_once_for_scheduled_retry(monkeypatch):
    import importlib.util
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    script = Path(__file__).resolve().parents[3] / "scripts/certification/run_marketing_creative_canary.py"
    spec = importlib.util.spec_from_file_location("marketing_canary_runner_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Store:
        def __init__(self, rows): self.rows, self.requests = rows, 0
        def _request(self, _path): self.requests += 1; return self.rows

    slept = []
    monkeypatch.setattr(module.time, "sleep", slept.append)
    due = (datetime.now(timezone.utc) + timedelta(seconds=3)).isoformat()
    store = Store([{"scheduled_at": due}])
    assert module._wait_for_next_retry(store, "corr_test", max_wait=10)
    assert store.requests == 1
    assert len(slept) == 1 and 2.0 <= slept[0] <= 4.0


def test_canary_controller_fails_closed_without_retry_or_with_unbounded_delay(monkeypatch):
    import importlib.util
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    script = Path(__file__).resolve().parents[3] / "scripts/certification/run_marketing_creative_canary.py"
    spec = importlib.util.spec_from_file_location("marketing_canary_runner_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: pytest.fail("unexpected sleep"))

    class Store:
        def __init__(self, rows): self.rows = rows
        def _request(self, _path): return self.rows

    assert module._wait_for_next_retry(Store([]), "corr_test") is False
    future = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
    with pytest.raises(RuntimeError, match="CANARY_RETRY_DELAY_EXCEEDS_BOUND"):
        module._wait_for_next_retry(Store([{"scheduled_at": future}]), "corr_test", max_wait=2)
