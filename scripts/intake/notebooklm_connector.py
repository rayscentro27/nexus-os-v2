#!/usr/bin/env python3
"""Optional NotebookLM connector foundation.

Status/report only for now. Does not store cookies/tokens, automate a browser, scrape broadly,
or send private/sensitive text to external AI.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime" / "notebooklm_connector_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "notebooklm_connector_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def configured() -> bool:
    # Presence-only check. Never print values.
    return bool(os.environ.get("NEXUS_NOTEBOOKLM_CONNECTOR_ENABLED") == "true" and os.environ.get("NEXUS_NOTEBOOKLM_NOTEBOOK_ID"))


def status(mode: str, source_url: str, notebook_id: str, dry_run: bool) -> dict[str, Any]:
    is_configured = configured() or bool(notebook_id)
    return {
        "ok": True,
        "generated_at": now(),
        "mode": mode,
        "dry_run": dry_run,
        "status": "notebooklm_connector_configured_manual_only" if is_configured else "NotebookLM connector not configured",
        "configured": is_configured,
        "source_url": source_url or None,
        "notebook_id_provided": bool(notebook_id),
        "writes": ["local_report"],
        "external_actions": {
            "browser_automation_started": False,
            "cookies_or_tokens_stored": False,
            "external_ai_called": False,
            "source_added": False,
            "summary_exported": False,
        },
        "next_action": "Configure an approved connector/session outside the repo, then run dry-run again." if not is_configured else "Use only approved public/non-sensitive sources; live add/export remains future-gated.",
    }


def write_report(report: dict[str, Any], explicit_path: str = "") -> None:
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [
        "# NotebookLM Connector Status",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- mode: {report['mode']}",
        f"- dry_run: {report['dry_run']}",
        f"- status: {report['status']}",
        "- cookies_or_tokens_stored: false",
        "- external_ai_called: false",
        "- browser_automation_started: false",
        "",
        "## Next Action",
        report["next_action"],
    ]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(lines) + "\n")
    if explicit_path:
        path = Path(explicit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) if path.suffix.lower() == ".json" else "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--mode", choices=["status", "add-source", "export-summary"], default="status")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--notebook-id", default="")
    parser.add_argument("--report-path", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-sensitive-data", action="store_true", default=True)
    args = parser.parse_args()

    if not args.no_sensitive_data:
        print(json.dumps({"ok": False, "error": "no_sensitive_data_required"}, indent=2))
        return 2
    if args.mode != "status" and not args.dry_run:
        print(json.dumps({"ok": False, "error": "live_notebooklm_actions_not_enabled"}, indent=2))
        return 2
    report = status(args.mode, args.source_url, args.notebook_id, args.dry_run)
    write_report(report, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
