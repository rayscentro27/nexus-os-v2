from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from nexus_product_evolution import telegram_control as control
from nexus_product_evolution import deployment


REAL_DEPLOYMENT_REQUEST = """Nexus, inspect the existing Voice Product Evolution mission and production deployment state. Do not create a new mission. My latest human test still shows preview 429 responses. Commit 68771666ec03f61b2910f4e4b1a2f8a3733e3807 disables rolling preview STT. Determine whether production is stale, identify the deployed commit/build, compare it with origin/main, and verify the production bundle."""


def test_operation_action_wins_over_human_test_subject():
    assert control.classify_product_evolution_request(REAL_DEPLOYMENT_REQUEST) == "DEPLOYMENT_INSPECTION"
    assert control.classify_product_evolution_request("I tested Voice and it failed.") == "RESUME_WITH_HUMAN_EVIDENCE"
    assert control.classify_product_evolution_request("Record the 429 test as FAIL.") == "RESUME_WITH_HUMAN_EVIDENCE"
    assert control.classify_product_evolution_request("Deploy the already-tested commit if governance permits.") == "DEPLOYMENT_RECONCILIATION"


def test_inspection_records_stale_bundle_without_fabricating_commit(monkeypatch):
    record = {"result": {"mission_id": "telegram-test", "execution_history": []}}
    monkeypatch.setattr(deployment, "_git", lambda *args: "68771666ec03f61b2910f4e4b1a2f8a3733e3807")
    html = b'<script type="module" src="/assets/app.js"></script>'
    bundle = b"unversioned unknown legacy Voice bundle"
    monkeypatch.setattr(deployment, "_fetch", lambda url: (200, {"x-nf-request-id": "safe-id"}, html if url.endswith("/admin") else bundle))
    inspected = deployment.inspect_deployment(record)
    assert inspected["deployment"]["deployed_commit"] == "UNKNOWN"
    assert inspected["deployment"]["stale_production"] == "YES"
    assert inspected["deployment"]["deployment_status"] == "DEPLOYMENT_STALE"
    assert any(item["event"] == "DEPLOYMENT_STALE" for item in inspected["execution_history"])


def test_candidate_verification_uses_stable_contract_across_all_assets(monkeypatch):
    commit = "a" * 40
    marker = deployment.VOICE_RUNTIME_CONTRACT_MARKER
    monkeypatch.setattr(deployment, "_fetch_application_bundles", lambda *_: {
        "http_status": 200,
        "assets": [
            {"url": "https://candidate/assets/vendor.js", "status": 200, "body": "unrelated chunk"},
            {"url": "https://candidate/assets/app.js", "status": 200, "body": f"NEXUS_BUILD_COMMIT:{commit}|{marker}"},
        ],
    })
    monkeypatch.setattr(deployment, "_cors_options", lambda *_: (204, {"access-control-allow-origin": "https://goclearonline.cc"}))
    result = deployment.verify_candidate_artifact("https://candidate", commit)
    assert result["status"] == "PASS"
    assert result["markers"]["build_sha"] == commit
    assert result["markers"]["persistent_rolling_preview"] == "DISABLED"
    assert result["markers"]["final_stt_after_silence"] == "ENABLED"
    assert result["markers"]["private_local_vad"] == "ENABLED"


def test_candidate_verification_does_not_require_minified_source_identifier(monkeypatch):
    commit = "b" * 40
    monkeypatch.setattr(deployment, "_fetch_application_bundles", lambda *_: {
        "http_status": 200,
        "assets": [{"status": 200, "body": f"NEXUS_BUILD_COMMIT:{commit}|{deployment.VOICE_RUNTIME_CONTRACT_MARKER}"}],
    })
    monkeypatch.setattr(deployment, "_cors_options", lambda *_: (204, {"access-control-allow-origin": "https://goclearonline.cc"}))
    result = deployment.verify_candidate_artifact("https://candidate", commit)
    assert result["status"] == "PASS"
