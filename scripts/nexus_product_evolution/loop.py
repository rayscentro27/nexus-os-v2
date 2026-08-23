"""A small, bounded product-evolution workflow.

This module is an orchestration layer, not a scheduler, agent brain, or
canonical work database.  Mission authors provide the research/build/test/
critic callbacks.  The loop records an auditable mission receipt, refuses
identical retries, and stops at the contract's cycle limit or a real blocker.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional


class FailureClass(str, Enum):
    IMPLEMENTATION_BUG = "IMPLEMENTATION_BUG"
    ENVIRONMENT_BLOCKER = "ENVIRONMENT_BLOCKER"
    CREDENTIAL_BLOCKER = "CREDENTIAL_BLOCKER"
    PROVIDER_BLOCKER = "PROVIDER_BLOCKER"
    LICENSE_BLOCKER = "LICENSE_BLOCKER"
    CAPACITY_BLOCKER = "CAPACITY_BLOCKER"
    HUMAN_HARDWARE_TEST_REQUIRED = "HUMAN_HARDWARE_TEST_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    UNKNOWN = "UNKNOWN"


class Stage(str, Enum):
    CONTRACT = "CONTRACT"
    RESEARCH = "RESEARCH"
    OPTIONS = "OPTIONS"
    PLAN = "PLAN"
    BUILD = "BUILD"
    TEST = "TEST"
    BROWSER = "BROWSER"
    CRITIC = "CRITIC"
    REGRESSION = "REGRESSION"
    SECURITY_LICENSE = "SECURITY_LICENSE"
    PREVIEW = "PREVIEW"
    VERIFY = "VERIFY"


@dataclass(frozen=True)
class MissionContract:
    goal: str
    user_visible_outcome: str
    acceptance_criteria: List[str]
    locked_systems: List[str] = field(default_factory=list)
    allowed_files: List[str] = field(default_factory=list)
    capability_candidates: List[str] = field(default_factory=list)
    security_boundaries: List[str] = field(default_factory=list)
    license_requirements: List[str] = field(default_factory=list)
    cost_ceiling: str = "$0 recurring unless explicitly approved"
    max_cycles: int = 5
    deployment_policy: str = "preview-first; production only under existing governance"
    human_only_gates: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.goal.strip() or not self.user_visible_outcome.strip():
            raise ValueError("goal and user_visible_outcome are required")
        if not self.acceptance_criteria:
            raise ValueError("at least one acceptance criterion is required")
        if not 1 <= self.max_cycles <= 5:
            raise ValueError("max_cycles must be between 1 and 5")


@dataclass
class MissionResult:
    mission_id: str
    status: str
    cycles: int
    stages: List[Dict[str, Any]]
    failures: List[Dict[str, Any]]
    critic: Dict[str, Any]
    receipt_path: Optional[str] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


class ProductEvolutionLoop:
    """Run a bounded mission with explicit callbacks and repair evidence."""

    def __init__(self, *, receipt_dir: Optional[Path] = None) -> None:
        self.receipt_dir = receipt_dir

    def run(
        self,
        contract: MissionContract,
        *,
        mission_id: str,
        stages: Mapping[Stage, Callable[[], Mapping[str, Any]]],
        critic: Callable[[MissionContract, List[Dict[str, Any]]], Mapping[str, Any]],
        repair: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None,
    ) -> MissionResult:
        evidence: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []
        seen_failures: set[str] = set()
        cycles = 0
        status = "PASS"
        last_critic: Dict[str, Any] = {}

        while cycles < contract.max_cycles:
            cycles += 1
            cycle: Dict[str, Any] = {"cycle": cycles, "started_at": _now(), "stages": []}
            for stage in Stage:
                callback = stages.get(stage)
                if callback is None:
                    continue
                try:
                    result = dict(callback())
                    result.setdefault("status", "PASS")
                    result["stage"] = stage.value
                    cycle["stages"].append(result)
                    evidence.append(result)
                    if result.get("status") in {"BLOCKED", "FAIL"}:
                        failure = self._failure(stage, result)
                        fingerprint = _fingerprint(failure)
                        failure["fingerprint"] = fingerprint
                        failures.append(failure)
                        cycle["failure"] = failure
                        if fingerprint in seen_failures or repair is None:
                            status = "PARTIAL" if failure["class"] in {
                                FailureClass.HUMAN_HARDWARE_TEST_REQUIRED.value,
                                FailureClass.CREDENTIAL_BLOCKER.value,
                                FailureClass.APPROVAL_REQUIRED.value,
                            } else "FAIL"
                            cycle["ended_at"] = _now()
                            evidence.append(cycle)
                            result_obj = self._result(mission_id, status, cycles, evidence, failures, last_critic)
                            return self._write(result_obj, contract)
                        seen_failures.add(fingerprint)
                        repair_result = dict(repair(failure))
                        repair_result["stage"] = "REPAIR"
                        repair_result["cycle"] = cycles
                        evidence.append(repair_result)
                        cycle["repair"] = repair_result
                        if repair_result.get("status") == "BLOCKED":
                            status = "PARTIAL"
                            cycle["ended_at"] = _now()
                            evidence.append(cycle)
                            return self._write(self._result(mission_id, status, cycles, evidence, failures, last_critic), contract)
                        break
                except Exception as exc:  # callbacks are deliberately isolated
                    failure = {
                        "stage": stage.value,
                        "class": FailureClass.IMPLEMENTATION_BUG.value,
                        "error": str(exc)[:500],
                    }
                    fingerprint = _fingerprint(failure)
                    failure["fingerprint"] = fingerprint
                    failures.append(failure)
                    if fingerprint in seen_failures or repair is None:
                        status = "FAIL"
                        cycle["failure"] = failure
                        cycle["ended_at"] = _now()
                        evidence.append(cycle)
                        return self._write(self._result(mission_id, status, cycles, evidence, failures, last_critic), contract)
                    seen_failures.add(fingerprint)
                    cycle["repair"] = dict(repair(failure))
                    break
            else:
                last_critic = dict(critic(contract, evidence))
                evidence.append({"stage": Stage.CRITIC.value, "cycle": cycles, **last_critic})
                cycle["critic"] = last_critic
                if last_critic.get("status") == "PASS":
                    cycle["ended_at"] = _now()
                    evidence.append(cycle)
                    return self._write(self._result(mission_id, "PASS", cycles, evidence, failures, last_critic), contract)
                failure = {
                    "stage": Stage.CRITIC.value,
                    "class": last_critic.get("failure_class", FailureClass.UNKNOWN.value),
                    "error": last_critic.get("summary", "Product critic did not pass"),
                    "scores": last_critic.get("scores", {}),
                }
                fingerprint = _fingerprint(failure)
                failure["fingerprint"] = fingerprint
                failures.append(failure)
                cycle["failure"] = failure
                if fingerprint in seen_failures or repair is None:
                    status = "PARTIAL" if failure["class"] in {
                        FailureClass.HUMAN_HARDWARE_TEST_REQUIRED.value,
                        FailureClass.CREDENTIAL_BLOCKER.value,
                    } else "FAIL"
                    cycle["ended_at"] = _now()
                    evidence.append(cycle)
                    return self._write(self._result(mission_id, status, cycles, evidence, failures, last_critic), contract)
                seen_failures.add(fingerprint)
                cycle["repair"] = dict(repair(failure))
            cycle["ended_at"] = _now()
            evidence.append(cycle)

        status = "PARTIAL" if failures else "PASS"
        return self._write(self._result(mission_id, status, cycles, evidence, failures, last_critic), contract)

    @staticmethod
    def _failure(stage: Stage, result: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "stage": stage.value,
            "class": str(result.get("failure_class", FailureClass.UNKNOWN.value)),
            "error": str(result.get("error", result.get("summary", "stage failed")))[:500],
        }

    def _result(self, mission_id: str, status: str, cycles: int, evidence: List[Dict[str, Any]], failures: List[Dict[str, Any]], critic: Dict[str, Any]) -> MissionResult:
        return MissionResult(mission_id, status, cycles, evidence, failures, critic)

    def _write(self, result: MissionResult, contract: MissionContract) -> MissionResult:
        if self.receipt_dir is None:
            return result
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        path = self.receipt_dir / f"{result.mission_id}.json"
        payload = {"contract": asdict(contract), "result": asdict(result), "created_at": _now()}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result.receipt_path = str(path)
        return result
