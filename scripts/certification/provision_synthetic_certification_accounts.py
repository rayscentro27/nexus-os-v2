#!/usr/bin/env python3
"""Provision dedicated Nexus certification accounts without printing secrets.

This script is intentionally local/server-side only. It reads Supabase secrets
from ignored environment files, creates missing synthetic Auth users, repairs
their authorization/profile rows, and stores generated passwords only in the
ignored `.env.e2e.local` file.
"""
from __future__ import annotations

import json
import os
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    import certifi  # type: ignore
except Exception:  # pragma: no cover - local environment fallback
    certifi = None


ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ROOT = Path(os.environ.get("NEXUS_ORIGINAL_REPO", "/Users/raymonddavis/nexus-os-v2"))
E2E_ENV = ROOT / ".env.e2e.local"
REPORT = ROOT / "NEXUS_SYNTHETIC_ACCOUNT_CERTIFICATION.md"
RUN_KEY = "20260803T204635Z"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where() if certifi else None)

ACCOUNTS = [
    {
        "key": "CERT_ADMIN",
        "label": "nexus-cert-admin",
        "email": f"nexus-cert-admin-{RUN_KEY}@goclear.test",
        "role": "admin",
        "tenant_id": "nexus-cert-admin",
        "client_id": None,
    },
    {
        "key": "PERSONA_A",
        "label": "Persona A",
        "email": f"persona-a-cert-{RUN_KEY}@goclear.test",
        "role": "client",
        "tenant_id": "tenant-cert-persona-a",
        "client_id": "client-cert-persona-a",
    },
    {
        "key": "PERSONA_B",
        "label": "Persona B",
        "email": f"persona-b-cert-{RUN_KEY}@goclear.test",
        "role": "client",
        "tenant_id": "tenant-cert-persona-b",
        "client_id": "client-cert-persona-b",
    },
    {
        "key": "PERSONA_C",
        "label": "Persona C",
        "email": f"persona-c-cert-{RUN_KEY}@goclear.test",
        "role": "client",
        "tenant_id": "tenant-cert-persona-c",
        "client_id": "client-cert-persona-c",
    },
    {
        "key": "PERSONA_D",
        "label": "Persona D",
        "email": f"persona-d-cert-{RUN_KEY}@goclear.test",
        "role": "client",
        "tenant_id": "tenant-cert-persona-d",
        "client_id": "client-cert-persona-d",
    },
]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def merged_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for root in (ORIGINAL_ROOT, ROOT):
        for name in (".env", ".env.local", ".env.e2e.local"):
            values.update(read_env(root / name))
    values.update({k: v for k, v in os.environ.items() if v})
    return values


def request(base: str, key: str, path: str, method: str = "GET", body: Any | None = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    url = base.rstrip("/") + path
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates",
        },
    )
    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=60) as resp:
        payload = resp.read()
        if not payload:
            return []
        return json.loads(payload.decode("utf-8"))


def find_user(base: str, key: str, email: str) -> dict[str, Any] | None:
    needle = email.lower()
    for page in range(1, 11):
        users = request(base, key, f"/auth/v1/admin/users?page={page}&per_page=200")
        rows = users.get("users", []) if isinstance(users, dict) else []
        for user in rows:
            if str(user.get("email", "")).lower() == needle:
                return user
        if len(rows) < 200:
            break
    return None


def upsert(base: str, key: str, table: str, row: dict[str, Any], conflict: str) -> None:
    query = urllib.parse.urlencode({"on_conflict": conflict})
    request(base, key, f"/rest/v1/{table}?{query}", "POST", row)


def patch_row(base: str, key: str, table: str, filters: str, row: dict[str, Any]) -> None:
    request(base, key, f"/rest/v1/{table}?{filters}", "PATCH", row)


def table_rows(base: str, key: str, table: str, select: str, filters: str) -> list[dict[str, Any]]:
    return request(base, key, f"/rest/v1/{table}?select={urllib.parse.quote(select)}&{filters}")


def ensure_env_values(env_file_values: dict[str, str]) -> tuple[dict[str, str], dict[str, bool]]:
    changed: dict[str, bool] = {}
    values = dict(env_file_values)
    values["E2E_ENABLE_AUTHENTICATED"] = "true"
    values["E2E_CERTIFICATION_RUN_KEY"] = RUN_KEY
    for account in ACCOUNTS:
        email_key = f"E2E_{account['key']}_EMAIL"
        password_key = f"E2E_{account['key']}_PASSWORD"
        if not values.get(email_key):
            values[email_key] = account["email"]
            changed[email_key] = True
        if not values.get(password_key):
            values[password_key] = secrets.token_urlsafe(30) + "A1!"
            changed[password_key] = True
    values["E2E_ADMIN_EMAIL"] = values["E2E_CERT_ADMIN_EMAIL"]
    values["E2E_ADMIN_PASSWORD"] = values["E2E_CERT_ADMIN_PASSWORD"]
    values["E2E_CLIENT_EMAIL"] = values["E2E_PERSONA_A_EMAIL"]
    values["E2E_CLIENT_PASSWORD"] = values["E2E_PERSONA_A_PASSWORD"]
    return values, changed


