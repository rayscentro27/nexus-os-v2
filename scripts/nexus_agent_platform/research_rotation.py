"""Bounded anti-starvation selector for the canonical Research heartbeat."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from nexus_agent_platform.governed.persistence import read_records

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "data" / "runtime" / "research_rotation_state.json"
MAX_CONSECUTIVE = 2
DEFAULT_LANES = ["SEO_SEARCH_DEMAND", "AFFILIATE_REVENUE", "GOCLEAR_BUSINESS", "CREDIT_REPAIR", "FUNDING_LENDER", "GRANTS_GOVERNMENT", "MERCHANDISE_POD", "REAL_ESTATE_AI", "YOUTUBE_ASSIGNED", "TRADING_MARKETS", "AI_NEXUS", "BUSINESS_MARKET"]

def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _load() -> dict[str, Any]:
    try:
        value = json.loads(STATE.read_text(encoding="utf-8")); return value if isinstance(value, dict) else {}
    except (OSError, ValueError): return {}

def active_lanes() -> list[str]:
    lanes = list(DEFAULT_LANES)
    for collection in ("research_requests", "research_questions"):
        for row in read_records(collection):
            lane = str(row.get("lane") or row.get("research_lane") or "").upper()
            status = str(row.get("status") or row.get("research_status") or "OPEN").upper()
            if lane and status not in {"CLOSED", "COMPLETED", "REJECTED"} and lane not in lanes: lanes.append(lane)
    return lanes

def select_next_lane(*, completed_lane: str | None = None) -> dict[str, Any]:
    state = _load(); counts = {str(k): int(v) for k, v in (state.get("consecutive_counts") or {}).items()}; last = str(state.get("last_lane") or ""); lanes = active_lanes()
    if completed_lane:
        counts[completed_lane] = counts.get(completed_lane, 0) + 1 if completed_lane == last else 1; last = completed_lane
    eligible = [lane for lane in lanes if counts.get(lane, 0) < MAX_CONSECUTIVE]
    if not eligible: eligible = lanes
    start = lanes.index(last) + 1 if last in lanes else 0; ordered = lanes[start:] + lanes[:start]
    selected = next((lane for lane in ordered if lane in eligible), eligible[0])
    payload = {"updated_at": _now(), "last_lane": last, "selected_lane": selected, "consecutive_counts": counts, "max_consecutive_loops": MAX_CONSECUTIVE, "lanes": lanes, "starvation_protection": True}
    STATE.parent.mkdir(parents=True, exist_ok=True); STATE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return payload
