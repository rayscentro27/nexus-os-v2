from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from nexus_product_evolution.release import approve_release, authorize_release_retry, bounded_deploy, create_release_candidate, parse_release_approval, parse_release_retry_authorization, prepare_release, repair_approved_release_binding, verify_or_rollback
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


def test_second_retry_requires_exact_ray_bound_authorization():
    import subprocess
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    package = create_release_candidate({"result": _result()}, candidate_commit=commit)
    package.update({"precheck_status": "PASS", "rollback_target": "deploy-known", "rollback_deploy_id": "deploy-known", "rollback_verified_url": "https://known-good.example", "rollback_executable": "PASS", "exact_sha_deploy_available": "PASS"})
    approved = approve_release(prepare_release(_result(), package), release_id=package["release_id"], commit=commit, target=package["target_url"])
    bound = repair_approved_release_binding(approved["result"])
    blocked = dict(bound["result"])
    blocked["release"] = {**blocked["release"], "retry_count": 1}
    blocked.update({"status": "BLOCKED", "current_stage": "BLOCKED", "blocker": "NETLIFY_AUTH_UNAVAILABLE"})
    authorized = authorize_release_retry(blocked, release_id=package["release_id"], commit=commit, target=package["target_url"], current_production_deploy="deploy-known", preflight_status="PASS", auth_status="PASS", rollback_executable="PASS", now=datetime.now(timezone.utc))
    assert authorized["status"] == "AUTHORIZED"
    assert authorized["result"]["release"]["second_retry_authorization"]["status"] == "PENDING"
    replay = authorize_release_retry(authorized["result"], release_id=package["release_id"], commit=commit, target=package["target_url"], current_production_deploy="deploy-known", preflight_status="PASS", auth_status="PASS", rollback_executable="PASS")
    assert replay["reason"] == "RETRY_AUTHORIZATION_REPLAY"
    assert authorize_release_retry(blocked, release_id=package["release_id"], commit="0" * 40, target=package["target_url"], current_production_deploy="deploy-known", preflight_status="PASS", auth_status="PASS", rollback_executable="PASS")["reason"] == "RETRY_RELEASE_BINDING_MISMATCH"


def test_second_retry_command_parser_is_exactly_bound():
    text = "AUTHORIZE RELEASE RETRY rel-telegram-release-test-abcdef123456 " + "a" * 40 + " https://goclearonline.cc"
    parsed = parse_release_retry_authorization(text)
    assert parsed["release_id"] == "rel-telegram-release-test-abcdef123456"
    assert parsed["commit"] == "a" * 40
    assert parsed["target"] == "https://goclearonline.cc"
    assert parse_release_retry_authorization("AUTHORIZE RELEASE RETRY rel-other-abcdef123456 " + "a" * 40 + " https://evil.example") is not None
    assert classify_product_evolution_request(text) == "RELEASE_RETRY_AUTHORIZATION"


def test_release_only_retry_cannot_be_claimed_as_generic_mission_and_is_consumed_once(tmp_path, monkeypatch):
    import json
    import subprocess
    from nexus_product_evolution import consumer
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    package = create_release_candidate({"result": _result()}, candidate_commit=commit)
    package.update({"precheck_status": "PASS", "rollback_target": "deploy-known", "rollback_deploy_id": "deploy-known", "rollback_verified_url": "https://known-good.example", "rollback_executable": "PASS", "exact_sha_deploy_available": "PASS"})
    approved = approve_release(prepare_release(_result(), package), release_id=package["release_id"], commit=commit, target=package["target_url"])
    bound = repair_approved_release_binding(approved["result"])
    blocked = dict(bound["result"])
    blocked.update({"status": "BLOCKED", "current_stage": "BLOCKED", "blocker": "NETLIFY_AUTH_UNAVAILABLE"})
    blocked["release"] = {**blocked["release"], "retry_count": 1}
    authorized = authorize_release_retry(blocked, release_id=package["release_id"], commit=commit, target=package["target_url"], current_production_deploy="deploy-known", preflight_status="PASS", auth_status="PASS", rollback_executable="PASS", now=datetime.now(timezone.utc))
    receipt = tmp_path / "release.json"
    receipt.write_text(json.dumps({"result": authorized["result"]}), encoding="utf-8")
    generic = consumer._claim(receipt, "phase15-test")
    assert generic["claimed"] is False
    monkeypatch.setattr(consumer, "inspect_netlify_control_plane", lambda: {"published_deploy_id": "deploy-known", "published_commit": "UNKNOWN"})
    deploy_calls = []
    verify = lambda record, sha, target: {"https": "PASS", "admin": "PASS", "production_commit": sha, "voice_marker": "PASS", "persistent_preview_guard": "PASS", "old_marker_absent": "PASS", "cors": "PASS"}
    first = consumer._dispatch_approved_release(receipt, "phase15-test", deploy_fn=lambda sha, target: (deploy_calls.append((sha, target)) or {"status": "PASS"}), verify_fn=verify, rollback_fn=lambda target: {"status": "PASS"})
    assert first["claimed"] is True
    saved = json.loads(receipt.read_text(encoding="utf-8"))["result"]
    assert saved["release"]["retry_count"] == 2
    assert saved["release"]["second_retry_authorization"]["status"] == "CONSUMED"
    second = consumer._dispatch_approved_release(receipt, "phase15-test", deploy_fn=lambda *_: {"status": "PASS"}, verify_fn=verify, rollback_fn=lambda target: {"status": "PASS"})
    assert second["claimed"] is False
    assert len(deploy_calls) == 1


