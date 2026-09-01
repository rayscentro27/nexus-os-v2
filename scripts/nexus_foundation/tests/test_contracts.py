from __future__ import annotations

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_foundation.contracts import (  # noqa: E402
    LOOP_CATALOG, RESOURCE_PERMISSIONS, SPECIALISTS, SPECIALIST_CONTRACT_FIELDS,
    TRADING_METRICS, build_goal, build_loop_state, build_work_order, complete_work_order, dependency_state, improvement_candidate, run_foundation_proof,
    load_organization, persist_organization, specialist_contract, trading_strategy, validate_trading_safety,
)


def test_roster_and_common_contract_are_complete():
    assert {"NOVA", "ALPHA", "JAX", "GROWTH", "CREATIVE", "CLYDE", "TRADING_ENGINE"} == set(SPECIALISTS)
    assert set(SPECIALIST_CONTRACT_FIELDS) <= set(specialist_contract("ALPHA"))
    assert RESOURCE_PERMISSIONS["TRADING_ENGINE"]["live_trading"] == "none"


def test_all_primary_loops_are_registered():
    required = {"OPPORTUNITY_LOOP", "VENTURE_PRODUCT_LOOP", "GROWTH_LOOP", "CLIENT_DELIVERY_LOOP", "ENGINEERING_LOOP", "CREATIVE_LOOP", "TRADING_RESEARCH_LOOP", "SYSTEM_OPERATIONS_LOOP", "CAPABILITY_IMPROVEMENT_LOOP", "EFFICIENCY_IMPROVEMENT_LOOP", "BUSINESS_LEARNING_LOOP", "EXECUTIVE_REVIEW_LOOP", "RUNTIME_RECOVERY_LOOP", "NETWORK_RECOVERY_LOOP"}
    assert required <= set(LOOP_CATALOG)
    assert LOOP_CATALOG["TRADING_RESEARCH_LOOP"]["owner"] == "TRADING_ENGINE"


def test_work_order_lifecycle_and_idempotency_key():
    order = build_work_order(goal_id="g", work_type="research", owner_specialist="ALPHA", inputs={"topic": "x"})
    assert order["status"] == "CREATED"
    completed = complete_work_order(order, {"status": "PASS", "artifact": "bounded"}, receipt_ref="r")
    assert completed["status"] == "COMPLETED"
    assert completed["return_to_nova"] is True
    assert len(completed["idempotency_key"]) == 64


def test_trading_contract_has_no_live_status_or_authority():
    strategy = trading_strategy()
    assert strategy["status"] == "CANDIDATE"
    assert "LIVE" not in strategy
    assert set(TRADING_METRICS) >= {"net_return", "max_drawdown", "expectancy", "sharpe"}
    assert validate_trading_safety() == {"LIVE_TRADING": False, "AUTO_TRADING": False, "PAPER_ONLY": True, "LIVE_TRADING_AUTHORITY": "NONE", "status": "PASS"}


def test_goal_loop_improvement_and_dependency_contracts():
    assert build_goal("g", owner="NEXUS", title="x")["status"] == "ACTIVE"
    assert build_loop_state("GROWTH_LOOP")["status"] == "READY"
    assert improvement_candidate("c", domain="efficiency")["status"] == "CANDIDATE"
    assert dependency_state("github", "DISCONNECTED")["secret_present"] is False


def test_organization_persists_and_reloads_from_governed_store():
    with tempfile.TemporaryDirectory() as directory:
        previous = os.environ.get("NEXUS_GOVERNED_DATA_DIR")
        os.environ["NEXUS_GOVERNED_DATA_DIR"] = directory
        try:
            counts = persist_organization()
            loaded = load_organization()
        finally:
            if previous is None:
                os.environ.pop("NEXUS_GOVERNED_DATA_DIR", None)
            else:
                os.environ["NEXUS_GOVERNED_DATA_DIR"] = previous
    assert counts["specialists"] == 7
    assert len(loaded["specialists"]) == 7
    assert len(loaded["specialist_permissions"]) == 7
    assert len(loaded["skill_assignments"]) == 6
    assert len(loaded["loop_state"]) == 14


def test_bounded_first_work_paths_and_recovery_proof():
    proof = run_foundation_proof()
    assert proof["status"] == "PASS"
    assert all(proof[key] == "COMPLETED" for key in ("business", "trading", "improvement", "repair"))
    assert proof["work_order_recovery"] == proof["loop_recovery"] == proof["process_recovery"] == proof["network_recovery"] == "PASS"
    assert proof["trading_safety"]["LIVE_TRADING_AUTHORITY"] == "NONE"