def write_e2e_env(values: dict[str, str]) -> None:
    safe_prefixes = ("E2E_",)
    existing = read_env(E2E_ENV)
    merged = {**existing, **{k: v for k, v in values.items() if k.startswith(safe_prefixes)}}
    ordered = sorted(merged)
    E2E_ENV.write_text("\n".join(f"{key}={merged[key]}" for key in ordered) + "\n")
    os.chmod(E2E_ENV, 0o600)


def create_auth_user(base: str, key: str, account: dict[str, Any], email: str, password: str) -> str:
    existing = find_user(base, key, email)
    if existing:
        # Credential drift is repaired through the server-only admin contract;
        # never expose or log the generated password.
        request(
            base,
            key,
            f"/auth/v1/admin/users/{existing['id']}",
            "PUT",
            {"password": password, "email_confirm": True, "user_metadata": {
                "synthetic": True, "certification_run": RUN_KEY,
                "label": account["label"], "role": account["role"],
            }},
        )
        return str(existing["id"])
    created = request(
        base,
        key,
        "/auth/v1/admin/users",
        "POST",
        {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "synthetic": True,
                "certification_run": RUN_KEY,
                "label": account["label"],
                "role": account["role"],
            },
            "app_metadata": {
                "synthetic": True,
                "certification_run": RUN_KEY,
                "role": account["role"],
            },
        },
    )
    created_id = created.get("id") or created.get("user", {}).get("id")
    if not created_id:
        raise RuntimeError("auth_user_creation_returned_no_id")
    return str(created_id)


def repair_admin(base: str, key: str, user_id: str, email: str) -> list[str]:
    actions: list[str] = []
    upsert(base, key, "admin_users", {"id": user_id, "email": email, "role": "admin", "active": True}, "id")
    actions.append("admin_users_active")
    upsert(
        base,
        key,
        "tenant_memberships",
        {
            "tenant_id": "nexus-cert-admin",
            "user_id": user_id,
            "role": "admin",
            "client_id": None,
        },
        "tenant_id,user_id",
    )
    actions.append("admin_membership_verified")
    return actions


def repair_client(base: str, key: str, account: dict[str, Any], user_id: str, email: str) -> list[str]:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tenant_id = str(account["tenant_id"])
    client_id = str(account["client_id"])
    label = str(account["label"])
    actions: list[str] = []
    upsert(
        base,
        key,
        "tenant_memberships",
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "role": "client",
            "client_id": client_id,
        },
        "tenant_id,user_id",
    )
    actions.append("tenant_membership_verified")
    upsert(
        base,
        key,
        "client_profiles",
        {
            "id": user_id,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "client_label": f"{label} Synthetic Certification",
            "title": f"{label} Synthetic Certification",
            "status": "active",
            "client_visible": True,
            "approval_required": False,
            "source": "synthetic_certification",
            "recommended_next_action": "Use this synthetic profile for controlled authentication and tenant-isolation certification.",
            "payload": {
                "synthetic": True,
                "certificationRun": RUN_KEY,
                "email": email,
                "persona": label,
            },
            "updated_at": now,
        },
        "id",
    )
    actions.append("client_profile_verified")
    for idx, category in enumerate(("credit_profile", "business_profile", "funding_readiness"), start=1):
        upsert(
            base,
            key,
            "readiness_scores",
            {
                "id": f"cert-{client_id}-{category}",
                "tenant_id": tenant_id,
                "client_id": client_id,
                "category": category,
                "title": category.replace("_", " ").title(),
                "summary": "Synthetic certification baseline. No real client data.",
                "status": "needs_more_information",
                "score": 0,
                "priority": str(idx),
                "risk_level": "unknown",
                "automation_level": "deterministic",
                "client_visible": True,
                "approval_required": False,
                "source": "synthetic_certification",
                "recommended_next_action": "Continue certification workflow.",
                "payload": {"synthetic": True, "certificationRun": RUN_KEY},
                "updated_at": now,
            },
            "id",
        )
    actions.append("readiness_rows_verified")
    upsert(
        base,
        key,
        "client_tasks",
        {
            "id": f"cert-{client_id}-task-upload",
            "tenant_id": tenant_id,
            "client_id": client_id,
            "category": "document_intake",
            "title": "Upload a synthetic certification document",
            "summary": "Synthetic task for upload-first certification only.",
            "status": "open",
            "priority": "1",
            "risk_level": "low",
            "automation_level": "deterministic",
            "client_visible": True,
            "approval_required": False,
            "source": "synthetic_certification",
            "recommended_next_action": "Upload a non-PII synthetic document.",
            "payload": {"synthetic": True, "certificationRun": RUN_KEY},
            "updated_at": now,
        },
        "id",
    )
    actions.append("task_row_verified")
    return actions


