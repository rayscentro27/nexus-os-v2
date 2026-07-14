#!/usr/bin/env python3
"""Print a secret-free parser worker/frontend environment alignment diagnostic."""
from pathlib import Path
from urllib.parse import urlparse
import os, platform, ssl, sys
try:
    import certifi
except ImportError:
    certifi = None

EXPECTED_REF = "iqjwgpnujbeoyaeuwehj"
def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for name in (".env.local", ".env"):
        path = Path(name)
        if path.exists():
            for line in path.read_text(errors="ignore").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1); values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({key: value for key, value in os.environ.items() if value})
    return values
def ref(value: str) -> str:
    host = urlparse(value).hostname or ""
    return host.split(".")[0] if host.endswith(".supabase.co") else ""
def main() -> int:
    env = load_env(); server_ref = ref(env.get("SUPABASE_URL", "")); frontend_ref = ref(env.get("VITE_SUPABASE_URL", ""))
    print(f"Python: {platform.python_version()}"); print(f"OpenSSL: {ssl.OPENSSL_VERSION}")
    print(f"certifi: present={bool(certifi)} path={certifi.where() if certifi else 'unavailable'}")
    print(f"server project ref: {server_ref or 'missing'}"); print(f"frontend project ref: {frontend_ref or 'missing'}")
    print(f"service role present server-side: {bool(env.get('SUPABASE_SERVICE_ROLE_KEY'))}"); print(f"frontend anon key present: {bool(env.get('VITE_SUPABASE_ANON_KEY'))}")
    aligned = server_ref == frontend_ref == EXPECTED_REF
    print(f"environment aligned: {aligned}")
    return 0 if aligned and env.get("SUPABASE_SERVICE_ROLE_KEY") and certifi else 1
if __name__ == "__main__": raise SystemExit(main())
