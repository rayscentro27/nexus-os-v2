import json


def _load_worker(monkeypatch):
    import scripts.nova.nova_telegram_worker as worker

    monkeypatch.setattr(worker, "_ENV", {worker.AB_CERTIFICATION_FLAG: "true"})
    return worker


def test_shadow_uses_hermes_interpreter_and_is_idempotent(monkeypatch, tmp_path):
    worker = _load_worker(monkeypatch)
    monkeypatch.setattr(worker, "NOVA_AB_DIR", str(tmp_path))
    monkeypatch.setattr(worker, "HERMES_SHADOW_SCRIPT", "/approved/hermes_shadow.py")
    monkeypatch.setattr(worker, "HERMES_SHADOW_PYTHON", "/approved/hermes/bin/python")
    monkeypatch.setattr(worker.os.path, "isfile", lambda path: True)
    monkeypatch.setattr(worker.os, "access", lambda path, mode: True)
    calls = []

    class Completed:
        returncode = 0
        stderr = ""
        stdout = json.dumps({
            "model": "openai/gpt-4o-mini",
            "final_response": "shadow answer",
            "messages": [],
            "completed": True,
        })

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    message = {"message_id": 77}

    first = worker._run_shadow_ab(900001, message, 123, "What can you help me think through?", primary_run_id="primary-1")
    second = worker._run_shadow_ab(900001, message, 123, "What can you help me think through?", primary_run_id="primary-1")

    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command[:2] == ["/approved/hermes/bin/python", "/approved/hermes_shadow.py"]
    assert kwargs["env"]["NOVA_HERMES_NATIVE_SHADOW"] == "true"
    assert "OPENROUTER_API_KEY" not in kwargs["env"]
    assert first["primary_run_id"] == "primary-1"
    assert first["shadow_run_id"] == first["run_id"]
    assert second["run_id"] == first["run_id"]
    assert first["shadow_telegram_send_count"] == 0


def test_fanout_is_before_governed_terminal_branch():
    from pathlib import Path

    source = Path("scripts/nova/nova_telegram_worker.py").read_text()
    fanout = source.index("ab_record = _run_shadow_ab(")
    governed = source.index("if is_operational_control_intent(text, control):")
    assert fanout < governed


def test_primary_shadow_failure_is_recorded_without_telegram_send(monkeypatch, tmp_path):
    worker = _load_worker(monkeypatch)
    monkeypatch.setattr(worker, "NOVA_AB_DIR", str(tmp_path))
    monkeypatch.setattr(worker, "HERMES_SHADOW_SCRIPT", "/approved/hermes_shadow.py")
    monkeypatch.setattr(worker, "HERMES_SHADOW_PYTHON", "/approved/hermes/bin/python")
    monkeypatch.setattr(worker.os.path, "isfile", lambda path: True)
    monkeypatch.setattr(worker.os, "access", lambda path, mode: True)

    class Failed:
        returncode = 1
        stdout = ""
        stderr = "No module named openai"

    monkeypatch.setattr(worker.subprocess, "run", lambda *args, **kwargs: Failed())
    record = worker._run_shadow_ab(900002, {"message_id": 78}, 123, "Search the internet")

    assert record["shadow"]["runtime_init"] is False
    assert "No module named openai" in record["shadow"]["error"]
    assert record["shadow_telegram_send_count"] == 0
