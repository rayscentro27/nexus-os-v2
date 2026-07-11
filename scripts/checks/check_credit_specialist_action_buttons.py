#!/usr/bin/env python3
"""Check Credit Specialist Workbench action buttons are wired safely."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

workbench = (ROOT / "src/components/CreditSpecialistWorkbench.jsx").read_text(errors="ignore")
case_engine = (ROOT / "src/lib/creditRepairCaseEngine.ts").read_text(errors="ignore")
app = (ROOT / "src/app/App.tsx").read_text(errors="ignore")

checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


add("Review Report handler exists", "function handleReviewReport" in workbench and "setReviewPanelOpen(true)" in workbench)
add("Run Parser Preview handler exists", "function handleRunParserPreview" in workbench and "setParserPanelOpen(true)" in workbench)
add("Create Credit Repair Case handler exists", "function handleCreateCreditRepairCase" in workbench and "getOrCreateCreditRepairCaseForDocument" in workbench)
add("Add Manual Item handler exists", "function handleAddManualItem" in workbench and "manualItemFormOpen" in workbench)
add("Mark Needs Info handler exists", "function handleMarkNeedsInfo" in workbench and "goclear_review_status: 'needs_info'" in workbench)
add("Review detail panel opens", "Report Detail" in workbench and "Safe file preview is not available yet" in workbench)
add("Case helper exists", "getOrCreateCreditRepairCaseForDocument" in case_engine and "credit_repair_cases" in case_engine)
add("Manual item form exists", "Add Manual Item" in workbench and "Save Manual Item" in workbench and "Specialist-entered item" in workbench)
unsafe_field_patterns = [
    r"<label[^>]*>\s*SSN",
    r"<label[^>]*>\s*Full DOB",
    r"<label[^>]*>\s*Full account",
    r"<input[^>]+placeholder=['\"][^'\"]*(SSN|full DOB|full account|bureau username|bureau password)",
]
add("Manual item form does not request unsafe fields", not any(re.search(pattern, workbench, re.I) for pattern in unsafe_field_patterns))
add("Parser preview does not fake live parsing", "Live uploaded file parsing requires a backend file extraction worker" in workbench)
add("Mark Needs Info has feedback/error", "Unable to mark needs info" in workbench and "Marked report as Needs Info" in workbench)
add("Action feedback exists", "actionMessage" in workbench and "actionError" in workbench)
add("Tabs have meaningful empty states", "Create a case from Client Queue" in workbench and "Add Manual Item from Client Queue" in workbench and "No mail jobs yet" in workbench)
add("No auto letters from upload", "No letters were created" in workbench and "No letters are generated automatically" in workbench)
add("No auto DocuPost from upload", "DocuPost" in workbench and "approval_required" in (ROOT / "src/lib/creditRepairWorkflow.ts").read_text(errors="ignore"))
add("Admin guard remains secure", "AdminGuard" in app and "ui-smoke" in app)
add("Test client not granted admin in code", "theworldzmine@gmail.com" not in (workbench + case_engine + app).lower())

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} credit specialist action button checks failed")

print("RESULT: PASS - credit specialist action buttons are wired safely")