def test_dispatch_blocks_when_production_changes_after_retry_authorization(tmp_path, monkeypatch):
    import json
    import subprocess
    from nexus_product_evolution import consumer
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    package = create_release_candidate({"result": _result()}, candidate_commit=commit)
    package.update({"precheck_status": "PASS", "rollback_target": "deploy-known", "rollback_deploy_id": "deploy-known", "rollback_verified_url": "https://known-good.example", "rollback_executable": "PASS", "exact_sha_deploy_available": "PASS"})
    approved = approve_release(prepare_release(_result(), package), release_id=package["release_id"], commit=commit, target=package["target_url"])
    bound = repair_approved_release_binding(approved["result"])
    blocked = dict(bound["result"]); blocked.update({"status": "BLOCKED", "current_stage": "BLOCKED"}); blocked["release"] = {**blocked["release"], "retry_count": 1}
    authorized = authorize_release_retry(blocked, release_id=package["release_id"], commit=commit, target=package["target_url"], current_production_deploy="deploy-known", preflight_status="PASS", auth_status="PASS", rollback_executable="PASS", now=datetime.now(timezone.utc))
    receipt = tmp_path / "release.json"; receipt.write_text(json.dumps({"result": authorized["result"]}), encoding="utf-8")
    monkeypatch.setattr(consumer, "inspect_netlify_control_plane", lambda: {"published_deploy_id": "new-deploy", "published_commit": "UNKNOWN"})
    result = consumer._dispatch_approved_release(receipt, "phase15-test", deploy_fn=lambda *_: {"status": "PASS"})
    assert result["claimed"] is False
    saved = json.loads(receipt.read_text(encoding="utf-8"))["result"]
    assert saved["blocker"] == "PRODUCTION_STATE_CHANGED_AFTER_RETRY_AUTHORIZATION"
    assert saved["release"]["second_retry_authorization"]["status"] == "INVALIDATED"


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


def test_authenticated_deploy_verify_failure_rolls_back_without_stale_auth_blocker():
    commit = "a" * 40
    result = {
        "status": "PARTIAL",
        "current_stage": "PRODUCTION_VERIFY",
        "blocker": None,
        "release": {
            "release_id": "rel-historical-test-abcdef123456",
            "release_candidate_commit": commit,
            "target_url": "https://goclearonline.cc",
            "approval_state": "APPROVED",
            "rollback_target": "known-good-deploy",
            "deployment_result": {"status": "DEPLOYED", "outcome": {"status": "PASS", "deploy_id": "candidate-deploy", "artifact_hash": "artifact"}},
        },
    }
    observed = {
        "https": "PASS", "admin": "PASS", "production_commit": commit,
        "voice_marker": "PASS", "persistent_preview_guard": "FAIL",
        "old_marker_absent": "PASS", "cors": "PASS",
        "failure_reason": "PRODUCTION_PERSISTENT_PREVIEW_GUARD_FAILED",
    }
    rollback_calls = []
    outcome = verify_or_rollback(result, release_id=result["release"]["release_id"], expected_commit=commit, observed=observed, rollback_fn=lambda target: (rollback_calls.append(target) or {"status": "PASS", "deploy_id": target}))
    saved = outcome["result"]
    assert outcome["status"] == "BLOCKED"
    assert saved["blocker"] == "PRODUCTION_PERSISTENT_PREVIEW_GUARD_FAILED"
    assert saved["release"]["candidate_currently_live"] is False
    assert saved["release"]["production_commit_after"] == "UNKNOWN"
    assert saved["release"]["production_deploy_id"] == "known-good-deploy"
    assert saved["release"]["rollback_result"]["status"] == "PASS"
    assert rollback_calls == ["known-good-deploy"]


def test_bounded_propagation_accepts_candidate_on_second_read(monkeypatch):
    from nexus_product_evolution import deployment
    commit = "c" * 40
    marker = deployment.VOICE_RUNTIME_CONTRACT_MARKER
    old = {"http_status": 200, "assets": [{"status": 200, "body": "NEXUS_BUILD_COMMIT:old"}]}
    new = {"http_status": 200, "assets": [{"status": 200, "body": f"NEXUS_BUILD_COMMIT:{commit}|{marker}"}]}
    reads = iter([old, new])
    monkeypatch.setattr(deployment, "_fetch_application_bundles", lambda *_: next(reads))
    monkeypatch.setattr(deployment, "_cors_options", lambda *_: (204, {"access-control-allow-origin": "https://goclearonline.cc"}))
    result = deployment._production_verification(commit, "https://goclearonline.cc", "candidate-deploy", control_plane={"published_deploy_id": "candidate-deploy"})
    assert result["status"] == "PASS"
    assert result["propagation_attempts"] == 2
