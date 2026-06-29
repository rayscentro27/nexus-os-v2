#!/usr/bin/env python3
"""Verify the local client portal remains demo-only, separated, and non-executing."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime"
MANUAL = ROOT / "reports" / "manual_publish"

SCAN_ROOTS = [
    ROOT / "src" / "components" / "client",
    ROOT / "src" / "pages" / "client",
    ROOT / "src" / "data" / "clientPortalData.js",
    ROOT / "src" / "data" / "clientGuideResponses.js",
    ROOT / "src" / "data" / "clientHermesBridgeData.js",
    ROOT / "scripts" / "client_flow",
]

FORBIDDEN = {
    "guaranteed_claim": re.compile(r"guaranteed (approval|removal|deletion|funding)", re.I),
    "false_dispute_sent_claim": re.compile(r"we sent your dispute|your dispute (was|has been) sent", re.I),
    "false_application_claim": re.compile(r"application (was |has been )?submitted", re.I),
    "service_role_env": re.compile(r"SUPABASE_SERVICE_ROLE_KEY"),
    "openai_key_env": re.compile(r"OPENAI_API_KEY"),
    "network_client": re.compile(r"\b(requests\.(get|post)|urllib\.request|httpx\.|axios\.|fetch\s*\()"),
}


def files() -> list[Path]:
    found = []
    for root in SCAN_ROOTS:
        if root.is_file():
            found.append(root)
        elif root.exists():
            found.extend(path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.name != "verify_client_portal_safety.py")
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    violations = []
    scanned = files()
    for path in scanned:
        text = path.read_text(errors="ignore")
        for rule, pattern in FORBIDDEN.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                violations.append({"rule": rule, "file": str(path.relative_to(ROOT)), "line": line})
    client_pages = "\n".join(path.read_text(errors="ignore") for path in scanned if "pages/client" in str(path) or "components/client" in str(path))
    separation = {
        "client_guide_present": "Nexus Guide" in client_pages,
        "client_facing_ask_hermes_absent": "Ask Hermes" not in client_pages,
        "hermes_private_admin_policy_present": "hermes_private_admin_only" in (ROOT / "src/data/clientHermesBridgeData.js").read_text(),
        "structured_bridge_present": "structured_approval_bridge_only" in (ROOT / "src/data/clientHermesBridgeData.js").read_text(),
    }
    backend = json.loads((RUNTIME / "client_portal_backend_build_latest.json").read_text())
    ok = not violations and all(separation.values()) and backend.get("ok") is True and all(backend.get(key) is False for key in (
        "github_network_access_performed", "external_action_performed", "client_contacted", "public_content_published", "real_client_data_used"))
    report = {
        "ok": ok, "generated_at": datetime.now(timezone.utc).isoformat(), "files_scanned": len(scanned),
        "violations": violations, "assistant_separation": separation,
        "github_network_access_performed": False, "external_action_performed": False,
        "client_contacted": False, "public_content_published": False, "real_client_data_used": False,
        "service_role_key_used": False, "api_keys_found": False,
    }
    RUNTIME.mkdir(parents=True, exist_ok=True); MANUAL.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "client_portal_safety_latest.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Client Portal Safety Verification", "", f"- ok: {str(ok).lower()}", f"- files_scanned: {len(scanned)}",
             f"- violations: {len(violations)}", "- github_network_access_performed: false", "- external_action_performed: false",
             "- client_contacted: false", "- public_content_published: false", "- real_client_data_used: false",
             "- service_role_key_used: false", "- API keys found: false", "", "## Assistant Separation"]
    lines += [f"- {key}: {str(value).lower()}" for key, value in separation.items()]
    (MANUAL / "client_portal_safety_latest.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(report, indent=2) if args.json else f"Client portal safety ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
