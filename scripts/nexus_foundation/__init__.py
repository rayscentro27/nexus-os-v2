"""Canonical WP8.1 Nexus organizational contracts.

This package normalizes metadata and deterministic validation around the
existing governed work-order/loop executors. It does not create a second
agent runtime or grant authority.
"""

from .contracts import (
    LOOP_CATALOG,
    RESOURCE_PERMISSIONS,
    SPECIALISTS,
    build_work_order,
    build_goal,
    build_loop_state,
    complete_work_order,
    dependency_state,
    assign_work_order,
    authority_allows,
    eligible_specialists,
    enforce_budgets,
    handoff_work_order,
    improvement_candidate,
    load_organization,
    metric,
    persist_organization,
    specialist_contract,
    trading_strategy,
    run_foundation_proof,
    transition_work_order,
    validate_trading_safety,
)

__all__ = [
    "LOOP_CATALOG", "RESOURCE_PERMISSIONS", "SPECIALISTS",
    "build_work_order", "build_goal", "build_loop_state", "complete_work_order", "dependency_state", "assign_work_order", "authority_allows", "eligible_specialists", "enforce_budgets", "handoff_work_order", "improvement_candidate", "load_organization", "metric", "persist_organization", "specialist_contract", "trading_strategy", "run_foundation_proof",
    "transition_work_order", "validate_trading_safety",
]
