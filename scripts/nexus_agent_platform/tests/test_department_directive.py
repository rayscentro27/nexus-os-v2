"""NEXUS_AUTOMATIC_DIRECTIVE_AND_CONTINUATION_R1 offline contract (fake store, fake Hermes; no network)."""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest

from nexus_agent_platform import department_directive as DD


class FakeStore:
    def __init__(self):
        self.jobs = {}

    def enqueue(self, department, job_type, *, priority=0, payload_ref=None, parent_job_id=None, correlation_id=None,
                max_attempts=1, idempotency_key=None, governance_context=None, **_):
        for j in self.jobs.values():
            if j.idempotency_key == idempotency_key:
                return j
        j = SimpleNamespace(job_id="job_" + uuid.uuid4().hex, department=department, job_type=job_type, state="QUEUED",
                            parent_job_id=parent_job_id, correlation_id=correlation_id, idempotency_key=idempotency_key,
                            governance_context=json.loads(json.dumps(governance_context or {})))
        self.jobs[j.job_id] = j
        return j

    def get(self, job_id):
        return self.jobs.get(job_id)

    def set_governance_context(self, job_id, ctx):
        self.jobs[job_id].governance_context = json.loads(json.dumps(ctx, default=str))


GOOD = {"campaign_concept": "Clear starting point", "target_audience": "Adults stuck on credit readiness",
        "hypothesis": "Stagnation framing beats benefit-led framing on CTR", "variant_a": "You don't need another promise. You need a clear starting point.",
        "variant_b": "Learn the three documents lenders review first.", "cta": "Get the free checklist", "channel_recommendation": ["Instagram"],
        "measurement_plan": {"primary": "CTR by variant"}, "creative_required": True,
        "creative_requirements": {"asset_requirements": ["1080x1080 image x2"], "message_variants": ["A", "B"], "channel_formats": ["IG feed"],
                                  "truth_constraints": ["no score promises"]}, "no_further_action_reason": None}


def hermes_ok(payload):
    return lambda prompt, session: {"ok": True, "text": json.dumps(payload), "tools": [], "session": session}


def _marketing_directive(store):
    d = DD.build_directive(target_department="MARKETING", objective="Bounded GoClear messaging experiment",
                           task="Turn the validated messaging pattern into a campaign package", required_output=["2 variants", "CTA"],
                           evidence_references=["research:job_x"], restrictions=["no guaranteed credit outcomes", "no publication", "no spend"])
    return DD.create_directive(store, d)


def test_schema_and_creation_never_executes():
    store = FakeStore()
    job, d = _marketing_directive(store)
    for k in ("directive_id", "project_id", "parent_directive_id", "source_department", "target_department", "objective", "task", "inputs",
              "evidence_references", "required_output", "success_criteria", "cost_policy", "approval_requirement", "dependencies",
              "status", "created_at", "completed_at", "next_department", "next_action"):
        assert k in d
    assert d["status"] == "READY" and d["directive_id"] == job.job_id and job.job_type == "DEPARTMENT_DIRECTIVE"
    assert job.governance_context["source"] == DD.SOURCE_NOVA and job.governance_context["spend_allowed"] is False
    assert [e["kind"] for e in d["events"]] == ["DIRECTIVE_CREATED"]
    with pytest.raises(ValueError):
        DD.build_directive(target_department="FINANCE", objective="x", task="y", required_output=["z"])


def test_marketing_completes_and_continues_to_creative_idempotently():
    store = FakeStore()
    job, d = _marketing_directive(store)
    out = DD.execute(store.get(job.job_id), store, hermes=hermes_ok(GOOD))
    assert out["status"] == "COMPLETED" and out["child_directive_id"]
    md = store.get(job.job_id).governance_context["directive"]
    assert md["status"] == "COMPLETE" and md["result"]["_provenance"]["directive_id"] == job.job_id
    assert [e["kind"] for e in md["events"]] == ["DIRECTIVE_CREATED", "WORK_STARTED", "CAMPAIGN_CREATED", "WORK_COMPLETED", "PROJECT_CONTINUED"]
    child = store.get(out["child_directive_id"]).governance_context["directive"]
    assert child["target_department"] == "CREATIVE" and child["parent_directive_id"] == job.job_id and child["project_id"] == md["project_id"]
    assert child["inputs"]["marketing_directive_id"] == job.job_id and child["approval_requirement"] == "PUBLICATION_REQUIRES_RAY_APPROVAL"
    again = DD.execute(store.get(job.job_id), store, hermes=hermes_ok(GOOD))
    assert again.get("idempotent") and len(store.jobs) == 2


