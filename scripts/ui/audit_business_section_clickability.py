#!/usr/bin/env python3
"""Audit business section clickability by inspecting source files.

Checks that:
  - Business tabs exist in the sidebar (clients, credit, opportunity, research, monetization, marketing)
  - Each tab has a corresponding page component
  - Page components are not just static display (check for useState, onClick handlers)

Returns JSON with: tabs_found, pages_verified, dead_actions_count, issues
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


def read_file(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except FileNotFoundError:
        return ""


def audit():
    issues = []
    tabs_found = []
    pages_verified = []
    dead_actions = 0

    admin_src = read_file(ADMIN_UI)

    # 1. Check business tabs exist in navGroups
    for tab_id, component_name in BUSINESS_TABS:
        pattern = rf"id:\s*['\"]{tab_id}['\"]"
        if re.search(pattern, admin_src):
            tabs_found.append(tab_id)
        else:
            issues.append(f"Tab '{tab_id}' not found in navGroups sidebar definition")
            dead_actions += 1

    # 2. Check each tab has a corresponding page component and renders it
    for tab_id, component_name in BUSINESS_TABS:
        comp_file = COMPONENTS_DIR / f"{component_name}.jsx"
        comp_src = read_file(comp_file)

        if not comp_src:
            issues.append(f"Component file missing: {component_name}.jsx")
            dead_actions += 1
            continue

        # Check the component is imported and used in NexusAdminUI
        import_pattern = rf"import\s+{component_name}\s+from"
        if not re.search(import_pattern, admin_src):
            issues.append(f"Component {component_name} not imported in NexusAdminUI.jsx")
            dead_actions += 1
            continue

        # Check the component is rendered in the page map for this tab
        render_pattern = rf"{tab_id}:\s*<.*?{component_name}"
        if not re.search(render_pattern, admin_src, re.DOTALL):
            issues.append(f"Component {component_name} not rendered for tab '{tab_id}' in page map")
            dead_actions += 1
            continue

        pages_verified.append(tab_id)

        # 3. Check component is not just static display
        has_use_state = "useState" in comp_src
        has_on_click = "onClick" in comp_src
        has_buttons = "<button" in comp_src

        if not has_use_state:
            issues.append(f"{component_name}: no useState found (may be static)")
        if not has_on_click:
            issues.append(f"{component_name}: no onClick handlers found")
        if not has_buttons:
            issues.append(f"{component_name}: no <button> elements found")

        if not (has_use_state and has_on_click and has_buttons):
            dead_actions += 1

    ok = len(tabs_found) == len(BUSINESS_TABS) and len(pages_verified) == len(BUSINESS_TABS) and dead_actions == 0
    payload = {
        "ok": ok,
        "status": "business_section_audit_passed" if ok else "business_section_audit_failed",
        "tabs_found": tabs_found,
        "tabs_expected": [t[0] for t in BUSINESS_TABS],
        "pages_verified": pages_verified,
        "dead_actions_count": dead_actions,
        "issues": issues,
        "external_action_performed": False,
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Audit business section clickability")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = parser.parse_args()

    payload = audit()

    if args.json:
        print(json.dumps(payload, indent=2))

    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
