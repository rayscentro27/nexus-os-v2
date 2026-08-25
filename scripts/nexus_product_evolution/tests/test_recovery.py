from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from nexus_product_evolution.recovery import (
    MAX_REPAIR_CYCLES,
    build_repair_contract,
    classify_release_failure,
    make_failure_receipt,
    repair_task_spec,
    run_recovery_cycle,
)
from nexus_product_evolution.deployment_strategy import strategy_failover_recommendation


COMMIT = "c63ad3197ddf63ecbbb323f35fba3ed284d80f26"
RELEASE = "rel-telegram-20260824172054-077bf5a7-c63ad3197ddf"


def failure(code="CANDIDATE_DEPLOY_URL_MISSING"):
    return {"failure_code": code, "phase": "candidate_artifact", "release_id": RELEASE, "candidate_sha": COMMIT, "candidate_deploy_id": "candidate-deploy", "production_deploy_before": "rollback-deploy", "reversible": True}


def test_failure_taxonomy_and_receipt_are_bounded():
    classified = classify_release_failure(failure())
    assert classified["failure_class"] == "CANDIDATE_URL"
    assert classified["repairable_internal"] is True
    receipt = make_failure_receipt(failure())
    assert receipt["failure_class"] == "CANDIDATE_URL"
    assert receipt["signature"]
    assert make_failure_receipt(failure())["signature"] == receipt["signature"]


def test_unrepairable_external_failure_stops_for_human():
    assert build_repair_contract(failure("NETLIFY_AUTH_UNAVAILABLE")) is None


def test_repair_task_reuses_bounded_builder_shape():
    task = repair_task_spec(failure(), starting_commit=COMMIT, mission_id="telegram-20260824172054-077bf5a7")
    assert task is not None
    assert task.max_retries == MAX_REPAIR_CYCLES - 1
    assert task.metadata["starting_commit"] == COMMIT
    assert "runtime.env" in task.protected_paths


def test_recovery_simulation_stops_at_new_candidate_and_never_deploys():
    calls = []
    def stage(name):
        def run(_contract):
            calls.append(name)
            return {"status": "PASS"}
        return run
    result = run_recovery_cycle(
        failure(), prior_cycles=0,
        build_fn=stage("builder"), test_fn=stage("tests"),
        preflight_fn=stage("preflight"), draft_verify_fn=stage("draft"),
        candidate_fn=stage("candidate"),
    )
    assert result["status"] == "RELEASE_CANDIDATE_READY"
    assert result["ray_interruption"] == "APPROVAL_ONLY"
    assert calls == ["builder", "tests", "preflight", "draft", "candidate"]


def test_recovery_cycle_limit_prevents_infinite_repair():
    result = run_recovery_cycle(
        failure(), prior_cycles=MAX_REPAIR_CYCLES,
        build_fn=lambda _: {"status": "PASS"}, test_fn=lambda _: {"status": "PASS"},
        preflight_fn=lambda _: {"status": "PASS"}, draft_verify_fn=lambda _: {"status": "PASS"},
        candidate_fn=lambda _: {"status": "PASS"},
    )
    assert result["status"] == "REPAIR_EXHAUSTED"


def test_failover_requires_independent_transport_failures_across_releases():
    failures = [{"failure_class": "DEPLOY_UPLOAD", "release_id": "r1"}, {"failure_class": "DEPLOY_CLI", "release_id": "r1"}, {"failure_class": "DEPLOY_AUTH", "release_id": "r2"}]
    result = strategy_failover_recommendation(failures)
    assert result["eligible"] is True
    assert result["activation"] == "DISABLED"
