#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def read(rel):
    p = ROOT / rel
    return p.read_text(errors="ignore") if p.exists() else ""

def exists(rel):
    return (ROOT / rel).exists()

app = read("src/app/App.tsx")
admin_access = read("src/lib/adminAccess.ts") or read("src/lib/adminAccess.js")

frontend_chunks = []
for p in (ROOT / "src").rglob("*"):
    if p.suffix in [".ts", ".tsx", ".js", ".jsx"]:
        try:
            frontend_chunks.append(f"\n/* {p.relative_to(ROOT)} */\n" + p.read_text(errors="ignore"))
        except Exception:
            pass

frontend_source = "\n".join(frontend_chunks)

guarded_admin_render = bool(re.search(
    r"<AdminGuard>[\s\S]{0,1500}<AuthGate>[\s\S]{0,1500}<NexusAdminUI\s+email=\{user\.email\}\s*/>",
    app,
    re.MULTILINE,
))

# Ignore safety-policy text/comments. Fail only on actual frontend service-role env/key usage.
service_role_risky = bool(re.search(
    r"(import\.meta\.env\.(VITE_)?SUPABASE_SERVICE_ROLE_KEY|process\.env\.(VITE_)?SUPABASE_SERVICE_ROLE_KEY|createClient\([^)]*service_role|serviceRoleKey\s*=|service_role_key\s*=)",
    frontend_source,
    re.IGNORECASE,
))

checks = [
    ("AdminGuard component exists", exists("src/components/auth/AdminGuard.tsx") or exists("src/components/auth/AdminGuard.jsx")),
    ("adminAccess helper exists", bool(admin_access.strip())),
    ("App.tsx identifies admin routes", "path === '/admin'" in app and "path.startsWith('/admin/')" in app),
    ("App.tsx uses AdminGuard for admin routes", "<AdminGuard>" in app and "NexusAdminUI" in app),
    ("AdminGuard wraps NexusAdminUI before render", guarded_admin_render),
    ("AuthGate exists but admin route is additionally guarded", "AuthGate" in app and "AdminGuard" in app),
    ("No actual service-role key usage in frontend source", not service_role_risky),
    ("adminAccess checks tenant_memberships role", "tenant_memberships" in admin_access and "role" in admin_access),
    ("adminAccess checks admin_users table", "admin_users" in admin_access),
    ("Unsupported owner role is not allowed", "'owner'" not in admin_access and '"owner"' not in admin_access),
]

client_routes_preserved = (
    "/client/login" in app
    and "/client/preview" in app
    and "path === '/client'" in app
    and "path.startsWith('/client/')" in app
    and "ClientPortalGate" in app
)

checks.append(("Client routes preserved in App.tsx", client_routes_preserved))

print("R4 Admin Route Guard Smoke Check\n")

failed = False
for label, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    failed = failed or not ok

print()
if failed:
    print("RESULT: FAIL — some checks did not pass")
    sys.exit(1)

print("RESULT: PASS — admin route guard checks passed")
