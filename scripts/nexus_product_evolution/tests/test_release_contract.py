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
    result = prepare_release(_result(), package)
    rejected = approve_release(result, release_id=package["release_id"], commit="0" * 40, target=package["target_url"])
    assert rejected["status"] == "REJECTED"
    approved = approve_release(result, release_id=package["release_id"], commit=commit, target=package["target_url"])
    assert approved["status"] == "APPROVED"
    blocked = bounded_deploy(approved["result"], release_id=package["release_id"], commit=commit, target=package["target_url"], deploy_fn=lambda *_: {"status": "PASS"})
    assert blocked["status"] == "DEPLOYED"


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
