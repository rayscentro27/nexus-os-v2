"""Mac -> Oracle reverse bridge transport check: Tailscale preferred, fallback
and drop are CONNECTION degradation only (never capability loss)."""
from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
tick = importlib.import_module("maintenance_tick")


def _setup(monkeypatch, tmp_path, peers: dict[int, str | None]):
    monkeypatch.setattr(tick, "TRANSPORT_STATE_DIR", tmp_path)
    live = os.getpid()
    for port, peer in peers.items():
        if peer == "MISSING":
            continue
        pid = live if peer != "DEAD" else 999_999_9
        (tmp_path / f"oracle_reverse_{port}.json").write_text(json.dumps(
            {"port": port, "ssh_pid": pid, "transport": "TAILSCALE", "started_at": "2026-11-13T05:00:00Z"}))

    def fake_run(argv, **kw):
        # one fake ssh pid stands for every live bridge; map lsof calls by order
        peer = fake_run.order.pop(0)
        return SimpleNamespace(stdout=f"ssh 1 u 3u IPv4 0x0 0t0 TCP 100.70.239.13:5000->{peer}:22 (ESTABLISHED)\n" if peer else "")
    fake_run.order = [p for p in peers.values() if p not in ("MISSING", "DEAD")]
    monkeypatch.setattr(tick.subprocess, "run", fake_run)


def test_all_bridges_on_tailscale_pass(monkeypatch, tmp_path):
    ts = tick.ORACLE_TAILSCALE_IP
    _setup(monkeypatch, tmp_path, {18765: ts, 18767: ts, 18768: ts})
    r = tick._oracle_bridges()
    assert r["status"] == "PASS"
    assert {b["transport"] for b in r["bridges"].values()} == {"TAILSCALE"}


def test_public_fallback_dead_and_unmanaged_degrade(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, {18765: tick.ORACLE_PUBLIC_IP, 18767: "DEAD", 18768: "MISSING"})
    r = tick._oracle_bridges()
    assert r["status"] == "DEGRADED"
    assert r["bridges"]["nexus_mcp"]["transport"] == "LEGACY_PUBLIC_FALLBACK"
    assert r["bridges"]["google_mcp"]["transport"] == "DOWN"
    assert r["bridges"]["research_mcp"]["transport"] == "UNMANAGED"


def test_bridge_rows_are_transport_only(monkeypatch, tmp_path):
    db = tmp_path / "s.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE health_checks(id,environment_id,service_id,check_type,state,checked_at,evidence,payload)")
    monkeypatch.setattr(tick, "SYSTEMS_DB", db)
    checks = {
        "node_oracle": {"connection": "ONLINE", "TAILSCALE": "Running", "HERMES": "active", "NOVA": "active",
                        "HOST_CONTROL": "active", "SEARXNG": "active", "BRIDGE_LISTEN": "18765,18768,"},
        "node_contabo_app_services": {"connection": "TIMEOUT"},
        "oracle_bridges": {"bridges": {
            "nexus_mcp": {"port": 18765, "transport": "TAILSCALE"},
            "google_mcp": {"port": 18767, "transport": "TAILSCALE"},          # no Oracle listener
            "research_mcp": {"port": 18768, "transport": "LEGACY_PUBLIC_FALLBACK"}}},
    }
    tick._record_node_health(checks)
    with sqlite3.connect(db) as con:
        rows = {r[0]: (r[1], r[2]) for r in con.execute(
            "SELECT service_id, check_type, state FROM health_checks WHERE service_id LIKE 'bridge-%'")}
    assert rows == {"bridge-nexus_mcp": ("TRANSPORT", "HEALTHY"),
                    "bridge-google_mcp": ("TRANSPORT", "DEGRADED"),
                    "bridge-research_mcp": ("TRANSPORT", "DEGRADED")}
