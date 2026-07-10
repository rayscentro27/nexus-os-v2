from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
style = ROOT / "src/styles/world-class-client-portal.css"
inline = ROOT / "src/components/client/InlineDocumentRequirement.jsx"
resources = ROOT / "src/clientPortal/clientResources.ts"
hero = ROOT / "public/assets/client-portal/nexus-funding-path-hero.png"

checks = []

def add(name, ok):
    checks.append((name, bool(ok)))

world_text = world.read_text(errors="ignore") if world.exists() else ""
style_text = style.read_text(errors="ignore") if style.exists() else ""
inline_text = inline.read_text(errors="ignore") if inline.exists() else ""
resources_text = resources.read_text(errors="ignore") if resources.exists() else ""

add("WorldClassClientPortal remains active", "WorldClassClientPortal" in world_text and "wc-client-portal" in world_text)
add("Current design files still exist", world.exists() and style.exists())
add("Hero image path still exists", hero.exists() and "/assets/client-portal/nexus-funding-path-hero.png" in world_text)
add("InlineDocumentRequirement exists", inline.exists() and "DocumentUploadZone" in inline_text)
add("DocumentUploadZone is embedded inline", "DocumentUploadZone" in world_text and "InlineDocumentRequirement" in world_text)
add("Profile guided intake sections exist", all(s in world_text for s in ["Basic Identity", "Credit Report Access", "Business Foundation", "EIN / Entity Details", "Funding Goals", "Required Documents", "Ready for Review"]))
add("EIN status exists", "ein_status" in world_text and "EIN status" in world_text)
add("Credit Report Access exists", "credit_report_access_status" in world_text and "Credit Report Access" in world_text)
add("CreditMonitoringConnectCard exists", "CreditMonitoringConnectCard" in world_text)
add("clientResources helper exists", resources.exists() and "getClientResources" in resources_text)
add("client-facing UI avoids affiliate wording", "affiliate" not in (world_text + resources_text).lower())
add("Resources language exists", any(term in world_text + resources_text for term in ["Resources", "Recommended Tools", "Partner Resources"]))
add("Request review has inline upload support", "review_support" in world_text and "InlineDocumentRequirement" in world_text)
add("Documents page remains master vault", "Master Document Vault" in world_text)
add("/client/credit-utilization compatibility remains", "'/client/credit-utilization'" in world_text)
add("Old design was not restored", "client-page" not in world_text and "ClientPageHeader" not in world_text)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} intake inline upload/resource checks failed")

print("RESULT: PASS — intake inline upload/resource checks passed")
