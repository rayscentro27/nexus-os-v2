#!/usr/bin/env python3
"""Run the credit report parser against local synthetic fixtures.

This script extracts text from each fixture PDF using extract_credit_report_text.py
logic (pypdf), then parses the text and writes structured output.

This script is local-only QA. It does not touch Supabase, real client data,
client_documents, dispute letters, or DocuPost.

Usage:
    python3 scripts/credit/parse_credit_report_fixture.py test_fixtures/credit_reports
    python3 scripts/credit/parse_credit_report_fixture.py test_fixtures/credit_reports \
        --expected test_fixtures/credit_reports/expected_extraction_manifest.json \
        --out reports/credit_repair/parser_fixture_results
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Any

PARSER_VERSION = "preview-0.2.0"
BUREAUS = ("experian", "equifax", "transunion")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def decode_pdf_literal(value: str) -> str:
    value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    return value


def extract_reportlab_text(pdf_path: Path) -> tuple[str, list[dict[str, str]]]:
    warnings: list[dict[str, str]] = []
    raw = pdf_path.read_bytes()
    chunks: list[str] = []
    for match in re.finditer(rb"\nstream\n(.*?)endstream", raw, re.S):
        data = match.group(1).strip()
        try:
            if data.endswith(b"~>"):
                data = data[:-2]
            decoded = base64.a85decode(data)
            inflated = zlib.decompress(decoded)
        except Exception:
            continue
        if b"Tj" not in inflated and b"TJ" not in inflated:
            continue
        if len(inflated) > 250_000:
            warnings.append({
                "code": "LARGE_STREAM_SKIPPED",
                "message": "Large PDF stream skipped by local fixture parser; OCR/manual review may be required.",
                "severity": "warning",
            })
            continue
        text_stream = inflated.decode("latin1", errors="ignore")
        chunks.extend(decode_pdf_literal(m.group(1)) for m in re.finditer(r"\(([^()]*(?:\\.[^()]*)*)\)\s*Tj", text_stream))
    if not chunks:
        warnings.append({
            "code": "REPORTLAB_STREAM_TEXT_NOT_FOUND",
            "message": "No ReportLab text stream literals were found. OCR or a PDF text extractor is required.",
            "severity": "warning",
        })
    return "\n".join(chunks), warnings


def extract_text_pypdf(pdf_path: Path) -> tuple[str, str, list[dict[str, str]]]:
    """Extract text using pypdf (primary method)."""
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
            "message": "pypdf is not installed. Install with: pip install pypdf (or use venv)",
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
    """Extract text from PDF using available tools in order of preference."""
    all_warnings: list[dict[str, str]] = []

    # 1. Try pypdf
    text, mode, warnings = extract_text_pypdf(pdf_path)
    all_warnings.extend(warnings)
    if text.strip():
        return text, mode, all_warnings

    # 2. Try pdftotext
    if shutil.which("pdftotext"):
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), "-"],
                text=True, capture_output=True, check=False, timeout=30,
            )
            if proc.returncode == 0 and clean(proc.stdout):
                return proc.stdout, "text_pdf", all_warnings
            all_warnings.append({
                "code": "PDFTOTEXT_FAILED",
                "message": clean(proc.stderr) or "pdftotext returned no text.",
                "severity": "warning",
            })
        except Exception:
            pass

    # 3. Try reportlab stream extraction
    text, reportlab_warnings = extract_reportlab_text(pdf_path)
    all_warnings.extend(reportlab_warnings)
    if clean(text):
        return text, "text_pdf", all_warnings

    # 4. Fallback
    if shutil.which("tesseract"):
        all_warnings.append({
            "code": "OCR_AVAILABLE_NOT_WIRED",
            "message": "Tesseract is installed but image-to-PDF OCR extraction is not wired.",
            "severity": "warning",
        })
    else:
        all_warnings.append({
            "code": "OCR_UNAVAILABLE",
            "message": "OCR dependency not available. File requires OCR or manual specialist review.",
            "severity": "error",
        })

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
        {
            "code": "SUGGESTED_EXTRACTION_ONLY",
            "message": "Suggested extraction only. Needs GoClear specialist review and is not verified yet.",
            "severity": "warning",
        },
        *extraction_warnings,
    ]
    if not clean(raw_text):
        warnings.append({"code": "NO_TEXT_EXTRACTED", "message": "No text was extracted. OCR or manual specialist review is required.", "severity": "error"})

    if format_guess == "mixed_credit_funding_bundle" and extraction_mode != "failed":
        extraction_mode = "mixed"
    if format_guess == "scanned_ocr_text" and not accounts and not inquiries:
        extraction_mode = "failed"
        warnings.append({
            "code": "SCANNED_IMAGE_TEXT_NOT_EXTRACTED",
            "message": "Only non-substantive text was available from the scanned fixture. OCR/manual specialist review is required.",
            "severity": "error",
        })

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
        "documentClassification": {
            "suggestedCategory": "mixed_credit_funding_bundle" if format_guess == "mixed_credit_funding_bundle" else "credit_report",
            "label": "Suggested extraction",
            "status": "Needs GoClear specialist review",
            "verified": False,
        },
        "warnings": warnings,
        "rawTextPreview": clean(raw_text)[:1200],
    }


def iter_pdfs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.glob("*.pdf"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reports/credit_repair/parser_fixture_results"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    raw_text_dir = args.out / "raw_text"
    raw_text_dir.mkdir(parents=True, exist_ok=True)

    expected = json.loads(args.expected.read_text()) if args.expected and args.expected.exists() else {}
    results = []
    for pdf in iter_pdfs(args.input):
        raw_text, extraction_mode, warnings = extract_text(pdf)

        # Write raw text for debugging
        if raw_text.strip():
            raw_text_file = raw_text_dir / f"{pdf.stem}_raw.txt"
            raw_text_file.write_text(raw_text, encoding="utf-8")

        result = parse_text(raw_text, pdf.name, extraction_mode, warnings)
        result["expectedManifest"] = expected.get(pdf.name)
        result["fixtureOnly"] = True
        out_file = args.out / f"{pdf.stem}.json"
        out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        results.append(result)

    summary_path = Path("reports/credit_repair/credit_report_parser_fixture_results_latest.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Credit Report Parser Fixture Results",
        "",
        "These results use fake/synthetic local test files only. Parser output is a suggested extraction, needs GoClear specialist review, and is not verified yet.",
        "",
        f"- Parser version: {PARSER_VERSION}",
        f"- Files tested: {len(results)}",
        f"- pypdf available: {_check_module('pypdf')}",
        f"- pdftotext available: {bool(shutil.which('pdftotext'))}",
        f"- Tesseract OCR available: {bool(shutil.which('tesseract'))}",
        "",
        "| File | Format guess | Extraction mode | Confidence | Accounts | Inquiries | Negative Candidates | OCR/manual status |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        status = "OCR/manual review required" if result["extractionMode"] == "failed" else "Suggested extraction ready"
        lines.append(
            f"| {result['sourceFileName']} | {result['sourceFormatGuess']} | {result['extractionMode']} | {result['confidence']} | "
            f"{len(result['accounts'])} | {len(result['inquiries'])} | {len(result['negativeItemCandidates'])} | {status} |"
        )
    lines.extend([
        "",
        "## Safety Gate",
        "",
        "- Parser suggestions do not create live report items automatically.",
        "- Parser suggestions do not create dispute letters automatically.",
        "- Specialist confirmation is required before creating structured case items.",
        "- Client approval and DocuPost gates remain unchanged.",
    ])
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} parser result file(s) to {args.out}")
    print(f"Wrote summary to {summary_path}")
    return 0


def _check_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    sys.exit(main())
