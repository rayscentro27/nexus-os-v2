"""Context resolution — follows context across turns.

Maintains per-agent context stores so follow-up references,
slot filling, and multi-intent messages can be handled properly.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


_CONTEXT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "runtime", "agent_context"
)


def _ensure_dir() -> None:
    os.makedirs(_CONTEXT_DIR, exist_ok=True)


def _context_path(agent_id: str) -> str:
    _ensure_dir()
    return os.path.join(_CONTEXT_DIR, f"{agent_id}_context.json")


def load_context(agent_id: str) -> Dict[str, Any]:
    path = _context_path(agent_id)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"active": {}, "history": [], "slots": {}, "updated_at": 0}


def save_context(agent_id: str, ctx: Dict[str, Any]) -> None:
    ctx["updated_at"] = time.time()
    with open(_context_path(agent_id), "w") as f:
        json.dump(ctx, f, indent=2, default=str)


def update_active_context(agent_id: str, key: str, value: Any, ttl: int = 600) -> None:
    ctx = load_context(agent_id)
    ctx["active"][key] = {
        "value": value,
        "expires_at": time.time() + ttl,
    }
    save_context(agent_id, ctx)


def get_active_context(agent_id: str) -> Dict[str, Any]:
    ctx = load_context(agent_id)
    now = time.time()
    active = {}
    for k, v in ctx.get("active", {}).items():
        if v.get("expires_at", 0) > now:
            active[k] = v["value"]
    return active


def clear_context(agent_id: str) -> None:
    save_context(agent_id, {"active": {}, "history": [], "slots": {}, "updated_at": time.time()})
