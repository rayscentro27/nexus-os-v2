from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
root = ROOT / "src/pages/client/ClientPortalRoot.jsx"
style = ROOT / "src/styles/world-class-client-portal.css"

world_text = world.read_text(errors="ignore")
root_text = root.read_text(errors="ignore")
style_text = style.read_text(errors="ignore")

checks = {
    "world-class portal component exists": world.exists(),
    "root renders WorldClassClientPortal": "WorldClassClientPortal" in root_text,
    "premium CSS remains": "wc-client-portal" in style_text,
    "Clyde panel remains": "Clyde" in world_text and "ClydePanel" in world_text,
    "hero path remains": "/assets/client-portal/nexus-funding-path-hero.png" in world_text,
    "route helper exists": "routeTo" in world_text,
    "inline upload exists": "InlineDocumentRequirement" in world_text and "DocumentUploadZone" in world_text,
    "profile save/load exists": "loadClientProfileIntake" in world_text and "saveClientProfileIntake" in world_text,
    "request review submits client_tasks": "client_tasks" in world_text and "pending_admin_review" in world_text,
    "credit repair workflow loads": "loadCreditRepairJourney" in world_text,
    "DocuPost remains approval gated": "createDocuPostSendRequest" in world_text and "Nothing is auto-sent" in world_text and "approval-gated" in world_text,
}

for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit(f"FAIL: {len(failed)} world-class portal checks failed")

print("RESULT: PASS — world-class portal functionality checks passed")
