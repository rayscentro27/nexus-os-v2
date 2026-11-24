"""Systems tick: Nova Research notification health requires an advancing R10
outbox, not merely a live worker (2026-11-04..14 outage: worker alive, one
undeliverable head event pinned 18 owner notices)."""
from __future__ import annotations

import importlib
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
tick = importlib.import_module("maintenance_tick")


def _stores(tmp_path, pending_ages_minutes, acked=1):
    bridge, jobs = tmp_path / "bridge.sqlite3", tmp_path / "jobs.sqlite3"
    now = datetime.now(timezone.utc)
    with sqlite3.connect(bridge) as b, sqlite3.connect(jobs) as j:
        b.execute("CREATE TABLE completion_events(event_id TEXT PRIMARY KEY, job_id TEXT UNIQUE NOT NULL, payload_json TEXT NOT NULL, delivered_at TEXT)")
        b.execute("CREATE TABLE bridge_jobs(request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, caller TEXT NOT NULL, job_id TEXT NOT NULL, created_at TEXT NOT NULL)")
        j.execute("CREATE TABLE jobs(job_id TEXT PRIMARY KEY, project_id TEXT, idempotency_key TEXT, payload TEXT, updated_at TEXT)")
        rows = [(f"event_ack{i}", f"job_ack{i}", now.isoformat(), 0) for i in range(acked)]
        rows += [(f"event_p{i}", f"job_p{i}", None, age) for i, age in enumerate(pending_ages_minutes)]
        for event_id, job_id, delivered, age in rows:
            b.execute("INSERT INTO completion_events VALUES(?,?,?,?)", (event_id, job_id, "{}", delivered))
            b.execute("INSERT INTO bridge_jobs VALUES(?,?,?,?,?)", ("r" + job_id, "f", "NOVA_NEXUS", job_id, now.isoformat()))
            j.execute("INSERT INTO jobs VALUES(?,?,?,?,?)", (job_id, "p", "k", "{}", (now - timedelta(minutes=age)).isoformat()))
    return bridge, jobs


def _probe(monkeypatch, stdout):
    monkeypatch.setattr(tick.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=stdout, stderr=""))


HEALTHY = "NOVA=active\nRELEASE=nova-r\nFROZEN=no\nLAST_SENT=2026-11-14T03:32:12+00:00\nFAILED=0\nDUPLICATE_SENDS=0\n"


def test_drained_outbox_with_live_consumer_passes(tmp_path, monkeypatch):
    bridge, jobs = _stores(tmp_path, [])
    monkeypatch.setattr(tick, "RESEARCH_RESULTS", bridge)
    monkeypatch.setattr(tick, "RESEARCH_JOBS_DB", jobs)
    _probe(monkeypatch, HEALTHY)
    result = tick._nova_research_notifications()
    assert result["status"] == "PASS" and result["pending_count"] == 0
    assert result["last_successful_delivery_at"].startswith("2026-11-14")


def test_live_worker_with_pinned_outbox_is_attention_not_healthy(tmp_path, monkeypatch):
    bridge, jobs = _stores(tmp_path, [9 * 24 * 60] + [60] * 17)
    monkeypatch.setattr(tick, "RESEARCH_RESULTS", bridge)
    monkeypatch.setattr(tick, "RESEARCH_JOBS_DB", jobs)
    _probe(monkeypatch, HEALTHY)
    result = tick._nova_research_notifications()
    assert result["status"] == "ATTENTION" and "OUTBOX_NOT_ADVANCING" in result["reasons"]
    assert result["pending_count"] == 18 and result["oldest_pending_event"] == "event_p0"


def test_inactive_consumer_fails_and_freeze_or_duplicates_need_attention(tmp_path, monkeypatch):
    bridge, jobs = _stores(tmp_path, [])
    monkeypatch.setattr(tick, "RESEARCH_RESULTS", bridge)
    monkeypatch.setattr(tick, "RESEARCH_JOBS_DB", jobs)
    _probe(monkeypatch, HEALTHY.replace("NOVA=active", "NOVA=inactive"))
    assert tick._nova_research_notifications()["status"] == "FAIL"
    _probe(monkeypatch, HEALTHY.replace("FROZEN=no", "FROZEN=yes").replace("DUPLICATE_SENDS=0", "DUPLICATE_SENDS=2"))
    result = tick._nova_research_notifications()
    assert result["status"] == "ATTENTION" and {"DELIVERY_FROZEN", "DUPLICATE_SENDS"} <= set(result["reasons"])


def test_unreadable_ledger_is_not_reported_healthy(tmp_path, monkeypatch):
    bridge, jobs = _stores(tmp_path, [])
    monkeypatch.setattr(tick, "RESEARCH_RESULTS", bridge)
    monkeypatch.setattr(tick, "RESEARCH_JOBS_DB", jobs)
    _probe(monkeypatch, "NOVA=active\nRELEASE=x\nFROZEN=no\nLEDGER=UNREADABLE\n")
    result = tick._nova_research_notifications()
    assert result["status"] == "ATTENTION" and "LEDGER_UNREADABLE" in result["reasons"]
