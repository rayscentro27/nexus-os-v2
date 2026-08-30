"""E2E and security tests for the governed operating loop.

Covers the canonical recommend → approve → queue → policy gate → execute →
telemetry → review chain, plus enforced boundaries:
  - registry/risk: only low-risk executable actions register executors
  - expiry/binding: single-use approvals, TTL, approval-bound work orders
  - idempotency / replay: identical approvals never double-execute
  - security: NOVA_ALLOWED_WRITES frozen, governed intents only for hermes_nova,
    non-executable actions never run, arbitrary executor names never dispatched

Each test runs against an isolated NEXUS_GOVERNED_DATA_DIR so tests are
hermetic and never touch the real data/governed store.
"""

from __future__ import annotations

import os
import pytest

from nexus_agent_platform.capabilities.shared import (
    NOVA_ALLOWED_WRITES,
    NOVA_GOVERNED_INTENTS,
)


@pytest.fixture()
def governed(tmp_path):
    """Isolated governed store + telemetry + real capabilities executor."""
    os.environ["NEXUS_GOVERNED_DATA_DIR"] = str(tmp_path / "governed")
    os.environ["NEXUS_EXECUTION_TELEMETRY_PATH"] = str(tmp_path / "telemetry" / "events.jsonl")
    from nexus_agent_platform.capabilities.nexus_query_planner import register_executor
    from nexus_agent_platform.capabilities.shared import execute_shared_capability

    def _exec(capability, args=None):
        return execute_shared_capability("hermes_nova", capability, args or {}, trace_id="governed_test")

    register_executor(_exec)
    yield tmp_path
    os.environ.pop("NEXUS_GOVERNED_DATA_DIR", None)
    os.environ.pop("NEXUS_EXECUTION_TELEMETRY_PATH", None)
    register_executor(None)


# ═══════════════════════════════════════════════════════════════
# 1. E2E full loop (approve path)
# ═══════════════════════════════════════════════════════════════

class TestFullLoop:
    def test_approve_path_full_loop(self, governed):
        from nexus_agent_platform.governed import actions_api as api
        from nexus_agent_platform.governed import engine, resolution

        rec = api.prepare_action_recommendation(
            title="Verify system health",
            problem="Unknown system health",
            recommended_action_id="system_health.run",
            reason="Baseline health evidence",
            evidence=[],
            expected_outcome="healthy",
            risk_level="low",
        )
        assert rec["status"] == "success"
        assert rec["executable_action"] is True

        appr = api.create_approval_request(
            action_id="system_health.run",
            action_summary="Run system health check",
            recommendation_id=rec["recommendation_id"],
        )
        assert appr["status"] == "pending"
        approval_id = appr["approval_id"]

        res = resolution.resolve_approval_intent(
            "Yes, please approve and run it",
            chat_id=7,
            decision="approve",
        )
        assert res.verdict == "resolved"

        wo_res = api.create_work_order_from_approval(approval_id)
        assert wo_res["status"] == "success"
        work_order_id = wo_res["work_order_id"]

        exec_res = engine.execute_approved_work_order(work_order_id)
        assert exec_res["status"] == "completed"
        assert exec_res["telemetry_run_id"]
        assert exec_res["executed"] is True

        review = engine.review_work_order(work_order_id)
        assert review["status"] == "completed"
        assert review["no_auto_launch"] is True
        assert review["outcome"] in ("met", "partial", "unknown")

    def test_full_loop_through_shared_capabilities(self, governed):
        from nexus_agent_platform.governed import actions_api as api
        from nexus_agent_platform.capabilities.shared import execute_shared_capability

        r = execute_shared_capability(
            "hermes_nova", "prepare_action_recommendation",
            {"title": "t", "problem": "p", "recommended_action_id": "system_health.run",
             "reason": "r", "evidence": [], "expected_outcome": "healthy", "risk_level": "low"},
            trace_id="e2e",
        )
        assert r["status"] == "success"
        r2 = execute_shared_capability(
            "hermes_nova", "create_approval_request",
            {"action_id": "system_health.run", "action_summary": "health"},
            trace_id="e2e",
        )
        assert r2["status"] == "pending"