def test_truth_check_blocks_guaranteed_claims():
    store = FakeStore()
    job, _ = _marketing_directive(store)
    bad = {**GOOD, "variant_b": "Guaranteed to raise your score 100 points."}
    out = DD.execute(store.get(job.job_id), store, hermes=hermes_ok(bad))
    assert out["status"] == "BLOCKED" and out["reason"] == "TRUTH_CHECK_FAILED" and len(store.jobs) == 1


def test_worker_failure_is_failed_not_terminal_for_project():
    store = FakeStore()
    job, _ = _marketing_directive(store)
    out = DD.execute(store.get(job.job_id), store, hermes=lambda p, s: {"ok": False, "error": "hermes_exit_1"})
    d = store.get(job.job_id).governance_context["directive"]
    assert out["status"] == "FAILED" and d["events"][-1]["kind"] == "WORK_FAILED"


def test_no_further_action_closes_branch_truthfully():
    store = FakeStore()
    job, _ = _marketing_directive(store)
    out = DD.execute(store.get(job.job_id), store, hermes=hermes_ok({**GOOD, "creative_required": False, "no_further_action_reason": "Evidence too weak."}))
    assert out["status"] == "COMPLETED" and "child_directive_id" not in out and len(store.jobs) == 1


def test_creative_blocks_without_local_fallback_and_project_stays_active():
    store = FakeStore()
    job, _ = _marketing_directive(store)
    child_id = DD.execute(store.get(job.job_id), store, hermes=hermes_ok(GOOD))["child_directive_id"]
    out = DD.execute(store.get(child_id), store)
    cd = store.get(child_id).governance_context["directive"]
    assert out["status"] == "BLOCKED" and out["reason"] == "CREATIVE_EXECUTION_BLOCKED"
    assert cd["result"]["fallback_used"] is False and {a["provider"] for a in cd["result"]["attempts"]} == {"meta_ai_browser_creative", "modal"}
    assert cd["events"][-1]["kind"] == "PROJECT_BLOCKED" and "required_action" in cd["events"][-1]
    assert store.get(job.job_id).governance_context["directive"]["status"] == "COMPLETE"  # marketing work stands


def test_creative_success_pauses_only_publication(monkeypatch):
    store = FakeStore()
    job, _ = _marketing_directive(store)
    child_id = DD.execute(store.get(job.job_id), store, hermes=hermes_ok(GOOD))["child_directive_id"]
    monkeypatch.setitem(DD.AUTONOMOUS_CREATIVE_EXECUTORS, "meta_ai_browser_creative", lambda d: {"ok": True, "assets": [{"path": "a.png"}]})
    out = DD.execute(store.get(child_id), store)
    cd = store.get(child_id).governance_context["directive"]
    assert out["status"] == "COMPLETED" and cd["status"] == "WAITING_APPROVAL" and cd["events"][-1]["kind"] == "APPROVAL_REQUIRED"


def test_events_carry_required_ids():
    store = FakeStore()
    job, _ = _marketing_directive(store)
    DD.execute(store.get(job.job_id), store, hermes=hermes_ok(GOOD))
    for ev in store.get(job.job_id).governance_context["directive"]["events"]:
        assert ev["project_id"] and ev["directive_id"] == job.job_id and ev["department"] == "MARKETING" and ev["status"] and "next" in ev


def test_directives_are_lightweight_so_creative_is_not_starved_by_heavy_gate():
    store = FakeStore()
    job, _ = _marketing_directive(store)
    child_id = DD.execute(store.get(job.job_id), store, hermes=hermes_ok(GOOD))["child_directive_id"]
    assert store.get(job.job_id).governance_context["resource_class"] == "LIGHTWEIGHT_INTERNAL"
    assert store.get(child_id).governance_context["resource_class"] == "LIGHTWEIGHT_INTERNAL"


# ---------------------------------------------------------------- NEXUS_FINAL_OVERNIGHT_COMPLETION_R1
class ContinuationStore(FakeStore):
    def _request(self, path):
        return [{"job_id": j.job_id, "state": j.state, "attempt_count": getattr(j, "attempt_count", 1), "max_attempts": 2}
                for j in self.jobs.values() if j.job_type == DD.JOB_TYPE and j.state in {"COMPLETED", "FAILED", "FAILED_RETRYABLE", "BLOCKED"}]


def _rea_directive(store, **inputs):
    d = DD.build_directive(target_department="REA", objective="Map the public workflow of the target web app",
                           task="Clean-room behavioural analysis", required_output=["workflows", "interfaces"],
                           business_id="vnt_goclear_credit_2026",
                           inputs={"target": "https://example.invalid/app", "authorization_ref": "owner-authorized:test", **inputs})
    return DD.create_directive(store, d)


