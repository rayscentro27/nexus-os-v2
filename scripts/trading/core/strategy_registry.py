"""Canonical strategy / immutable strategy-version registry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import canonical_hash
from .store import ROOT, StoreError, TradingStore, utc_now

WICK_SPEC_PATH = ROOT / "data" / "governed" / "mercury_strategy_specs" / "strategy_wick_sequence_breakout_v1.json"
RULES_IMPL_PATH = Path(__file__).with_name("wick_rules.py")
EVIDENCE_PATH = ROOT / "data" / "governed" / "wick_sequence_baseline_v1_backtest.json"
STRATEGY_ID = "strat_wick_sequence_breakout"
AUTHORIZED_STATUSES = {"CERTIFICATION", "PAPER_ACTIVE"}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_wick_version(spec_path: Path = WICK_SPEC_PATH, evidence_path: Path = EVIDENCE_PATH) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text())
    logic = spec["strategy_logic"]
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    frozen = {"instrument": spec["market"], "timeframe": logic["timeframe"], "logic": logic}
    rules_hash = canonical_hash(frozen)
    version_id = f"wsb-{spec['market'].lower().replace('_', '')}-{logic['timeframe'].lower()}-v1-{rules_hash[:12]}"
    return {
        "strategy_id": STRATEGY_ID,
        "strategy_version_id": version_id,
        "name": "Wick Sequence Breakout v1 (EUR_USD H1 baseline)",
        "asset_class": "FOREX",
        "instrument": spec["market"],
        "timeframe": logic["timeframe"],
        "entry_rules": {
            "formation": f">= {logic['formation']['min_sequence_bars']} same-side wick bars in {logic['formation']['lookback_bars']}-bar window form a box",
            "long": "completed bar CLOSE above box top with buyer volume-proxy share >= 0.5 and breakout range >= 1.5x SMA20(range)",
            "short": "completed bar CLOSE below box bottom with seller volume-proxy share > 0.5 and breakout range >= 1.5x SMA20(range)",
            "entry_timing": logic["breakout"]["entry_timing"],
            "invalidation": f"box expires after {logic['invalidation_timeout_bars']} bars without breakout",
        },
        "exit_rules": {"stop_or_target": "first of stop or target; same-bar collision = STOP_FIRST", "one_position_at_a_time": True},
        "stop_rule": f"entry -/+ {logic['atr']['stop_multiple']} x Wilder ATR({logic['atr']['period']}) at signal bar",
        "target_rule": f"entry +/- {logic['atr']['target_multiple_r']}R",
        "position_sizing_rule": "evidence: risk 1% equity per trade; paper execution: capped by risk policy max_order_units (certification = 1 unit)",
        "allowed_session": logic.get("session", "NONE"),
        "parameters": logic,
        "source": {
            "mercury_spec_path": str(spec_path.relative_to(ROOT)) if spec_path.is_relative_to(ROOT) else str(spec_path),
            "mercury_spec_sha256": file_sha256(spec_path),
            "mercury_case_id": spec.get("case_id"),
            "source_refs": spec.get("source_refs"),
            "evidence_replay": "artifacts/trading/wick_sequence_baseline_v1_replay.py",
            "evidence_data_sha256": evidence.get("data_sha256"),
            "evidence_summary": {k: evidence.get(k) for k in ("trade_count", "win_rate", "profit_factor", "expectancy", "max_drawdown_fraction", "net_result_equity_fraction", "date_start", "date_end", "bar_count")},
        },
        "rules_hash": rules_hash,
        "rules_impl_sha256": file_sha256(RULES_IMPL_PATH),
        "created_at": utc_now(),
        "status": "CERTIFICATION",
        "live_trading": False,
    }


def freeze(store: TradingStore, version: dict[str, Any]) -> dict[str, Any]:
    """Idempotent freeze. An existing version id must match byte-for-byte on rules."""
    existing = store.get("strategy_versions", version["strategy_version_id"])
    if existing:
        if existing["rules_hash"] != version["rules_hash"] or existing["rules_impl_sha256"] != version["rules_impl_sha256"]:
            raise StoreError("strategy_version_mutation_blocked")
        return existing
    if not store.get("strategies", version["strategy_id"]):
        store.append("strategies", {"strategy_id": version["strategy_id"], "name": "Wick Sequence Breakout", "asset_class": "FOREX",
                                    "origin": "MERCURY_STRATEGY_SYNTHESIS", "created_at": utc_now()})
    return store.append("strategy_versions", version)


def authorization(store: TradingStore, strategy_version_id: str, policy: dict[str, Any]) -> tuple[bool, str]:
    version = store.get("strategy_versions", strategy_version_id)
    if not version:
        return False, "strategy_version_not_registered"
    if strategy_version_id not in policy.get("authorized_strategy_versions", []):
        return False, "strategy_version_not_in_policy_allowlist"
    if version.get("status") not in AUTHORIZED_STATUSES:
        return False, f"strategy_version_status_{version.get('status')}"
    if version.get("rules_impl_sha256") != file_sha256(RULES_IMPL_PATH):
        return False, "strategy_rules_implementation_changed_since_freeze"
    if canonical_hash({"instrument": version["instrument"], "timeframe": version["timeframe"], "logic": version["parameters"]}) != version["rules_hash"]:
        return False, "strategy_rules_hash_mismatch"
    return True, "authorized"
