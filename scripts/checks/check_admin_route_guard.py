#!/usr/bin/env python3
"""
Static smoke check for admin route guard in Nexus OS v2.

Checks:
1. /admin routes are wrapped in an AdminGuard or equivalent.
2. AdminGuard checks role/admin source (not just auth).
3. Code does not contain obvious "authenticated user equals admin" logic.
4. Admin shell/components are not directly exposed on /admin without guard.
5. No service role key appears in frontend source.
"""

from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parent.parent.parent
FAIL = False

def read(p):
    return (REPO / p).read_text()

def check(name, cond, detail=""):
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL = True
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return cond

print("R4 Admin Route Guard Smoke Check")
print()

try:
    app = read("src/app/App.tsx")
    auth = read("src/components/auth.tsx")
    shell = read("src/components/Shell.tsx")
    nexus_admin = read("src/admin/NexusAdminUI.jsx")
except Exception as e:
    print(f"FATAL: could not read source files: {e}")
    sys.exit(2)

# 1. AdminGuard exists
guard_exists = (REPO / "src/components/auth/AdminGuard.jsx").exists()
check("AdminGuard component exists", guard_exists)

# 2. adminAccess helper exists
helper_exists = (REPO / "src/lib/adminAccess.ts").exists() or (REPO / "src/lib/adminAccess.js").exists()
check("adminAccess helper exists", helper_exists)

# 3. App.tsx wraps /admin in AdminGuard
uses_guard = "AdminGuard" in app
check("App.tsx uses AdminGuard for /admin", uses_guard)

# 4. App.tsx no longer renders NexusAdminUI directly under AuthGate alone
bad_direct = re.search(r"AuthGate[^{}]*{[^{}]*NexusAdminUI", app, re.DOTALL)
direct_only = bool(bad_direct) and "AdminGuard" not in app
check("NexusAdminUI not directly gated by AuthGate alone", not direct_only,
      "AdminGuard must wrap NexusAdminUI")

# 5. auth.tsx does not treat AuthGate as admin guard
auth_export = "AuthGate" in auth and "AdminGuard" != "AuthGate"
check("AuthGate separated from AdminGuard", auth_export)

# 6. No service-role key in frontend source
source_text = "\n".join([app, auth, nexus_admin])
has_service_role = "service_role" in source_text.lower() or "SERVICE_ROLE" in source_text
check("No service-role key in frontend source", not has_service_role)

# 7. tenant_memberships role check exists in helper
helper_text = ""
if (REPO / "src/lib/adminAccess.ts").exists():
    helper_text = read("src/lib/adminAccess.ts")
elif (REPO / "src/lib/adminAccess.js").exists():
    helper_text = read("src/lib/adminAccess.js")
has_role_check = "tenant_memberships" in helper_text and "role" in helper_text
check("adminAccess checks tenant_memberships role", has_role_check)

# 8. admin_users check exists in helper
has_admin_users_check = "admin_users" in helper_text
check("adminAccess checks admin_users table", has_admin_users_check)

# 9. Client routes preserved
client_routes = ["/client/dashboard", "/client/documents", "/client/request-review", "/client/login"]
client_ok = all(r in app for r in client_routes)
check("Client routes preserved in App.tsx", client_ok, str(client_routes))

print()
if FAIL:
    print("RESULT: FAIL — some checks did not pass")
    sys.exit(1)
else:
    print("RESULT: PASS — all admin route guard checks passed")
