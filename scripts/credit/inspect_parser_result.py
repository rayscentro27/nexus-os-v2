#!/usr/bin/env python3
"""Inspect a saved parser result row from credit_report_parser_results.

Usage:
    source .venv-credit/bin/activate
    python3 scripts/credit/inspect_parser_result.py --parser-result-id <ID>
    python3 scripts/credit/inspect_parser_result.py --document-id <DOCUMENT_ID>

Optional:
    --verbose   Print first item preview with masked account only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


def load_env() -> dict[str, str]:
    env = {}
    for env_file in [".env.local", ".env"]:
        p = Path(env_file)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        env[key] = value
    for key in list(env.keys()):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def supabase_get(url: str, key: str, path: str) -> list[dict[str, Any]]:
    full_url = f"{url}/rest/v1/{path}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(full_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"ERROR: Supabase GET failed ({e.code}): {body}", file=sys.stderr)
        return []


def safe_count(value: Any) -> int:
    """Count array items safely, handling both list and JSON string."""
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return len(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    return 0


def safe_keys(value: Any) -> list[str]:
    """Get object keys safely, handling both dict and JSON string."""
    if isinstance(value, dict):
        return list(value.keys())
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return list(parsed.keys())
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect parser result row")
    parser.add_argument("--parser-result-id", help="Parser result row ID")
    parser.add_argument("--document-id", help="Document ID to look up")
    parser.add_argument("--verbose", action="store_true", help="Print first item preview")
    args = parser.parse_args()

    if not args.parser_result_id and not args.document_id:
        print("ERROR: Provide --parser-result-id or --document-id", file=sys.stderr)
        return 1

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_role_key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_role_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required.", file=sys.stderr)
        return 1

    if args.parser_result_id:
        rows = supabase_get(supabase_url, service_role_key,
            f"credit_report_parser_results?id=eq.{args.parser_result_id}&select=*")
    else:
        rows = supabase_get(supabase_url, service_role_key,
            f"credit_report_parser_results?document_id=eq.{args.document_id}&select=*&order=created_at.desc&limit=1")

    if not rows:
        print("ERROR: No parser result found.", file=sys.stderr)
        return 1

    row = rows[0]
    print("=" * 60)
    print("PARSER RESULT INSPECTION")
    print("=" * 60)
    print(f"  ID:                  {row.get('id')}")
    print(f"  Document ID:         {row.get('document_id')}")
    print(f"  Source file:         {row.get('source_file_name')}")
    print(f"  Extraction mode:     {row.get('extraction_mode')}")
    print(f"  Confidence:          {row.get('confidence')}")
    print(f"  Text length:         {row.get('text_length')}")
    print(f"  Status:              {row.get('status')}")
    print(f"  Needs specialist:    {row.get('needs_specialist_review')}")
    print(f"  Created at:          {row.get('created_at')}")
    print()

    # Count fields - handle both jsonb and double-encoded strings
    accounts_count = safe_count(row.get("accounts"))
    inquiries_count = safe_count(row.get("inquiries"))
    negative_count = safe_count(row.get("negative_candidates"))
    drafts_count = safe_count(row.get("structured_item_drafts"))
    suggestions_count = safe_count(row.get("dispute_strategy_suggestions"))
    bureaus = row.get("bureaus_detected", [])
    if isinstance(bureaus, str):
        try:
            bureaus = json.loads(bureaus)
        except (json.JSONDecodeError, TypeError):
            bureaus = []
    warnings_count = safe_count(row.get("warnings"))
    personal_count = safe_count(row.get("personal_info_variations"))
    util_keys = safe_keys(row.get("utilization_summary"))

    print("COUNTS:")
    print(f"  Accounts:                    {accounts_count}")
    print(f"  Inquiries:                   {inquiries_count}")
    print(f"  Negative candidates:         {negative_count}")
    print(f"  Structured item drafts:      {drafts_count}")
    print(f"  Dispute strategy suggestions:{suggestions_count}")
    print(f"  Personal info variations:    {personal_count}")
    print(f"  Bureaus detected:            {', '.join(bureaus) if isinstance(bureaus, list) else bureaus}")
    print(f"  Warnings:                    {warnings_count}")
    print(f"  Utilization summary keys:    {util_keys}")
    print()

    # Check for double-encoding
    print("DATA SHAPE CHECK:")
    for field in ["accounts", "inquiries", "negative_candidates", "structured_item_drafts",
                  "dispute_strategy_suggestions", "bureaus_detected", "warnings",
                  "personal_info_variations", "utilization_summary"]:
        val = row.get(field)
        if isinstance(val, str):
            print(f"  {field}: STRING (double-encoded!) — length={len(val)}")
        elif isinstance(val, list):
            print(f"  {field}: list (correct) — length={len(val)}")
        elif isinstance(val, dict):
            print(f"  {field}: dict (correct) — keys={list(val.keys())[:5]}")
        else:
            print(f"  {field}: {type(val).__name__} — {val}")
    print()

    # Verbose mode: first item preview
    if args.verbose:
        accounts_raw = row.get("accounts", [])
        if isinstance(accounts_raw, str):
            try:
                accounts_raw = json.loads(accounts_raw)
            except (json.JSONDecodeError, TypeError):
                accounts_raw = []
        if isinstance(accounts_raw, list) and accounts_raw:
            item = accounts_raw[0]
            print("FIRST ACCOUNT PREVIEW (masked):")
            print(f"  Bureau:        {item.get('bureau')}")
            print(f"  Furnisher:     {item.get('furnisherName')}")
            print(f"  Account Name:  {item.get('accountName')}")
            print(f"  Account Masked:{item.get('accountNumberMasked')}")
            print(f"  Item Type:     {item.get('itemType')}")
            print(f"  Status:        {item.get('status')}")
            print(f"  Confidence:    {item.get('confidence')}")
        else:
            print("  No accounts to preview.")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