def verify_login(base: str, anon_key: str, email: str, password: str) -> tuple[bool, str]:
    try:
        data = request(
            base,
            anon_key,
            "/auth/v1/token?grant_type=password",
            "POST",
            {"email": email, "password": password},
        )
        user_id = data.get("user", {}).get("id")
        token_ok = bool(data.get("access_token")) and bool(data.get("refresh_token"))
        if not user_id or not token_ok:
            return False, "NO_SESSION"
        return True, user_id
    except urllib.error.HTTPError as err:
        return False, f"HTTP_{err.code}"


def main() -> int:
    env = merged_env()
    base = env.get("SUPABASE_URL") or env.get("VITE_SUPABASE_URL")
    service_key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = env.get("VITE_SUPABASE_ANON_KEY")
    if not base or not service_key or not anon_key:
        print("FAIL: Supabase URL, anon key, or service-role key is missing")
        return 1

    e2e_values, changed = ensure_env_values(read_env(E2E_ENV))
    write_e2e_env(e2e_values)

    rows: list[dict[str, Any]] = []
    failures = 0
    for account in ACCOUNTS:
        email = e2e_values[f"E2E_{account['key']}_EMAIL"]
        password = e2e_values[f"E2E_{account['key']}_PASSWORD"]
        try:
            user_id = create_auth_user(base, service_key, account, email, password)
            actions = repair_admin(base, service_key, user_id, email) if account["role"] == "admin" else repair_client(base, service_key, account, user_id, email)
            login_ok, login_detail = verify_login(base, anon_key, email, password)
            if not login_ok:
                failures += 1
            rows.append(
                {
                    "account": account["label"],
                    "email_masked": mask_email(email),
                    "role": account["role"],
                    "auth_user_id_suffix": user_id[-8:],
                    "tenant_id": account["tenant_id"],
                    "client_id": account["client_id"] or "",
                    "credential_configured": "yes",
                    "login": "PASS" if login_ok else f"FAIL_{login_detail}",
                    "actions": ", ".join(actions),
                    "password_generated_this_run": "yes" if changed.get(f"E2E_{account['key']}_PASSWORD") else "no",
                }
            )
        except urllib.error.HTTPError as err:
            failures += 1
            rows.append(
                {
                    "account": account["label"],
                    "email_masked": mask_email(email),
                    "role": account["role"],
                    "auth_user_id_suffix": "",
                    "tenant_id": account["tenant_id"],
                    "client_id": account["client_id"] or "",
                    "credential_configured": "yes",
                    "login": f"BLOCKED_HTTP_{err.code}",
                    "actions": "failed before completion",
                    "password_generated_this_run": "yes" if changed.get(f"E2E_{account['key']}_PASSWORD") else "no",
                }
            )

    write_report(rows, failures)
    for row in rows:
        print(f"{row['account']}: auth suffix {row['auth_user_id_suffix'] or 'unknown'} role {row['role']} tenant {row['tenant_id']} login {row['login']}")
    print(f"Report: {REPORT.name}")
    return 1 if failures else 0


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked = local[:1] + "***"
    else:
        masked = local[:2] + "***" + local[-1:]
    return f"{masked}@{domain}"


def write_report(rows: list[dict[str, Any]], failures: int) -> None:
    lines = [
        "# Nexus Synthetic Account Certification",
        "",
        f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"Certification run: {RUN_KEY}",
        f"Result: {'PASS' if failures == 0 else 'FAIL'}",
        "",
        "No passwords, tokens, keys, or full secret values are included in this report.",
        "",
        "| Account | Email | Role | Auth user suffix | Tenant | Client | Credential configured | Login | Actions |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {account} | {email_masked} | {role} | {auth_user_id_suffix} | {tenant_id} | {client_id} | {credential_configured} | {login} | {actions} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("Credentials are stored only in ignored local `.env.e2e.local`.")
    REPORT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
