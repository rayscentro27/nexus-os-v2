from contextlib import nullcontext

from nova import nova_telegram_worker as worker


def test_current_lineage_followup_classification_accepts_ordinary_messages():
    lineage = {"project_id": "project_current1", "job_id": "job_current1"}
    assert worker.current_lineage_followup_kind(
        "Nova, create a small internal note and verify it", lineage
    ) is None
    assert worker.current_lineage_followup_kind(
        "What are you working on right now, and what step are you on?", lineage
    ) is None
    assert worker.current_lineage_followup_kind(
        "Nova, check the Research project you just created", lineage
    ) == "READ"
    assert worker.current_lineage_followup_kind("Continue that project", lineage) == "CONTINUE"


def _prepare_status_turn(monkeypatch, delivered):
    monkeypatch.setattr(worker, "_acquire_chat_lock", lambda _chat: True)
    monkeypatch.setattr(worker, "_release_chat_lock", lambda _chat: None)
    monkeypatch.setattr(worker, "is_authorized", lambda *_: True)
    monkeypatch.setattr(worker, "stage_execution", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(worker, "find_linked_objective_assignment", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(worker, "create_mission", lambda *_: (_ for _ in ()).throw(
        AssertionError("read-only status query created a mission")))
    monkeypatch.setattr(worker, "_exact_research_status_response", lambda job_id: (
        f"JOB_ID={job_id}\nSTATE=BLOCKED", 26,
        {"status": "ok", "job": {"job_id": job_id, "correlation_id": "root-existing"}},
    ))
    monkeypatch.setattr(worker, "_deliver_response", delivered)


def test_repeated_status_replies_get_fresh_governor_identities(monkeypatch, tmp_path):
    from nexus_agent_platform import provider_enforcement

    reservations, message_counter = set(), iter((700, 701, 702))

    def execute(provider, service, capability, estimate, operation, *, job_id=None,
                job_type="", correlation_id=None, purpose="", **_kwargs):
        key = (provider, job_id, purpose)
        if key in reservations:
            raise AssertionError("reservation replay")
        reservations.add(key)
        return operation()

    monkeypatch.setattr(provider_enforcement, "authorize_telegram_action", lambda *_a, **_k: "RAY_NOTIFICATION")
    monkeypatch.setattr(provider_enforcement, "execute", execute)
    monkeypatch.setattr(worker, "NOVA_DELIVERY_DIR", str(tmp_path))

    def send_attempt(chat_id, _chunk, **_kwargs):
        body = provider_enforcement.execute_telegram_delivery(
            chat_id, lambda: {"ok": True, "result": {"message_id": next(message_counter)}},
        )
        return {"ok": True, "message_id": body["result"]["message_id"]}

    monkeypatch.setattr(worker, "_tg_send_attempt", send_attempt)
    _prepare_status_turn(monkeypatch, worker._deliver_response)

    # Reserve the initial acknowledgement once under its own mission identity.
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "original-mission")
    monkeypatch.setenv("NEXUS_JOB_TYPE", "NOVA_TELEGRAM_DELIVERY")
    monkeypatch.setenv("NEXUS_CORRELATION_ID", "root-existing")
    provider_enforcement.execute_telegram_delivery(
        7, lambda: {"ok": True, "result": {"message_id": next(message_counter)}},
    )

    request = "Nova, check the current state of job_example123."
    for update_id in (101, 102):
        assert worker._process_message_inner(
            {}, {}, {"id": 7}, {"id": 8}, 7, 8, "ray", request, update_id,
        ) is True

    assert len(reservations) == 3
    assert {key[1] for key in reservations} == {
        "original-mission", "nova-telegram-update-101", "nova-telegram-update-102",
    }
    assert all(worker._load_delivery(update_id)["state"] == "DELIVERED" for update_id in (101, 102))


def test_status_failure_is_logged_as_failure_not_delivery(monkeypatch):
    logs, errors = [], []
    _prepare_status_turn(monkeypatch, lambda *_args, **_kwargs: {
        "state": "FAILED_TERMINAL", "message_ids": [], "last_error": "RESERVATION_REPLAY_DENIED",
    })
    monkeypatch.setattr(worker, "_log", logs.append)
    monkeypatch.setattr(worker, "_log_error", errors.append)
    assert worker._process_message_inner(
        {}, {}, {"id": 7}, {"id": 8}, 7, 8, "ray",
        "Nova, check the current state of job_example123.", 103,
    ) is True
    assert not any("status delivered" in line for line in logs)
    assert any("state=FAILED_TERMINAL" in line and "RESERVATION_REPLAY_DENIED" in line for line in errors)


def test_missing_telegram_credential_still_fails_before_provider(monkeypatch):
    monkeypatch.setattr(worker, "get_env", lambda: {})
    result = worker._tg_send_attempt("42", "safe test", token=None)
    assert result == {"ok": False, "retryable": False, "error": "telegram_token_missing"}
