from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from nexus_product_evolution.release import approve_release, bounded_deploy, create_release_candidate, parse_release_approval, prepare_release, verify_or_rollback
from nexus_product_evolution.telegram_control import classify_product_evolution_request


def _result():
    return {"mission_id": "telegram-release-test", "execution": {"builder": {"attempts": [{"status": "pass"}]}}, "deployment": {"deployment_status": "DEPLOYMENT_STALE", "deployed_commit": "UNKNOWN"}}


def test_release_candidate_is_exact_sha_and_target_bound():
    import subprocess
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    package = create_release_candidate({"result": _result()}, candidate_commit=commit)
    assert package["immutable_sha"] is True
    assert package["target_bound"] is True
    assert package["release_candidate_commit"] == commit
    assert package["risk_classification"] == "Level 3 / blocked_high_risk"


def test_approval_requires_exact_release_id_sha_and_target():
    import subprocess
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    package = create_release_candidate({"result": _result()}, candidate_commit=commit)
    package.update({"precheck_status": "PASS", "rollback_target": "deploy-known", "rollback_deploy_id": "deploy-known", "rollback_verified_url": "https://known-good.example", "rollback_executable": "PASS", "exact_sha_deploy_available": "PASS"})
    result = prepare_release(_result(), package)
    rejected = approve_release(result, release_id=package["release_id"], commit="0" * 40, target=package["target_url"])
    assert rejected["status"] == "REJECTED"
    approved = approve_release(result, release_id=package["release_id"], commit=commit, target=package["target_url"])
    assert approved["status"] == "APPROVED"
    blocked = bounded_deploy(approved["result"], release_id=package["release_id"], commit=commit, target=package["target_url"], deploy_fn=lambda *_: {"status": "PASS"})
    assert blocked["status"] == "DEPLOYED"


def test_unknown_rollback_blocks_deploy_and_moving_target_is_rejected():
    import subprocess
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    package = create_release_candidate({"result": _result()}, candidate_commit=commit)
    package.update({"precheck_status": "PASS", "rollback_target": "UNKNOWN", "rollback_deploy_id": "UNKNOWN", "rollback_verified_url": "UNKNOWN", "rollback_executable": "PASS", "exact_sha_deploy_available": "PASS"})
    result = prepare_release(_result(), package)
    approved = approve_release(result, release_id=package["release_id"], commit=commit, target=package["target_url"])
    assert bounded_deploy(approved["result"], release_id=package["release_id"], commit=commit, target=package["target_url"], deploy_fn=lambda *_: {"status": "PASS"})["reason"] == "ROLLBACK_TARGET_UNKNOWN"
    moving = {"release": {"rollback_target": "main"}}
    outcome = verify_or_rollback(moving, release_id="rel-test", expected_commit=commit, observed={"https": "PASS"}, rollback_fn=lambda target: {"status": "PASS"})
    assert outcome["rollback"]["reason"] == "ROLLBACK_TARGET_UNKNOWN_OR_MOVING"


def test_approval_parser_and_verification_rollback():
    parsed = parse_release_approval("APPROVE RELEASE rel-telegram-release-test-abcdef123456 0123456789abcdef0123456789abcdef01234567 https://goclearonline.cc")
    assert parsed["release_id"].startswith("rel-")
    result = {"release": {"rollback_target": "known-good", "verification_result": "NOT_RUN"}}
    outcome = verify_or_rollback(result, release_id="rel-test", expected_commit="abc", observed={"https": "PASS", "admin": "FAIL"}, rollback_fn=lambda target: {"status": "PASS", "target": target})
    assert outcome["status"] == "BLOCKED"
    assert outcome["rollback"]["status"] == "PASS"
    assert outcome["result"]["current_stage"] == "BLOCKED"


def test_telegram_release_approval_is_first_class():
    assert classify_product_evolution_request("APPROVE RELEASE rel-telegram-release-test-abcdef123456 0123456789abcdef0123456789abcdef01234567 https://goclearonline.cc") == "RELEASE_APPROVAL"


