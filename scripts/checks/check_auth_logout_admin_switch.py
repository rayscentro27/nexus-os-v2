from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

cleanup = ROOT / "src/lib/authSessionCleanup.ts"
admin_guard = ROOT / "src/components/auth/AdminGuard.tsx"
auth = ROOT / "src/components/auth.tsx"
app = ROOT / "src/app/App.tsx"
world = ROOT / "src/pages/client/WorldClassClientPortal.jsx"
client_shell = ROOT / "src/components/client/ClientPortalShell.jsx"
client_login = ROOT / "src/pages/client/ClientLoginPage.tsx"
admin_shell = ROOT / "src/components/NexusAppShell.jsx"
reset_page = ROOT / "src/pages/AuthResetPage.tsx"

files = {
    "cleanup": cleanup.read_text(errors="ignore") if cleanup.exists() else "",
    "admin_guard": admin_guard.read_text(errors="ignore") if admin_guard.exists() else "",
    "auth": auth.read_text(errors="ignore") if auth.exists() else "",
    "app": app.read_text(errors="ignore") if app.exists() else "",
    "world": world.read_text(errors="ignore") if world.exists() else "",
    "client_shell": client_shell.read_text(errors="ignore") if client_shell.exists() else "",
    "client_login": client_login.read_text(errors="ignore") if client_login.exists() else "",
    "admin_shell": admin_shell.read_text(errors="ignore") if admin_shell.exists() else "",
    "reset": reset_page.read_text(errors="ignore") if reset_page.exists() else "",
}
combined = "\n".join(files.values()).lower()
frontend = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "src").rglob("*") if p.suffix in {".ts", ".tsx", ".jsx", ".js"}).lower()

checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


logout_surfaces = files["world"] + files["client_shell"] + files["admin_shell"] + files["auth"] + files["client_login"]

add("authSessionCleanup.ts exists", cleanup.exists() and "clearNexusAuthSession" in files["cleanup"])
add("cleanup calls Supabase global sign out with fallback", "scope: 'global'" in files["cleanup"] and "supabase.auth.signOut()" in files["cleanup"])
add("cleanup covers localStorage/sessionStorage", "localStorage" in files["cleanup"] and "sessionStorage" in files["cleanup"])
add("cleanup covers Supabase/Nexus keys", all(term in files["cleanup"] for term in ["supabase", "sb-", "nexus", "client_profile", "tenant_membership", "admin_user", "goclear"]))
add("logout buttons use cleanup helper", "forceAuthResetAndRedirect('/client/login')" in logout_surfaces and "forceAuthResetAndRedirect('/admin/login')" in logout_surfaces)
add("admin blocked page shows signed-in email safely", "You are signed in as" in files["admin_guard"] and "data.user?.email" in files["admin_guard"])
add("admin blocked page has switch account action", "Sign out and switch account" in files["admin_guard"] and "forceAuthResetAndRedirect('/admin/login')" in files["admin_guard"])
add("admin blocked page has client dashboard route", "/client/dashboard" in files["admin_guard"])
add("admin login route exists", "path === '/admin/login'" in files["app"] and "AdminLoginPage" in files["auth"])
add("auth reset route exists", "path === '/auth/reset'" in files["app"] and "Session cleared" in files["reset"])
add("client login has reset stuck session", "Reset stuck session" in files["client_login"])
service_role_risky = bool(re.search(
    r"(import\.meta\.env\.(VITE_)?SUPABASE_SERVICE_ROLE_KEY|process\.env\.(VITE_)?SUPABASE_SERVICE_ROLE_KEY|createClient\([^)]*service_role|serviceRoleKey\s*=|service_role_key\s*=)",
    frontend,
    re.I,
))
add("no service role in frontend", not service_role_risky)
add("no admin bypass added", "ui-smoke" in files["app"] and "theworldzmine@gmail.com" not in frontend and "allowed: true" not in files["admin_guard"])
add("no tokens/secrets logged", all(term not in combined for term in ["access_token", "refresh_token", "console.log(data.session", "console.log(session", "token:"]))
add("SIGNED_OUT resets auth state", "SIGNED_OUT" in files["auth"] and "setUser(null)" in files["auth"])

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} auth logout/admin switch checks failed")

print("RESULT: PASS - auth logout and admin account switching checks passed")