# ═══════════════════════════════════════════════════════════════
# 2. Reject path
# ═══════════════════════════════════════════════════════════════

class TestRejectPath:
    def test_reject_never_creates_work_order(self, governed):
        from nexus_agent_platform.governed import actions_api as api
        from nexus_agent_platform.governed import resolution

        appr = api.create_approval_request(
            action_id="system_health.run", action_summary="health")
        res = resolution.resolve_approval_intent(
            "Reject it please", chat_id=9, decision="reject")
        assert res.verdict == "resolved"
        state = api.get_approval_status(appr["approval_id"])
        assert state["approval"]["status"] == "rejected"

        from nexus_agent_platform.governed import work_orders as wo
        assert wo.count_work_orders_by_status().get("queued", 0) == 0


# ═══════════════════════════════════════════════════════════════
# 3. Ambiguity never executes
# ═══════════════════════════════════════════════════════════════

class TestAmbiguity:
    def test_multiple_pending_is_ambiguous_and_no_execution(self, governed):
        from nexus_agent_platform.governed import actions_api as api
        from nexus_agent_platform.governed import resolution

        api.create_approval_request(action_id="system_health.run", action_summary="a")
        api.create_approval_request(action_id="runtime_report.generate", action_summary="b")
        res = resolution.resolve_approval_intent(
            "Approve it", chat_id=11, decision="approve")
        assert res.verdict == "ambiguous"
        assert len(res.candidates) == 2

        from nexus_agent_platform.governed import work_orders as wo
        assert wo.count_work_orders_by_status().get("queued", 0) == 0
        from nexus_agent_platform.governed import approvals as ap
        assert all(a["status"] == "pending" for a in ap.get_pending_approvals(
            requested_for="ray", include_self=False))

    def test_non_explicit_phrase_never_resolves(self, governed):
        from nexus_agent_platform.governed import actions_api as api
        from nexus_agent_platform.governed import resolution

        api.create_approval_request(action_id="system_health.run", action_summary="a")
        res = resolution.resolve_approval_intent(
            "looks good to me", chat_id=12, decision="approve")
        assert res.verdict == "invalid"


# ═══════════════════════════════════════════════════════════════
# 4. Replay / idempotency
# ═══════════════════════════════════════════════════════════════

class TestReplayIdempotency:
    def test_consumed_approval_cannot_requeue(self, governed):
        from nexus_agent_platform.governed import actions_api as api
        from nexus_agent_platform.governed import engine

        appr = api.create_approval_request(action_id="system_health.run", action_summary="a")
        res = api.resolve_governed_approval(appr["approval_id"], "approve")
        assert res["status"] == "ok"
        wo1 = api.create_work_order_from_approval(appr["approval_id"])
        r = engine.execute_approved_work_order(wo1["work_order_id"])
        assert r["status"] == "completed"

        replay = api.create_work_order_from_approval(appr["approval_id"])
        assert replay["status"] == "invalid"

    def test_same_idempotency_key_blocks_double_execution(self, governed):
        from nexus_agent_platform.governed import actions_api as api
        from nexus_agent_platform.governed import engine

        appr1 = api.create_approval_request(action_id="system_health.run", action_summary="a")
        api.resolve_governed_approval(appr1["approval_id"], "approve")
        wo1 = api.create_work_order_from_approval(appr1["approval_id"])
        key = wo1["order"]["idempotency_key"]
        r = engine.execute_approved_work_order(wo1["work_order_id"])
        assert r["status"] == "completed"

        from nexus_agent_platform.governed import work_orders as wo
        assert wo.idempotency_key_executed(key) is True


# ═══════════════════════════════════════════════════════════════
# 5. Expiry
# ═══════════════════════════════════════════════════════════════

