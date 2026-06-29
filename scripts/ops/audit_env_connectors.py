#!/usr/bin/env python3
"""Inventory Nexus connector key names without revealing raw values."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from same_day_common import ROOT, fingerprint, is_gitignored, masked, now, parse_env, write_report  # noqa: E402

HOME = Path.home()
CANDIDATES = [ROOT, HOME / "nexuslive", HOME / "nexus-ai-council-sandbox", HOME / "nexus", HOME / "Nexus",
              HOME / "nexus-os", HOME / "Desktop/nexuslive", HOME / "Documents/nexuslive", HOME / "Downloads/nexuslive",
              HOME / "projects/nexuslive", HOME / "Projects/nexuslive", HOME / "code/nexuslive", HOME / "Code/nexuslive"]
ENV_NAMES = {".env", ".env.local", ".env.production", ".env.development"}


def category(key: str) -> str:
    k = key.upper()
    rules = [
        ("Supabase", ("SUPABASE",)), ("Netlify", ("NETLIFY",)), ("Resend/email", ("RESEND", "SMTP", "SENDGRID", "MAILGUN")),
        ("Meta/Facebook/Instagram", ("META", "FACEBOOK", "INSTAGRAM", "FB_")), ("YouTube/Google", ("YOUTUBE", "GOOGLE_API", "GOOGLE_CLIENT")),
        ("OpenAI/Anthropic/AI providers", ("OPENAI", "ANTHROPIC", "GEMINI", "PERPLEXITY", "GROQ", "MISTRAL")),
        ("Oanda/trading", ("OANDA", "ALPACA", "BROKER")), ("Telegram", ("TELEGRAM",)), ("Stripe/payment", ("STRIPE", "PAYPAL", "SQUARE")),
        ("Airtable/CRM", ("AIRTABLE", "HUBSPOT", "SALESFORCE", "CRM_")), ("Google Calendar/Gmail/Drive", ("GMAIL", "GOOGLE_CALENDAR", "GOOGLE_DRIVE")),
        ("Storage/document upload", ("STORAGE", "S3_", "AWS_", "CLOUDINARY")), ("Social scheduling/publish", ("BUFFER", "HOOTSUITE", "LATER_")),
        ("SmartCredit", ("SMARTCREDIT",)),
    ]
    for label, needles in rules:
        if any(needle in k for needle in needles):
            return label
    return "Other unknown connectors"


def files() -> list[Path]:
    found: set[Path] = set()
    for base in CANDIDATES:
        if not base.is_dir():
            continue
        for path in base.glob("*.env"):
            if path.is_file(): found.add(path.resolve())
        for name in ENV_NAMES:
            path = base / name
            if path.is_file(): found.add(path.resolve())
    return sorted(found)


def build() -> tuple[dict, dict]:
    env_files = files(); inventory = []; by_key: dict[str, list[dict]] = defaultdict(list)
    for path in env_files:
        scope = "v2" if path.parent == ROOT else "original_nexus"
        ignored = is_gitignored(path) if path.is_relative_to(ROOT) else True
        for key, value in parse_env(path).items():
            item = {"key": key, "category": category(key), "present": bool(value), "value_length": len(value),
                    "masked_preview": masked(value), "sha256_fingerprint_10": fingerprint(value), "source_file": str(path),
                    "source_scope": scope, "source_file_gitignored": ignored,
                    "frontend_forbidden": any(x in key.upper() for x in ("SERVICE_ROLE", "SECRET", "TOKEN", "PRIVATE", "PASSWORD", "API_KEY")),
                    "needs_netlify_environment": key.startswith("VITE_") or key in {"NETLIFY_AUTH_TOKEN", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"},
                    "local_only": any(x in key.upper() for x in ("SERVICE_ROLE", "PRIVATE", "PASSWORD", "SECRET"))}
            inventory.append(item); by_key[key].append(item)
    original = {x["key"] for x in inventory if x["source_scope"] == "original_nexus" and x["present"]}
    v2 = {x["key"] for x in inventory if x["source_scope"] == "v2" and x["present"]}
    missing_values = sorted({x["key"] for x in inventory if x["source_scope"] == "v2" and not x["present"]})
    conflicts = sorted(key for key, values in by_key.items() if len({x["sha256_fingerprint_10"] for x in values if x["present"]}) > 1)
    duplicates = sorted(key for key, values in by_key.items() if len(values) > 1)
    report = {"ok": True, "generated_at": now(), "status": "internal_active", "raw_values_included": False,
              "env_files_found": [str(x) for x in env_files], "env_file_count": len(env_files), "key_record_count": len(inventory),
              "connector_categories": sorted({x["category"] for x in inventory}), "inventory": inventory,
              "external_action_performed": False,
              "summary": f"Found {len(env_files)} Nexus environment files and safely inventoried {len(inventory)} key records."}
    gap = {"ok": True, "generated_at": now(), "status": "internal_active", "raw_values_included": False,
           "original_keys_missing_in_v2": sorted(original - v2), "v2_keys_not_in_original": sorted(v2 - original),
           "v2_keys_with_missing_values": missing_values, "duplicate_keys": duplicates, "conflicting_fingerprints": conflicts,
           "frontend_forbidden_keys": sorted({x["key"] for x in inventory if x["frontend_forbidden"]}),
           "netlify_environment_candidates": sorted({x["key"] for x in inventory if x["needs_netlify_environment"]}),
           "local_only_keys": sorted({x["key"] for x in inventory if x["local_only"]}), "external_action_performed": False,
           "summary": "Compared original Nexus and Nexus OS v2 by key name and masked fingerprint only."}
    write_report("env_connector_inventory", "Environment Connector Inventory", report,
                 {"Environment files": report["env_files_found"], "Masked inventory": inventory})
    write_report("env_connector_gap_analysis", "Environment Connector Gap Analysis", gap,
                 {"Missing in v2": gap["original_keys_missing_in_v2"], "Conflicts": conflicts, "Frontend forbidden": gap["frontend_forbidden_keys"]})
    return report, gap


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--json",action="store_true"); a=p.parse_args(); report,gap=build()
    out={"ok":True,"env_files_found":report["env_file_count"],"key_records":report["key_record_count"],"missing_in_v2":len(gap["original_keys_missing_in_v2"]),"raw_values_included":False}
    print(json.dumps(out,indent=2) if a.json else out); return 0


if __name__ == "__main__": raise SystemExit(main())
