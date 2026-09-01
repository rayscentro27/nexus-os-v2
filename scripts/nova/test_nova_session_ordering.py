import threading
import time

from nova_telegram_worker import _acquire_chat_lock, _is_progress_only_response, _release_chat_lock


def test_same_chat_lock_waits_for_existing_owner(monkeypatch, tmp_path):
    monkeypatch.setattr("nova_telegram_worker.NOVA_STATE_DIR", str(tmp_path))
    first = _acquire_chat_lock("chat", wait_seconds=1)
    acquired = []

    def contender():
        acquired.append(_acquire_chat_lock("chat", wait_seconds=2))

    thread = threading.Thread(target=contender)
    thread.start()
    time.sleep(0.15)
    assert not acquired
    _release_chat_lock("chat")
    thread.join(timeout=2)
    assert acquired and acquired[0].endswith("chat_chat.lock")
    _release_chat_lock("chat")


def test_dead_lock_owner_is_recovered(monkeypatch, tmp_path):
    monkeypatch.setattr("nova_telegram_worker.NOVA_STATE_DIR", str(tmp_path))
    lock_dir = tmp_path / "nova_locks"
    lock_dir.mkdir()
    lock = lock_dir / "chat_dead.lock"
    lock.write_text("999999999\n")
    acquired = _acquire_chat_lock("dead", wait_seconds=1)
    assert acquired.endswith("chat_dead.lock")
    _release_chat_lock("dead")


def test_progress_only_model_output_is_not_a_terminal_answer():
    assert _is_progress_only_response("Let me check Nexus. Please hold on a moment.", [])
    assert not _is_progress_only_response("There are no current blockers.", [])
    assert not _is_progress_only_response("Please hold on.", ["nexus_get_blockers"])
