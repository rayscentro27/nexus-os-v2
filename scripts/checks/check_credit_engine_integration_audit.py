#!/usr/bin/env python3
"""Check: Credit Engine Integration Audit completeness.

Verifies that all required audit reports, scripts, and safety gates exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def check_file_exists(path: str, label: str) -> bool:
    p = Path(path)
    exists = p.exists()
    status = "PASS" if exists else "FAIL"
    print(f"  [{status}] {label}: {path}")
    return exists


def check_file_contains(path: str, substrings: list[str], label: str) -> bool:
    p = Path(path)
    if not p.exists():
        print(f"  [FAIL] {label}: file does not exist ({path})")
        return False
    content = p.read_text(encoding="utf-8", errors="ignore")
    results = []
    for sub in substrings:
        found = sub.lower() in content.lower()
        results.append(found)
        if not found:
            print(f"  [FAIL] {label}: missing '{sub}' in {path}")
    if all(results):
        print(f"  [PASS] {label}")
    return all(results)


def check_no_forbidden_patterns(path: str, patterns: list[str], label: str) -> bool:
    p = Path(path)
    if not p.exists():
        print(f"  [SKIP] {label}: file does not exist")
        return True
    content = p.read_text(encoding="utf-8", errors="ignore")
    found_bad = []
    for pat in patterns:
        if pat.lower() in content.lower():
            found_bad.append(pat)
    if found_bad:
        print(f"  [FAIL] {label}: found forbidden patterns: {found_bad}")
        return False
    print(f"  [PASS] {label}")
    return True


def main() -> int:
    print("=== Credit Engine Integration Audit Check ===\n")
    all_pass = True

    # Phase A: Research report
    print("--- Phase A: Research Report ---")
    all_pass &= check_file_exists(
        "reports/credit_repair/open_source_credit_engine_research_latest.md",
        "Open source research report"
    )

    # Phase B: Gap audit
    print("\n--- Phase B: Gap Audit ---")
    all_pass &= check_file_exists(
        "reports/credit_repair/nexus_credit_engine_gap_audit_latest.md",
        "Nexus engine gap audit"
    )

    # Phase C: Extraction script
    print("\n--- Phase C: Extraction Script ---")
    all_pass &= check_file_exists(
        "scripts/credit/extract_credit_report_text.py",
        "extract_credit_report_text.py"
    )

    # Phase D: Parser CLI
    print("\n--- Phase D: Parser CLI ---")
    all_pass &= check_file_exists(
        "scripts/credit/parse_credit_report_fixture.py",
        "parse_credit_report_fixture.py"
    )
    all_pass &= check_file_contains(
        "scripts/credit/parse_credit_report_fixture.py",
        ["pypdf", "raw_text"],
        "Parser uses extraction path"
    )

    # Phase G: Proof script
    print("\n--- Phase G: Proof Script ---")
    all_pass &= check_file_exists(
        "scripts/credit/prove_credit_engine_flow.py",
        "prove_credit_engine_flow.py"
    )

    # Phase H: Dispute letter draft generator
    print("\n--- Phase H: Dispute Letter Draft ---")
    all_pass &= check_file_exists(
        "src/lib/disputeLetterDraftGenerator.ts",
        "disputeLetterDraftGenerator.ts"
    )

    # Phase L: Engine proof
    print("\n--- Phase L: Engine Proof ---")
    all_pass &= check_file_exists(
        "reports/credit_repair/engine_proof/engine_proof_summary_latest.md",
        "Engine proof summary"
    )

    # Phase I: SmartCredit import path
    print("\n--- Phase I: SmartCredit Import ---")
    all_pass &= check_file_exists(
        "reports/credit_repair/smartcredit_import_path_latest.md",
        "SmartCredit import path report"
    )

    # Phase J: Postponed integrations
    print("\n--- Phase J: Postponed Integrations ---")
    all_pass &= check_file_exists(
        "reports/credit_repair/postponed_external_integrations_latest.md",
        "Postponed integrations report"
    )

    # Phase N: Parser fixture results
    print("\n--- Phase N: Parser Fixture Results ---")
    all_pass &= check_file_exists(
        "reports/credit_repair/credit_report_parser_fixture_results_latest.md",
        "Parser fixture results"
    )

    # Safety checks
    print("\n--- Safety Checks ---")

    # No fake OCR claims
    all_pass &= check_no_forbidden_patterns(
        "reports/credit_repair/nexus_credit_engine_gap_audit_latest.md",
        ["OCR works", "OCR is working", "OCR success"],
        "No fake OCR claims in gap audit"
    )

    # No bureau credential collection
    all_pass &= check_no_forbidden_patterns(
        "src/lib/creditReportParser.ts",
        ["password", "credential", "bureau_login", "ssn", "social_security"],
        "No bureau credential collection in parser"
    )

    # No automatic DocuPost send
    all_pass &= check_no_forbidden_patterns(
        "src/lib/creditRepairWorkflow.ts",
        ["auto_send", "automatic_send", "send_without_approval"],
        "No automatic DocuPost send"
    )

    # No guarantee language (positive guarantees only — disclaimers like "does not guarantee" are OK)
    all_pass &= check_no_forbidden_patterns(
        "src/lib/disputeStrategyKnowledge.ts",
        ["guaranteed removal", "guaranteed deletion", "guaranteed score", "we guarantee", "will guarantee"],
        "No positive guarantee language in dispute strategy"
    )

    # Specialist/client approval gates documented
    all_pass &= check_file_contains(
        "src/lib/creditRepairWorkflow.ts",
        ["specialist_review", "client_review", "client_approved", "approval_required"],
        "Approval gates documented in workflow"
    )

    # Summary
    print(f"\n{'=' * 50}")
    if all_pass:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
    print(f"{'=' * 50}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
