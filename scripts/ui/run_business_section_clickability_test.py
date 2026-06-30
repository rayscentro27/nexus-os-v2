#!/usr/bin/env python3
"""Test business section clickability by inspecting source files.

Tests that:
  - Business tabs open real pages (not fallback)
  - Each page has interactive elements (buttons, drawers, state)
  - No "coming soon" or "not implemented" placeholders

Returns JSON with: tests_passed, tests_failed, details
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
ADMIN_UI = SRC / "admin" / "NexusAdminUI.jsx"
COMPONENTS_DIR = SRC / "components"

BUSINESS_TABS = [
    ("clients", "ClientsPanel"),
    ("credit", "CreditFundingPanel"),
    ("opportunity", "BusinessOpportunitiesPanel"),
    ("research", "ResearchEnginePanel"),
    ("monetization", "MonetizationPanel"),
    ("marketing", "MarketingDraftsPanel"),
]

PLACEHOLDER_PATTERNS = [
    r"coming\s+soon",
    r"not\s+implemented",
    r"placeholder",
    r"todo",
    r"under\s+construction",
    r"work\s+in\s+progress",
    r"stay\s+tuned",
]


def read_file(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except FileNotFoundError:
        return ""


def run_tests():
    details = []
    passed = 0
    failed = 0

    admin_src = read_file(ADMIN_UI)

    for tab_id, component_name in BUSINESS_TABS:
        comp_file = COMPONENTS_DIR / f"{component_name}.jsx"
        comp_src = read_file(comp_file)

        # Test 1: Tab exists in sidebar
        tab_exists = bool(re.search(rf"id:\s*['\"]{tab_id}['\"]", admin_src))
        test_result = {"test": f"{tab_id}: tab exists in sidebar", "passed": tab_exists}
        if tab_exists:
            passed += 1
        else:
            failed += 1
        details.append(test_result)

        # Test 2: Component file exists
        file_exists = comp_file.exists()
        test_result = {"test": f"{tab_id}: component file exists ({component_name}.jsx)", "passed": file_exists}
        if file_exists:
            passed += 1
        else:
            failed += 1
            details.append(test_result)
            continue
        details.append(test_result)

        # Test 3: Component is imported in NexusAdminUI
        imported = bool(re.search(rf"import\s+{component_name}\s+from", admin_src))
        test_result = {"test": f"{tab_id}: component imported in NexusAdminUI", "passed": imported}
        if imported:
            passed += 1
        else:
            failed += 1
        details.append(test_result)

        # Test 4: Component is rendered in page map (not falling back to CommandCenter)
        rendered = bool(re.search(rf"{tab_id}:\s*<.*?{component_name}", admin_src, re.DOTALL))
        test_result = {"test": f"{tab_id}: component rendered in page map (not fallback)", "passed": rendered}
        if rendered:
            passed += 1
        else:
            failed += 1
        details.append(test_result)

        # Test 5: Has interactive buttons
        button_count = len(re.findall(r"<button", comp_src))
        has_buttons = button_count >= 1
        test_result = {"test": f"{tab_id}: has interactive buttons (found {button_count})", "passed": has_buttons}
        if has_buttons:
            passed += 1
        else:
            failed += 1
        details.append(test_result)

        # Test 6: Has useState for state management
        has_state = "useState" in comp_src
        test_result = {"test": f"{tab_id}: uses useState for state management", "passed": has_state}
        if has_state:
            passed += 1
        else:
            failed += 1
        details.append(test_result)

        # Test 7: Has drawer/detail overlay (real page pattern)
        has_drawer = "Drawer" in comp_src or "drawer" in comp_src.lower() or "overlay" in comp_src.lower()
        test_result = {"test": f"{tab_id}: has drawer or detail overlay", "passed": has_drawer}
        if has_drawer:
            passed += 1
        else:
            failed += 1
        details.append(test_result)

        # Test 8: No placeholder text
        has_placeholder = any(re.search(p, comp_src, re.IGNORECASE) for p in PLACEHOLDER_PATTERNS)
        no_placeholder = not has_placeholder
        test_result = {"test": f"{tab_id}: no placeholder/coming-soon text", "passed": no_placeholder}
        if no_placeholder:
            passed += 1
        else:
            failed += 1
            # Find which placeholder was found
            for p in PLACEHOLDER_PATTERNS:
                m = re.search(p, comp_src, re.IGNORECASE)
                if m:
                    test_result["placeholder_found"] = m.group()
                    break
        details.append(test_result)

        # Test 9: Has onClick handlers
        onClick_count = len(re.findall(r"onClick", comp_src))
        has_onclick = onClick_count >= 1
        test_result = {"test": f"{tab_id}: has onClick handlers (found {onClick_count})", "passed": has_onclick}
        if has_onclick:
            passed += 1
        else:
            failed += 1
        details.append(test_result)

    all_passed = failed == 0
    payload = {
        "ok": all_passed,
        "status": "business_clickability_test_passed" if all_passed else "business_clickability_test_failed",
        "tests_passed": passed,
        "tests_failed": failed,
        "total_tests": passed + failed,
        "details": details,
        "external_action_performed": False,
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Test business section clickability")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    payload = run_tests()

    if args.json:
        print(json.dumps(payload, indent=2))

    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
