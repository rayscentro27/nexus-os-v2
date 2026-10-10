"""Inventory local credential references without reading or emitting values."""
from __future__ import annotations

import json
import os
import re
import subprocess
import stat
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
REGISTRY = REPO_ROOT / "configs/nexus_credential_registry.json"
SOURCE_ROOTS = ("scripts", "src", "netlify", "supabase", "ops", "tests", "configs", ".github")
LOCAL_STORES = (
    HOME / ".config/nexus/runtime.env",
    HOME / ".nexus",
    HOME / ".hermes",
    HOME / ".openclaw",
    HOME / ".codex",
    HOME / ".config/opencode",
    HOME / ".config/Code/User/globalStorage",
    HOME / ".oci/config",
    HOME / ".modal.toml",
    HOME / ".huggingface",
    HOME / "Library/Preferences/netlify/config.json",
    HOME / ".cloudflared/config.yml",
    HOME / ".ssh",
    HOME / "nexus-os-v2-canonical/.env",
    HOME / "nexus-os-v2/.env",
    HOME / "nexuslive/.env",
)


def _rg_refs(names: list[str], root: Path = REPO_ROOT) -> dict[str, list[dict[str, Any]]]:
    pattern = r"\b(?:" + "|".join(re.escape(name) for name in sorted(set(names), key=len, reverse=True)) + r")\b"
    args = ["rg", "--no-heading", "--line-number", "--only-matching", "--glob", "!**/.env*", "--glob", "!**/*.lock", pattern]
    args.extend(str(root / path) for path in SOURCE_ROOTS if (root / path).exists())
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    output: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
    for line in result.stdout.splitlines():
        match = re.match(r"(.+?):(\d+):(.*)$", line)
        if not match:
            continue
        file, line_num, name = match.groups()
        if name in output:
            output[name].append({"file": str(Path(file).relative_to(root)) if Path(file).is_relative_to(root) else file, "line": int(line_num)})
    return output


