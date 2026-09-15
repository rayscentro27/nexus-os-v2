"""Mandatory live-state barrier before Nexus stops or escalates.

This module is intentionally provider-agnostic.  Runtimes supply small
read-only loaders for canonical state and connector revalidators.  A stale
checkpoint can therefore never be used as the final reason to stop while
machine work remains or the reported blocker has cleared.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BlockerRecord:
    blocker_id: str
    blocker_type: str
    created_at: str
    last_verified_at: str | None
    evidence: str
    revalidation_method: str
    revalidation_interval_seconds: int
    currently_valid: bool
    exact_action: str | None = None
    superseded: bool = False

    def refreshed(self, *, valid: bool, evidence: str | None = None) -> "BlockerRecord":
        return BlockerRecord(
            **{**asdict(self), "last_verified_at": _now(), "currently_valid": valid,
               "evidence": evidence or self.evidence, "superseded": not valid}
        )


@dataclass(frozen=True)
class BackgroundResult:
    task_id: str
    state: str
    result: Any = None


def revalidate_blockers(
    blockers: Iterable[BlockerRecord],
    verifier: Callable[[BlockerRecord], tuple[bool, str | None]],
) -> list[BlockerRecord]:
    """Refresh every blocker immediately before it can influence an exit."""
    refreshed: list[BlockerRecord] = []
    for blocker in blockers:
        valid, evidence = verifier(blocker)
        refreshed.append(blocker.refreshed(valid=bool(valid), evidence=evidence))
    return refreshed


def background_result_barrier(
    tasks: Iterable[Mapping[str, Any]],
    wait_for: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> list[BackgroundResult]:
    """Join relevant background work or explicitly classify its boundary."""
    results: list[BackgroundResult] = []
    for task in tasks:
        state = str(task.get("state", "STILL_RUNNING_BUT_INDEPENDENT")).upper()
        if state == "RUNNING" and wait_for is not None:
            resolved = dict(wait_for(task))
            state = str(resolved.get("state", "TIMED_OUT")).upper()
            task_result = resolved.get("result")
        else:
            task_result = task.get("result")
        if state not in {"COMPLETED", "FAILED", "TIMED_OUT", "STILL_RUNNING_BUT_INDEPENDENT"}:
            state = "STILL_RUNNING_BUT_INDEPENDENT"
        results.append(BackgroundResult(str(task.get("task_id", "unknown")), state, task_result))
    return results


def pre_exit_state_reload(
    *,
    loaders: Mapping[str, Callable[[], Any]],
    blockers: Iterable[BlockerRecord] = (),
    blocker_verifier: Callable[[BlockerRecord], tuple[bool, str | None]] | None = None,
    background_tasks: Iterable[Mapping[str, Any]] = (),
    background_waiter: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    machine_work_probe: Callable[[Mapping[str, Any]], bool] | None = None,
    requested_ray_action: str | None = None,
) -> dict[str, Any]:
    """Reload all relevant state, then decide whether stopping is permitted.

    The returned ``ray_action_required`` is false whenever a blocker cleared,
    relevant background work completed, or any machine-actionable work is
    still present.  Callers must use this result instead of an earlier
    checkpoint snapshot.
    """
    state = {name: loader() for name, loader in loaders.items()}
    blocker_rows = list(blockers)
    if blocker_verifier is not None:
        blocker_rows = revalidate_blockers(blocker_rows, blocker_verifier)
    background = background_result_barrier(background_tasks, background_waiter)
    machine_remaining = bool(machine_work_probe(state)) if machine_work_probe else False
    valid_blockers = [row for row in blocker_rows if row.currently_valid]
    completed_relevant = any(row.state == "COMPLETED" for row in background)
    timeout_or_failure = [row for row in background if row.state in {"FAILED", "TIMED_OUT"}]
    can_escalate = bool(valid_blockers and requested_ray_action and not machine_remaining and not completed_relevant)
    return {
        "pre_exit_state_reload": "COMPLETED",
        "reloaded_sources": list(state),
        "blockers": [asdict(row) for row in blocker_rows],
        "blocker_revalidation": "PASS" if blocker_verifier is not None else "NOT_CONFIGURED",
        "blocker_superseded": any(row.superseded for row in blocker_rows),
        "background_result_barrier": [asdict(row) for row in background],
        "background_failures_or_timeouts": [row.task_id for row in timeout_or_failure],
        "machine_actionable_work_remaining": machine_remaining,
        "ray_action_required": can_escalate,
        "codex_required_to_continue": machine_remaining or completed_relevant or not can_escalate,
        "next_action": requested_ray_action if can_escalate else "CONTINUE_FROM_RELOADED_STATE",
    }


def assert_safe_to_stop(result: Mapping[str, Any]) -> None:
    """Fail closed if a caller tries to stop with unresolved machine work."""
    if result.get("machine_actionable_work_remaining"):
        raise RuntimeError("LOCAL_BLOCKER_GLOBAL_STOP_FORBIDDEN: machine work remains")
    if result.get("background_result_barrier") and any(
        row.get("state") == "STILL_RUNNING_BUT_INDEPENDENT" for row in result["background_result_barrier"]
    ):
        raise RuntimeError("BACKGROUND_RESULT_BARRIER_INCOMPLETE")
