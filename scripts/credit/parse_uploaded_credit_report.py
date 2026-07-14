#!/usr/bin/env python3
"""Parse an uploaded credit report from Supabase Storage.

This script is server/admin/local only. It uses the Supabase service role
key to download files from storage and parse them. It never runs in the browser.

Usage:
    source .venv-credit/bin/activate
    python3 scripts/credit/parse_uploaded_credit_report.py --document-id <DOCUMENT_ID>

Requirements:
    - SUPABASE_URL in environment or .env
    - SUPABASE_SERVICE_ROLE_KEY in environment or .env
    - pypdf installed (pip install pypdf)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.request
import urllib.error
import ssl
from pathlib import Path
from typing import Any

import certifi
from funding_readiness_credit_analysis import analyze_credit_for_funding_readiness
from cross_bureau_credit_comparison import compare_credit_report
from credit_strategy_matcher import match_credit_strategies


PARSER_VERSION = "live-0.1.0"
BUREAUS = ("experian", "equifax", "transunion")
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def load_env() -> dict[str, str]:
    """Load env vars from .env / .env.local if present."""
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
    # Environment variables override file
    for key in list(env.keys()):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def supabase_request(method: str, url: str, service_role_key: str, path: str, **kwargs) -> dict[str, Any]:
    """Make a request to Supabase REST API."""
    full_url = f"{url}/rest/v1/{path}"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
        "Prefer": kwargs.pop("prefer", "return=representation"),
    }
    headers.update(kwargs.pop("headers", {}))

    data = json.dumps(kwargs.get("body")).encode() if "body" in kwargs else None
    req = urllib.request.Request(full_url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Supabase {method} failed ({e.code}): {body}") from e


def download_storage_file(url: str, service_role_key: str, bucket: str, path: str, dest: Path) -> Path:
    """Download a file from Supabase Storage."""
    download_url = f"{url}/storage/v1/object/{bucket}/{path}"
    req = urllib.request.Request(download_url, headers={
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    })
    with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
        dest.write_bytes(resp.read())
    return dest


def extract_text_pypdf(pdf_path: Path) -> tuple[str, str, list[dict[str, str]]]:
    """Extract text using pypdf."""
    warnings: list[dict[str, str]] = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        text_parts: list[str] = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
            else:
                warnings.append({"code": f"EMPTY_PAGE_{i+1}", "message": f"Page {i+1} returned no text.", "severity": "warning"})
        text = "\n".join(text_parts)
        if text.strip():
            return text, "text_pdf", warnings
    except ImportError:
        warnings.append({"code": "PYPDF_NOT_INSTALLED", "message": "pip install pypdf", "severity": "error"})
    except Exception as e:
        warnings.append({"code": "PYPDF_ERROR", "message": str(e), "severity": "warning"})
    return "", "failed", warnings


def detect_format(raw_text: str, file_name: str) -> str:
    haystack = f"{file_name} {raw_text}".lower()
    if re.search(r"mixed|funding|bank statement|profit|loss|ein|business formation", haystack):
        return "mixed_credit_funding_bundle"
    if re.search(r"monitoring|score alert|dashboard|credit monitoring", haystack):
        return "monitoring_export"
    if re.search(r"annualcreditreport|annual credit report|disclosure", haystack):
        return "annual_report_style"
    if re.search(r"3[- ]bureau|three bureau|tradeline", haystack):
        return "three_bureau_tradeline"
    if re.search(r"scan|screenshot|ocr", haystack):
        return "scanned_ocr_text"
    return "unknown"


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def detect_bureau(line: str) -> str:
    lower = line.lower()
    for bureau in BUREAUS:
        if bureau in lower:
            return bureau
    return "other"


def money_after(text: str, labels: list[str]) -> str | None:
    for label in labels:
        match = re.search(label + r"[^$0-9-]*(\$?[0-9][0-9,]*(?:\.\d{2})?)", text, re.I)
        if match:
            value = match.group(1)
            return value if value.startswith("$") else f"${value}"
    return None


def utilization(line: str) -> int | None:
    explicit = re.search(r"(\d{1,3})\s*%\s*(?:utilization|utilized|used)?", line, re.I)
    if explicit:
        return int(explicit.group(1))
    balance = money_after(line, ["balance", "reported balance"])
    limit = money_after(line, ["limit", "credit limit"])
    if not balance or not limit:
        return None
    balance_num = float(re.sub(r"[^0-9.]", "", balance) or 0)
    limit_num = float(re.sub(r"[^0-9.]", "", limit) or 0)
    return round((balance_num / limit_num) * 100) if balance_num and limit_num else None


def infer_item_type(line: str) -> str:
    if re.search(r"collection|collector|medical collection", line, re.I):
        return "collection"
    if re.search(r"charge[- ]?off", line, re.I):
        return "charge_off"
    if re.search(r"late|30 day|60 day|90 day", line, re.I):
        return "late_payment"
    if re.search(r"inquiry|hard pull", line, re.I):
        return "inquiry"
    if re.search(r"address|name|employer|personal information", line, re.I):
        return "personal_info"
    if re.search(r"duplicate", line, re.I):
        return "duplicate_account"
    if re.search(r"utilization|credit limit|balance", line, re.I):
        return "utilization"
    return "other"


def suggest_reasons(text: str) -> list[str]:
    lower = text.lower()
    if "duplicate" in lower:
        return ["duplicate", "verify_or_validate", "not_sure"]
    if "balance" in lower or "utilization" in lower:
        return ["incorrect_balance", "verify_or_validate", "not_sure"]
    if "late" in lower:
        return ["late_payment_wrong", "incorrect_dates", "not_sure"]
    if "inquiry" in lower or "unauthorized" in lower:
        return ["unauthorized_inquiry", "verify_or_validate", "not_sure"]
    if "personal" in lower or "address" in lower or "name" in lower:
        return ["personal_info_error", "mixed_file", "not_sure"]
    if "paid" in lower or "settled" in lower:
        return ["paid_or_settled_wrong", "incorrect_balance", "not_sure"]
    if "old" in lower or "outdated" in lower:
        return ["outdated", "incorrect_dates", "not_sure"]
    if "collection" in lower or "charge" in lower:
        return ["verify_or_validate", "not_mine", "not_sure"]
    return ["verify_or_validate", "not_sure"]


def parse_text(raw_text: str, source_file_name: str, extraction_mode: str, extraction_warnings: list[dict[str, str]]) -> dict[str, Any]:
    lines = [clean(line) for line in re.split(r"\n|(?<=\.)\s+", raw_text) if clean(line)]
    accounts = []
    inquiries = []
    personal = []
    for line in lines:
        if re.search(r"inquiry|hard pull|permissible purpose", line, re.I):
            inquiries.append({
                "bureau": detect_bureau(line),
                "company": clean(re.split(r"[-|:]", line)[0])[:100] or "Inquiry",
                "date": (re.search(r"(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})", line) or [None, None])[1],
                "inquiryType": "hard" if re.search(r"hard", line, re.I) else "unknown",
                "notes": line,
                "confidence": "medium",
            })
        if re.search(r"address|name variation|employer|personal information|old address", line, re.I):
            personal.append({
                "field": "address" if re.search(r"address", line, re.I) else "personal_info",
                "value": line[:160],
                "bureau": detect_bureau(line),
                "concern": "possible personal information error",
                "confidence": "low",
            })
        if re.search(r"collection|charge[- ]?off|late|utilization|balance|credit limit|duplicate|settled|paid|tradeline|account", line, re.I):
            item_type = infer_item_type(line)
            util = utilization(line)
            account_num_masked = None
            acct_match = re.search(r"(?:account|acct)[^0-9*]*([*Xx\d -]{4,})", line, re.I)
            if acct_match:
                digits = re.sub(r"\D", "", acct_match.group(1))
                if digits:
                    account_num_masked = f"****{digits[-4:]}"
            reason_bits = [item_type if item_type != "other" else "", "high_utilization" if util and util >= 30 else ""]
            accounts.append({
                "bureau": detect_bureau(line),
                "furnisherName": clean(re.split(r"[-|:]", line)[0])[:80] or None,
                "accountName": clean(re.split(r"[-|:]", line)[0])[:80] or None,
                "accountNumberMasked": account_num_masked,
                "itemType": item_type,
                "status": (re.search(r"status\s*[:\-]\s*([^.;|]+)", line, re.I) or [None, None])[1],
                "reportedBalance": money_after(line, ["balance", "reported balance"]),
                "creditLimit": money_after(line, ["limit", "credit limit"]),
                "utilizationPercent": util,
                "dateOpened": (re.search(r"opened\s*[:\-]?\s*([0-9/ -]{6,12})", line, re.I) or [None, None])[1],
                "dateReported": (re.search(r"reported\s*[:\-]?\s*([0-9/ -]{6,12})", line, re.I) or [None, None])[1],
                "paymentStatus": (re.search(r"(30|60|90)\s*day\s*late", line, re.I) or [None])[0],
                "notes": line,
                "negativeCandidateReason": ", ".join([bit for bit in reason_bits if bit]) or None,
                "suggestedDisputeReasons": suggest_reasons(line),
                "confidence": "medium" if len(line) > 30 else "low",
            })

    high_util = [a for a in accounts if (a.get("utilizationPercent") or 0) >= 30]
    negative = [
        *[a for a in accounts if a.get("negativeCandidateReason") or a.get("itemType") in {"collection", "charge_off", "late_payment", "utilization", "duplicate_account"}],
        *inquiries,
        *[p for p in personal if re.search(r"error|old|variation|mismatch", p.get("concern", "") + " " + p.get("value", ""), re.I)],
    ]
    format_guess = detect_format(raw_text, source_file_name)
    warnings = [
        {"code": "SUGGESTED_EXTRACTION_ONLY", "message": "Suggested extraction only. Needs GoClear specialist review.", "severity": "warning"},
        *extraction_warnings,
    ]
    if not clean(raw_text):
        warnings.append({"code": "NO_TEXT_EXTRACTED", "message": "No text was extracted.", "severity": "error"})

    return {
        "parserVersion": PARSER_VERSION,
        "sourceFileName": source_file_name,
        "sourceFormatGuess": format_guess,
        "extractionMode": extraction_mode,
        "confidence": "medium" if len(clean(raw_text)) > 200 and len(accounts) >= 3 else "low",
        "needsSpecialistReview": True,
        "clientNameGuess": (re.search(r"client\s*:\s*([A-Z][A-Za-z ]{2,80})", raw_text, re.I) or [None, None])[1],
        "reportDateGuess": (re.search(r"(?:date|report date)\s*:\s*([0-9\-/]{8,12})", raw_text, re.I) or [None, None])[1],
        "bureausDetected": [b for b in BUREAUS if re.search(b, raw_text, re.I)],
        "accounts": accounts[:30],
        "inquiries": inquiries[:20],
        "personalInfoVariations": personal[:20],
        "utilizationSummary": {
            "revolvingAccounts": len([a for a in accounts if re.search(r"utilization|balance|credit limit", a.get("notes", ""), re.I)]),
            "highUtilizationAccounts": len(high_util),
            "highestUtilizationPercent": max([a.get("utilizationPercent") or 0 for a in high_util], default=None),
            "notes": [f"{a.get('accountName') or 'Account'} at {a.get('utilizationPercent')}% utilization" for a in high_util],
        },
        "negativeItemCandidates": negative,
        "warnings": warnings,
        "rawTextPreview": clean(raw_text)[:1200],
    }


def build_structured_items(parse_result: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for candidate in parse_result.get("negativeItemCandidates", []):
        if "itemType" in candidate:
            items.append({
                "bureau": candidate.get("bureau", "other"),
                "furnisherName": candidate.get("furnisherName"),
                "accountName": candidate.get("accountName"),
                "accountNumberMasked": candidate.get("accountNumberMasked"),
                "itemType": candidate.get("itemType", "other"),
                "status": candidate.get("status"),
                "reportedBalance": candidate.get("reportedBalance"),
                "creditLimit": candidate.get("creditLimit"),
                "utilizationPercent": candidate.get("utilizationPercent"),
                "negativeCandidateReason": candidate.get("negativeCandidateReason"),
                "suggestedDisputeReasons": candidate.get("suggestedDisputeReasons", []),
                "confidence": candidate.get("confidence", "low"),
            })
    return items


def generate_dispute_suggestions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions = []
    for item in items:
        reasons = item.get("suggestedDisputeReasons", ["verify_or_validate"])
        for reason in reasons[:2]:
            suggestions.append({
                "itemAccountName": item.get("accountName") or item.get("furnisherName") or "Unknown",
                "bureau": item.get("bureau", "other"),
                "itemType": item.get("itemType", "other"),
                "disputeReason": reason,
                "reasonLabel": reason.replace("_", " ").title(),
                "recommended": reason == "verify_or_validate",
            })
    return suggestions


def generate_letter_preview(items: list[dict[str, Any]], client_name: str = "[Consumer Name]") -> str:
    today = __import__("datetime").datetime.now().strftime("%B %d, %Y")
    lines = [
        client_name, "[Consumer Address]", "", today, "",
        "[Bureau Address]", "",
        "Re: Request for Investigation / Verification — Fair Credit Reporting Act (FCRA)", "",
        "Dear Credit Bureau Dispute Department,", "",
        "I am writing to dispute the following information on my credit report.", "",
        "Disputed Items:",
    ]
    for i, item in enumerate(items[:5], 1):
        lines.append(f"  {i}. {item.get('accountName') or item.get('furnisherName') or '[Account]'} ({item.get('accountNumberMasked') or 'XXXX'})")
        lines.append(f"     Bureau: {item.get('bureau', 'Unknown')} · Type: {item.get('itemType', 'Unknown')}")
    lines.extend([
        "",
        "Please investigate these items and correct or remove any information that cannot be accurately verified.",
        "",
        "Sincerely,", client_name, "",
        "---",
        "Draft preview only. This document requires review and approval before use.",
        "Nexus does not guarantee deletion, a credit score change, or a specific reporting outcome.",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse an uploaded credit report from Supabase Storage")
    parser.add_argument("--document-id", required=True, help="client_documents row ID")
    parser.add_argument("--out", type=Path, default=Path("reports/credit_repair/live_upload_parser_results"))
    args = parser.parse_args()

    env = load_env()
    supabase_url = env.get("SUPABASE_URL")
    service_role_key = env.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env or environment.", file=sys.stderr)
        print("Add to .env or .env.local:", file=sys.stderr)
        print("  SUPABASE_URL=https://your-project.supabase.co", file=sys.stderr)
        print("  SUPABASE_SERVICE_ROLE_KEY=your-service-role-key", file=sys.stderr)
        return 1

    document_id = args.document_id
    out_dir = args.out / document_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch document metadata
    print(f"Fetching document metadata for {document_id}...")
    try:
        docs = supabase_request("GET", supabase_url, service_role_key,
            f"client_documents?id=eq.{document_id}&select=*")
    except Exception as e:
        print(f"ERROR: Failed to fetch document: {e}", file=sys.stderr)
        return 1

    if not docs:
        print(f"ERROR: Document {document_id} not found.", file=sys.stderr)
        return 1

    doc = docs[0]
    title = doc.get("title") or doc.get("file_name") or "uploaded_report.pdf"
    category = doc.get("category") or ""
    client_id = doc.get("client_id", "unknown")
    tenant_id = doc.get("tenant_id", "tenant_default")

    # Verify it looks like a credit report
    check_text = f"{category} {doc.get('source', '')} {title}".lower()
    is_credit = "credit" in check_text and ("report" in check_text or "tradeline" in check_text or "bureau" in check_text)
    if not is_credit:
        print(f"WARNING: Document '{title}' (category={category}) does not appear to be a credit report.")
        print("Proceeding anyway, but results may be empty or irrelevant.")

    # 2. Extract storage path from summary or try common patterns
    storage_path = None
    summary = doc.get("summary", "") or ""
    # Try to find storage path in summary: "stored at {path}"
    path_match = re.search(r"stored at\s+(\S+)", summary)
    if path_match:
        storage_path = path_match.group(1)

    if not storage_path:
        # Try to reconstruct from user_id pattern
        user_id = doc.get("client_id", "unknown")
        # We need the original auth user id, which might be in the document
        # Try listing storage to find it
        print("Storage path not found in metadata. Attempting to list storage...")
        try:
            list_url = f"{supabase_url}/storage/v1/object/list/client-documents"
            req = urllib.request.Request(list_url, headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
                "Content-Type": "application/json",
            }, method="POST", data=json.dumps({
                "prefix": "",
                "limit": 100,
                "offset": 0,
            }).encode())
            with urllib.request.urlopen(req, timeout=30) as resp:
                files = json.loads(resp.read().decode())
                # Look for files matching this document's timestamp or name
                for f in files:
                    name = f.get("name", "")
                    if title.replace(" ", "_").lower() in name.lower():
                        storage_path = f"{f.get('id', '')}/{name}" if f.get("id") else name
                        break
                if not storage_path and files:
                    print(f"Could not find exact match. Found {len(files)} files in storage.")
                    print("Set the storage path manually or re-upload the document.")
                    return 1
        except Exception as e:
            print(f"ERROR: Could not list storage: {e}", file=sys.stderr)
            print("Please provide the full storage path manually.", file=sys.stderr)
            return 1

    # 3. Download file
    print(f"Downloading from storage: {storage_path}...")
    with tempfile.TemporaryDirectory(prefix="nexus_parser_") as tmpdir:
        local_file = Path(tmpdir) / title.replace("/", "_")
        try:
            download_storage_file(supabase_url, service_role_key, "client-documents", storage_path, local_file)
        except Exception as e:
            print(f"ERROR: Failed to download file: {e}", file=sys.stderr)
            print(f"Storage path: {storage_path}", file=sys.stderr)
            return 1

        print(f"Downloaded: {local_file.name} ({local_file.stat().st_size} bytes)")

        # 4. Extract text
        print("Extracting text...")
        text, extraction_mode, extraction_warnings = extract_text_pypdf(local_file)
        print(f"  Mode: {extraction_mode}, Text length: {len(text)} chars")

        # 5. Parse
        print("Parsing credit report...")
        parse_result = parse_text(text, title, extraction_mode, extraction_warnings)
        print(f"  Accounts: {len(parse_result['accounts'])}")
        print(f"  Inquiries: {len(parse_result['inquiries'])}")
        print(f"  Review candidates: {len(parse_result['negativeItemCandidates'])}")

        # 6. Build structured items
        structured_items = build_structured_items(parse_result)
        suggestions = generate_dispute_suggestions(structured_items)
        letter_preview = generate_letter_preview(structured_items) if structured_items else ""

        # 7. Save artifacts locally
        (out_dir / "extracted_text.txt").write_text(text, encoding="utf-8")
        (out_dir / "parse_result.json").write_text(json.dumps(parse_result, indent=2), encoding="utf-8")
        (out_dir / "structured_item_drafts.json").write_text(json.dumps(structured_items, indent=2), encoding="utf-8")
        (out_dir / "dispute_strategy_suggestions.json").write_text(json.dumps(suggestions, indent=2), encoding="utf-8")
        if letter_preview:
            (out_dir / "letter_preview.md").write_text(letter_preview, encoding="utf-8")

        # 8. Insert/update parser result in database
        print("Saving parser result to database...")
        system_review = analyze_credit_for_funding_readiness(parse_result)
        print("Saving parser payload:")
        print(f"  accounts={len(parse_result['accounts'])}")
        print(f"  inquiries={len(parse_result['inquiries'])}")
        print(f"  review_candidates={len(parse_result['negativeItemCandidates'])}")
        print(f"  personal_info_variations={len(parse_result['personalInfoVariations'])}")
        print(f"  structured_item_drafts={len(structured_items)}")
        print(f"  recommendations={len(system_review['fundingImpactItems'])}")
        print(f"  bureaus={len(parse_result['bureausDetected'])}")
        db_row = {
            "tenant_id": tenant_id,
            "client_id": client_id,
            "document_id": document_id,
            "source_file_name": title,
            "source_storage_path": storage_path,
            "parser_version": PARSER_VERSION,
            "extraction_mode": extraction_mode,
            "extraction_success": bool(text.strip()),
            "text_length": len(text),
            "confidence": parse_result["confidence"],
            # Do NOT use json.dumps() for jsonb columns — PostgREST handles serialization.
            # Sending JSON strings causes double-encoding and the frontend reads strings instead of arrays.
            "bureaus_detected": parse_result["bureausDetected"],
            "accounts": parse_result["accounts"],
            "inquiries": parse_result["inquiries"],
            "personal_info_variations": parse_result["personalInfoVariations"],
            "utilization_summary": parse_result["utilizationSummary"],
            "negative_candidates": parse_result["negativeItemCandidates"],
            "structured_item_drafts": structured_items,
            "dispute_strategy_suggestions": suggestions,
            "letter_preview": letter_preview,
            "warnings": parse_result["warnings"],
            "status": "suggested_extraction",
            "needs_specialist_review": True,
        }

        # Check if result already exists for this document
        try:
            existing = supabase_request("GET", supabase_url, service_role_key,
                f"credit_report_parser_results?document_id=eq.{document_id}&select=id&order=created_at.desc&limit=1")

            if existing:
                result_id = existing[0]["id"]
                supabase_request("PATCH", supabase_url, service_role_key,
                    f"credit_report_parser_results?id=eq.{result_id}",
                    body=db_row)
                print(f"  Updated existing parser result: {result_id}")
            else:
                result = supabase_request("POST", supabase_url, service_role_key,
                    "credit_report_parser_results",
                    body=db_row)
                result_id = result[0]["id"] if result else "unknown"
                print(f"  Created parser result: {result_id}")

            # Verify saved row — read back and check counts match
            verify_rows = supabase_request("GET", supabase_url, service_role_key,
                f"credit_report_parser_results?id=eq.{result_id}&select=accounts,inquiries,negative_candidates,structured_item_drafts,dispute_strategy_suggestions,bureaus_detected")
            if verify_rows:
                vrow = verify_rows[0]
                v_accounts = len(vrow.get("accounts") or []) if isinstance(vrow.get("accounts"), list) else 0
                v_inquiries = len(vrow.get("inquiries") or []) if isinstance(vrow.get("inquiries"), list) else 0
                v_negative = len(vrow.get("negative_candidates") or []) if isinstance(vrow.get("negative_candidates"), list) else 0
                v_drafts = len(vrow.get("structured_item_drafts") or []) if isinstance(vrow.get("structured_item_drafts"), list) else 0
                v_suggestions = len(vrow.get("dispute_strategy_suggestions") or []) if isinstance(vrow.get("dispute_strategy_suggestions"), list) else 0
                print("Saved row verification:")
                print(f"  accounts={v_accounts}")
                print(f"  inquiries={v_inquiries}")
                print(f"  review_candidates={v_negative}")
                print(f"  structured_item_drafts={v_drafts}")
                print(f"  recommendations={v_suggestions}")
                expected = (len(parse_result['accounts']), len(parse_result['inquiries']), len(parse_result['negativeItemCandidates']), len(structured_items), len(suggestions))
                actual = (v_accounts, v_inquiries, v_negative, v_drafts, v_suggestions)
                if expected != actual:
                    print(f"ERROR: Parser save verification mismatch. expected={expected} saved={actual}", file=sys.stderr)
                    return 2
            else:
                print("ERROR: Could not read back saved parser row for verification.", file=sys.stderr)
                return 2

            comparison = compare_credit_report(parse_result, result_id, document_id)
            strategy_matches = match_credit_strategies(comparison)
            system_review["summary"].update({
                "canonicalAccountCount": len(comparison["canonicalAccounts"]),
                "crossBureauDiscrepancyCount": len(comparison["discrepancies"]),
                "strategyCardCount": len(strategy_matches),
            })
            print("Cross-bureau strategy analysis:")
            print(f"  canonical_accounts={len(comparison['canonicalAccounts'])}")
            print(f"  discrepancies={len(comparison['discrepancies'])}")
            print(f"  strategy_cards={len(strategy_matches)}")

            review_row = {
                "tenant_id": tenant_id, "client_id": client_id, "document_id": document_id,
                "parser_result_id": result_id, "status": "pending_review", "summary": system_review["summary"],
                "funding_impact_items": system_review["fundingImpactItems"], "utilization_actions": system_review["utilizationActions"],
                "report_item_reviews": system_review["reportItemReviews"], "inquiry_reviews": system_review["inquiryReviews"],
                "personal_info_reviews": system_review["personalInfoReviews"], "evidence_needed": system_review["evidenceNeeded"],
                "specialist_exceptions": system_review["specialistExceptions"], "no_action_items": system_review["noActionItems"],
                "recommended_next_steps": system_review["recommendedNextSteps"], "confidence_summary": system_review["confidenceSummary"],
                "tier_1_impact": system_review["tier1Impact"], "tier_2_impact": system_review["tier2Impact"],
                "needs_specialist_review": True, "client_visible": False,
            }
            existing_reviews = supabase_request("GET", supabase_url, service_role_key, f"credit_report_system_reviews?document_id=eq.{document_id}&select=id&order=created_at.desc&limit=1")
            if existing_reviews:
                system_review_id = existing_reviews[0]["id"]
                supabase_request("PATCH", supabase_url, service_role_key, f"credit_report_system_reviews?id=eq.{system_review_id}", body=review_row)
            else:
                created_reviews = supabase_request("POST", supabase_url, service_role_key, "credit_report_system_reviews", body=review_row)
                system_review_id = created_reviews[0]["id"]
            verified_reviews = supabase_request("GET", supabase_url, service_role_key, f"credit_report_system_reviews?id=eq.{system_review_id}&select=funding_impact_items,utilization_actions,report_item_reviews,inquiry_reviews,evidence_needed,specialist_exceptions,no_action_items")
            if not verified_reviews:
                print("ERROR: System review save verification failed.", file=sys.stderr)
                return 3
            saved_review = verified_reviews[0]
            count = lambda key: len(saved_review.get(key) or []) if isinstance(saved_review.get(key), list) else 0
            print("System review created:")
            for label, key in (("funding-impact items","funding_impact_items"),("utilization actions","utilization_actions"),("report-item reviews","report_item_reviews"),("inquiry reviews","inquiry_reviews"),("evidence-needed","evidence_needed"),("specialist exceptions","specialist_exceptions"),("no-action items","no_action_items")):
                print(f"  {label}={count(key)}")

            # Recommendations are rebuilt deterministically for this document. Ordinary,
            # confident cards are client-visible; ambiguous matches route to GoClear.
            supabase_request("DELETE", supabase_url, service_role_key,
                f"credit_strategy_recommendations?document_id=eq.{document_id}")
            recommendation_rows = [{
                "tenant_id": tenant_id, "client_id": client_id, "document_id": document_id,
                "parser_result_id": result_id, "system_review_id": system_review_id,
                "canonical_account_id": match["canonicalAccountId"], "discrepancy_id": match["discrepancyId"],
                "strategy_id": match["strategyId"], "strategy_version": match["strategyVersion"],
                "status": "exception_required" if match["specialistException"] else "client_choice_pending",
                "client_visible": not match["specialistException"], "confidence": match["confidence"],
                "payload": match,
            } for match in strategy_matches]
            if recommendation_rows:
                supabase_request("POST", supabase_url, service_role_key, "credit_strategy_recommendations", body=recommendation_rows)
            print(f"  durable_strategy_recommendations={len(recommendation_rows)}")
            print(f"  GoClear_exceptions={sum(1 for row in recommendation_rows if not row['client_visible'])}")
        except Exception as e:
            print(f"ERROR: Could not save verified parser/system review data: {e}", file=sys.stderr)
            print("Local artifacts were preserved; apply the additive migration or correct server credentials, then retry.", file=sys.stderr)
            return 3

        # 9. Write summary
        summary_text = f"""# Live Upload Parser Result — {title}

- Document ID: {document_id}
- Client ID: {client_id}
- Parser version: {PARSER_VERSION}
- Extraction mode: {extraction_mode}
- Text length: {len(text)} chars
- Accounts parsed: {len(parse_result['accounts'])}
- Inquiries parsed: {len(parse_result['inquiries'])}
- Negative candidates: {len(parse_result['negativeItemCandidates'])}
- Structured item drafts: {len(structured_items)}
- Dispute suggestions: {len(suggestions)}
- Letter preview: {'Generated' if letter_preview else 'None'}
- Confidence: {parse_result['confidence']}
- Bureaus detected: {', '.join(parse_result['bureausDetected']) or 'None'}
- Needs specialist review: Yes (always)
- Status: suggested_extraction

## Safety Gate

- This is a suggested extraction only.
- No letters were created automatically.
- No DocuPost was triggered.
- Specialist confirmation required before any actions.
- Client approval required before any mailing.
"""
        (out_dir / "summary.md").write_text(summary_text, encoding="utf-8")

    print(f"\nDone. Artifacts written to: {out_dir}")
    print(f"Run 'Refresh Parser Results' in Credit Specialist Workbench to see results.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