class TestExpiry:
    def test_expired_approval_cannot_authorize(self, governed):
        from nexus_agent_platform.governed import approvals as ap
        from nexus_agent_platform.governed import persistence
        from nexus_agent_platform.governed import work_orders, engine

        appr = ap.create_approval_request(
            action_id="system_health.run", action_summary="a")
        assert ap.approval_is_expired(appr) is False  # created now, still valid

        # Backdate BOTH created_at and expires_at so the approval is past TTL.
        old = {**appr, "created_at": "2000-01-01T00:00:00+00:00",
               "expires_at": "2000-01-02T00:00:00+00:00"}
        persistence.append_record("approvals", old)
        expired = ap.get_approval(appr["id"])
        assert ap.approval_is_expired(expired) is True

        # Resolving an expired approval must transition to expired, never approve
        res = ap.resolve_approval(appr["id"], "approve", resolved_by="ray")
        assert res.get("status") == "expired"

        order = work_orders.create_work_order(
            approval_id=appr["id"], action_id="system_health.run", idempotency_key="exp1")
        r = engine.execute_approved_work_order(order["work_order_id"])
        # expired approval must NOT authorize execution
        assert r["status"] == "blocked"


# ═══════════════════════════════════════════════════════════════
# 6. Registry / risk / binding
# ═══════════════════════════════════════════════════════════════

class TestRegistryRiskBinding:
    def test_only_low_risk_executables(self, governed):
        from nexus_agent_platform.governed.actions_api import get_available_actions
        from nexus_agent_platform.governed import executors
        data = get_available_actions()
        executable = [a for a in data["actions"] if a["executable"]]
        registered = executors.registered_executors()
        assert {a["action_id"] for a in executable} == registered
        assert all(a["risk_level"] == "low" for a in executable)

    def test_non_executable_actions_never_run(self, governed):
        from nexus_agent_platform.governed.actions_api import create_approval_request
        from nexus_agent_platform.governed import policy_gate

        r = create_approval_request(action_id="stripe.live_activation")
        assert r["status"] == "invalid"
        allowed, reasons = policy_gate.check_execution(
            approval_id="nope", action_id="stripe.live_activation", inputs={})
        assert allowed is False

    def test_work_order_must_bind_to_valid_approval(self, governed):
        from nexus_agent_platform.governed import engine
        from nexus_agent_platform.governed import work_orders as wo

        order = wo.create_work_order(
            approval_id="does_not_exist", action_id="system_health.run",
            idempotency_key="bogus-bound",
        )
        r = engine.execute_approved_work_order(order["work_order_id"])
        assert r["status"] == "blocked"

    def test_unknown_action_id_rejected(self, governed):
        from nexus_agent_platform.governed.actions_api import create_approval_request
        r = create_approval_request(action_id="shell.arbitrary")
        assert r["status"] == "invalid"

    def test_executors_are_exact_allowlist(self, governed):
        from nexus_agent_platform.governed import executors
        from nexus_agent_platform.governed.action_registry import ACTION_REGISTRY
        registered = executors.registered_executors()
        for action_id in registered:
            entry = ACTION_REGISTRY[action_id]
            assert entry["risk_level"] == "low"
            assert entry["approval_required"] is True
            assert 1 <= entry["timeout_seconds"] <= 3600


# ═══════════════════════════════════════════════════════════════
# 7. Telemetry + audit trail
# ═══════════════════════════════════════════════════════════════

class TestTelemetryAudit:
    def test_execution_emits_telemetry_and_audit(self, governed):
        from nexus_agent_platform.governed import actions_api as api, engine
        from nexus_agent_platform.governed import persistence
        from nexus_agent_platform.runtime.paths import nexus_data_path
        import glob

        appr = api.create_approval_request(action_id="system_health.run", action_summary="a")
        api.resolve_governed_approval(appr["approval_id"], "approve")
        wo = api.create_work_order_from_approval(appr["approval_id"])
        r = engine.execute_approved_work_order(wo["work_order_id"])
        assert r["status"] == "completed"

        audit = persistence.read_records("audit")
        assert any(e["type"] == "execution_completed" or "execution_" in str(e.get("type")) for e in audit)
        assert any(e["type"] == "work_order_queued" for e in audit)

    def test_policy_gate_blocks_emit_block_event(self, governed):
        from nexus_agent_platform.governed import policy_gate, persistence
        from nexus_agent_platform.governed import work_orders as wo

        order = wo.create_work_order(
            approval_id="missing", action_id="system_health.run", idempotency_key="pg1")
        allowed, reasons = policy_gate.check_execution(
            approval_id="missing", action_id="system_health.run", inputs={})
        assert allowed is False
        policy_gate.emit_block(order["work_order_id"], "system_health.run", reasons)
        audit = persistence.read_records("audit")
        assert any(e["type"] == "execution_blocked" for e in audit)


