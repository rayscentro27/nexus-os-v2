import json

from scripts.nexus_product_evolution.loop import MissionContract, ProductEvolutionLoop, Stage
from scripts.nexus_product_evolution import telegram_control


def test_running_loop_honors_receipt_cancel(tmp_path):
    contract = MissionContract(goal="cancel fixture", user_visible_outcome="safe stop", acceptance_criteria=["stop at checkpoint"], max_cycles=3)
    calls = []

    def build():
        calls.append("build")
        path = tmp_path / "cancel-fixture.json"
        value = json.loads(path.read_text())
        value["result"]["control"] = {"action": "cancel"}
        path.write_text(json.dumps(value))
        return {"status": "PASS"}

    result = ProductEvolutionLoop(receipt_dir=tmp_path).run(
        contract,
        mission_id="cancel-fixture",
        stages={Stage.BUILD: build, Stage.TEST: lambda: {"status": "PASS"}},
        critic=lambda _c, _e: {"status": "PASS"},
    )
    assert result.status == "CANCELLED"
    assert calls == ["build"]


def test_terminal_mission_cannot_be_cancelled(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_control, "RECEIPT_DIR", tmp_path)
    path = tmp_path / "done.json"
    path.write_text(json.dumps({"result": {"mission_id": "done", "status": "PASS"}}))
    result = telegram_control.mark_control("done", "cancel")
    assert result["control_result"] == "REJECTED_TERMINAL"
