"""Canonical, redacted credential identity and health control plane."""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, urllib.parse, urllib.request, urllib.error
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/nexus_credential_registry.json"
RUNTIME_ENV = Path.home() / ".config/nexus/runtime.env"
SOURCE_ORDER = ("PROCESS_ENV", "CANONICAL_RUNTIME_ENV", "LEGACY_ENV", "MACOS_KEYCHAIN", "NETLIFY_ENV", "SUPABASE_SECRET", "CLOUDFLARE_SECRET")
ENV_FILES = (RUNTIME_ENV, ROOT / ".env.local", ROOT / ".env", ROOT / ".env.nexus.recovered.local", Path.home() / "nexuslive/.env", Path.home() / "nexus/.env")

def _load() -> list[dict[str, Any]]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["credentials"]

def _parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file(): return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1); value = value.strip().strip("'\"")
            if key.strip() and value: values[key.strip()] = value
    return values

@lru_cache(maxsize=1)
def _netlify_env_names() -> set[str]:
    """Read Netlify environment metadata without returning any values."""
    cli = shutil.which("netlify")
    if not cli:
        return set()
    try:
        proc = subprocess.run([cli, "env:list", "--json", "--context", "production"], cwd=ROOT, capture_output=True,
                              text=True, timeout=8, check=False)
        if proc.returncode != 0:
            return set()
        payload = json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return set()
    names: set[str] = set()
    if isinstance(payload, dict):
        # Netlify CLI versions have emitted both {NAME: value} and
        # {variables: [{key: NAME}]} shapes. Only keys/names are retained.
        names.update(str(key) for key in payload if re.fullmatch(r"[A-Z][A-Z0-9_]+", str(key)))
        variables = payload.get("variables")
        if isinstance(variables, list):
            for item in variables:
                if isinstance(item, dict):
                    name = item.get("key") or item.get("name")
                    if isinstance(name, str) and re.fullmatch(r"[A-Z][A-Z0-9_]+", name):
                        names.add(name)
    return names

def generate_credential_display_name(*, provider: str, purpose: str, environment: str, runtime: str = "macmini", major: int = 1, unique_id: str | None = None) -> str:
    if environment not in {"prod", "test", "dev", "practice", "canary"}: raise ValueError("invalid environment")
    normalized = lambda value: re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    name = f"nexus-{environment}-{normalized(provider)}-{normalized(purpose)}-{normalized(runtime)}-v{int(major)}"
    return f"{name}-{normalized(unique_id)}" if unique_id else name

def registry_entry(credential_id: str) -> dict[str, Any]:
    for entry in _load():
        if entry["credential_id"] == credential_id: return entry
    raise KeyError(credential_id)

def _source_values() -> dict[str, dict[str, str]]:
    result = {"PROCESS_ENV": dict(os.environ)}
    result["CANONICAL_RUNTIME_ENV"] = _parse(RUNTIME_ENV)
    for path in ENV_FILES[1:]: result[f"LEGACY_ENV:{path}"] = _parse(path)
    # Keychain values are intentionally represented as a source map only when
    # explicitly requested by resolution; never serialize the returned value.
    result["MACOS_KEYCHAIN"] = {}
    # Presence-only remote metadata. Values are never retained, serialized, or
    # made available to provider adapters by this catalog process.
    result["NETLIFY_ENV"] = {name: "[REMOTE_CONFIGURED]" for name in _netlify_env_names()}
    return result

def _keychain_value(credential_id: str, component: str) -> str | None:
    """Read one secret from macOS Keychain without ever returning it to reports."""
    if sys.platform != "darwin":
        return None
    service = f"nexus/{credential_id}"
    account = component
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        value = result.stdout.strip()
        return value if result.returncode == 0 and value else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def keychain_status(credential_id: str, component: str) -> str:
    return "CONFIGURED" if _keychain_value(credential_id, component) else "NOT_FOUND"

def store_keychain(credential_id: str, component: str, value: str, *, replace: bool = False) -> dict[str, Any]:
    """Store one component in Keychain; values never enter return data or logs."""
    if not value: raise ValueError("empty_secret")
    if sys.platform != "darwin": return {"stored": False, "status": "UNSUPPORTED_PLATFORM", "values_included": False}
    if _keychain_value(credential_id, component) and not replace:
        return {"stored": False, "status": "ALREADY_CONFIGURED", "values_included": False}
    try:
        service = f"nexus/{credential_id}"
        proc = subprocess.run(["security", "add-generic-password", "-U", "-s", service, "-a", component, "-w", value], capture_output=True, text=True, timeout=5, check=False)
        return {"stored": proc.returncode == 0, "status": "STORED" if proc.returncode == 0 else "STORE_FAILED", "values_included": False}
    except (OSError, subprocess.TimeoutExpired):
        return {"stored": False, "status": "STORE_FAILED", "values_included": False}

