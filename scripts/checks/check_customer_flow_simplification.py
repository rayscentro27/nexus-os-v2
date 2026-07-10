from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
style = ROOT / "src/styles/world-class-client-portal.css"
flow = ROOT / "src/lib/customerFlowEngine.ts"
report_flow = ROOT / "src/lib/creditReportReviewFlow.ts"
strategy = ROOT / "src/lib/creditStrategyResearchEngine.ts"
resources = ROOT / "src/clientPortal/clientResources.ts"
guidance = ROOT / "src/clientPortal/clientGuidance.ts"

texts = {
    "world": world.read_text(errors="ignore") if world.exists() else "",
    "style": style.read_text(errors="ignore") if style.exists() else "",
    "flow": flow.read_text(errors="ignore") if flow.exists() else "",
    "report_flow": report_flow.read_text(errors="ignore") if report_flow.exists() else "",
    "strategy": strategy.read_text(errors="ignore") if strategy.exists() else "",
    "resources": resources.read_text(errors="ignore") if resources.exists() else "",
    "guidance": guidance.read_text(errors="ignore") if guidance.exists() else "",
}

combined_client = "\n".join([texts["world"], texts["resources"], texts["guidance"]]).lower()

checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


add("customerFlowEngine.ts exists", flow.exists() and "calculateCustomerFlowStatus" in texts["flow"])
add("Credit Profile / Business Profile / Business Funding language exists", all(term in texts["world"] for term in ["Credit Profile", "Business Profile", "Business Funding"]))
add("Home dashboard references the 3 main tracks", "wc-trackGrid" in texts["world"] and "Your Goal" in texts["world"])
add("Credit Profile has report-first flow", report_flow.exists() and "Start with Your Credit Report" in texts["world"] and "Upload Credit Report" in texts["report_flow"])
add("Business Profile combines personal/business setup flow", "Personal & business intake" in texts["world"] and "Complete your business foundation" in texts["world"])
add("Business Funding has readiness/review flow", "Funding Readiness Snapshot" in texts["world"] and "Request GoClear Funding Review" in texts["world"])
add("Resources do not use affiliate wording", "affiliate" not in texts["resources"].lower() and "sponsored" not in texts["resources"].lower() and "commission" not in texts["resources"].lower())
add("Clyde guidance is simplified and action-oriented", "Clyde Credit Specialist" in texts["world"] and "what GoClear is reviewing" in texts["world"] and "next step" in texts["world"])
add("no guaranteed deletion/funding/score language", all(term not in combined_client for term in ["guaranteed deletion", "guaranteed approval", "guaranteed funding", "guaranteed score", "instant score increase"]))
add("world-class design remains active", "wc-client-portal" in texts["style"] and "WorldClassClientPortal" in texts["world"])
add("old design not restored", "ClientPortalPages" not in texts["world"] and "client-page" not in texts["world"])
add("route compatibility remains: credit utilization", "'/client/credit-utilization': { key: 'credit'" in texts["world"])
add("route compatibility remains: credit repair journey", "'/client/credit-repair-journey': { key: 'credit'" in texts["world"])
add("route compatibility remains: dispute review", "'/client/dispute-review': { key: 'dispute'" in texts["world"])
add("route compatibility remains: business setup", "'/client/business-setup': { key: 'business'" in texts["world"])
add("route compatibility remains: funding readiness", "'/client/funding-readiness': { key: 'funding'" in texts["world"])
add("backend strategy layer exists", strategy.exists() and "recommendNextRoundStrategy" in texts["strategy"])

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} customer flow simplification checks failed")

print("RESULT: PASS - customer flow simplification checks passed")
