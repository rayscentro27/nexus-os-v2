"""Redacted reconciliation of remote Netlify integrations and inbound paths."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from nexus_agent_platform.credential_control_plane import _netlify_env_names
from nexus_product_evolution.netlify_adapter import _netlify_executable, _netlify_status_probe

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/certification"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_report() -> dict:
    names = _netlify_env_names()
    status = _netlify_status_probe()
    voice_names = {"CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN"}
    meta_names = sorted(name for name in names if name.startswith(("META_", "FACEBOOK_", "INSTAGRAM_", "IG_")))
    return {
        "schema_version": "nexus.remote-integrations-reconciliation.v1",
        "generated_at": _now(),
        "netlify": {"cli": bool(_netlify_executable()), "authenticated_site_status": status.get("status"),
                    "site_id_present": bool(status.get("site_id")), "site_url": status.get("target", "UNKNOWN")},
        "remote_environment_presence": {
            name: {"present": name in names, "source": "NETLIFY_ENV", "value_included": False}
            for name in ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN", "GROQ_API_KEY", "OPENROUTER_API_KEY")
        },
        "meta_server_variable_names": [{"name": name, "present": True, "value_included": False} for name in meta_names],
        "credentials": {
            "credential.cloudflare.voice_service.prod.v1": "AVAILABLE_REMOTE_NETLIFY" if voice_names <= names else "UNVERIFIED",
            "credential.groq.models.prod.v1": "AVAILABLE_REMOTE_NETLIFY" if "GROQ_API_KEY" in names else "MISSING_OR_UNVERIFIED",
            "credential.openrouter.models.prod.v1": "AVAILABLE_REMOTE_NETLIFY" if "OPENROUTER_API_KEY" in names else "MISSING_OR_UNVERIFIED",
        },
        "voice": {"netlify_configuration": "PASS" if voice_names <= names else "PARTIAL",
                  "relay_present": (ROOT / "netlify/functions/voice-relay.mjs").exists(),
                  "access_headers_implemented": True, "remote_health": "NOT_RUN_AUTHENTICATED_USER_REQUIRED"},
        "meta": {"graph_auth": "EXISTING_CERTIFIED", "callback_url": "/.netlify/functions/meta-webhook",
                 "historical_handler_found": False, "current_handler_found": (ROOT / "netlify/functions/meta-webhook.mjs").exists(),
                 "signature_validation": "IMPLEMENTED_LOCAL_FIXTURE_ONLY", "persistence": "NOT_CONFIGURED",
                 "verify_token_present": "NO_METADATA_EVIDENCE", "app_secret_present": "NO_METADATA_EVIDENCE",
                 "deployment": "NOT_PERFORMED"},
        "communication_matrix": [
            {"capability": "Facebook Page API", "credential_source": "existing certified provider/local control plane", "provider_auth": "READY", "inbound": "NOT_READY", "read": "READY", "outbound": "GATED", "authority": "GATED_OUTBOUND"},
            {"capability": "Instagram Business", "credential_source": "existing Meta provider", "provider_auth": "ASSOCIATED", "inbound": "NOT_READY", "read": "READY", "outbound": "GATED", "authority": "GATED_OUTBOUND"},
            {"capability": "Meta Webhooks", "credential_source": "server secret names not proven", "provider_auth": "AUTH_REQUIRED", "inbound": "NOT_READY", "read": "NOT_REQUIRED", "outbound": "NONE", "authority": "INGEST_ONLY"},
            {"capability": "Telegram", "credential_source": "existing certified credential", "provider_auth": "READY", "inbound": "READY", "read": "READY", "outbound": "GATED", "authority": "GOVERNED"},
            {"capability": "YouTube", "credential_source": "existing certified credential", "provider_auth": "READY", "inbound": "N/A", "read": "READY", "outbound": "GATED", "authority": "READ_ONLY"},
            {"capability": "Resend", "credential_source": "local configured", "provider_auth": "PARTIAL", "inbound": "N/A", "read": "PARTIAL", "outbound": "GATED", "authority": "GATED_OUTBOUND"},
            {"capability": "Cloudflare Voice", "credential_source": "REMOTE_NETLIFY", "provider_auth": "CONFIGURED_UNTESTED", "inbound": "N/A", "read": "PARTIAL", "outbound": "GATED", "authority": "REMOTE_TRANSPORT"},
        ],
        "external_mutations": 0,
        "user_action_required": ["Configure META_WEBHOOK_VERIFY_TOKEN and META_APP_SECRET server-side before deploying the inbound callback."],
        "secrets_exposed": False,
    }


def write_reports() -> dict:
    report = build_report()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "nexus_remote_integrations_reconciliation_latest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Nexus Remote Integrations Reconciliation", "", "Redacted; no credential values are persisted.", "",
             f"- Netlify CLI/site: `{report['netlify']['authenticated_site_status']}`",
             f"- Meta callback implementation: `{report['meta']['current_handler_found']}`",
             f"- Meta persistence: `{report['meta']['persistence']}`",
             f"- Voice remote configuration: `{report['voice']['netlify_configuration']}`",
             f"- External mutations: `{report['external_mutations']}`", "", "## Remote Variables", "",
             "| Variable | Present | Source | |", "|---|---|---|---|"]
    for key, value in report["remote_environment_presence"].items():
        lines.append(f"| `{key}` | {value['present']} | `{value['source']}` | |")
    lines += ["", "## Remaining Gates", "", "- Meta webhook server secrets are not proven by current metadata; callback deployment and persistence remain gated.", "- Voice remote health is untested because the relay requires an authenticated Nexus user request.", "- Outbound social/email actions remain gated."]
    (OUT / "nexus_remote_integrations_reconciliation_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(write_reports(), indent=2, sort_keys=True))