def fake_rea_submit(store):
    def submit(_store, raw):
        child = store.enqueue("REA", "REA_EXECUTION", idempotency_key="rea:" + raw["objective"], governance_context={"rea_engine": raw})
        return {"nexus_job_id": child.job_id, "rea_session_id": "rea_" + "0" * 24}
    return submit


def test_contract_has_started_at_business_id_and_event_ids():
    store = FakeStore()
    job, d = _rea_directive(store)
    assert d["business_id"] == d["venture_id"] == "vnt_goclear_credit_2026"
    assert "started_at" in d and d["started_at"] is None
    ev = d["events"][0]
    assert ev["event_id"].startswith("evt_") and ev["business_id"] == "vnt_goclear_credit_2026"


def test_rea_directive_requires_target_and_authorization():
    with pytest.raises(ValueError, match="inputs.target"):
        DD.build_directive(target_department="REA", objective="x", task="y", required_output=["z"], inputs={})
    with pytest.raises(ValueError, match="authorization_ref"):
        DD.build_directive(target_department="REA", objective="x", task="y", required_output=["z"], inputs={"target": "t"})


def test_rea_directive_hands_off_then_continuation_completes():
    store = ContinuationStore()
    job, d = _rea_directive(store)
    out = DD.execute(job, store, rea_submit=fake_rea_submit(store))
    assert out["status"] == "COMPLETED" and out["directive_status"] == "RUNNING"
    d = store.get(job.job_id).governance_context["directive"]
    assert d["started_at"] and d["result"]["rea_job_id"]
    assert [e["kind"] for e in d["events"]][-1] == "REA_WORK_STARTED"
    job.state = "COMPLETED"
    assert DD.continue_directives(store)["rea_completed"] == 0          # REA child still running -> nothing
    store.get(d["result"]["rea_job_id"]).state = "COMPLETED"
    assert DD.continue_directives(store)["rea_completed"] == 1
    d = store.get(job.job_id).governance_context["directive"]
    assert d["status"] == "COMPLETE" and d["events"][-1]["kind"] == "REA_WORK_COMPLETED"
    assert DD.execute(store.get(job.job_id), store)["idempotent"]       # re-dispatch never resubmits


def test_rea_failure_blocks_and_notifies_once():
    store = ContinuationStore()
    job, d = _rea_directive(store)
    DD.execute(job, store, rea_submit=fake_rea_submit(store))
    job.state = "COMPLETED"
    rea_id = store.get(job.job_id).governance_context["directive"]["result"]["rea_job_id"]
    store.get(rea_id).state = "BLOCKED"
    assert DD.continue_directives(store)["rea_failed"] == 1
    kinds = [e["kind"] for e in store.get(job.job_id).governance_context["directive"]["events"]]
    assert kinds[-2:] == ["REA_WORK_FAILED", "PROJECT_BLOCKED"]
    assert DD.continue_directives(store)["rea_failed"] == 0


def test_continuation_holds_approval_resumes_when_approved_and_blocks_exhausted_failures():
    store = ContinuationStore()
    job, d = _marketing_directive(store)
    d = dict(store.get(job.job_id).governance_context["directive"]); d["status"] = "WAITING_APPROVAL"; DD._save(store, job, d)
    job.state = "COMPLETED"
    assert DD.continue_directives(store)["held"] == 1
    d["approval"] = {"approval_id": "apr_1", "status": "APPROVED"}; DD._save(store, job, d)
    assert DD.continue_directives(store)["resumed"] == 1
    assert store.get(job.job_id).governance_context["directive"]["events"][-1]["kind"] == "PROJECT_CONTINUED"
    job2, d2 = DD.create_directive(store, DD.build_directive(target_department="MARKETING", objective="other", task="t", required_output=["x"]))
    d2 = dict(store.get(job2.job_id).governance_context["directive"]); d2["status"] = "FAILED"; DD._save(store, job2, d2)
    job2.state = "FAILED"
    assert DD.continue_directives(store)["blocked"] == 1
    assert DD.continue_directives(store)["blocked"] == 0                  # notify once


def test_marketing_emits_campaign_created_with_related_ids():
    store = FakeStore()
    job, _ = _marketing_directive(store)
    DD.execute(job, store, hermes=hermes_ok(GOOD))
    evs = store.get(job.job_id).governance_context["directive"]["events"]
    cc = [e for e in evs if e["kind"] == "CAMPAIGN_CREATED"]
    assert len(cc) == 1 and cc[0]["campaign_id"].startswith("camp_")