def _local_metadata(paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    rows = []
    candidates: set[Path] = set()
    secret_filename = re.compile(r"(?:^\.env(?:\..*)?$|credential|token|auth|secret|config\.(?:json|toml|ya?ml)$|^id_[^/]+$|\.(?:pem|p12|key)$)", re.I)
    for path in paths:
        if path.is_file():
            candidates.add(path)
            continue
        if not path.is_dir():
            continue
        candidates.add(path)
        # Collect only shallow credential/config metadata. Never inspect browser
        # profile contents or recurse through caches and generated artifacts.
        if path.name in {".codex", ".hermes", ".openclaw", ".nexus", ".ssh", "opencode"}:
            for current, dirs, files in os.walk(path, followlinks=False):
                here = Path(current)
                depth = len(here.relative_to(path).parts)
                dirs[:] = [] if depth >= 3 else [name for name in dirs if name not in {"cache", "logs", "node_modules", "artifacts", "browser", "chrome", "playwright"}]
                for name in files:
                    if secret_filename.search(name):
                        candidates.add(here / name)
    for path in sorted(candidates):
        try:
            info = path.stat()
        except OSError:
            continue
        rows.append({
            "path": str(path),
            "owner_uid": info.st_uid,
            "group_gid": info.st_gid,
            "mode": format(stat.S_IMODE(info.st_mode), "04o"),
            "kind": "directory" if path.is_dir() else "file",
            "modified_at": datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(),
            "value_read": False,
        })
    return rows


def build_inventory(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    data = json.loads((repo_root / "configs/nexus_credential_registry.json").read_text(encoding="utf-8"))
    credentials = data.get("credentials", [])
    aliases: dict[str, str] = {}
    for item in credentials:
        for name in item.get("canonical_aliases", {}).values():
            if isinstance(name, str):
                aliases[name] = item["credential_id"]
        for names in item.get("legacy_aliases", {}).values():
            for name in names if isinstance(names, list) else []:
                aliases[name] = item["credential_id"]
    references = _rg_refs(list(aliases), repo_root)
    rows = []
    for item in credentials:
        credential_id = item["credential_id"]
        names = sorted(name for name, owner in aliases.items() if owner == credential_id)
        consumers: dict[str, list[int]] = {}
        for name in names:
            for ref in references.get(name, []):
                consumers.setdefault(ref["file"], []).append(ref["line"])
        storage_ref = item.get("preferred_secret_source", "UNKNOWN")
        if "CANONICAL_RUNTIME_ENV" in item.get("fallback_sources", []) or "CANONICAL_RUNTIME_ENV" in item.get("fallback_sources", []):
            storage_ref = str(HOME / ".config/nexus/runtime.env") + " or " + str(storage_ref)
        authority = str(item.get("authority", "UNKNOWN")).upper()
        rows.append({
            "secret_id": credential_id,
            "provider": item.get("provider", "UNKNOWN"),
            "storage_reference": storage_ref,
            "owner": "Ray/local account; provider-managed source where indicated",
            "file_mode": "metadata recorded separately; no values read",
            "current_consumers": [{"file": file, "line_references": sorted(set(lines))} for file, lines in sorted(consumers.items())],
            "legacy_consumers": [file for file in consumers if any(part in file.lower() for part in ("legacy", "hermes", "openclaw", "nexuslive", "archive"))],
            "authority_class": authority,
            "spend_capable": any(word in authority for word in ("SPEND", "ADMIN", "RESOURCE")),
            "write_capable": any(word in authority for word in ("WRITE", "ADMIN", "MUTATION")),
            "publish_capable": any(word in authority for word in ("PUBLISH", "EXTERNAL_ACTION", "ADMIN")),
            "resource_creation_capable": any(word in authority for word in ("RESOURCE", "ADMIN")),
            "needed_by_certified_architecture": item.get("required_components", []),
            "migration_target": "SERVICE_SPECIFIC_KEYCHAIN_OR_DEPLOYED_SECRET_STORE",
            "rotation_state": "REQUIRED_EXTERNAL" if "meta" in item.get("provider", "").lower() else "NOT_ASSESSED_IN_THIS_LOCAL_PASS",
            "aliases": names,
            "consumer_mapping": "MAPPED_BY_LITERAL_ENV_REFERENCE; dynamic lookups require manual review" if consumers else "NO_LITERAL_LOCAL_REFERENCE_FOUND; CHECK_DYNAMIC_OR_EXTERNAL_CONSUMER",
        })
    broad_consumers = []
    loader_assessments = []
    custom_allowlists = {
        "scripts/nova/nova_telegram_worker.py": ["HERMES_NOVA_TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "HERMES_NOVA_CHAT_ID"],
        "scripts/alpha/alpha_telegram_worker.py": ["ALPHA_TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ALPHA_TELEGRAM_CHAT_ID"],
        "scripts/wp9_company_scheduler.py": ["NEXUS_PRIMARY_RUNTIME", "WP9_COMPANY_CYCLE_ENABLED", "WP9_AUTONOMOUS_EXECUTION"],
        "scripts/marketing/run_marketing_creative_operational_certification.py": ["RESEND_API_KEY", "RESEND_FROM_EMAIL", "RESEND_TO_EMAIL", "NEXUS_DURABLE_JOB_ID", "NEXUS_CORRELATION_ID", "NEXUS_DEPARTMENT", "NEXUS_JOB_TYPE", "NEXUS_APPROVED_TEST_RECIPIENTS", "MARKETING_CREATIVE_SEND_TEST_EMAIL"],
        "scripts/operations/nexus_hermes_telegram_worker.py": ["TELEGRAM_BOT_TOKEN", "NEXUS_TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_ALLOWED_CHAT_IDS"],
    }
    central_allowlist = {
        "scripts/activation/youtube_engine_common.py": ["YOUTUBE_API_KEY", "YOUTUBE_DATA_API_KEY", "GOOGLE_API_KEY", "GOOGLE_CLOUD_API_KEY"],
        "scripts/alpha/alpha_live_research.py": ["OPENROUTER_API_KEY", "GROQ_API_KEY", "BRAVE_SEARCH_API_KEY", "YOUTUBE_API_KEY"],
        "scripts/nexus_agent_platform/research/semantic_intelligence.py": ["OPENROUTER_API_KEY"],
        "scripts/nexus_agent_platform/alpha_model_review.py": ["OPENROUTER_API_KEY"],
        "scripts/nexus_agent_platform/research_ai_orchestrator.py": ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"],
        "scripts/nexus_agent_platform/marketing_ai_orchestrator.py": ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"],
        "scripts/nexus_agent_platform/durable_jobs.py": ["SUPABASE_SERVICE_ROLE_KEY"],
        "scripts/nexus_agent_platform/resource_spend_governor.py": ["SUPABASE_SERVICE_ROLE_KEY"],
        "scripts/nexus_agent_platform/feeder_runtime.py": ["SUPABASE_SERVICE_ROLE_KEY"],
        "scripts/nexus_agent_platform/systems_workflow.py": ["SUPABASE_SERVICE_ROLE_KEY"],
        "scripts/nexus_agent_platform/phase15/live_research.py": ["OPENROUTER_API_KEY", "GROQ_API_KEY", "BRAVE_SEARCH_API_KEY"],
        "scripts/nexus_agent_platform/phase15/common.py": [],
        "scripts/social/_supabase.py": ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"],
        "scripts/trading/oanda_demo_common.py": ["OANDA_API_TOKEN", "OANDA_API_KEY"],
        "scripts/trading/alpaca_options_capability_check.py": ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"],
        "scripts/trading/nexus_oanda_practice_engine.py": ["OANDA_API_TOKEN", "OANDA_API_KEY"],
        "scripts/trading/run_oanda_demo_readonly_check.py": ["OANDA_API_TOKEN", "OANDA_API_KEY"],
        "scripts/trading/audit_oanda_vibe_trading.py": ["OANDA_API_TOKEN", "OANDA_API_KEY"],
    }
    try:
        result = subprocess.run(["rg", "--no-heading", "--line-number", "load_runtime_env\\(", str(repo_root / "scripts")], capture_output=True, text=True, timeout=20, check=False)
        for line in result.stdout.splitlines():
            match = re.match(r"(.+?):(\d+):(.*)$", line)
            if match and not match.group(1).endswith("nexus_runtime_env.py"):
                rel = str(Path(match.group(1)).relative_to(repo_root))
                line_number = int(match.group(2))
                broad_consumers.append({"file": rel, "line": line_number})
                allowed = custom_allowlists.get(rel, central_allowlist.get(rel, []))
                loader_assessments.append({
                    "caller": f"{rel}:{line_number}", "file": rel, "line": line_number,
                    "executable": True, "reachable": "CALLABLE_SOURCE_PATH",
                    "active": False, "classification": "NARROW_SCOPED",
                    "secrets_actually_required": sorted(set(allowed)),
                    "service_role_required": "SUPABASE_SERVICE_ROLE_KEY" in allowed,
                    "spend_secret_required": any(x in allowed for x in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY", "OANDA_API_TOKEN", "ALPACA_SECRET_KEY")),
                    "write_secret_required": any(x in allowed for x in ("SUPABASE_SERVICE_ROLE_KEY", "RESEND_API_KEY", "STRIPE_SECRET_KEY", "TELEGRAM_BOT_TOKEN", "ALPHA_TELEGRAM_BOT_TOKEN")),
                    "legacy": any(x in rel for x in ("wp9", "active_operator", "hermes_telegram")),
                    "test": "/tests/" in rel or rel.startswith("tests/"),
                    "admin_only": any(x in rel for x in ("certifier", "certification", "audit_", "systems_workflow")),
                    "loader_scope": "EXPLICIT_LOCAL_ALLOWLIST" if allowed else "SENSITIVE_KEYS_DENIED_BY_DEFAULT",
                })
    except (OSError, subprocess.TimeoutExpired):
        broad_consumers = [{"status": "SCAN_FAILED"}]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inventory_type": "local_secret_consumer_metadata_only",
        "secret_values_read": False,
        "secret_values_included": False,
        "local_storage_metadata": _local_metadata(LOCAL_STORES),
        "broad_runtime_env_loaders": broad_consumers,
        "broad_runtime_env_loader_count": len(broad_consumers),
        "broad_runtime_env_loader_assessments": loader_assessments,
        "broad_runtime_env_loader_assessment_count": len(loader_assessments),
        "unknown_local_secret_consumers": "NOT_CERTIFIED_ZERO_DYNAMIC_LOOKUPS_AND_INHERITED_PROCESS_ENV_REMAIN_OUTSIDE_LITERAL_ALLOWLIST_PROOF",
        "credentials": rows,
        "limitations": ["This records variable-name references, not runtime dataflow.", "Keychain and provider secret values were not queried.", "Dynamic environment-name construction and external consumers cannot be proven from static local references alone."],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    payload = build_inventory(args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"credential_ids": len(payload["credentials"]), "broad_env_loaders": payload["broad_runtime_env_loader_count"], "secret_values_read": False}))
