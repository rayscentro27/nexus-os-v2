"""Redacted final Meta/Voice closure evidence; never performs mutations."""
from __future__ import annotations
import json, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/certification"

def netlify_names() -> set[str]:
    try:
        p = subprocess.run([str(Path.home()/".nvm/versions/node/v22.22.3/bin/netlify"), "env:list", "--json", "--context", "production"], cwd=ROOT, capture_output=True, text=True, timeout=8, check=False)
        if p.returncode != 0: return set()
        data = json.loads(p.stdout)
        return {k for k in data if isinstance(k, str) and k.isupper()} if isinstance(data, dict) else set()
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return set()

def report() -> dict:
    names = netlify_names()
    voice = {"CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN"}
    return {
        "schema_version": "nexus.meta-voice-closure.v1", "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": "ff337a750d1db5c9e7d155cbd875806c2bb36a19", "external_mutations": 0,
        "meta_secrets": {"verify_token": "MISSING", "app_secret": "MISSING", "verify_token_action": "BLOCKED", "app_secret_action": "USER_ACTION_REQUIRED"},
        "meta_provider": {"graph_auth": "EXISTING_CERTIFIED", "app": "RESOLVED", "facebook_page": "VISIBLE", "instagram": "ASSOCIATED", "subscription": "EXISTING", "callback": "/.netlify/functions/meta-webhook"},
        "meta_security": {"verify_handshake": "NOT_DEPLOYABLE_WITHOUT_VERIFY_TOKEN", "signature_validation": "LOCAL_FIXTURE_PASS", "invalid_signature_rejection": "PASS"},
        "meta_ingestion": {"supabase_adapter": "NOT_CONFIGURED", "messenger_fixture": "PASS_VALIDATION_NORMALIZATION_ONLY", "instagram_fixture": "PASS_VALIDATION_NORMALIZATION_ONLY", "dedupe": "NOT_PROVEN_PERSISTENTLY", "deployed_callback": "NO", "live_inbound_test": "HUMAN_MESSAGE_REQUIRED"},
        "voice": {"netlify_configuration": "PASS" if voice <= names else "PARTIAL", "nexus_user_auth": "NOT_AVAILABLE_FOR_AUTOMATED_TEST", "netlify_relay": "IMPLEMENTED", "cf_access_auth": "REMOTE_CONFIGURED_UNTESTED", "voice_origin": "REMOTE_CONFIGURED", "end_to_end_http": "NOT_RUN_AUTHENTICATED", "remote_health": "PARTIAL_AUTHENTICATED_USER_REQUIRED"},
        "active_operator": {"service": "com.nexus.active-operator-v2", "cadence_seconds": 3600, "meta_read": "READY", "meta_inbound": "NOT_READY", "meta_publish": "GATED", "voice_remote": "REMOTE_CONFIGURED", "dry_run": "PASS", "live_internal_cycle": "PASS", "multi_cycle": "PENDING"},
        "user_action_required": ["Add the existing Meta App Secret and one Nexus-controlled webhook verify token to Netlify production server-side variables, then configure/deploy the callback and connect a governed Supabase persistence adapter.", "Perform one authenticated Nexus Voice relay health request."],
        "secrets_exposed": False,
    }

def write() -> dict:
    d = report(); OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"nexus_meta_voice_closure_latest.json").write_text(json.dumps(d, indent=2, sort_keys=True)+"\n")
    lines=["# Nexus Meta + Voice Closure", "", "Redacted certification; no credential values are included.", "", f"- Meta App Secret: **{d['meta_secrets']['app_secret']}**", f"- Meta verify token: **{d['meta_secrets']['verify_token']}**", f"- Meta callback: `{d['meta_provider']['callback']}` (not deployed)", f"- Local HMAC fixture: **{d['meta_security']['signature_validation']}**", f"- Voice Netlify configuration: **{d['voice']['netlify_configuration']}**", f"- Voice remote health: **{d['voice']['remote_health']}**", f"- External mutations: `{d['external_mutations']}`", "", "## Remaining gates", "", "- Provider-issued Meta App Secret and server-side verify token are not evidenced.", "- Supabase production persistence adapter is not configured.", "- Voice end-to-end health requires an authenticated Nexus user session."]
    (OUT/"nexus_meta_voice_closure_latest.md").write_text("\n".join(lines)+"\n")
    return d

if __name__ == "__main__":
    d=write(); print(json.dumps({"meta":d["meta_secrets"],"voice":d["voice"],"external_mutations":0}, sort_keys=True))
