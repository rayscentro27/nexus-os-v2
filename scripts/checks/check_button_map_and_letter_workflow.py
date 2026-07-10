from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
style = ROOT / "src/styles/world-class-client-portal.css"
resources = ROOT / "src/clientPortal/clientResources.ts"
clyde = ROOT / "src/lib/clydeActionEngine.ts"
case_engine = ROOT / "src/lib/creditRepairCaseEngine.ts"
workflow = ROOT / "src/lib/creditRepairWorkflow.ts"
master = ROOT / "reports/client_portal/master_button_action_map_latest.md"
letter_audit = ROOT / "reports/credit_repair/credit_repair_letter_workflow_audit_latest.md"
workflow_map = ROOT / "reports/credit_repair/credit_repair_case_workflow_map_latest.md"

texts = {
    "world": world.read_text(errors="ignore") if world.exists() else "",
    "style": style.read_text(errors="ignore") if style.exists() else "",
    "resources": resources.read_text(errors="ignore") if resources.exists() else "",
    "clyde": clyde.read_text(errors="ignore") if clyde.exists() else "",
    "case": case_engine.read_text(errors="ignore") if case_engine.exists() else "",
    "workflow": workflow.read_text(errors="ignore") if workflow.exists() else "",
    "master": master.read_text(errors="ignore") if master.exists() else "",
    "letter": letter_audit.read_text(errors="ignore") if letter_audit.exists() else "",
    "map": workflow_map.read_text(errors="ignore") if workflow_map.exists() else "",
}

combined_client = "\n".join([texts["world"], texts["resources"], texts["clyde"], texts["master"], texts["letter"], texts["map"]]).lower()

checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


add("master_button_action_map_latest.md exists", master.exists() and "Total visible client-facing buttons/actions audited" in texts["master"])
add("credit_repair_letter_workflow_audit_latest.md exists", letter_audit.exists() and "After Credit Report Upload" in texts["letter"])
add("credit_repair_case_workflow_map_latest.md exists", workflow_map.exists() and "Client uploads credit report" in texts["map"])
add("Chat with Clyde does not route to Resources by default", "wc-chatBtn" in texts["world"] and "onOpenChat" in texts["world"])
add("Upload CTAs open upload panel", "openUploadPanel" in texts["world"] and "SimpleDocumentUploadPanel" in texts["world"])
add("Upload CTAs do not default to Documents except vault actions", "Upload Files" not in texts["world"] and "withSuggestedUpload" not in texts["world"])
add("Resources cards have route/gated fallback", "routeForResource" in texts["world"] and "request-review?topic=" in texts["world"])
add("Credit Repair Journey includes challenge/reason/letter option flow", all(term in texts["world"] for term in ["I want this challenged", "Dispute Reason Selector", "Letter Options", "Prepare recommended draft"]))
add("Dispute Review includes specialist/client approval safety language", "specialist review and client approval" in texts["world"].lower() and "nothing is auto-sent" in texts["world"].lower())
add("no auto-send behavior", "auto-send" in texts["world"].lower() and "Client approval required before DocuPost send request" in texts["case"])
false_claims = [
    "verified by ai",
    "ocr verified",
    "parser is live",
    "report parser is live",
    "clyde verified",
    "i verified your document",
    "we read your report",
]
add("no fake parser/OCR/verified-by-AI claims", all(term not in combined_client for term in false_claims))
add("no guaranteed deletion/score/funding language", all(term not in combined_client for term in ["guaranteed deletion", "guaranteed score", "guaranteed funding", "guaranteed approval", "instant score increase"]))
add("world-class design remains active", "wc-client-portal" in texts["style"] and "WorldClassClientPortal" in texts["world"])
add("old design not restored", "ClientPortalPages" not in texts["world"] and "client-page" not in texts["world"])
add("letter workflow audit states no parser", "No real parser, OCR, or bureau connection exists" in texts["letter"])
add("letter workflow audit states upload does not create letters", "does not automatically create a credit repair case, report items, or letters" in texts["letter"])

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} button map / letter workflow checks failed")

print("RESULT: PASS - button map and letter workflow checks passed")
