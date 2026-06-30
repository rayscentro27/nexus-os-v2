#!/usr/bin/env python3
"""Test business approval flows by inspecting component source files.

Tests that:
  - Approval buttons exist in business panels (check component source)
  - Receipt feedback is shown after approval
  - No real external actions are triggered
  - Ask Hermes inline button exists in each business panel

Returns JSON with: approval_flow_tests, receipt_tests, safety_tests
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS_DIR = ROOT / "src" / "components"

BUSINESS_PANELS = {
    "ClientsPanel": "ClientsPanel.jsx",
    "CreditFundingPanel": "CreditFundingPanel.jsx",
    "BusinessOpportunitiesPanel": "BusinessOpportunitiesPanel.jsx",
    "ResearchEnginePanel": "ResearchEnginePanel.jsx",
    "MonetizationPanel": "MonetizationPanel.jsx",
    "MarketingDraftsPanel": "MarketingDraftsPanel.jsx",
}

EXTERNAL_ACTION_PATTERNS = [
    r"fetch\s*\(",
    r"axios\.",
    r"XMLHttpRequest",
    r"navigator\.sendBeacon",
    r"window\.open",
    r"document\.location\s*=",
    r"window\.location\s*=",
    r"\.submit\(\)",
    r"\/api\/",
    r"\/webhook",
    r"supabase\.\w+\(",
]


def read_file(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except FileNotFoundError:
        return ""


def run_tests():
    approval_flow_tests = []
    receipt_tests = []
    safety_tests = []

    for panel_name, filename in BUSINESS_PANELS.items():
        comp_path = COMPONENTS_DIR / filename
        comp_src = read_file(comp_path)

        if not comp_src:
            approval_flow_tests.append({
                "panel": panel_name,
                "test": "component file exists",
                "passed": False,
                "detail": f"File not found: {filename}",
            })
            continue

        # --- Approval Flow Tests ---

        # Test: Approve button exists
        approve_buttons = len(re.findall(r"(?:Approve|approve)", comp_src))
        has_approve = approve_buttons >= 1
        approval_flow_tests.append({
            "panel": panel_name,
            "test": "approve button exists",
            "passed": has_approve,
            "detail": f"Found {approve_buttons} Approve references",
        })

        # Test: Hold button exists
        hold_buttons = len(re.findall(r"(?:Hold|hold)", comp_src))
        has_hold = hold_buttons >= 1
        approval_flow_tests.append({
            "panel": panel_name,
            "test": "hold button exists",
            "passed": has_hold,
            "detail": f"Found {hold_buttons} Hold references",
        })

        # Test: Reject button exists
        reject_buttons = len(re.findall(r"(?:Reject|reject)", comp_src))
        has_reject = reject_buttons >= 1
        approval_flow_tests.append({
            "panel": panel_name,
            "test": "reject button exists",
            "passed": has_reject,
            "detail": f"Found {reject_buttons} Reject references",
        })

        # Test: handleAction function sets status
        has_handle_action = bool(re.search(r"function\s+handle(?:Action|Approve|Hold)", comp_src))
        approval_flow_tests.append({
            "panel": panel_name,
            "test": "handleAction function exists",
            "passed": has_handle_action,
        })

        # --- Receipt Tests ---

        # Test: receipt state is declared
        has_receipt_state = bool(re.search(r"receipt.*useState|useState.*receipt", comp_src))
        receipt_tests.append({
            "panel": panel_name,
            "test": "receipt state declared (useState)",
            "passed": has_receipt_state,
        })

        # Test: receipt is set on action
        has_set_receipt = bool(re.search(r"setReceipt\s*\(", comp_src))
        receipt_tests.append({
            "panel": panel_name,
            "test": "setReceipt called on action",
            "passed": has_set_receipt,
        })

        # Test: receipt is rendered in JSX
        has_receipt_render = bool(re.search(r"nxos-receipt|receipt\s*&&", comp_src))
        receipt_tests.append({
            "panel": panel_name,
            "test": "receipt feedback rendered in JSX",
            "passed": has_receipt_render,
        })

        # --- Safety Tests ---

        # Test: No real external actions triggered
        external_calls = []
        for pattern in EXTERNAL_ACTION_PATTERNS:
            matches = re.findall(pattern, comp_src)
            if matches:
                external_calls.extend(matches)
        no_external = len(external_calls) == 0
        safety_tests.append({
            "panel": panel_name,
            "test": "no real external actions triggered",
            "passed": no_external,
            "detail": f"Found {len(external_calls)} external call patterns" if external_calls else "Clean",
            "external_calls": external_calls[:5],
        })

        # Test: Approval actions are local-only (status state, not API calls)
        has_local_status = bool(re.search(r"setStatus\s*\(", comp_src))
        safety_tests.append({
            "panel": panel_name,
            "test": "approval actions are local-only (setStatus, not API)",
            "passed": has_local_status,
        })

        # Test: Ask Hermes button exists
        has_ask_hermes = bool(re.search(r"Ask\s+Hermes|onAskHermes", comp_src))
        safety_tests.append({
            "panel": panel_name,
            "test": "Ask Hermes inline button exists",
            "passed": has_ask_hermes,
        })

        # Test: Receipt mentions "local status only" or similar safety language
        has_safety_note = bool(re.search(r"local\s+status|local\s+only|no\s+(?:backend|publishing|external)|safe\s+internal", comp_src, re.IGNORECASE))
        safety_tests.append({
            "panel": panel_name,
            "test": "safety language present (local-only disclaimer)",
            "passed": has_safety_note,
        })

    all_approval_passed = all(t["passed"] for t in approval_flow_tests)
    all_receipt_passed = all(t["passed"] for t in receipt_tests)
    all_safety_passed = all(t["passed"] for t in safety_tests)
    all_passed = all_approval_passed and all_receipt_passed and all_safety_passed

    payload = {
        "ok": all_passed,
        "status": "business_approval_flow_test_passed" if all_passed else "business_approval_flow_test_failed",
        "approval_flow_tests": approval_flow_tests,
        "approval_flow_passed": all_approval_passed,
        "receipt_tests": receipt_tests,
        "receipt_passed": all_receipt_passed,
        "safety_tests": safety_tests,
        "safety_passed": all_safety_passed,
        "external_action_performed": False,
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Test business approval flows")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    payload = run_tests()

    if args.json:
        print(json.dumps(payload, indent=2))

    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
