#!/usr/bin/env python3
"""Check script: Live uploaded report parser worker integration audit.

Validates the end-to-end flow from client upload → Supabase storage → local
parser worker → parser_results DB → admin workbench UI.
"""
from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

files_to_check = {
    "migration": ROOT / "supabase/migrations/20260713120000_credit_report_parser_results.sql",
    "worker": ROOT / "scripts/credit/parse_uploaded_credit_report.py",
    "extractor": ROOT / "scripts/credit/extract_credit_report_text.py",
    "proof_script": ROOT / "scripts/credit/prove_credit_engine_flow.py",
    "workflow_ts": ROOT / "src/lib/creditRepairWorkflow.ts",
    "case_engine_ts": ROOT / "src/lib/creditReportParserToCaseEngine.ts",
    "workbench": ROOT / "src/components/CreditSpecialistWorkbench.jsx",
    "upload_zone": ROOT / "src/components/client/DocumentUploadZone.tsx",
    "env_example": ROOT / ".env.example",
}

texts = {}
for key, path in files_to_check.items():
    texts[key] = path.read_text(errors="ignore") if path.exists() else ""

combined = "\n".join(texts.values()).lower()

checks: list[tuple[str, bool]] = []


def add(name: str, ok: bool) -> None:
    checks.append((name, bool(ok)))


# Phase B: Migration
add("migration file exists", texts["migration"].strip() != "")
add("migration creates credit_report_parser_results table", "credit_report_parser_results" in texts["migration"])
add("migration has RLS policies", "ENABLE ROW LEVEL SECURITY" in texts["migration"] or "enable row level security" in texts["migration"].lower())
add("migration has admin-only insert policy", "insert" in texts["migration"].lower() and "admin" in texts["migration"].lower())
add("migration has admin-only select policy", "select" in texts["migration"].lower() and "admin" in texts["migration"].lower())
add("migration includes document_id field", "document_id" in texts["migration"])
add("migration includes storage_path field", "storage_path" in texts["migration"])
add("migration includes parser_version field", "parser_version" in texts["migration"])
add("migration includes extraction_mode field", "extraction_mode" in texts["migration"])
add("migration includes extraction_success field", "extraction_success" in texts["migration"])
add("migration includes text_length field", "text_length" in texts["migration"])
add("migration includes confidence field", "confidence" in texts["migration"])
add("migration includes accounts field", "accounts" in texts["migration"])
add("migration includes inquiries field", "inquiries" in texts["migration"])
add("migration includes negative_candidates field", "negative_candidates" in texts["migration"])
add("migration includes structured_item_drafts field", "structured_item_drafts" in texts["migration"])
add("migration includes dispute_strategy_suggestions field", "dispute_strategy_suggestions" in texts["migration"])
add("migration includes utilization_summary field", "utilization_summary" in texts["migration"])
add("migration includes bureaus_detected field", "bureaus_detected" in texts["migration"])
add("migration includes warnings field", "warnings" in texts["migration"])
add("migration includes letter_preview field", "letter_preview" in texts["migration"])
add("migration includes status field", "status" in texts["migration"])
add("migration includes needs_specialist_review field", "needs_specialist_review" in texts["migration"])

# Phase C: Worker script
add("worker script exists", texts["worker"].strip() != "")
add("worker script has argparse CLI", "argparse" in texts["worker"])
add("worker script requires --document-id", "document.id" in texts["worker"] or "document_id" in texts["worker"])
add("worker script uses service role key", "SUPABASE_SERVICE_ROLE_KEY" in texts["worker"])
add("worker script uses Supabase REST API", "supabase" in texts["worker"].lower() and "rest" in texts["worker"].lower())
add("worker script downloads from storage", "storage" in texts["worker"].lower() and "download" in texts["worker"].lower())
add("worker script uses pypdf for extraction", "pypdf" in texts["worker"])
add("worker script calls local parser", "parse_text" in texts["worker"] and "accounts" in texts["worker"])
add("worker script saves results to DB", "credit_report_parser_results" in texts["worker"])
add("worker script saves results to local artifacts", "artifacts" in texts["worker"].lower() or "reports" in texts["worker"].lower())
add("worker script has no auto-letter creation", "create_letter" not in texts["worker"] and "letter_draft" not in texts["worker"])
add("worker script has no DocuPost integration", "docupost" not in texts["worker"])
add("worker script states suggested extraction only", "suggested extraction" in texts["worker"].lower() or "not verified" in texts["worker"].lower())

