#!/usr/bin/env python3
"""Static guard for Nexus Funding Readiness positioning and safety gates."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"missing required file: {path}")
    return target.read_text(encoding="utf-8")

def require(text: str, phrase: str, surface: str) -> None:
    if phrase.lower() not in text.lower():
        raise AssertionError(f"{surface} missing: {phrase}")

def main() -> int:
    positioning = read("src/content/nexusPositioning.ts")
    client_paths = [
        "src/pages/client/WorldClassClientPortal.jsx",
        "src/pages/client/ClientPortalPages.jsx",
        "src/components/client/CreditRepairJourneyView.jsx",
        "src/components/client/ClientPortalShell.jsx",
        "src/clientPortal/clientGuidance.ts",
        "src/clientPortal/clientResources.ts",
        "src/lib/clydeActionEngine.ts",
    ]
    client_copy = "\n".join(read(path) for path in client_paths)
    admin = read("src/components/CreditSpecialistWorkbench.jsx") + read("src/admin/NexusAdminUI.jsx")
    letters = read("src/lib/disputeLetterDraftGenerator.ts") + admin
    workflow = read("src/lib/creditRepairWorkflow.ts") + read("src/lib/creditRepairCaseEngine.ts")

    require(positioning, "Nexus Funding Readiness", "positioning guide")
    require(positioning, "Funding readiness does not guarantee approval", "funding disclaimer")

    restricted_claims = [
        r"guaranteed deletion", r"guaranteed score(?: increase)?",
        r"guaranteed approval", r"we repair your credit",
        r"remove negative items", r"credit repair experts",
    ]
    for pattern in restricted_claims:
        if re.search(pattern, client_copy, flags=re.I):
            raise AssertionError(f"restricted client-facing claim found: {pattern}")

    require(admin, "Credit & Funding Readiness Review", "admin")
    require(admin, "funding-impact items", "report analysis")
    require(admin, "Suggested next steps", "report analysis")
    require(client_copy, "Tier 1 and Tier 2 funding", "client/Clyde copy")
    require(client_copy, "does not guarantee", "Clyde safety guidance")
    require(letters, "Draft preview only", "draft letter preview")
    require(letters, "requires review and approval before use", "draft letter approval disclaimer")
    require(workflow, "Client approval required", "DocuPost gate")
    require(workflow, "approved_for_docupost", "DocuPost gate")
    if re.search(r"(?:automatically|auto[- ]?send).{0,40}DocuPost", client_copy + admin, flags=re.I) and not re.search(r"no (?:letters? (?:are )?sent )?automatically|no auto-send|not auto-sent", client_copy + admin, flags=re.I):
        raise AssertionError("auto-send language is not explicitly negated")

    print("PASS: Nexus Funding Readiness positioning and safety gates verified")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
