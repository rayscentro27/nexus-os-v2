"""Per-route file-backed Operator routing switch."""
from __future__ import annotations

import json
import os
from pathlib import Path

ALLOWED_MODES = {"LEGACY_LIVE", "SHADOW", "CANONICAL"}
ALLOWED_ROUTES = {
    "R24.current", "R24.last_completed",
    "NOTE_CREATE", "NOTE_READ", "NOTE_UPDATE", "NOTE_DELETE",
    "FILE_CREATE", "FILE_READ", "FILE_UPDATE", "FILE_DELETE",
    # Wave 3 decision-only routes. Research execution remains on legacy paths.
    "R12.research_assignment", "R13.research_intent",
    "R13.case_resolution", "R13.continue_vs_new",
    "R14.research_assignment", "R15.research_continue",
}
DEFAULT_CONFIG = Path(os.environ.get("NOVA_OPERATOR_ROUTING_MODE_FILE") or
                      "/home/opc/.config/nova-operator-routing-mode.json")


def read_mode(path: Path = DEFAULT_CONFIG) -> str:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        mode = str(value.get("default", value.get("mode", "LEGACY_LIVE"))).upper()
    except (OSError, ValueError, AttributeError):
        return "LEGACY_LIVE"
    return mode if mode in ALLOWED_MODES else "LEGACY_LIVE"


def write_mode(path: Path, mode: str) -> str:
    """Atomically replace a mode file; intended for operator-controlled config."""
    selected = str(mode).upper()
    if selected not in ALLOWED_MODES:
        raise ValueError("INVALID_OPERATOR_ROUTING_MODE")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({"schema_version": 1, "default": selected, "routes": {}}, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)
    return selected


def read_route_mode(route_id: str, path: Path = DEFAULT_CONFIG) -> str:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        mode = str((value.get("routes") or {}).get(route_id, value.get("default", value.get("mode", "LEGACY_LIVE")))).upper()
    except (OSError, ValueError, AttributeError):
        return "LEGACY_LIVE"
    return mode if mode in ALLOWED_MODES else "LEGACY_LIVE"


def write_route_mode(path: Path, route_id: str, mode: str) -> str:
    selected = str(mode).upper()
    if selected not in ALLOWED_MODES:
        raise ValueError("INVALID_OPERATOR_ROUTING_MODE")
    if route_id not in ALLOWED_ROUTES:
        raise ValueError("UNAUTHORIZED_OPERATOR_ROUTING_ROUTE")
    path = Path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        value = {"schema_version": 1, "default": "LEGACY_LIVE", "routes": {}}
    value.setdefault("schema_version", 1)
    value.setdefault("default", "LEGACY_LIVE")
    value.setdefault("routes", {})
    value["routes"][route_id] = selected
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return selected
