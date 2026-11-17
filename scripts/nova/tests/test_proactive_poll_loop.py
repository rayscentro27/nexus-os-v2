from __future__ import annotations

import signal

from nova import nova_telegram_worker as worker


def test_persistent_worker_checks_proactive_events_in_existing_poll_loop(monkeypatch):
    handlers = {}
    checks = []

    monkeypatch.setattr(worker.signal, "signal", lambda sig, handler: handlers.update({sig: handler}))
    monkeypatch.setattr(worker, "write_status", lambda *_args: None)
    monkeypatch.setattr(worker, "_retry_pending_deliveries", lambda: 0)
    monkeypatch.setattr(worker, "_resume_authorized_missions", lambda: 0)
    monkeypatch.setattr(worker, "_process_proactive_communications", lambda: checks.append("check"))

    def poll(_method, _payload, **_kwargs):
        handlers[signal.SIGTERM](None, None)
        return {"ok": True, "result": []}

    monkeypatch.setattr(worker, "_tg_api", poll)
    monkeypatch.setattr(worker, "load_offset", lambda: 0)

    worker.run_poll()

    # One startup check and one check after the persistent Telegram poll.
    assert checks == ["check", "check"]
