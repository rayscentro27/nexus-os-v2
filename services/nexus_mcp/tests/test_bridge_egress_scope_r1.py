"""DIRECTIVE_EGRESS_GOVERNOR_REPAIR_R1 contract.

Defect proven: the long-lived MCP bridge charged unscoped Supabase reads/writes to the
feeder's process-lifetime fallback identity ``feeder-process-<pid>`` (120-request cap),
so 120 tiny proactive polls exhausted it and later directive creation/reads were refused.

Repair: bridge reads run in per-request scopes and governed actions in per-invocation
budgets. Controls stay authoritative: every scope, job budget and cost decision still blocks.
Run with PYTHONPATH=<release>/scripts:<release>.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

from nexus_agent_platform import supabase_egress_guard as G
from services.nexus_mcp import server


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "JOB_EGRESS_DIR", tmp_path / "job_egress")
    monkeypatch.setattr(G, "SYSTEMS_INCIDENTS", tmp_path / "incidents.jsonl")
    for k in ("NEXUS_DURABLE_JOB_ID", "NEXUS_DURABLE_EXECUTION_ID", "NEXUS_JOB_BUDGET"):
        monkeypatch.delenv(k, raising=False)


def _preflight(n):
    for _ in range(n):
        G._update_job_egress(method="GET", path="nexus_durable_jobs?select=job_id&limit=20", preflight=True)


def test_defect_process_fallback_identity_exhausts_across_unrelated_calls(monkeypatch):
    """Reproduces process-lifetime accumulation with a small test cap."""
    monkeypatch.setattr(G, "JOB_MAX_REQUESTS", 3)
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "feeder-process-424242")
    _preflight(3)
    with pytest.raises(G.JobEgressBudgetExceeded, match="JOB_EGRESS_BUDGET_EXCEEDED:feeder-process-424242"):
        _preflight(1)


def test_scoped_reads_do_not_accumulate_across_requests(monkeypatch):
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "feeder-process-424242")
    for i in range(G.JOB_MAX_REQUESTS * 2):            # far beyond the old process cap
        with G.mcp_read_egress_scope(f"req-{i}"):
            _preflight(1)


def test_one_read_scope_stays_bounded(monkeypatch):
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "feeder-process-424242")
    with G.mcp_read_egress_scope("bounded-read"):
        _preflight(G.MCP_READ_MAX_REQUESTS)
        with pytest.raises(G.JobEgressBudgetExceeded, match="MCP_READ_REQUEST_LIMIT"):
            _preflight(1)


def test_external_egress_block_per_request_scope_still_enforced(monkeypatch):
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "feeder-process-424242")
    with G.mcp_read_egress_scope("runaway-read"):
        _preflight(G.MCP_READ_MAX_REQUESTS)
        with pytest.raises(G.JobEgressBudgetExceeded, match="MCP_READ_REQUEST_LIMIT"):
            _preflight(1)
    with G.mcp_read_egress_scope("large-read"):
        with pytest.raises(G.JobEgressBudgetExceeded, match="MCP_READ_RESPONSE_LIMIT"):
            G._update_job_egress(method="GET", path="nexus_durable_jobs", response_bytes=G.MCP_READ_MAX_RESPONSE_BYTES + 1)


def test_runaway_retry_block_real_durable_job_budget_unchanged(monkeypatch):
    """Exact durable-job identities keep job-wide budgets; scopes never apply to them."""
    monkeypatch.setattr(G, "JOB_MAX_REQUESTS", 3)
    job = "job_" + uuid.uuid4().hex
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", job)
    with G.mcp_read_egress_scope("inside-job") as scope:
        assert scope is None                            # no per-request relief for real jobs
        _preflight(3)
        with pytest.raises(G.JobEgressBudgetExceeded, match=f"JOB_EGRESS_BUDGET_EXCEEDED:{job}"):
            _preflight(1)


def test_mcp_scope_does_not_reset_durable_job_budget(monkeypatch):
    monkeypatch.setattr(G, "JOB_MAX_REQUESTS", 1)
    job = "job_" + uuid.uuid4().hex
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", job)
    _preflight(1)
    with G.mcp_read_egress_scope("durable-job-read") as scope:
        assert scope is None
        with pytest.raises(G.JobEgressBudgetExceeded, match=f"JOB_EGRESS_BUDGET_EXCEEDED:{job}"):
            _preflight(1)


def test_action_invocation_budget_is_bounded(monkeypatch):
    """Per-invocation action identity (as _action_call sets) is capped at 32 requests."""
    rid = "nexus-mcp-" + uuid.uuid4().hex
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", rid)
    monkeypatch.setenv("NEXUS_DURABLE_EXECUTION_ID", rid)
    monkeypatch.setenv("NEXUS_JOB_BUDGET", json.dumps({"max_requests": 2, "max_response_bytes": 1_000_000}))
    _preflight(2)
    with pytest.raises(G.JobEgressBudgetExceeded, match=f"JOB_EGRESS_BUDGET_EXCEEDED:{rid}"):
        _preflight(1)


def test_paid_provider_block_cost_governor_unchanged(tmp_path):
    from nexus_agent_platform.resource_spend_governor import GovernanceDenied, LocalGovernorStore
    store = LocalGovernorStore(tmp_path / "paid-governor.sqlite3")
    store.set_policy("MODAL", "test", "PAID_ACTION", "DAILY",
                     autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                     hard_limits={"rate": {}, "usage": {},
                                  "money": {"per_job": 10, "per_day": 10, "per_month": 100}},
                     approval_required=True)
    with pytest.raises(GovernanceDenied, match="SPEND_NOT_AUTHORIZED"):
        store.reserve("MODAL", "test", "PAID_ACTION", "synthetic-job",
                      {"requests": 1, "cost": 0.5, "billable": True}, purpose="contract-test")


def test_bridge_server_scopes_reads_and_actions():
    """The canonical bridge wraps read and action boundaries before release build."""
    root = Path(os.environ.get("NEXUS_BRIDGE_RELEASE") or Path(__file__).resolve().parents[3])
    assert Path(server.__file__).resolve() == (root / "services/nexus_mcp/server.py").resolve()
    src = (root / "services/nexus_mcp/server.py").read_text()
    assert "with mcp_read_egress_scope(request_id):" in src
    assert "scoped_invocation = not previous_egress_job or previous_egress_job.startswith(\"feeder-process-\")" in src
    assert 'budget["max_requests"] = min(32' in src             # invocation cap preserved
    assert "authorize_action(tool_name)" in src                # allowlist preserved
    assert "def mcp_read_egress_scope(request_id: str):" in (root / "scripts/nexus_agent_platform/supabase_egress_guard.py").read_text()
    assert Path(G.__file__).resolve() == (root / "scripts/nexus_agent_platform/supabase_egress_guard.py").resolve()


def test_safe_synthetic_directive_create_and_event_readback(tmp_path, monkeypatch):
    """Certify the actual directive creator against the isolated local durable store."""
    from nexus_agent_platform import durable_jobs, durable_objective_control

    monkeypatch.setattr(server, "nexus_research_state_path", lambda *parts: tmp_path.joinpath(*parts))
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path / "receipts")
    monkeypatch.setattr(server, "authorize_action", lambda _name: None)
    monkeypatch.setattr(durable_objective_control, "load_active_campaign", lambda: {})
    monkeypatch.setattr(durable_objective_control, "ACTIVE_CAMPAIGN_PATH", tmp_path / "no-campaign.json")
    monkeypatch.setenv("NEXUS_DURABLE_JOBS_LOCAL", "1")
    monkeypatch.setenv("NEXUS_DURABLE_JOBS_DB", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "feeder-process-52256")
    parent_request = "synthetic-parent-request-r1"
    result = server._action_call("nexus_assign_department_query", server._assign_department_query, {
        "department": "SYSTEMS", "question": "run Nexus system health check",
        "parent_request_id": parent_request,
    })
    assert result["status"] == "queued"
    job = durable_jobs.default_store().get(result["job_id"])
    assert job is not None and job.correlation_id == parent_request
    assert job.governance_context["paid_provider_authorized"] is False
    assert job.governance_context["external_actions_authorized"] is False
    assert Path(job.payload_ref).is_file()

    ledger = tmp_path / "runtime" / "research_execution_jobs.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"execution_id": job.job_id, "status": "QUEUED",
                                  "provider_execution": False}) + "\n")
    events = server._get_research_execution_trace(job.job_id)
    assert events["status"] == "ok" and events["event_count"] == 1
    assert events["events"][0]["status"] == "QUEUED"
    assert "provider_execution" not in events["events"][0]
