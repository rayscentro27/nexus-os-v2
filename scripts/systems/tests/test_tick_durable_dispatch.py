"""Systems tick reports the durable dispatcher as its own SERVICE health from
the dispatcher's per-run receipts; failure never marks capability loss."""
from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
tick = importlib.import_module("maintenance_tick")

OK = {"started": 0, "ready": 2, "health": {"generated_at": "2026-11-13T14:00:00+00:00", "blocked": 101,
      "running": 0, "expired_leases": 0}, "run": {"status": "OK", "jobs_claimable": 2, "requests_used": 9}}
EXHAUSTED = {"status": "BUDGET_EXHAUSTED", "stage": "dispatch", "at": "2026-11-13T14:00:30+00:00"}


def _setup(monkeypatch, tmp_path, lines, *, age=5, loaded=True, last_exit="0"):
    log = tmp_path / "d.log"
    log.write_text("".join(json.dumps(x) + "\n" for x in lines))
    os.utime(log, (time.time() - age, time.time() - age))
    monkeypatch.setattr(tick, "DISPATCHER_LOG", log)
    monkeypatch.setattr(tick, "DISPATCHER_ERROR_LOG", tmp_path / "missing.log")
    monkeypatch.setattr(tick, "_launchd", lambda label, interval=None: {
        "status": "PASS" if loaded else "FAIL", "loaded": loaded, "interval_seconds": 30, "last_exit": last_exit})


def test_healthy_dispatcher(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, [OK])
    r = tick._durable_dispatch()
    assert (r["status"], r["service_health"], r["queue_health"]) == ("PASS", "HEALTHY", "HEALTHY")
    assert r["blocked_job_count"] == 101 and r["claimable_job_count"] == 2
    assert r["last_success"] == "2026-11-13T14:00:00+00:00" and r["capability_affected"] is False


def test_budget_exhausted_is_degraded_not_capability_loss(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, [OK, EXHAUSTED])
    r = tick._durable_dispatch()
    assert (r["status"], r["service_health"]) == ("ATTENTION", "DEGRADED")
    assert r["last_success"] == "2026-11-13T14:00:00+00:00" and r["last_failure"] == EXHAUSTED["at"]
    assert r["capability"] == "durable_dispatch" and r["capability_affected"] is False


def test_stale_or_unloaded_dispatcher_fails(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, [OK], age=600)
    assert tick._durable_dispatch()["service_health"] == "FAILED"
    _setup(monkeypatch, tmp_path, [OK], loaded=False)
    assert tick._durable_dispatch()["status"] == "FAIL"


def test_dispatcher_row_is_service_only(monkeypatch, tmp_path):
    db = tmp_path / "s.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE health_checks(id,environment_id,service_id,check_type,state,checked_at,evidence,payload)")
    monkeypatch.setattr(tick, "SYSTEMS_DB", db)
    _setup(monkeypatch, tmp_path, [OK, EXHAUSTED])
    tick._record_node_health({"durable_dispatch": tick._durable_dispatch(),
                              "node_oracle": {"connection": "TIMEOUT"},
                              "node_contabo_app_services": {"connection": "TIMEOUT"}})
    with sqlite3.connect(db) as con:
        rows = con.execute("SELECT environment_id, check_type, state, payload FROM health_checks "
                           "WHERE service_id='durable-dispatcher'").fetchall()
    assert len(rows) == 1 and rows[0][:3] == ("MAC_MINI", "SERVICE", "DEGRADED")
    assert json.loads(rows[0][3])["capability_affected"] is False
