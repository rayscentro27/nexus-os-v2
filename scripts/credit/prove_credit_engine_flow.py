#!/usr/bin/env python3
"""Prove one fake credit report can move through the Nexus engine locally.

This script demonstrates the full engine flow:
1. Extract text from a PDF fixture
2. Parse the extracted text into structured credit items
3. Create local JSON case draft
4. Create structured item drafts
5. Generate dispute strategy suggestions for negative candidates
6. Generate a draft letter preview
7. Write proof artifacts

This script never sends DocuPost, never contacts Supabase, and never
touches real client data.

Usage:
    python3 scripts/credit/prove_credit_engine_flow.py <pdf_path>
    python3 scripts/credit/prove_credit_engine_flow.py <pdf_path> --out reports/credit_repair/engine_proof
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import base64
import zlib
from pathlib import Path
from typing import Any

PARSER_VERSION = "proof-0.1.0"
BUREAUS = ("experian", "equifax", "transunion")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def extract_text_pypdf(pdf_path: Path) -> tuple[str, str, list[dict[str, str]]]:
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
                warnings.append({
                    "code": f"EMPTY_PAGE_{i+1}",
                    "message": f"Page {i+1} returned no extractable text.",
                    "severity": "warning",
                })
        text = "\n".join(text_parts)
        if text.strip():
            return text, "text_pdf", warnings
    except ImportError:
        warnings.append({
            "code": "PYPDF_NOT_INSTALLED",
            "message": "pypdf is not installed. Install with: pip install pypdf",
            "severity": "error",
        })
    except Exception as e:
        warnings.append({
            "code": "PYPDF_ERROR",
            "message": f"pypdf failed: {e}",
            "severity": "warning",
        })
    return "", "failed", warnings


def extract_text(pdf_path: Path) -> tuple[str, str, list[dict[str, str]]]:
    all_warnings: list[dict[str, str]] = []

    text, mode, warnings = extract_text_pypdf(pdf_path)
    all_warnings.extend(warnings)
    if text.strip():
        return text, mode, all_warnings

    if shutil.which("pdftotext"):
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                text=True, capture_output=True, check=False, timeout=30,
            )
            if proc.returncode == 0 and clean(proc.stdout):
                return proc.stdout, "text_pdf", all_warnings
        except Exception:
            pass

    all_warnings.append({
        "code": "NO_TEXT_EXTRACTED",
        "message": "No text could be extracted from this PDF.",
        "severity": "error",
    })
    return "", "failed", all_warnings


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
            account = {
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
            }
            accounts.append(account)

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
    """Convert parse result negative candidates to structured item drafts."""
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
    """Generate dispute strategy suggestions for structured items."""
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
                "evidenceNeeded": _evidence_for_reason(reason),
                "nextAction": "Prepare draft for GoClear specialist review",
                "caution": _caution_for_reason(reason),
            })
    return suggestions


def _evidence_for_reason(reason: str) -> list[str]:
    mapping = {
        "duplicate": ["Report screenshots from bureaus"],
        "incorrect_balance": ["Statement", "Payment proof"],
        "late_payment_wrong": ["Payment confirmation", "Creditor letter"],
        "unauthorized_inquiry": ["Client statement", "Denial/approval record"],
        "personal_info_error": ["Government ID", "Proof of address"],
        "verify_or_validate": ["Account notices", "Client statement"],
        "outdated": ["Old statements", "Prior report"],
        "not_mine": ["Government ID", "Proof of address"],
    }
    return mapping.get(reason, ["Client statement"])


def _caution_for_reason(reason: str) -> str:
    mapping = {
        "duplicate": "Specialist should confirm duplicate identity.",
        "incorrect_balance": "Upload only proof the client chooses to provide.",
        "late_payment_wrong": "Specialist should compare timeline.",
        "unauthorized_inquiry": "Do not claim fraud unless client states it.",
        "personal_info_error": "Do not collect SSN or full DOB.",
        "verify_or_validate": "Specialist should refine the reason if possible.",
        "outdated": "Specialist must review dates before sending.",
        "not_mine": "Do not claim identity theft unless client states that.",
    }
    return mapping.get(reason, "Specialist review required.")


def generate_letter_preview(items: list[dict[str, Any]], suggestions: list[dict[str, Any]], client_name: str = "[Consumer Name]") -> str:
    """Generate a draft letter preview from structured items."""
    today = __import__("datetime").datetime.now().strftime("%B %d, %Y")
    lines = [
        client_name,
        "[Consumer Address]",
        "",
        today,
        "",
        "[Bureau Address]",
        "",
        "Re: Request for Investigation / Verification — Fair Credit Reporting Act (FCRA)",
        "",
        "Dear Credit Bureau Dispute Department,",
        "",
        "I am writing to dispute the following information on my credit report. I believe the items listed below are inaccurate, incomplete, or cannot be verified, and I request an investigation under the Fair Credit Reporting Act, 15 U.S.C. § 1681.",
        "",
        "Disputed Items:",
    ]

    for i, item in enumerate(items[:5], 1):
        lines.append(f"  {i}. {item.get('accountName') or item.get('furnisherName') or '[Account]'} ({item.get('accountNumberMasked') or 'XXXX'})")
        lines.append(f"     Bureau: {item.get('bureau', 'Unknown')}")
        lines.append(f"     Type: {item.get('itemType', 'Unknown')}")
        if item.get("status"):
            lines.append(f"     Status: {item['status']}")
        if item.get("utilizationPercent"):
            lines.append(f"     Utilization: {item['utilizationPercent']}%")

    lines.extend([
        "",
        "Please investigate these items, contact the furnisher for verification, and correct or remove any information that cannot be accurately verified as required by law.",
        "",
        "If any item is found to be inaccurate or unverifiable, please remove it from my credit report and provide me with an updated copy.",
        "",
        "Sincerely,",
        client_name,
        "",
        "---",
        "DRAFT PREVIEW — Requires GoClear specialist review and client approval before any mailing request.",
        "This draft does not guarantee deletion, score increase, or favorable outcome.",
        "Do not include SSN, full DOB, full account numbers, or sensitive identifiers.",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove credit engine flow with a fake report")
    parser.add_argument("input", type=Path, help="PDF fixture path")
    parser.add_argument("--out", type=Path, default=Path("reports/credit_repair/engine_proof"))
    args = parser.parse_args()

    pdf_path = args.input.resolve()
    if not pdf_path.exists():
        print(f"Error: {pdf_path} does not exist", file=sys.stderr)
        return 1

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Credit Engine Proof Flow ===")
    print(f"Input: {pdf_path.name}")
    print()

    # Step 1: Extract text
    print("Step 1: Extracting text...")
    raw_text, extraction_mode, extraction_warnings = extract_text(pdf_path)
    text_file = out_dir / "extracted_text.txt"
    text_file.write_text(raw_text, encoding="utf-8")
    print(f"  Extraction mode: {extraction_mode}")
    print(f"  Text length: {len(raw_text)} chars")
    print(f"  Warnings: {len(extraction_warnings)}")
    if not raw_text.strip():
        print("  FAILED: No text extracted. Cannot proceed.")
        return 1
    print()

    # Step 2: Parse credit report
    print("Step 2: Parsing credit report...")
    parse_result = parse_text(raw_text, pdf_path.name, extraction_mode, extraction_warnings)
    parse_file = out_dir / "parse_result.json"
    parse_file.write_text(json.dumps(parse_result, indent=2), encoding="utf-8")
    print(f"  Accounts found: {len(parse_result['accounts'])}")
    print(f"  Inquiries found: {len(parse_result['inquiries'])}")
    print(f"  Personal info variations: {len(parse_result['personalInfoVariations'])}")
    print(f"  Negative candidates: {len(parse_result['negativeItemCandidates'])}")
    print(f"  Bureaus detected: {parse_result['bureausDetected']}")
    print(f"  Utilization: {parse_result['utilizationSummary']}")
    print(f"  Confidence: {parse_result['confidence']}")
    print()

    # Step 3: Build structured items
    print("Step 3: Building structured item drafts...")
    structured_items = build_structured_items(parse_result)
    items_file = out_dir / "structured_items_draft.json"
    items_file.write_text(json.dumps(structured_items, indent=2), encoding="utf-8")
    print(f"  Structured items: {len(structured_items)}")
    print()

    # Step 4: Generate dispute suggestions
    print("Step 4: Generating dispute strategy suggestions...")
    suggestions = generate_dispute_suggestions(structured_items)
    suggestions_file = out_dir / "dispute_strategy_suggestions.json"
    suggestions_file.write_text(json.dumps(suggestions, indent=2), encoding="utf-8")
    print(f"  Suggestions: {len(suggestions)}")
    for s in suggestions[:3]:
        print(f"    - {s['itemAccountName']}: {s['disputeReason']} ({s['itemType']})")
    print()

    # Step 5: Generate letter preview
    print("Step 5: Generating draft letter preview...")
    letter_text = generate_letter_preview(structured_items, suggestions)
    letter_file = out_dir / "letter_draft_preview.md"
    letter_file.write_text(letter_text, encoding="utf-8")
    print(f"  Letter preview: {len(letter_text)} chars")
    print()

    # Step 6: Summary
    print("Step 6: Writing proof summary...")
    summary_lines = [
        "# Credit Engine Proof Summary",
        "",
        f"- **Input file:** {pdf_path.name}",
        f"- **Parser version:** {PARSER_VERSION}",
        f"- **Extraction mode:** {extraction_mode}",
        f"- **Text length:** {len(raw_text)} chars",
        f"- **Accounts parsed:** {len(parse_result['accounts'])}",
        f"- **Inquiries parsed:** {len(parse_result['inquiries'])}",
        f"- **Negative candidates:** {len(parse_result['negativeItemCandidates'])}",
        f"- **Structured items drafted:** {len(structured_items)}",
        f"- **Dispute suggestions:** {len(suggestions)}",
        f"- **Letter preview generated:** {'Yes' if letter_text.strip() else 'No'}",
        f"- **Bureaus detected:** {', '.join(parse_result['bureausDetected']) or 'None'}",
        f"- **Utilization summary:** {parse_result['utilizationSummary']}",
        f"- **Confidence:** {parse_result['confidence']}",
        f"- **Needs specialist review:** Yes (always)",
        "",
        "## Proof Criteria",
        "",
        f"- Text extracted: {'PASS' if raw_text.strip() else 'FAIL'}",
        f"- At least one account parsed: {'PASS' if parse_result['accounts'] else 'FAIL'}",
        f"- At least one negative candidate or utilization issue: {'PASS' if parse_result['negativeItemCandidates'] or parse_result['utilizationSummary']['highUtilizationAccounts'] > 0 else 'FAIL'}",
        f"- At least one dispute suggestion: {'PASS' if suggestions else 'FAIL'}",
        f"- Letter preview generated: {'PASS' if letter_text.strip() else 'FAIL'}",
        f"- No DocuPost send created: PASS (this script never sends)",
        "",
        "## Safety Gate",
        "",
        "- This proof uses fake/synthetic data only.",
        "- No real client data was accessed.",
        "- No Supabase connection was made.",
        "- No DocuPost send was triggered.",
        "- Specialist review required before any real actions.",
        "- Client approval required before any real mailing.",
    ]
    summary_file = out_dir / "engine_proof_summary_latest.md"
    summary_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print()

    # Final verdict
    criteria = {
        "text_extracted": bool(raw_text.strip()),
        "accounts_parsed": bool(parse_result["accounts"]),
        "negative_candidates": bool(parse_result["negativeItemCandidates"] or parse_result["utilizationSummary"]["highUtilizationAccounts"] > 0),
        "dispute_suggestions": bool(suggestions),
        "letter_preview": bool(letter_text.strip()),
        "no_docupost_send": True,
    }
    all_pass = all(criteria.values())
    print("=== Proof Result ===")
    for k, v in criteria.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nOverall: {'ALL CRITERIA PASSED' if all_pass else 'SOME CRITERIA FAILED'}")
    print(f"Proof artifacts written to: {out_dir}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