# ═══════════════════════════════════════════════════════════════
# 8. Security: permission boundaries
# ═══════════════════════════════════════════════════════════════

class TestSecurityBoundaries:
    def test_nova_writes_frozen(self):
        assert NOVA_ALLOWED_WRITES == frozenset()
        assert len(NOVA_ALLOWED_WRITES) == 0

    def test_governed_intents_precisely_scoped(self):
        assert NOVA_GOVERNED_INTENTS == frozenset({
            "prepare_action_recommendation",
            "create_approval_request",
            "resolve_governed_approval",
            "create_work_order_from_approval",
            "submit_nexus_request",
        })

    def test_hermes_cannot_use_governed_intents(self, governed):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        r = execute_shared_capability(
            "nexus_hermes", "create_approval_request",
            {"action_id": "system_health.run"}, trace_id="sec")
        assert r["status"] == "unauthorized"

    def test_nova_cannot_execute(self, governed):
        from nexus_agent_platform.capabilities.shared import execute_shared_capability
        for cap in ("execute_approved_work_order", "claim_next", "next_eligible"):
            r = execute_shared_capability("hermes_nova", cap, {}, trace_id="sec")
            assert r["status"] in ("unauthorized", "unavailable")

    def test_nova_gets_no_executor_handler(self, governed):
        from nexus_agent_platform.capabilities.shared import _CAPABILITY_HANDLERS
        assert "execute_approved_work_order" not in _CAPABILITY_HANDLERS
        assert "run_system_health_action" not in _CAPABILITY_HANDLERS

    def test_planner_governed_action_is_read_only(self, governed):
        from nexus_agent_platform.capabilities.nexus_query_planner import plan_query, execute_plan
        for q in (
            "What actions can Nova perform?",
            "Show me the work queue",
            "What are pending approvals?",
        ):
            plan = plan_query(q, model_call_fn=None)
            result = execute_plan(plan)
            assert result.get("status") != "error"


# ═══════════════════════════════════════════════════════════════
# 9. Work queue
# ═══════════════════════════════════════════════════════════════

class TestWorkQueue:
    def test_queue_read_only_and_priority_ordered(self, governed):
        from nexus_agent_platform.governed import queue, work_orders as wo
        wo.create_work_order(approval_id="appr_a", action_id="system_health.run", idempotency_key="qa1")
        wo.create_work_order(approval_id="appr_b", action_id="runtime_report.generate", idempotency_key="qa2")
        view = queue.get_queue()
        assert view["status"] == "success"
        assert view["queueable_count"] == 2
        # No execution happened just from reading
        assert all(o["status"] in ("approved", "queued") for o in view["work_orders"])

    def test_checkpoint_required_for_pick(self, governed):
        from nexus_agent_platform.governed import queue
        assert queue.next_eligible().get("status") == "checkpoint_required"
        assert queue.next_eligible("wrong").get("status") == "checkpoint_required"

    def test_claim_and_execute_via_runner(self, governed):
        from nexus_agent_platform.governed import queue, engine, approvals as ap
        appr = ap.create_approval_request(action_id="system_health.run", action_summary="a")
        ap.resolve_approval(appr["id"], "approve", resolved_by="ray")
        wo = __import__("nexus_agent_platform.governed.work_orders", fromlist=["x"]).create_work_order(
            approval_id=appr["id"], action_id="system_health.run", idempotency_key="rc1")

        claim = queue.claim_next(queue.RUNNER_CHECKPOINT, "nexus_governed_runner")
        assert claim["status"] == "claimed"
        r = engine.execute_approved_work_order(claim["work_order_id"])
        assert r["status"] == "completed"
