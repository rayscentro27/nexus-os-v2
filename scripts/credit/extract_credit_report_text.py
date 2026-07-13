#!/usr/bin/env python3
"""Extract text from credit report PDFs using available local tools.

Tries in order:
1. pypdf (Python library)
2. pdftotext command-line tool
3. Fallback with clear error message

This script is local-only QA. It does not touch Supabase, real client data,
or DocuPost.

Usage:
    python3 scripts/credit/extract_credit_report_text.py <pdf_path>
    python3 scripts/credit/extract_credit_report_text.py <pdf_dir> --out <output_dir>
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def try_pypdf(pdf_path: Path) -> tuple[str, str, list[dict[str, str]]]:
    """Attempt extraction using pypdf."""
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
            return text, "pypdf", warnings
        warnings.append({
            "code": "PYPDF_NO_TEXT",
            "message": "pypdf returned no extractable text. File may be image-only.",
            "severity": "warning",
        })
    except ImportError:
        warnings.append({
            "code": "PYPDF_NOT_INSTALLED",
            "message": "pypdf is not installed. Install with: pip install pypdf",
            "severity": "error",
        })
    except Exception as e:
        warnings.append({
            "code": "PYPDF_ERROR",
            "message": f"pypdf extraction failed: {e}",
            "severity": "error",
        })
    return "", "failed", warnings


def try_pdftotext(pdf_path: Path) -> tuple[str, str, list[dict[str, str]]]:
    """Attempt extraction using pdftotext command."""
    warnings: list[dict[str, str]] = []
    if not shutil.which("pdftotext"):
        warnings.append({
            "code": "PDFTOTEXT_NOT_INSTALLED",
            "message": "pdftotext is not installed. Install with: brew install poppler",
            "severity": "info",
        })
        return "", "failed", warnings
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout, "pdftotext", warnings
        warnings.append({
            "code": "PDFTOTEXT_FAILED",
            "message": proc.stderr.strip() or "pdftotext returned no text.",
            "severity": "warning",
        })
    except subprocess.TimeoutExpired:
        warnings.append({
            "code": "PDFTOTEXT_TIMEOUT",
            "message": "pdftotext timed out after 30 seconds.",
            "severity": "warning",
        })
    except Exception as e:
        warnings.append({
            "code": "PDFTOTEXT_ERROR",
            "message": f"pdftotext failed: {e}",
            "severity": "warning",
        })
    return "", "failed", warnings


def extract_text(pdf_path: Path) -> dict[str, Any]:
    """Extract text from a PDF using available tools."""
    all_warnings: list[dict[str, str]] = []

    # Try pypdf first
    text, mode, warnings = try_pypdf(pdf_path)
    all_warnings.extend(warnings)
    if text.strip():
        return {
            "success": True,
            "text": text,
            "extractionMode": mode,
            "textLength": len(text),
            "toolUsed": "pypdf",
            "warnings": all_warnings,
        }

    # Try pdftotext second
    text, mode, warnings = try_pdftotext(pdf_path)
    all_warnings.extend(warnings)
    if text.strip():
        return {
            "success": True,
            "text": text,
            "extractionMode": mode,
            "textLength": len(text),
            "toolUsed": "pdftotext",
            "warnings": all_warnings,
        }

    # Failed
    all_warnings.append({
        "code": "ALL_METHODS_FAILED",
        "message": "No text could be extracted. OCR or manual specialist review is required.",
        "severity": "error",
    })
    return {
        "success": False,
        "text": "",
        "extractionMode": "failed",
        "textLength": 0,
        "toolUsed": "none",
        "warnings": all_warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from credit report PDFs")
    parser.add_argument("input", type=Path, help="PDF file or directory of PDFs")
    parser.add_argument("--out", type=Path, default=None, help="Output directory for results")
    args = parser.parse_args()

    input_path = args.input.resolve()
    out_dir = (args.out or input_path.parent / "extraction_results").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs: list[Path] = []
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        pdfs = [input_path]
    elif input_path.is_dir():
        pdfs = sorted(input_path.glob("*.pdf"))
    else:
        print(f"Error: {input_path} is not a PDF file or directory", file=sys.stderr)
        return 1

    if not pdfs:
        print(f"No PDF files found in {input_path}", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    for pdf_path in pdfs:
        print(f"Extracting: {pdf_path.name}...")
        result = extract_text(pdf_path)
        result["fileName"] = pdf_path.name
        result["filePath"] = str(pdf_path)

        # Save raw text
        if result["success"] and result["text"]:
            text_file = out_dir / f"{pdf_path.stem}_raw_text.txt"
            text_file.write_text(result["text"], encoding="utf-8")
            result["rawTextFile"] = str(text_file)

        # Save metadata JSON
        meta_file = out_dir / f"{pdf_path.stem}_extraction_meta.json"
        meta_data = {k: v for k, v in result.items() if k != "text"}
        meta_file.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
        result["metaFile"] = str(meta_file)

        status = "OK" if result["success"] else "FAILED"
        print(f"  [{status}] mode={result['extractionMode']} tool={result['toolUsed']} length={result['textLength']}")
        results.append(result)

    # Summary
    summary = {
        "totalFiles": len(results),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "toolsAvailable": {
            "pypdf": _check_module("pypdf"),
            "pdftotext": bool(shutil.which("pdftotext")),
        },
        "results": [{k: v for k, v in r.items() if k != "text"} for r in results],
    }
    summary_file = out_dir / "extraction_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSummary: {summary['successful']}/{summary['totalFiles']} extracted successfully")
    print(f"Results written to: {out_dir}")
    return 0


def _check_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    sys.exit(main())
