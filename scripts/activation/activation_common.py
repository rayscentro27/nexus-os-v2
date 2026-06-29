#!/usr/bin/env python3
"""Shared, deterministic utilities for Nexus safe internal activation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime"
MANUAL = ROOT / "reports" / "manual_publish"
SUPABASE_READY = RUNTIME / "supabase_ready"
DASHBOARD_DATA = ROOT / "src" / "data" / "continuousDashboardData.json"
PUBLIC_STATUS = ROOT / "public" / "runtime" / "hermes-current.json"

SAFETY = {
    "external_action_performed": False,
    "money_spent": False,
    "public_content_published": False,
    "client_contacted": False,
    "real_money_trade_placed": False,
    "demo_trade_placed": False,
    "disputes_submitted": False,
    "letters_mailed": False,
    "paid_api_called": False,
    "level_3_blocked": True,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    for path in (RUNTIME, MANUAL, SUPABASE_READY, DASHBOARD_DATA.parent, PUBLIC_STATUS.parent,
                 ROOT / "data" / "feedback", ROOT / "ops" / "launchd"):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return rel(path)


def markdown_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "none"
    if isinstance(value, (list, dict)):
        return f"`{json.dumps(value, ensure_ascii=False)}`"
    return str(value)


def write_report(stem: str, title: str, payload: dict[str, Any], sections: dict[str, Any] | None = None) -> tuple[str, str]:
    ensure_dirs()
    enriched = {"title": title, "generated_at": now(), **payload}
    runtime_path = RUNTIME / f"{stem}_latest.json"
    manual_path = MANUAL / f"{stem}_latest.md"
    write_json(runtime_path, enriched)
    lines = [f"# {title}", "", f"- generated_at: {enriched['generated_at']}"]
    for key in ("ok", "status", "mode", "summary", "next_money_action", "recommended_next_action",
                "external_action_performed", "money_spent", "public_content_published",
                "client_contacted", "real_money_trade_placed", "demo_trade_placed"):
        if key in enriched:
            lines.append(f"- {key}: {markdown_value(enriched[key])}")
    for heading, content in (sections or {}).items():
        lines.extend(["", f"## {heading}", ""])
        if isinstance(content, list):
            if not content:
                lines.append("- none")
            else:
                for item in content:
                    if isinstance(item, dict):
                        label = item.get("title") or item.get("name") or item.get("id") or "item"
                        detail = item.get("next_action") or item.get("purpose") or item.get("status") or item.get("summary") or ""
                        lines.append(f"- **{label}**" + (f" — {detail}" if detail else ""))
                    else:
                        lines.append(f"- {item}")
        elif isinstance(content, dict):
            for key, value in content.items():
                lines.append(f"- {key}: {markdown_value(value)}")
        else:
            lines.append(str(content))
    manual_path.write_text("\n".join(lines) + "\n")
    return rel(runtime_path), rel(manual_path)


def approval_card(card_id: str, title: str, category: str, action: str, outcome: str,
                  risk: str = "medium") -> dict[str, Any]:
    return {
        "id": card_id,
        "title": title,
        "category": category,
        "why_it_matters": outcome,
        "expected_outcome": outcome,
        "risk": risk,
        "exact_action_requested": action,
        "options": ["approve", "reject", "defer"],
        "approval_required": True,
        "external_action_performed": False,
    }
