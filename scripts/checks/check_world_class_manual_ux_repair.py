import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
root = ROOT / "src/pages/client/ClientPortalRoot.jsx"
style = ROOT / "src/styles/world-class-client-portal.css"
admin_guard = ROOT / "src/components/auth/AdminGuard.tsx"

world_text = world.read_text(errors="ignore") if world.exists() else ""
root_text = root.read_text(errors="ignore") if root.exists() else ""
style_text = style.read_text(errors="ignore") if style.exists() else ""
admin_text = admin_guard.read_text(errors="ignore") if admin_guard.exists() else ""


def css_size(selector, prop="width"):
    matches = re.findall(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", style_text)
    values = []
    for block in matches:
        for value in re.findall(rf"{prop}\s*:\s*(\d+)px", block):
            values.append(int(value))
    return max(values or [0])


checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


add("WorldClassClientPortal remains active", world.exists() and "wc-client-portal" in world_text)
add("world-class-client-portal.css remains active", style.exists() and "Manual UX repair" in style_text)
add("/client/dispute-review routes through world-class portal", "'/client/dispute-review': { key: 'dispute'" in world_text and "<ClientPortalShell" not in root_text and "clientPageMap" not in root_text)
add("No Hermes Guidance legacy panel in world-class dispute JSX", "Hermes Guidance" not in world_text)
add("Chat with Clyde does not route to Resources by default", "Chat with Clyde" in world_text and "onClick={onOpenChat}" in world_text)
add("Clyde chat drawer/modal exists", "function ClydeChatDrawer" in world_text and "wc-clydeDrawer" in style_text)
add("Credit Health upload handler exists", "openCreditUpload" in world_text and "credit_report" in world_text)
add("Credit Health resource route exists", "/client/resources?category=credit-monitoring" in world_text)
add("Credit Health funding readiness route exists", "/client/funding-readiness" in world_text)
add("Credit Monitoring Connection has gated state", "Credit monitoring connection is coming soon" in world_text and "Connect securely" in world_text and "disabled" in world_text)
add("Credit Health layout uses scroll/flow repair", ".wc-pageHost{overflow:auto}" in style_text and ".wc-panel-credit{grid-template-rows:178px auto minmax(245px,1fr) auto auto}" in style_text)
add("soft icon CSS size >= 64px", css_size(".wc-softIcon,.wc-miniIcon") >= 64)
add("mini/card icon CSS size >= 64px", css_size(".wc-softIcon,.wc-miniIcon") >= 64)
add("bot icon CSS size >= 88px", css_size(".wc-bot") >= 88)
add("nav icon CSS size >= 30px", css_size(".wc-navIcon") >= 30)
add("upload icon CSS size >= 80px", css_size(".wc-uploadIcon") >= 80)
add("step icon CSS size >= 56px", css_size(".wc-stepDot") >= 56)
add("No preview radio toggles reintroduced", "pageToggle" not in world_text and "checked~" not in style_text and 'type="radio"' not in world_text)
add("Client-facing affiliate wording absent", "affiliate" not in (world_text + style_text).lower())
add("AdminGuard not weakened", admin_guard.exists() and "AdminGuard" in admin_text and "checkAdminAccess" in admin_text)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} manual UX repair checks failed")

print("RESULT: PASS - world-class manual UX repair checks passed")
