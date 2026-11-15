"""Business Loop R1: offline end-to-end cycle + failure injection (no network, no publishing)."""
from __future__ import annotations

import pytest

from business_loop import departments as D
from business_loop import loop as L
from business_loop.project_state import ProjectStore

EXPECTED = {"RESEARCH->MARKETING", "MARKETING->CREATIVE", "MARKETING->COMMERCE", "CREATIVE->MARKETING", "CREATIVE->DISTRIBUTION",
            "COMMERCE->DISTRIBUTION", "DISTRIBUTION->METRICS", "METRICS->ANALYSIS"}


class FakeGraph:
    def get(self, path, fields):
        return 200, {"reactions": {"summary": {"total_count": 2}}, "comments": {"summary": {"total_count": 0}}, "like_count": 1, "comments_count": 0}

    def _request(self, method, path, params=None):
        if params["metric"] in ("post_impressions", "reach", "views"):
            return 200, {"data": [{"values": [{"value": 20}]}]}
        return 400, {"error": {"message": "metric deprecated"}}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    monkeypatch.setattr(D, "ROOT", tmp_path)  # creative output goes to tmp
    return ProjectStore(tmp_path / "bl")


def hooks(**over):
    base = {"research": lambda p: D.research(p, landing_check=lambda u: 200),
            "distribution": lambda p, b, c, co: D.distribution(p, b, c, co, request_writer=lambda r: r),
            "metrics": lambda p: D.metrics(p, graph_factory=FakeGraph)}
    base.update(over)
    return base


def test_full_cycle_handoffs_continuation_and_costs(store):
    out = L.run_cycle(store, hooks=hooks())
    p = out["project"]
    assert p["status"] == "ACTIVE"
    hs = store.handoffs(p["project_id"])
    transitions = {h["transition"] for h in hs}
    assert EXPECTED <= transitions and any(t.startswith("ANALYSIS->") for t in transitions)
    for h in hs:
        for k in ("SOURCE_WORK_ITEM", "DESTINATION_WORK_ITEM", "SUMMARY", "NEXT_ACTION", "STATUS", "TIMESTAMP"):
            assert h.get(k) not in (None, ""), (h["transition"], k)
        assert h["contract_validation"]["valid"] and h["manual_ray_handoff"] is False
    assert all(v == 0 for v in p["cost_ledger"].values())
    assert any(a.get("approval_kind") == "COMMERCE_GO_LIVE" for a in p["approvals_required"])
    assert out["continuation"]["status"] == "READY"
    t = L.tick(store)  # continuation routes to the owner and onward
    assert t["project_status"] == "ACTIVE" and t["routed"]
    t2 = L.tick(store)
    assert t2["project_status"] == "ACTIVE"


def test_inject_ai_provider_unavailable(store):
    def boom(_):
        raise ConnectionError("provider down")
    out = L.run_cycle(store, hooks=hooks(marketing=lambda p, rh: D.marketing(p, rh, ai_provider=boom)))
    ev = store.events(out["project"]["project_id"], "ISSUE_RECORDED")
    assert any(e["code"] == "AI_PROVIDER_UNAVAILABLE" and e["recovery"] == "DETERMINISTIC_COMPOSER_FALLBACK" for e in ev)
    assert out["project"]["status"] == "ACTIVE" and out["continuation"]


def test_inject_creative_generation_failure(store):
    def bad_renderer(*a, **k):
        raise OSError("render failed")
    out = L.run_cycle(store, hooks=hooks(creative=lambda p, b: D.creative(p, b, renderer=bad_renderer)))
    ev = store.events(out["project"]["project_id"], "ISSUE_RECORDED")
    assert sum(e["code"] == "CREATIVE_GENERATION_FAILURE" for e in ev) == 3
    assert out["project"]["status"] == "ACTIVE" and out["continuation"]


def test_publishing_approval_missing_pauses_only_publication(store):
    out = L.run_cycle(store, hooks=hooks())
    ev = store.events(out["project"]["project_id"], "ISSUE_RECORDED")
    assert any(e["code"] == "PUBLISHING_APPROVAL_MISSING" for e in ev)
    assert any("approval_request_id" in a for a in out["project"]["approvals_required"])
    assert out["project"]["status"] == "ACTIVE"


def test_inject_metrics_unavailable(store):
    def down():
        raise TimeoutError()
    out = L.run_cycle(store, hooks=hooks(metrics=lambda p: D.metrics(p, graph_factory=down)))
    pid = out["project"]["project_id"]
    assert any(e["code"] == "METRICS_TEMPORARILY_UNAVAILABLE" for e in store.events(pid, "RECOVERABLE_FAILURE"))
    assert any(w["stage"] == "METRICS_RETRY" and w["status"] == "READY" for w in store.work_items(pid))
    assert out["project"]["status"] == "ACTIVE" and out["continuation"]


def test_inject_research_insufficient_evidence(store):
    out = L.run_cycle(store, hooks=hooks(research=lambda p: D.research(p, landing_check=lambda u: None)))
    pid = out["project"]["project_id"]
    assert any(e["code"] == "NOT_ENOUGH_EVIDENCE" for e in store.events(pid, "RECOVERABLE_FAILURE"))
    assert out["project"]["status"] == "ACTIVE"
    assert any(w["stage"] == "RESEARCH_RETRY" for w in store.work_items(pid))


def test_project_cannot_be_terminated_by_department(store):
    p = L.ensure_project(store)
    with pytest.raises(PermissionError):
        store.save_project(p, status="STOPPED_SAFETY")


def test_rerun_cycle_dedupes_approvals_and_supersedes_old_continuations(store):
    L.run_cycle(store, hooks=hooks())
    out = L.run_cycle(store, hooks=hooks())
    p = out["project"]
    keys = [a.get("approval_request_id") or a.get("approval_kind") for a in p["approvals_required"]]
    assert len(keys) == len(set(keys)) == 2
    ready = [w for w in store.work_items(p["project_id"]) if w["status"] == "READY"]
    assert [w["work_item_id"] for w in ready] == [out["continuation"]["work_item_id"]]