def resolve(credential_id: str, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    entry = registry_entry(credential_id); sources = _source_values();
    if environ is not None: sources["PROCESS_ENV"] = dict(environ)
    components = {}
    for component, canonical in entry["canonical_aliases"].items():
        aliases = [canonical, *entry.get("legacy_aliases", {}).get(component, [])]
        found: list[dict[str, str]] = []
        for source, values in sources.items():
            if source == "MACOS_KEYCHAIN":
                if _keychain_value(credential_id, component):
                    found.append({"source": source, "alias": canonical})
                continue
            for alias in aliases:
                if values.get(alias): found.append({"source": source.split(":", 1)[0], "alias": alias})
        found.sort(key=lambda row: (SOURCE_ORDER.index(row["source"]) if row["source"] in SOURCE_ORDER else 99, aliases.index(row["alias"])))
        components[component] = {"canonical_alias": canonical, "accepted_aliases": aliases, "found": found, "selected": found[0] if found else None}
    present = all(item["selected"] for item in components.values())
    sources_found = sorted({item["selected"]["source"] for item in components.values() if item["selected"]})
    classification = "AVAILABLE_REMOTE_NETLIFY" if present and sources_found == ["NETLIFY_ENV"] else ("AVAILABLE_LOCAL" if present else "MISSING")
    return {"credential_id": credential_id, "provider": entry["provider"], "purpose": entry["purpose"], "environment": entry["environment"], "canonical_aliases": entry["canonical_aliases"], "legacy_aliases": entry.get("legacy_aliases", {}), "provider_display_name": entry["provider_display_name"], "components": components, "source_precedence": list(SOURCE_ORDER), "source_found": sources_found, "source_classification": classification, "authenticated": "UNKNOWN", "result": "AVAILABLE" if present else "MISSING", "values_included": False}

def apply_to_process(credential_id: str) -> dict[str, Any]:
    """Map the selected legacy value into the canonical provider env name in memory only."""
    entry = registry_entry(credential_id); sources = _source_values(); applied = []
    for component, canonical in entry["canonical_aliases"].items():
        aliases = [canonical, *entry.get("legacy_aliases", {}).get(component, [])]
        for source in SOURCE_ORDER:
            values = sources.get(source, {})
            if source == "MACOS_KEYCHAIN":
                keychain_value = _keychain_value(credential_id, component)
                if keychain_value:
                    os.environ[canonical] = keychain_value
                    for compatibility_alias in aliases[1:]: os.environ.setdefault(compatibility_alias, keychain_value)
                    applied.append(component); break
            alias = next((candidate for candidate in aliases if values.get(candidate)), None)
            if alias:
                os.environ[canonical] = values[alias]
                # Provider adapters may still read a legacy name during the
                # compatibility window; this is process memory only.
                for compatibility_alias in aliases[1:]:
                    os.environ.setdefault(compatibility_alias, values[alias])
                applied.append(component); break
    return {"credential_id": credential_id, "components_applied": applied, "values_included": False}

def catalog() -> dict[str, Any]:
    records = [resolve(entry["credential_id"]) for entry in _load()]
    for record in records:
        entry = registry_entry(record["credential_id"])
        health = {"status":"NOT_RUN","http_status":None}
        if record["credential_id"] == "credential.brave.web_search.prod.v1" and record["result"] == "AVAILABLE":
            apply_to_process(record["credential_id"])
            key = os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY")
            if key:
                try:
                    request = urllib.request.Request("https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q":"Nexus credential canary","count":1}), headers={"Accept":"application/json","X-Subscription-Token":key})
                    with urllib.request.urlopen(request, timeout=10) as response: health = {"status":"PASS","http_status":response.status}
                except urllib.error.HTTPError as exc: health = {"status":"AUTH_REQUIRED" if exc.code in {401,402,403} else "DEGRADED","http_status":exc.code}
                except Exception: health = {"status":"DEGRADED","http_status":None}
        result = record["result"]
        if health["status"] == "AUTH_REQUIRED": result = "AUTH_REQUIRED"
        record.update({"last_health_check": health, "authenticated":"YES" if health["status"] == "PASS" else ("NO" if health["status"] == "AUTH_REQUIRED" else "UNKNOWN"), "result":result, "permissions_scopes": [], "expiry_known": "NO", "rotation_due": "UNKNOWN", "capabilities": entry.get("capabilities", []), "authority": entry.get("authority")})
    return {"schema_version":"nexus.credential-catalog.v1", "generated_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "raw_values_included":False, "credentials":records}

def write_reports() -> dict[str, Any]:
    report = catalog(); target = ROOT / "reports/runtime"; target.mkdir(parents=True, exist_ok=True)
    (target / "nexus_credential_catalog_latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# Nexus Credential Catalog", "", "Redacted identity inventory; secret values are never written.", "", "| Identity | Provider | Components | Sources | Result |", "|---|---|---|---|---|"]
    for row in report["credentials"]:
        components = ", ".join(f"{key}:{'PRESENT' if value['selected'] else 'MISSING'}" for key, value in row["components"].items())
        lines.append(f"| {row['credential_id']} | {row['provider']} | {components} | {', '.join(row['source_found']) or 'none'} | {row['result']} |")
    (target / "nexus_credential_catalog_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__": print(json.dumps(write_reports(), indent=2))