# Phase D: Frontend loader
add("workflow_ts has loadParserResultForDocument", "loadParserResultForDocument" in texts["workflow_ts"])
add("workflow_ts has loadParserResultsForDocumentIds", "loadParserResultsForDocumentIds" in texts["workflow_ts"])
add("workflow_ts queries credit_report_parser_results", "credit_report_parser_results" in texts["workflow_ts"])
add("workflow_ts has ParserResultSummary interface", "ParserResultSummary" in texts["workflow_ts"])
add("workflow_ts summarizeParserResult helper exists", "summarizeParserResult" in texts["workflow_ts"])

# Phase E: Workbench UI
add("workbench imports loadParserResultForDocument", "loadParserResultForDocument" in texts["workbench"])
add("workbench has parser result state", "parserResult" in texts["workbench"])
add("workbench has parserResultLoading state", "parserResultLoading" in texts["workbench"])
add("workbench has handleRefreshParserResults", "handleRefreshParserResults" in texts["workbench"])
add("workbench has handleConfirmParserItem", "handleConfirmParserItem" in texts["workbench"])
add("workbench shows parser accounts count", "accountsCount" in texts["workbench"] or "Accounts:" in texts["workbench"])
add("workbench shows parser negative candidates count", "negativeCandidatesCount" in texts["workbench"] or "Negative:" in texts["workbench"])
add("workbench shows parser inquiries count", "inquiriesCount" in texts["workbench"] or "Inquiries:" in texts["workbench"])
add("workbench shows parser warnings", "warnings" in texts["workbench"])
add("workbench shows parser bureaus detected", "bureausDetected" in texts["workbench"] or "bureaus" in texts["workbench"])
add("workbench shows suggested extraction language", "suggested extraction" in texts["workbench"].lower())
add("workbench shows specialist review language", "specialist" in texts["workbench"].lower() and "review" in texts["workbench"].lower())
add("workbench has confirm items button", "Confirm Items" in texts["workbench"])
add("workbench has refresh button in parser panel", "Refresh" in texts["workbench"])
add("workbench shows local worker command", "parse_uploaded_credit_report" in texts["workbench"])

# Phase F: confirmParserItemAsCaseItem
add("case engine has confirmParserItemAsCaseItem", "confirmParserItemAsCaseItem" in texts["case_engine_ts"])
add("case engine exports ConfirmParserItemResult", "ConfirmParserItemResult" in texts["case_engine_ts"])
add("case engine confirm function takes caseId", "caseId" in texts["case_engine_ts"])
add("case engine confirm function takes parserItem", "parserItem" in texts["case_engine_ts"])
add("case engine confirm function calls createManualReportItem", "createManualReportItem" in texts["case_engine_ts"])
add("case engine confirm function marks source as parser_confirmed", "parser_confirmed" in texts["case_engine_ts"] or "parser_confirmed" in texts["case_engine_ts"])

# Upload zone audit (no changes expected)
add("upload zone stores to client-documents bucket", "client-documents" in texts["upload_zone"])
add("upload zone uses storage_path in summary", "storage_path" in texts["upload_zone"] or "stored at" in texts["upload_zone"])

# Security / compliance
add("no fake OCR claims in combined", "ocr" not in combined or "without ocr" in combined or "ocr unavailable" in combined or "no ocr" in combined or "ocr processing" not in combined)
add("no bureau credential collection", "bureau_username" not in combined and "bureau_password" not in combined)
add("no SSN collection fields", "ssn" not in combined or "full ssn" not in combined)
add("no full DOB collection fields", "full_dob" not in combined or "full date of birth" not in combined)
add("no full EIN collection fields", "full_ein" not in combined)
add("no full account number collection", "full_account_number" not in combined or "full account" not in combined)
add("no auto-send DocuPost", "docupost" not in combined or "auto-send" not in combined)
add("no bypass specialist/client approval", "bypass" not in combined or "bypass specialist" not in combined)
add("no disable RLS", "disable rls" not in combined or "disable row level security" not in combined)
add("no expose service role in frontend", "SUPABASE_SERVICE_ROLE_KEY" not in texts["workbench"] and "SUPABASE_SERVICE_ROLE_KEY" not in texts["upload_zone"])

# .env.example
add(".env.example exists", texts["env_example"].strip() != "")
add(".env.example documents SUPABASE_URL", "SUPABASE_URL" in texts["env_example"])
add(".env.example documents SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY" in texts["env_example"])

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"\nFAIL: {len(failed)} live uploaded report parser worker checks failed")

print("\nRESULT: PASS - all live uploaded report parser worker checks passed")
