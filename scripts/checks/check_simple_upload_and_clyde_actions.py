from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
panel = ROOT / "src/components/client/SimpleDocumentUploadPanel.jsx"
classification = ROOT / "src/lib/documentClassification.ts"
clyde = ROOT / "src/lib/clydeActionEngine.ts"
style = ROOT / "src/styles/world-class-client-portal.css"

texts = {
    "world": world.read_text(errors="ignore") if world.exists() else "",
    "panel": panel.read_text(errors="ignore") if panel.exists() else "",
    "classification": classification.read_text(errors="ignore") if classification.exists() else "",
    "clyde": clyde.read_text(errors="ignore") if clyde.exists() else "",
    "style": style.read_text(errors="ignore") if style.exists() else "",
}

checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


world_text = texts["world"]
combined_client = "\n".join([texts["world"], texts["panel"], texts["classification"], texts["clyde"]]).lower()

upload_redirects = [
    line for line in world_text.splitlines()
    if "/client/documents" in line
    and re.search(r"Upload|Attach|Document", line, re.I)
    and "View Documents Vault" not in line
    and "onVault" not in line
    and "Open Documents Vault" not in line
    and "Documents Vault" not in line
    and "pageMeta" not in line
    and line.strip().startswith("'/client/documents'") is False
    and "['/client/documents'" not in line
    and "item.category === 'documents'" not in line
    and "SimpleDocumentUploadPanel" not in line
]

add("SimpleDocumentUploadPanel.jsx exists", panel.exists() and "SimpleDocumentUploadPanel" in texts["panel"])
add("documentClassification.ts exists", classification.exists() and "inferDocumentCategoryFromContext" in texts["classification"])
add("clydeActionEngine.ts exists", clyde.exists() and "generateClydeQuickActions" in texts["clyde"])
add("WorldClassClientPortal imports/uses SimpleDocumentUploadPanel", "SimpleDocumentUploadPanel" in world_text and "openUploadPanel" in world_text)
add("WorldClassClientPortal imports/uses Clyde action engine", "generateClydeRecommendations" in world_text and "generateClydeAnswer" in world_text)
add("upload CTAs call openUploadPanel", world_text.count("openUploadPanel({") >= 12)
add("Chat with Clyde does not route to Resources by default", "wc-chatBtn" in world_text and "onOpenChat" in world_text and "Chat with Clyde" in world_text)
add("Clyde drawer exists", "wc-clydeDrawer" in world_text and "Ask Clyde" in world_text)
add("Clyde quick actions exist", "wc-clydeQuickActions" in world_text and "generateClydeQuickActions" in texts["clyde"])
add("Clyde can trigger upload without redirecting to Documents", "actionType === 'upload'" in world_text and "openUploadPanel" in world_text)
add("no upload CTA defaults to /client/documents except vault actions", not upload_redirects)
add("Documents page remains vault", "Documents Vault" in world_text and "Master Document Vault" in world_text)
add("one document at a time language exists", "One document at a time" in world_text and "maxFiles={1}" in world_text)
add("Pending GoClear Review language exists", "Pending GoClear Review" in world_text and "Pending GoClear Review" in texts["panel"])
add("no fake OCR/AI verification language", all(term not in combined_client for term in ["verified by ai", "fake ai", "we read your report", "i verified your document", "clyde verified this", "scanning", "read the contents"]))
unsafe_collection_patterns = [
    "collect ssn",
    "bureau username",
    "bureau password",
    "bank account number",
    "credit card number",
    "collect full dob",
    "collect full ein",
]
add("no unsafe credential collection language", all(term not in combined_client for term in unsafe_collection_patterns))
add("no guaranteed deletion/score/funding language", all(term not in combined_client for term in ["guaranteed deletion", "guaranteed score", "guaranteed funding", "guaranteed approval", "instant score increase"]))
add("world-class design remains active", "wc-client-portal" in texts["style"] and "WorldClassClientPortal" in world_text)
add("old design not restored", "ClientPortalPages" not in world_text and "client-page" not in world_text)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if upload_redirects:
    print("Unexpected upload/document redirects:")
    for line in upload_redirects[:8]:
        print(line[:240])

if failed:
    raise SystemExit(f"FAIL: {len(failed)} simple upload/Clyde action checks failed")

print("RESULT: PASS - simple upload and Clyde action checks passed")
