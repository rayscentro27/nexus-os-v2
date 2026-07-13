#!/usr/bin/env python3
"""Check: parser result save/load shape consistency.

Validates that:
1. parse_uploaded_credit_report.py sends raw objects (no json.dumps) for jsonb columns
2. Worker verifies saved row counts after insert
3. creditRepairWorkflow.ts reads accounts/inquiries/negative_candidates correctly
4. CreditSpecialistWorkbench displays normalized counts
5. No hard-coded counts, no fake results, no auto letters, no auto DocuPost
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

worker_file = ROOT / "scripts/credit/parse_uploaded_credit_report.py"
workflow_file = ROOT / "src/lib/creditRepairWorkflow.ts"
workbench_file = ROOT / "src/components/CreditSpecialistWorkbench.jsx"
inspect_file = ROOT / "scripts/credit/inspect_parser_result.py"

texts = {
    "worker": worker_file.read_text(errors="ignore") if worker_file.exists() else "",
    "workflow": workflow_file.read_text(errors="ignore") if workflow_file.exists() else "",
    "workbench": workbench_file.read_text(errors="ignore") if workbench_file.exists() else "",
    "inspect": inspect_file.read_text(errors="ignore") if inspect_file.exists() else "",
}
combined = "\n".join(texts.values()).lower()

checks: list[tuple[str, bool]] = []


def add(name: str, ok: bool) -> None:
    checks.append((name, bool(ok)))


# Worker: no json.dumps for jsonb columns
add("worker does NOT use json.dumps() for accounts column",
    "json.dumps" not in texts["worker"] or 'json.dumps(parse_result["accounts"])' not in texts["worker"])
add("worker does NOT use json.dumps() for inquiries column",
    "json.dumps" not in texts["worker"] or 'json.dumps(parse_result["inquiries"])' not in texts["worker"])
add("worker does NOT use json.dumps() for negative_candidates column",
    "json.dumps" not in texts["worker"] or 'json.dumps(parse_result["negativeItemCandidates"])' not in texts["worker"])
add("worker does NOT use json.dumps() for structured_item_drafts column",
    "json.dumps" not in texts["worker"] or 'json.dumps(structured_items)' not in texts["worker"])
add("worker does NOT use json.dumps() for dispute_strategy_suggestions column",
    "json.dumps" not in texts["worker"] or 'json.dumps(suggestions)' not in texts["worker"])
add("worker does NOT use json.dumps() for bureaus_detected column",
    "json.dumps" not in texts["worker"] or 'json.dumps(parse_result["bureausDetected"])' not in texts["worker"])
add("worker does NOT use json.dumps() for warnings column",
    "json.dumps" not in texts["worker"] or 'json.dumps(parse_result["warnings"])' not in texts["worker"])
add("worker does NOT use json.dumps() for personal_info_variations column",
    "json.dumps" not in texts["worker"] or 'json.dumps(parse_result["personalInfoVariations"])' not in texts["worker"])
add("worker does NOT use json.dumps() for utilization_summary column",
    "json.dumps" not in texts["worker"] or 'json.dumps(parse_result["utilizationSummary"])' not in texts["worker"])

# Worker: sends raw objects
add("worker sends raw accounts object to db_row",
    '"accounts": parse_result["accounts"]' in texts["worker"] or '"accounts": parse_result.get("accounts")' in texts["worker"])
add("worker sends raw inquiries object to db_row",
    '"inquiries": parse_result["inquiries"]' in texts["worker"] or '"inquiries": parse_result.get("inquiries")' in texts["worker"])
add("worker sends raw negative_candidates object to db_row",
    '"negative_candidates": parse_result["negativeItemCandidates"]' in texts["worker"] or '"negative_candidates": parse_result.get("negativeItemCandidates")' in texts["worker"])

# Worker: verification read-back
add("worker reads back saved row for verification",
    "Saved row verification" in texts["worker"] or "verify_rows" in texts["worker"])
add("worker prints accounts count before save",
    "Saving parser payload" in texts["worker"] and "accounts=" in texts["worker"])

# Frontend loader: handles double-encoded strings
add("workflow has parseJsonbField helper", "parseJsonbField" in texts["workflow"])
add("workflow parseJsonbField handles JSON string fallback", "JSON.parse" in texts["workflow"])
add("workflow summarizeParserResult uses parseJsonbField", "parseJsonbField(row.accounts)" in texts["workflow"])

# Frontend loader: correct column names
add("workflow reads accounts column", "row.accounts" in texts["workflow"])
add("workflow reads inquiries column", "row.inquiries" in texts["workflow"])
add("workflow reads negative_candidates column", "row.negative_candidates" in texts["workflow"])
add("workflow reads structured_item_drafts column", "row.structured_item_drafts" in texts["workflow"])
add("workflow reads dispute_strategy_suggestions column", "row.dispute_strategy_suggestions" in texts["workflow"])
add("workflow reads bureaus_detected column", "row.bureaus_detected" in texts["workflow"])
add("workflow reads utilization_summary column", "row.utilization_summary" in texts["workflow"])

# Frontend loader: normalizes counts
add("workflow computes accountsCount from array length", "accountsCount: accounts.length" in texts["workflow"])
add("workflow computes inquiriesCount from array length", "inquiriesCount: inquiries.length" in texts["workflow"])
add("workflow computes negativeCandidatesCount from array length", "negativeCandidatesCount: negativeCandidates.length" in texts["workflow"])
add("workflow computes structuredItemDraftsCount from array length", "structuredItemDraftsCount: structuredDrafts.length" in texts["workflow"])
add("workflow computes disputeSuggestionsCount from array length", "disputeSuggestionsCount: suggestions.length" in texts["workflow"])

# Frontend loader: returns raw arrays too
add("workflow returns accounts count in summary", "accountsCount: accounts.length" in texts["workflow"])

# Workbench: displays counts
add("workbench displays accountsCount", "accountsCount" in texts["workbench"])
add("workbench displays negativeCandidatesCount", "negativeCandidatesCount" in texts["workbench"])
add("workbench displays inquiriesCount", "inquiriesCount" in texts["workbench"])
add("workbench has mismatch detection for zero accounts", "0 accounts" in texts["workbench"].lower() or "shape mismatch" in texts["workbench"].lower())

# No hard-coded counts
add("no hard-coded 26 accounts in code", "26" not in texts["worker"] or "accounts=26" not in texts["worker"])

# No fake results
add("no fake OCR claims", "ocr" not in combined or "without ocr" in combined or "ocr unavailable" in combined or "no ocr" in combined or "ocr processing" not in combined)

# No auto letters
add("no auto-letter creation from parser", "create_letter" not in texts["worker"] and "letter_draft" not in texts["worker"])

# No auto DocuPost
add("no auto-DocuPost send", "docupost" not in texts["worker"])

# Inspect tool exists
add("inspect_parser_result.py exists", inspect_file.exists() and "parser result inspection" in texts["inspect"].lower())
add("inspect tool handles double-encoded fields", "safe_count" in texts["inspect"] or "json.loads" in texts["inspect"])

# DB migration columns match
migration_file = ROOT / "supabase/migrations/20260713120000_credit_report_parser_results.sql"
migration_text = migration_file.read_text(errors="ignore") if migration_file.exists() else ""
add("migration has accounts jsonb column", '"accounts" jsonb' in migration_text or "accounts jsonb" in migration_text)
add("migration has inquiries jsonb column", '"inquiries" jsonb' in migration_text or "inquiries jsonb" in migration_text)
add("migration has negative_candidates jsonb column", '"negative_candidates" jsonb' in migration_text or "negative_candidates jsonb" in migration_text)
add("migration has structured_item_drafts jsonb column", '"structured_item_drafts" jsonb' in migration_text or "structured_item_drafts jsonb" in migration_text)
add("migration has dispute_strategy_suggestions jsonb column", '"dispute_strategy_suggestions" jsonb' in migration_text or "dispute_strategy_suggestions jsonb" in migration_text)
add("migration has bureaus_detected jsonb column", '"bureaus_detected" jsonb' in migration_text or "bureaus_detected jsonb" in migration_text)
add("migration has utilization_summary jsonb column", '"utilization_summary" jsonb' in migration_text or "utilization_summary jsonb" in migration_text)
add("migration has personal_info_variations jsonb column", '"personal_info_variations" jsonb' in migration_text or "personal_info_variations jsonb" in migration_text)
add("migration has warnings jsonb column", '"warnings" jsonb' in migration_text or "warnings jsonb" in migration_text)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"\nFAIL: {len(failed)} parser result save/load shape checks failed")

print("\nRESULT: PASS - all parser result save/load shape checks passed")
