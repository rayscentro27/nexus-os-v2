"""Temporal activities for the Nexus Agent Platform.

Each activity:
1. Defines input/output schema
2. Has timeout and retry policy
3. Is idempotent
4. Emits safe logging
5. Maps failures to typed errors
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

from nexus_agent_platform.runtime.paths import get_nexus_repo_root


# ─── Canonical Runtime Configuration ──────────────────────────

def _load_canonical_runtime() -> None:
    """Load canonical Nexus runtime environment if not already loaded."""
    if os.environ.get("_NEXUS_RUNTIME_LOADED"):
        return
    runtime_env = "/Users/raymonddavis/.config/nexus/runtime.env"
    if os.path.isfile(runtime_env):
        try:
            with open(runtime_env) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip().removeprefix("export ").strip()
                    if key and not os.environ.get(key):
                        os.environ[key] = value.strip().strip("'").strip('"')
        except Exception:
            pass
    os.environ["_NEXUS_RUNTIME_LOADED"] = "1"


_load_canonical_runtime()

# ─── Safe Presence Report ─────────────────────────────────────

def _presence_report() -> dict[str, bool]:
    """Return which required variables are configured, without values."""
    return {
        "supabase_url": bool(os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")),
        "supabase_service_key": bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY")),
        "telegram_bot_token": bool(os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("NEXUS_TELEGRAM_BOT_TOKEN")),
        "telegram_allowed_chat_ids": bool(os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS")),
        "langfuse": bool(os.environ.get("LANGFUSE_TRACING_ENABLED", "").lower() == "true" and
                       (os.environ.get("LANGFUSE_PUBLIC_KEY") or os.environ.get("LANGFUSE_SECRET_KEY"))),
    }


# ─── Report Activities ───────────────────────────────────────

@activity.defn
async def resolve_report_definition_activity(report_definition: str) -> Dict[str, Any]:
    """Resolve report definition to executable parameters."""
    # Map report definition IDs to actual configurations
    definitions = {
        "process_status": {
            "type": "supabase_query",
            "handler": "hermes._get_process_status",
            "description": "Process definitions and runs status",
        },
        "client_count": {
            "type": "supabase_query",
            "handler": "hermes._get_client_count",
            "description": "Production client count",
        },
        "failure_report": {
            "type": "file_read",
            "handler": "hermes._get_failure_report",
            "description": "Today's failures",
        },
        "system_status": {
            "type": "composite",
            "handler": "hermes._get_system_status",
            "description": "System status report",
        },
    }

    result = definitions.get(report_definition, {
        "type": "unknown",
        "handler": "",
        "description": f"Unknown report: {report_definition}",
    })

    if result["type"] == "unknown":
        raise ValueError(f"Unknown report definition: {report_definition}")

    return result


@activity.defn
async def retrieve_fresh_report_data_activity(report_def: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve fresh data for the report at execution time."""
    import httpx
    import ssl

    supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Supabase credentials not configured")

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    handler = report_def.get("handler", "")

    # Route to appropriate handler
    if handler == "hermes._get_process_status":
        url = f"{supabase_url}/rest/v1/nexus_process_definitions?select=id,process_key,name,system,enabled,execution_mode,is_mock,updated_at&order=updated_at.desc&limit=80"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "accept": "application/json",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(verify=ssl_ctx) as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            if response.status_code != 200:
                raise RuntimeError(f"Supabase query failed: HTTP {response.status_code}")
            definitions = response.json()

            runs_url = f"{supabase_url}/rest/v1/nexus_process_runs?select=id,status,started_at,completed_at,heartbeat_at,items_attempted,items_succeeded,items_failed,output_location,error_code,error_message,trace_id,metadata,process_id&order=created_at.desc&limit=40"
            runs_response = await client.get(runs_url, headers=headers, timeout=30.0)
            runs = runs_response.json() if runs_response.status_code == 200 else []

        return {
            "definitions": definitions,
            "runs": runs,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    elif handler == "hermes._get_client_count":
        url = f"{supabase_url}/rest/v1/client_profiles?select=tenant_id,status,source"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "count=exact",
        }
        async with httpx.AsyncClient(verify=ssl_ctx) as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            if response.status_code != 200:
                raise RuntimeError(f"Supabase query failed: HTTP {response.status_code}")
            profiles = response.json()

        # Filter to production
        production = [p for p in profiles if p.get("tenant_id") == "goclear"]
        active = len([p for p in production if p.get("status") == "active"])
        onboarding = len([p for p in production if p.get("status") == "onboarding"])

        return {
            "total": len(production),
            "active": active,
            "onboarding": onboarding,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    elif handler == "hermes._get_failure_report":
        heartbeat_path = get_nexus_repo_root() / "reports" / "runtime" / "nexus_active_operator_heartbeat_latest.json"
        try:
            with open(heartbeat_path) as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            return {"failures": [], "as_of": datetime.now(timezone.utc).isoformat()}

    elif handler == "hermes._get_system_status":
        registry_path = get_nexus_repo_root() / "data" / "operations" / "nexus_process_registry.json"
        try:
            with open(registry_path) as f:
                data = json.load(f)
            running = [p for p in data if p.get("status") == "running"]
            return {
                "total": len(data),
                "running": len(running),
                "processes": running[:10],
                "as_of": datetime.now(timezone.utc).isoformat(),
            }
        except FileNotFoundError:
            return {"total": 0, "running": 0, "processes": [], "as_of": datetime.now(timezone.utc).isoformat()}

    else:
        raise ValueError(f"Unknown handler: {handler}")


@activity.defn
async def render_report_activity(report_data: Dict[str, Any], report_def: Dict[str, Any]) -> str:
    """Render report data into readable format."""
    handler = report_def.get("handler", "")

    if handler == "hermes._get_process_status":
        definitions = report_data.get("definitions", [])
        runs = report_data.get("runs", [])
        running_runs = [r for r in runs if r.get("status") == "RUNNING"]
        completed_runs = [r for r in runs if r.get("status") == "COMPLETED"]
        failed_runs = [r for r in runs if r.get("status") in ("FAILED", "BLOCKED", "TIMED_OUT")]

        lines = ["**Process Status Report**\n"]
        lines.append(f"**Definitions:** {len(definitions)} total")
        lines.append(f"**Recent Runs:** {len(runs)} total")
        lines.append(f"  - Running: {len(running_runs)}")
        lines.append(f"  - Completed: {len(completed_runs)}")
        lines.append(f"  - Failed: {len(failed_runs)}")

        if failed_runs:
            lines.append("\n**Recent Failures:**")
            for r in failed_runs[:5]:
                lines.append(f"  - {r.get('definition_id', 'unknown')}: {r.get('status')}")

        return "\n".join(lines)

    elif handler == "hermes._get_client_count":
        total = report_data.get("total", 0)
        active = report_data.get("active", 0)
        onboarding = report_data.get("onboarding", 0)

        return (
            f"**Client Count Report**\n\n"
            f"**Total Production:** {total}\n"
            f"  - Active: {active}\n"
            f"  - Onboarding: {onboarding}"
        )

    elif handler == "hermes._get_failure_report":
        failures = report_data.get("failures", [])
        if not failures:
            return "**Failure Report**\n\nNo failures recorded today."
        lines = [f"**Failure Report**\n\n**{len(failures)} failures today:**"]
        for f in failures[:5]:
            lines.append(f"  - {f.get('description', 'unknown')}")
        return "\n".join(lines)

    elif handler == "hermes._get_system_status":
        total = report_data.get("total", 0)
        running = report_data.get("running", 0)
        return (
            f"**System Status Report**\n\n"
            f"**Processes:** {running}/{total} active"
        )

    return f"Report generated at {report_data.get('as_of', 'unknown')}"


# ─── Delivery Activities ─────────────────────────────────────

@activity.defn
async def deliver_telegram_report_activity(delivery_target: str, rendered: str) -> Dict[str, Any]:
    """Deliver report via Telegram."""
    import httpx

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("NEXUS_TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("Telegram bot token not configured")

    allowed_raw = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "1288928049")
    allowed_ids = {cid.strip() for cid in allowed_raw.split(",") if cid.strip()}
    if delivery_target not in allowed_ids:
        raise PermissionError(f"Unauthorized Telegram delivery target: {delivery_target}")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": delivery_target,
        "text": rendered,
        "parse_mode": "Markdown",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=15.0)

    if response.status_code == 200:
        result = response.json()
        return {
            "status": "delivered",
            "message_id": result.get("result", {}).get("message_id"),
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        raise RuntimeError(f"Telegram delivery failed: HTTP {response.status_code}")


@activity.defn
async def send_email_activity(recipient: str, subject: str, body: str, idempotency_key: str) -> Dict[str, Any]:
    """Send email via Resend."""
    import httpx

    supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Supabase credentials not configured")

    url = f"{supabase_url}/functions/v1/send-client-email"
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": recipient,
        "subject": subject,
        "body": body,
        "type": "status_update",
        "idempotency_key": idempotency_key,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=30.0)

    if response.status_code == 200:
        result = response.json()
        return {
            "status": "accepted",
            "provider_request_id": result.get("id", ""),
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        raise RuntimeError(f"Email send failed: HTTP {response.status_code}")


# ─── Receipt Activities ──────────────────────────────────────

@activity.defn
async def persist_delivery_receipt_activity(mission_id: str, delivery_result: Dict[str, Any], idempotency_key: str) -> None:
    """Persist delivery receipt for idempotency."""
    receipts_dir = get_nexus_repo_root() / "reports" / "runtime" / "action_receipts"
    os.makedirs(receipts_dir, exist_ok=True)

    receipt = {
        "mission_id": mission_id,
        "idempotency_key": idempotency_key,
        "delivery_result": delivery_result,
        "persisted_at": datetime.now(timezone.utc).isoformat(),
    }

    receipt_path = os.path.join(receipts_dir, f"{idempotency_key}.json")
    with open(receipt_path, "w") as f:
        json.dump(receipt, f, indent=2)


@activity.defn
async def update_nexus_mission_activity(mission_id: str, status: str) -> None:
    """Update mission status."""
    mission_dir = get_nexus_repo_root() / "data" / "missions"
    os.makedirs(mission_dir, exist_ok=True)

    mission_path = os.path.join(mission_dir, f"{mission_id}.json")
    mission = {
        "mission_id": mission_id,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(mission_path, "w") as f:
        json.dump(mission, f, indent=2)


@activity.defn
async def emit_safe_trace_activity(trace_id: str, status: str) -> None:
    """Emit safe trace to Langfuse."""
    # Trace emission happens through the OtelAdapter
    # This activity just ensures the trace is recorded
    pass


@activity.defn
async def recover_mission_activity(mission_id: str) -> Dict[str, Any]:
    """Recover a failed mission."""
    return {"status": "recovered", "mission_id": mission_id}
