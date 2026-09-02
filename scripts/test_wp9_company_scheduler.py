import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.wp9_company_scheduler as scheduler


def test_authority_is_internal_only():
    value = scheduler.authority()
    assert value["new_paid_spend"] is False
    assert value["live_trading"] is False
    assert value["client_production_mutation"] is False


def test_cycle_ids_are_unique():
    assert scheduler.cycle_id() != scheduler.cycle_id()


def test_state_defaults_pending():
    path = Path("/tmp/wp9-test-state.json")
    path.unlink(missing_ok=True)
    old = scheduler.STATE
    scheduler.STATE = path
    try:
        assert scheduler.state()["certification_state"] == "PENDING_NIGHT_1"
    finally:
        scheduler.STATE = old
        path.unlink(missing_ok=True)


def test_transport_receipts_redact_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler, "RUNTIME", tmp_path)
    monkeypatch.setenv("HERMES_NOVA_TELEGRAM_BOT_TOKEN", "")
    receipt = scheduler.send_telegram("test", event_type="WARNING", cycle="c", dry_run=False)
    assert receipt["status"] == "BLOCKED_NOT_CONFIGURED"
    assert "token" not in json.dumps(receipt).lower()