def test_canonical_release_dispatch_claims_once(monkeypatch, tmp_path):
    import json
    import subprocess
    from nexus_product_evolution import consumer
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    package = create_release_candidate({"result": _result()}, candidate_commit=commit)
    package.update({"precheck_status": "PASS", "rollback_target": "deploy-known", "rollback_deploy_id": "deploy-known", "rollback_verified_url": "https://known-good.example", "rollback_executable": "PASS", "exact_sha_deploy_available": "PASS"})
    approved = approve_release(prepare_release(_result(), package), release_id=package["release_id"], commit=commit, target=package["target_url"])
    receipt = tmp_path / "release.json"
    receipt.write_text(json.dumps({"result": approved["result"]}))
    deploy_calls = []
    deploy = lambda sha, target: (deploy_calls.append((sha, target)) or {"status": "PASS"})
    verify = lambda record, sha, target: {"https": "PASS", "admin": "PASS", "production_commit": sha, "voice_marker": "PASS", "persistent_preview_guard": "PASS", "old_marker_absent": "PASS", "cors": "PASS"}
    first = consumer._dispatch_approved_release(receipt, "phase15-test", deploy_fn=deploy, verify_fn=verify, rollback_fn=lambda target: {"status": "PASS"})
    second = consumer._dispatch_approved_release(receipt, "phase15-test", deploy_fn=deploy, verify_fn=verify, rollback_fn=lambda target: {"status": "PASS"})
    assert first["claimed"] is True
    assert first["status"] == "PASS"
    assert second["claimed"] is False
    assert deploy_calls == [(commit, package["target_url"])]


def test_approved_release_retry_repairs_legacy_fingerprint_once(monkeypatch, tmp_path):
    import json
    from datetime import datetime, timedelta, timezone
    from nexus_product_evolution import consumer
    commit = "a" * 40
    mission = "telegram-retry-test"
    release_id = "rel-telegram-retry-test-abcdef123456"
    receipt = tmp_path / f"{mission}.json"
    now = datetime.now(timezone.utc)
    receipt.write_text(json.dumps({"result": {
        "mission_id": mission,
        "status": "BLOCKED",
        "current_stage": "BLOCKED",
        "execution_history": [
            {"event": "RELEASE_DISPATCH_CLAIMED"},
            {"event": "DEPLOYMENT_STARTED"},
        ],
        "release": {
            "release_id": release_id,
            "release_candidate_commit": commit,
            "target_url": "https://goclearonline.cc",
            "approval_state": "APPROVED",
            "approved_at": now.isoformat(),
            "approval_expires_at": (now + timedelta(hours=1)).isoformat(),
            "changed_paths": [],
            "precheck_status": "PASS",
            "rollback_executable": "PASS",
            "deployment_result": {"status": "BLOCKED", "reason": "MATERIAL_RELEASE_CHANGE"},
        },
    }}), encoding="utf-8")
    monkeypatch.setattr(consumer, "RECEIPT_DIR", tmp_path)
    first = consumer.prepare_approved_release_retry(mission, release_id=release_id, candidate_commit=commit, target="https://goclearonline.cc", current_production_deploy="6a8afe4e3f3b97d82a138f28")
    assert first["status"] == "RETRY_READY"
    value = json.loads(receipt.read_text(encoding="utf-8"))["result"]
    assert value["current_stage"] == "APPROVED_RELEASE_PENDING_DEPLOYMENT"
    assert value["release"]["approval_fingerprint"]
    assert any(item["event"] == "RELEASE_RETRY_READY" for item in value["execution_history"])
    second = consumer.prepare_approved_release_retry(mission, release_id=release_id, candidate_commit=commit, target="https://goclearonline.cc", current_production_deploy="6a8afe4e3f3b97d82a138f28")
    assert second["status"] == "NOT_ELIGIBLE"
