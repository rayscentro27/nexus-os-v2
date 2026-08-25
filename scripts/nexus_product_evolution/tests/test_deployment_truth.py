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
