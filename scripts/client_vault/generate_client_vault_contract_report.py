#!/usr/bin/env python3
"""Generate the Client Vault contract report (dry-run). Mock only — no live connection."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime" / "client_vault_contract_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "client_vault_contract_latest.md"

ADAPTER_INTERFACE = [
    "client_profiles", "credit_report_metadata", "credit_score_snapshots", "business_profile",
    "business_setup_items", "proof_uploads", "letter_packets", "mailing_records", "workflow_tasks",
    "reminder_tasks", "funding_readiness_summaries", "affiliate_attribution_events",
    "consent_events", "audit_events", "sanitized_signal_export",
]
DATA_MODEL = [
    "client_profile", "client_credit_report", "client_credit_score_snapshot", "client_business_profile",
    "client_business_setup_item", "client_proof_upload", "client_letter_packet", "client_mailing_record",
    "client_workflow_task", "client_reminder_event", "client_funding_readiness_summary",
    "client_affiliate_attribution_event", "client_consent_event", "client_audit_event",
]
FUTURE_BACKENDS = ["separate_supabase_project", "separate_schema", "self_hosted_supabase",
                   "plain_postgres_vault", "other_backend"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()
    report = {
        "ok": True,
        "title": "Client Vault Contract",
        "generated_at": now(),
        "dry_run": True,
        "connection_status": "not_connected_by_design",
        "adapter_in_use": "mock",
        "second_supabase_connected": False,
        "real_credentials_present": False,
        "real_client_data_present": False,
        "adapter_interface": ADAPTER_INTERFACE,
        "data_model": DATA_MODEL,
        "supported_future_backends": FUTURE_BACKENDS,
        "counts": {"adapter_methods": len(ADAPTER_INTERFACE), "data_model_entities": len(DATA_MODEL),
                   "future_backends": len(FUTURE_BACKENDS)},
        "summary": "Client Vault contract + mock adapter only. No live connection, no 2nd Supabase, no real credentials, no real client data.",
        "safety": {"real_vault_connected": False, "second_supabase_connected": False,
                   "real_credentials_present": False, "real_client_data_present": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- connection_status: {report['connection_status']}",
         f"- adapter_in_use: {report['adapter_in_use']}", f"- second_supabase_connected: {report['second_supabase_connected']}",
         f"- real_client_data_present: {report['real_client_data_present']}", "", "## Adapter interface"]
    L += [f"- {x}" for x in ADAPTER_INTERFACE] + ["", "## Data model"] + [f"- {x}" for x in DATA_MODEL]
    L += ["", "## Future backends"] + [f"- {x}" for x in FUTURE_BACKENDS]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
