from contextlib import nullcontext

from nova import nova_telegram_worker as worker


def test_operator_route_gate_initializes_lineage_reference_for_ordinary_turns():
    lineage = {"case_id": "case-current", "project_id": "project-current"}

    should_route, lineage_reference = worker._operator_route_gate(
        False, "good afternoon nova", lineage, None,
    )

    assert should_route is False
    assert lineage_reference is False


def test_pre_mission_exception_uses_durable_owner_delivery_identity(monkeypatch):
    from nova import semantic_orchestration

    mission = {"mission_id": "mission-update-900", "correlation_id": "corr-update-900"}
    observed = {}

    monkeypatch.setattr(worker, "_acquire_chat_lock", lambda _chat_id: True)
    monkeypatch.setattr(worker, "_release_chat_lock", lambda _chat_id: None)
    monkeypatch.setattr(worker, "is_authorized", lambda *_args: True)
    monkeypatch.setattr(worker, "stage_execution", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(worker, "create_mission", lambda *_args: dict(mission))
    monkeypatch.setattr(worker, "update_mission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(semantic_orchestration, "resolve_owner_request", lambda _text: (_ for _ in ()).throw(
        RuntimeError("fixture failure before mission creation")))
    monkeypatch.setattr(worker, "_log_error", lambda _message: None)

    def deliver(update_id, chat_id, response, *, mission_id=None, **_kwargs):
        observed.update({
            "update_id": update_id,
            "chat_id": chat_id,
            "response": response,
            "mission_id": mission_id,
            "durable_job_id": worker.os.environ.get("NEXUS_DURABLE_JOB_ID"),
            "correlation_id": worker.os.environ.get("NEXUS_CORRELATION_ID"),
        })
        return {"state": "DELIVERED", "message_ids": [901]}

    monkeypatch.setattr(worker, "_deliver_response", deliver)

    assert worker._process_message_inner(
        {}, {}, {"id": 7}, {"id": 8}, 7, 8, "ray", "good afternoon nova", 900,
    ) is True

    assert observed["update_id"] == 900
    assert observed["mission_id"] == "mission-update-900"
    assert observed["durable_job_id"] == "nova-telegram-update-900"
    assert observed["correlation_id"] == "corr-update-900"
    assert "couldn't complete that request" in observed["response"]
