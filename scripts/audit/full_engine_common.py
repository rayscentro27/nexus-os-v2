#!/usr/bin/env python3
"""Shared local-only helpers for the Nexus full-engine proof audit."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime"
MANUAL = ROOT / "reports" / "manual_publish"
SUPABASE = RUNTIME / "supabase_ready"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def env_presence(*names: str) -> dict[str, bool]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(errors="ignore").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    return {name: bool(values.get(name)) for name in names}


def ensure_dirs() -> None:
    for path in (RUNTIME, MANUAL, SUPABASE):
        path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return str(path.relative_to(ROOT))


def write_report(stem: str, title: str, payload: dict[str, Any], sections: dict[str, Any] | None = None) -> tuple[str, str]:
    ensure_dirs()
    report = {"title": title, "generated_at": now(), **payload}
    runtime = RUNTIME / f"{stem}_latest.json"
    manual = MANUAL / f"{stem}_latest.md"
    write_json(runtime, report)
    lines = [f"# {title}", "", f"- generated_at: {report['generated_at']}"]
    for key in ("ok", "mode", "status", "summary", "external_action_performed", "real_client_data_used",
                "public_content_published", "client_contacted", "real_money_trade_placed", "next_required_action",
                "next_money_action"):
        if key in report:
            value = report[key]
            if isinstance(value, bool):
                value = str(value).lower()
            lines.append(f"- {key}: {value}")
    for heading, content in (sections or {}).items():
        lines.extend(["", f"## {heading}", ""])
        if isinstance(content, list):
            if not content:
                lines.append("- none")
            for item in content:
                if isinstance(item, dict):
                    name = item.get("title") or item.get("name") or item.get("connector_id") or item.get("case_id") or item.get("id") or "item"
                    detail = item.get("status") or item.get("summary") or item.get("next_action") or ""
                    lines.append(f"- **{name}**" + (f" — {detail}" if detail else ""))
                else:
                    lines.append(f"- {item}")
        elif isinstance(content, dict):
            for key, value in content.items():
                lines.append(f"- {key}: {json.dumps(value) if isinstance(value, (list, dict)) else value}")
        else:
            lines.append(str(content))
    manual.write_text("\n".join(lines) + "\n")
    return str(runtime.relative_to(ROOT)), str(manual.relative_to(ROOT))


def record(record_id: str, category: str, title: str, **extra: Any) -> dict[str, Any]:
    data = {
        "id": record_id, "tenant_id": "tenant_demo_goclear", "client_id": "synthetic_audit_only",
        "category": category, "title": title, "summary": title, "status": "generated_report_only",
        "priority": "medium", "risk_level": "low", "automation_level": "internal_active",
        "client_visible": False, "approval_required": False, "external_action_performed": False,
        "source": "local_full_engine_audit", "recommended_next_action": "Review local proof.", "created_at": now(),
    }
    data.update(extra)
    return data
