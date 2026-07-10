from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

helper = ROOT / "src/lib/creditRepairCaseEngine.ts"
knowledge = ROOT / "src/lib/disputeStrategyKnowledge.ts"
world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
admin = ROOT / "src/components/CreditSpecialistWorkbench.jsx"
root = ROOT / "src/pages/client/ClientPortalRoot.jsx"
style = ROOT / "src/styles/world-class-client-portal.css"
migrations = list((ROOT / "supabase/migrations").glob("*credit_repair_case_engine*.sql"))

texts = {
    "helper": helper.read_text(errors="ignore") if helper.exists() else "",
    "knowledge": knowledge.read_text(errors="ignore") if knowledge.exists() else "",
    "world": world.read_text(errors="ignore") if world.exists() else "",
    "admin": admin.read_text(errors="ignore") if admin.exists() else "",
    "root": root.read_text(errors="ignore") if root.exists() else "",
    "style": style.read_text(errors="ignore") if style.exists() else "",
    "migration": "\n".join(p.read_text(errors="ignore") for p in migrations),
}

combined = "\n".join(texts.values()).lower()

checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


add("creditRepairCaseEngine helper exists", helper.exists() and "getOrCreateCreditRepairCase" in texts["helper"])
add("disputeStrategyKnowledge exists", knowledge.exists() and "DISPUTE_REASON_LABELS" in texts["knowledge"])
add("case engine migration exists", bool(migrations) and "credit_repair_cases" in texts["migration"] and "credit_dispute_outcomes" in texts["migration"])
add("case engine route content exists in WorldClassClientPortal", "CreditRepairCaseEnginePanel" in texts["world"] and "Credit Repair Case Engine" in texts["world"])
add("dispute reason selector exists", "Dispute Reason Selector" in texts["world"] and "not_mine" in texts["knowledge"] and "incorrect_balance" in texts["knowledge"])
add("letter options exist", "Letter Options" in texts["world"] and "generateDisputeLetterOptions" in texts["helper"])
add("client approval language exists", "client approval" in texts["world"].lower() and "clientApproveLetter" in texts["helper"])
add("specialist review language exists", "specialist review" in texts["world"].lower() and "approveLetterForClientReview" in texts["helper"])
add("DocuPost no-auto-send safety language exists", "No auto-send" in texts["world"] and "approval-gated" in texts["world"])
add("outcome categories exist", all(term in texts["knowledge"] for term in ["deleted", "corrected", "verified", "no_response", "client_evidence_needed"]))
add("Clyde credit specialist language exists", "which items you want challenged" in texts["world"] and "prepare dispute options" in texts["world"])
add("no guaranteed deletion language", "guaranteed deletion" not in combined and "guaranteed score increase" not in combined and "instant credit repair" not in combined)
add("no unsafe sensitive collection", "bureau username" not in combined and "bureau password" not in combined and "full account numbers" in texts["world"])
add("/client/dispute-review remains world-class shell", "'/client/dispute-review': { key: 'dispute'" in texts["world"] and "<ClientPortalShell" not in texts["root"])
add("/admin/credit-specialist references case engine", "Case Engine" in texts["admin"] and "OUTCOME_CATEGORIES" in texts["admin"])
add("current design remains active", "wc-client-portal" in texts["style"] and "wc-caseEngine" in texts["style"])

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} credit repair case engine checks failed")

print("RESULT: PASS - credit repair case engine checks passed")
