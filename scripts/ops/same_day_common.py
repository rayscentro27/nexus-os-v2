#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime"
MANUAL = ROOT / "reports" / "manual_publish"
SUPABASE_READY = RUNTIME / "supabase_ready"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_report(stem: str, title: str, data: dict[str, Any], sections: dict[str, Any] | None = None) -> None:
    write_json(RUNTIME / f"{stem}_latest.json", data)
    lines = [f"# {title}", "", f"Generated: {data.get('generated_at', now())}", ""]
    for key, value in data.items():
        if key in {"generated_at", "records", "items", "inventory", "files", "keys"} or isinstance(value, (dict, list)):
            continue
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    for heading, value in (sections or {}).items():
        lines.extend(["", f"## {heading}", ""])
        if isinstance(value, list):
            for item in value:
                lines.append(f"- `{json.dumps(item, sort_keys=True)}`" if isinstance(item, dict) else f"- {item}")
        elif isinstance(value, dict):
            for key, item in value.items():
                lines.append(f"- **{key}:** {json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item}")
        else:
            lines.append(str(value))
    (MANUAL / f"{stem}_latest.md").parent.mkdir(parents=True, exist_ok=True)
    (MANUAL / f"{stem}_latest.md").write_text("\n".join(lines).rstrip() + "\n")


def parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return result
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key.replace("_", "").isalnum():
            result[key] = value
    return result


def masked(value: str) -> str:
    if not value:
        return ""
    if len(value) < 6:
        return "***"
    return f"{value[:3]}***{value[-2:]}"


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:10] if value else ""


def is_gitignored(path: Path) -> bool:
    check = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=ROOT)
    return check.returncode == 0


def env_presence(*names: str) -> dict[str, bool]:
    local: dict[str, str] = dict(os.environ)
    for path in (ROOT / ".env", ROOT / ".env.local", ROOT / ".env.nexus.recovered.local"):
        local.update(parse_env(path))
    return {name: bool(local.get(name)) for name in names}
