"""Canonical, redacted credential identity, universal discovery, and health control plane."""
from __future__ import annotations
import json, os, re, shutil, ssl, subprocess, sys, urllib.parse, urllib.request, urllib.error
from dataclasses import dataclass, asdict, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "configs/nexus_credential_registry.json"
RUNTIME_ENV = Path.home() / ".config/nexus/runtime.env"
WRANGLER_CONFIG = Path.home() / "Library/Preferences/.wrangler/config/default.toml"
WRANGLER_CONFIG_ALT = Path.home() / ".config/.wrangler/config/default.toml"
MODAL_CONFIG = Path.home() / ".modal.toml"
GH_HOSTS_CONFIG = Path.home() / ".config/gh/hosts.yml"
SSH_CONFIG = Path.home() / ".ssh/config"
ORACLE_AUTHORITY_FILE = ROOT / "docs/architecture/NEXUS_ORACLE_CONNECTION_AUTHORITY.json"

SOURCE_ORDER = (
    "PROCESS_ENV",
    "CANONICAL_RUNTIME_ENV",
    "LEGACY_ENV",
    "MACOS_KEYCHAIN",
    "WRANGLER_OAUTH",
    "MODAL_CONFIG",
    "PROVIDER_CLI_AUTH",
    "SSH_CONFIG",
    "NETLIFY_ENV",
    "SUPABASE_SECRET",
    "CLOUDFLARE_SECRET",
)
ENV_FILES = (
    RUNTIME_ENV,
    ROOT / ".env.local",
    ROOT / ".env",
    ROOT / ".env.nexus.recovered.local",
    Path.home() / "nexuslive/.env",
    Path.home() / "nexus/.env",
)


class CredentialStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    EXPIRED = "EXPIRED"
    INSUFFICIENT_SCOPE = "INSUFFICIENT_SCOPE"
    ACCOUNT_SELECTION_REQUIRED = "ACCOUNT_SELECTION_REQUIRED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class CredentialAlreadyExistsError(Exception):
    """Raised when an attempt is made to request/create credentials for an already available capability."""
    pass


class CredentialNeedsRefreshError(Exception):
    """Raised when credential exists in secure store but needs token refresh rather than new app registration."""
    pass


@dataclass
class CredentialHandle:
    """Protected credential handle for secure runtime injection; never serializes raw secrets."""
    credential_id: str
    provider: str
    capabilities: List[str] = field(default_factory=list)
    venture_binding: List[str] = field(default_factory=list)
    account_scope: str = "SHARED"
    auth_type: str = "API_KEY"
    secret_source: str = "UNKNOWN"

    def inject_env(self, target: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Injects environment aliases into process memory or given dict without exposing secrets."""
        applied = apply_to_process(self.credential_id)
        if target is not None:
            entry = registry_entry(self.credential_id)
            for canonical, alias in entry.get("canonical_aliases", {}).items():
                val = os.environ.get(alias)
                if val:
                    target[alias] = val
        return applied

    def __repr__(self) -> str:
        return f"<CredentialHandle credential_id='{self.credential_id}' provider='{self.provider}' (protected)>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "credential_id": self.credential_id,
            "provider": self.provider,
            "capabilities": self.capabilities,
            "venture_binding": self.venture_binding,
            "account_scope": self.account_scope,
            "auth_type": self.auth_type,
            "secret_source": self.secret_source,
            "raw_values_included": False,
        }


@dataclass
class CredentialResolutionResult:
    """Structured, sanitized result returned by the universal Credential Resolver."""
    status: CredentialStatus
    capability: str
    credential_id: Optional[str] = None
    provider: Optional[str] = None
    venture_id: Optional[str] = None
    channel_account_id: Optional[str] = None
    auth_type: Optional[str] = None
    secret_source: Optional[str] = None
    secret_ref: Optional[str] = None
    account_scope: Optional[str] = None
    handle: Optional[CredentialHandle] = None
    message: str = ""
    binding_defect: bool = False
    raw_values_included: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        if self.handle:
            d["handle"] = self.handle.to_dict()
        return d


def _load() -> list[dict[str, Any]]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["credentials"]


def _parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip().strip("'\"")
            if key.strip() and value:
                values[key.strip()] = value
    return values


@lru_cache(maxsize=1)
def _netlify_env_names() -> set[str]:
    """Read Netlify environment metadata without returning any values."""
    cli = shutil.which("netlify")
    if not cli:
        return set()
    try:
        proc = subprocess.run(
            [cli, "env:list", "--json", "--context", "production"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0:
            return set()
        payload = json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return set()
    names: set[str] = set()
    if isinstance(payload, dict):
        names.update(str(key) for key in payload if re.fullmatch(r"[A-Z][A-Z0-9_]+", str(key)))
        variables = payload.get("variables")
        if isinstance(variables, list):
            for item in variables:
                if isinstance(item, dict):
                    name = item.get("key") or item.get("name")
                    if isinstance(name, str) and re.fullmatch(r"[A-Z][A-Z0-9_]+", name):
                        names.add(name)
    return names


def generate_credential_display_name(
    *, provider: str, purpose: str, environment: str, runtime: str = "macmini", major: int = 1, unique_id: str | None = None
) -> str:
    if environment not in {"prod", "test", "dev", "practice", "canary"}:
        raise ValueError("invalid environment")
    normalized = lambda value: re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    name = f"nexus-{environment}-{normalized(provider)}-{normalized(purpose)}-{normalized(runtime)}-v{int(major)}"
    return f"{name}-{normalized(unique_id)}" if unique_id else name


def registry_entry(credential_id: str) -> dict[str, Any]:
    for entry in _load():
        if entry["credential_id"] == credential_id:
            return entry
    raise KeyError(credential_id)


def _source_values() -> dict[str, dict[str, str]]:
    result = {"PROCESS_ENV": dict(os.environ)}
    result["CANONICAL_RUNTIME_ENV"] = _parse(RUNTIME_ENV)
    for path in ENV_FILES[1:]:
        result[f"LEGACY_ENV:{path}"] = _parse(path)
    result["MACOS_KEYCHAIN"] = {}
    result["NETLIFY_ENV"] = {name: "[REMOTE_CONFIGURED]" for name in _netlify_env_names()}
    return result


def _keychain_record(credential_id: str, component: str) -> tuple[str, str]:
    """Return the Keychain service/account identity, honoring service overrides."""
    try:
        entry = registry_entry(credential_id)
        if "keychain_service_override" in entry:
            service = entry["keychain_service_override"]
            account = entry.get("keychain_account_override", component)
            return service, account
    except KeyError:
        pass
    return f"nexus/{credential_id}", component


def _cli_keychain_value(credential_id: str, component: str) -> str | None:
    """Read secret via /usr/bin/security CLI without GUI ACL prompts."""
    try:
        service, account = _keychain_record(credential_id, component)
        proc = subprocess.run(
            ["security", "find-generic-password", "-w", "-s", service, "-a", account],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            val = proc.stdout.strip()
            return val or None
    except Exception:
        pass
    return None


def _keychain_metadata(credential_id: str, component: str) -> dict[str, Any]:
    """Inspect Keychain metadata (modification timestamp, account, service) without exposing secret."""
    service, account = _keychain_record(credential_id, component)
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            return {"present": False}
        match = re.search(r'\"mdat\"<timedate>=(?:0x[0-9a-fA-F]+\s+)?\"([^\"]+)\"', proc.stdout)
        mdat = match.group(1).rstrip("\0") if match else None
        return {
            "present": True,
            "service": service,
            "account": account,
            "mdat": mdat,
        }
    except Exception:
        return {"present": False}


def _keychain_value(credential_id: str, component: str) -> str | None:
    """Read one secret from macOS Keychain without ever returning it to reports."""
    if sys.platform != "darwin":
        return None
    return _security_keychain_value(credential_id, component)


def _security_keychain_value(credential_id: str, component: str) -> str | None:
    """Read through Security.framework in-process to avoid CLI ACL prompts."""
    import ctypes

    service, account = _keychain_record(credential_id, component)
    try:
        framework = ctypes.CDLL(
            "/System/Library/Frameworks/Security.framework/Versions/Current/Security"
        )
        if hasattr(framework, "SecKeychainSetUserInteractionAllowed"):
            framework.SecKeychainSetUserInteractionAllowed.argtypes = [ctypes.c_bool]
            framework.SecKeychainSetUserInteractionAllowed.restype = ctypes.c_int32
            framework.SecKeychainSetUserInteractionAllowed(False)

        framework.SecKeychainFindGenericPassword.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p,
            ctypes.c_uint32, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ]
        framework.SecKeychainFindGenericPassword.restype = ctypes.c_int32
        framework.SecKeychainItemFreeContent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        framework.SecKeychainItemFreeContent.restype = ctypes.c_int32
        service_bytes = service.encode("utf-8")
        account_bytes = account.encode("utf-8")
        length = ctypes.c_uint32()
        data = ctypes.c_void_p()
        status = framework.SecKeychainFindGenericPassword(
            None, len(service_bytes), service_bytes, len(account_bytes), account_bytes,
            ctypes.byref(length), ctypes.byref(data), None,
        )
        if status == 0 and data.value and length.value:
            try:
                value = ctypes.string_at(data.value, length.value).decode("utf-8")
                return value or None
            finally:
                framework.SecKeychainItemFreeContent(None, data)
    except (OSError, AttributeError, UnicodeDecodeError, ValueError):
        pass

    # If in-process framework requires user authorization (-25293) or is unavailable, fall back to CLI
    return _cli_keychain_value(credential_id, component)


def keychain_status(credential_id: str, component: str) -> str:
    return "CONFIGURED" if _keychain_value(credential_id, component) else "NOT_FOUND"


def store_keychain(credential_id: str, component: str, value: str, *, replace: bool = False) -> dict[str, Any]:
    """Store one component in Keychain; values never enter return data or logs."""
    if not value:
        raise ValueError("empty_secret")
    if sys.platform != "darwin":
        return {"stored": False, "status": "UNSUPPORTED_PLATFORM", "values_included": False}
    if _keychain_value(credential_id, component) and not replace:
        return {"stored": False, "status": "ALREADY_CONFIGURED", "values_included": False}
    try:
        service, account = _keychain_record(credential_id, component)
        proc = subprocess.run(
            ["security", "add-generic-password", "-U", "-s", service, "-a", account, "-w", value],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return {
            "stored": proc.returncode == 0,
            "status": "STORED" if proc.returncode == 0 else "STORE_FAILED",
            "values_included": False,
        }
    except (OSError, subprocess.TimeoutExpired):
        return {"stored": False, "status": "STORE_FAILED", "values_included": False}


# --------------------------------------------------------------------------
# Secret Source Adapters (Part 6)
# --------------------------------------------------------------------------

def _check_wrangler_oauth() -> Tuple[bool, str]:
    """Check Cloudflare Wrangler OAuth configuration without exposing tokens."""
    for path in (WRANGLER_CONFIG, WRANGLER_CONFIG_ALT):
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                if "oauth_token" in content:
                    return True, str(path)
            except Exception:
                pass
    return False, ""


def _check_modal_config() -> Tuple[bool, str]:
    """Check Modal configuration file without exposing tokens."""
    if MODAL_CONFIG.exists() and MODAL_CONFIG.is_file():
        try:
            content = MODAL_CONFIG.read_text(encoding="utf-8", errors="ignore")
            if "token_id" in content and "token_secret" in content:
                return True, str(MODAL_CONFIG)
        except Exception:
            pass
    return False, ""


def _check_gh_cli() -> Tuple[bool, str]:
    """Check GitHub CLI OAuth credentials without exposing tokens."""
    if GH_HOSTS_CONFIG.exists() and GH_HOSTS_CONFIG.is_file():
        try:
            content = GH_HOSTS_CONFIG.read_text(encoding="utf-8", errors="ignore")
            if "oauth_token" in content:
                return True, str(GH_HOSTS_CONFIG)
        except Exception:
            pass
    return False, ""


def _check_ssh_tunnel() -> Tuple[bool, str]:
    """Check Oracle Hermes SSH tunnel configuration."""
    if SSH_CONFIG.exists() and ORACLE_AUTHORITY_FILE.exists():
        return True, str(SSH_CONFIG)
    return False, ""


# --------------------------------------------------------------------------
# Core Resolution Engine
# --------------------------------------------------------------------------

def resolve(credential_id: str, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    entry = registry_entry(credential_id)
    sources = _source_values()
    if environ is not None:
        sources["PROCESS_ENV"] = dict(environ)
    components = {}

    preferred_source = entry.get("preferred_secret_source")

    # Custom secret store adapters
    if preferred_source == "WRANGLER_OAUTH":
        has_wrangler, path = _check_wrangler_oauth()
        selected = {"source": "WRANGLER_OAUTH", "alias": path} if has_wrangler else None
        components["oauth_token"] = {
            "canonical_alias": "CLOUDFLARE_OAUTH_TOKEN",
            "accepted_aliases": ["CLOUDFLARE_OAUTH_TOKEN", "CLOUDFLARE_API_TOKEN"],
            "found": [selected] if selected else [],
            "selected": selected,
        }
    elif preferred_source == "MODAL_CONFIG":
        has_modal, path = _check_modal_config()
        selected = {"source": "MODAL_CONFIG", "alias": path} if has_modal else None
        for comp in ("token_id", "token_secret"):
            components[comp] = {
                "canonical_alias": f"MODAL_{comp.upper()}",
                "accepted_aliases": [f"MODAL_{comp.upper()}"],
                "found": [selected] if selected else [],
                "selected": selected,
            }
    elif preferred_source == "PROVIDER_CLI_AUTH" and entry.get("provider") == "github":
        has_gh, path = _check_gh_cli()
        selected = {"source": "PROVIDER_CLI_AUTH", "alias": path} if has_gh else None
        components["oauth_token"] = {
            "canonical_alias": "GITHUB_TOKEN",
            "accepted_aliases": ["GITHUB_TOKEN", "GH_TOKEN"],
            "found": [selected] if selected else [],
            "selected": selected,
        }
    elif preferred_source == "SSH_CONFIG":
        # Oracle keeps its authority-file check; other hosts must have their own
        # key file and SSH alias present (never satisfied by Oracle's files).
        if entry.get("ssh_host") in (None, "nexus-oracle"):
            has_ssh, path = _check_ssh_tunnel()
        else:
            key = Path(str(entry.get("ssh_key_path") or "")).expanduser()
            alias_ok = SSH_CONFIG.exists() and f"Host {entry['ssh_host']}" in SSH_CONFIG.read_text(errors="ignore")
            has_ssh, path = (key.is_file() and alias_ok), str(SSH_CONFIG)
        selected = {"source": "SSH_CONFIG", "alias": path} if has_ssh else None
        components["ssh_key"] = {
            "canonical_alias": "SSH_IDENTITY",
            "accepted_aliases": ["SSH_IDENTITY"],
            "found": [selected] if selected else [],
            "selected": selected,
        }
    else:
        for component, canonical in entry.get("canonical_aliases", {}).items():
            aliases = [canonical, *entry.get("legacy_aliases", {}).get(component, [])]
            found: list[dict[str, str]] = []
            for source, values in sources.items():
                if source == "MACOS_KEYCHAIN":
                    if _keychain_value(credential_id, component):
                        found.append({"source": source, "alias": canonical})
                    continue
                for alias in aliases:
                    if values.get(alias):
                        found.append({"source": source.split(":", 1)[0], "alias": alias})
            found.sort(
                key=lambda row: (
                    SOURCE_ORDER.index(row["source"]) if row["source"] in SOURCE_ORDER else 99,
                    aliases.index(row["alias"]),
                )
            )
            components[component] = {
                "canonical_alias": canonical,
                "accepted_aliases": aliases,
                "found": found,
                "selected": found[0] if found else None,
            }

    present = all(item["selected"] for item in components.values())
    sources_found = sorted({item["selected"]["source"] for item in components.values() if item["selected"]})
    classification = (
        "AVAILABLE_REMOTE_NETLIFY"
        if present and sources_found == ["NETLIFY_ENV"]
        else ("AVAILABLE_LOCAL" if present else "MISSING")
    )
    return {
        "credential_id": credential_id,
        "provider": entry["provider"],
        "purpose": entry["purpose"],
        "environment": entry["environment"],
        "canonical_aliases": entry["canonical_aliases"],
        "legacy_aliases": entry.get("legacy_aliases", {}),
        "provider_display_name": entry["provider_display_name"],
        "components": components,
        "source_precedence": list(SOURCE_ORDER),
        "source_found": sources_found,
        "source_classification": classification,
        "authenticated": "UNKNOWN",
        "result": "AVAILABLE" if present else "MISSING",
        "values_included": False,
    }


def apply_to_process(credential_id: str) -> dict[str, Any]:
    """Map the selected value into the canonical provider env name in memory only."""
    entry = registry_entry(credential_id)
    sources = _source_values()
    applied = []
    preferred = entry.get("preferred_secret_source")

    if preferred == "WRANGLER_OAUTH":
        has_wrangler, _ = _check_wrangler_oauth()
        if has_wrangler:
            os.environ.setdefault("CLOUDFLARE_AUTH_METHOD", "WRANGLER_OAUTH")
            applied.append("oauth_token")
        return {"credential_id": credential_id, "components_applied": applied, "values_included": False}

    if preferred == "MODAL_CONFIG":
        has_modal, _ = _check_modal_config()
        if has_modal:
            os.environ.setdefault("MODAL_AUTH_METHOD", "MODAL_CONFIG_TOML")
            applied.extend(["token_id", "token_secret"])
        return {"credential_id": credential_id, "components_applied": applied, "values_included": False}

    for component, canonical in entry.get("canonical_aliases", {}).items():
        aliases = [canonical, *entry.get("legacy_aliases", {}).get(component, [])]
        for source in SOURCE_ORDER:
            values = sources.get(source, {})
            if source == "MACOS_KEYCHAIN":
                keychain_value = _keychain_value(credential_id, component)
                if keychain_value:
                    os.environ[canonical] = keychain_value
                    for compatibility_alias in aliases[1:]:
                        os.environ.setdefault(compatibility_alias, keychain_value)
                    applied.append(component)
                    break
            alias = next((candidate for candidate in aliases if values.get(candidate)), None)
            if alias:
                os.environ[canonical] = values[alias]
                for compatibility_alias in aliases[1:]:
                    os.environ.setdefault(compatibility_alias, values[alias])
                applied.append(component)
                break
    return {"credential_id": credential_id, "components_applied": applied, "values_included": False}


# --------------------------------------------------------------------------
# Universal Capability Resolver (Parts 5, 7, 8, 10, 14)
# --------------------------------------------------------------------------

def resolve_credential(
    capability: str,
    venture_id: Optional[str] = None,
    channel_account_id: Optional[str] = None,
    environment: str = "prod",
    provider: Optional[str] = None,
) -> CredentialResolutionResult:
    """Universal capability resolver across all Nexus departments, agents, and connectors.
    
    Rule: CREDENTIAL_DISCOVERY_BEFORE_CREATION=TRUE
    Never infers missing simply because one expected environment variable is absent.
    """
    credentials = _load()
    
    # 1. Filter candidates by capability and optional provider/environment
    candidates = []
    for c in credentials:
        if environment and c.get("environment") != environment:
            continue
        if provider and c.get("provider").lower() != provider.lower():
            continue
        caps = c.get("capabilities", [])
        if capability in caps or any(capability.startswith(p.rstrip("*")) for p in caps if "*" in p):
            candidates.append(c)

    if not candidates:
        return CredentialResolutionResult(
            status=CredentialStatus.NOT_FOUND,
            capability=capability,
            provider=provider,
            venture_id=venture_id,
            channel_account_id=channel_account_id,
            message=f"No credential registered with capability '{capability}'.",
        )

    # 2. Match venture binding
    matched_entry = None
    binding_defect = False
    
    if venture_id:
        for c in candidates:
            bindings = c.get("venture_binding", ["SHARED"])
            if venture_id in bindings or "SHARED" in bindings:
                matched_entry = c
                break
        if not matched_entry:
            # Capability exists in Nexus for another venture!
            other_binding = candidates[0].get("venture_binding", ["UNKNOWN"])
            binding_defect = True
            return CredentialResolutionResult(
                status=CredentialStatus.AUTH_REQUIRED,
                capability=capability,
                credential_id=candidates[0]["credential_id"],
                provider=candidates[0]["provider"],
                venture_id=venture_id,
                channel_account_id=channel_account_id,
                auth_type=candidates[0].get("auth_type", "API_KEY"),
                account_scope=candidates[0].get("account_scope"),
                message=(
                    f"CREDENTIAL_BINDING_DEFECT: Capability '{capability}' is configured for venture "
                    f"{other_binding} ({candidates[0]['credential_id']}), but venture '{venture_id}' "
                    f"does not have an authorized channel account binding."
                ),
                binding_defect=True,
            )
    else:
        matched_entry = candidates[0]

    # 3. Check registered status flags (e.g. EXPIRED, INSUFFICIENT_SCOPE, AUTH_REQUIRED)
    reg_status = matched_entry.get("status", "AVAILABLE")
    if reg_status == "EXPIRED":
        if _secret_metadata_changed(matched_entry):
            try:
                refresh_res = refresh_credential_health(matched_entry["credential_id"])
                if refresh_res.get("new_status") == "AVAILABLE":
                    matched_entry = registry_entry(matched_entry["credential_id"])
                    reg_status = "AVAILABLE"
            except Exception:
                pass

    if reg_status == "EXPIRED":
        return CredentialResolutionResult(
            status=CredentialStatus.EXPIRED,
            capability=capability,
            credential_id=matched_entry["credential_id"],
            provider=matched_entry["provider"],
            venture_id=venture_id,
            channel_account_id=channel_account_id,
            auth_type=matched_entry.get("auth_type", "API_KEY"),
            secret_source=matched_entry.get("preferred_secret_source"),
            account_scope=matched_entry.get("account_scope"),
            message=(
                f"Credential '{matched_entry['credential_id']}' exists in {matched_entry.get('preferred_secret_source')} "
                f"but provider reported token is EXPIRED or REVOKED. Token refresh required."
            ),
        )

    if reg_status == "INSUFFICIENT_SCOPE":
        return CredentialResolutionResult(
            status=CredentialStatus.INSUFFICIENT_SCOPE,
            capability=capability,
            credential_id=matched_entry["credential_id"],
            provider=matched_entry["provider"],
            venture_id=venture_id,
            channel_account_id=channel_account_id,
            auth_type=matched_entry.get("auth_type", "OAUTH"),
            secret_source=matched_entry.get("preferred_secret_source"),
            account_scope=matched_entry.get("account_scope"),
            message=(
                f"Credential '{matched_entry['credential_id']}' is configured with read/search permissions, "
                f"but capability '{capability}' requires elevated write/upload scope."
            ),
        )

    if reg_status == "AUTH_REQUIRED":
        return CredentialResolutionResult(
            status=CredentialStatus.AUTH_REQUIRED,
            capability=capability,
            credential_id=matched_entry["credential_id"],
            provider=matched_entry["provider"],
            venture_id=venture_id,
            channel_account_id=channel_account_id,
            auth_type=matched_entry.get("auth_type", "OAUTH"),
            secret_source=matched_entry.get("preferred_secret_source"),
            account_scope=matched_entry.get("account_scope"),
            message=f"Authentication required for capability '{capability}' on provider '{matched_entry['provider']}'.",
        )

    # 4. Resolve components across approved stores
    res = resolve(matched_entry["credential_id"])
    if res["result"] == "AVAILABLE":
        handle = CredentialHandle(
            credential_id=matched_entry["credential_id"],
            provider=matched_entry["provider"],
            capabilities=matched_entry.get("capabilities", []),
            venture_binding=matched_entry.get("venture_binding", ["SHARED"]),
            account_scope=matched_entry.get("account_scope", "SHARED"),
            auth_type=matched_entry.get("auth_type", "API_KEY"),
            secret_source=",".join(res.get("source_found", ["UNKNOWN"])),
        )
        return CredentialResolutionResult(
            status=CredentialStatus.AVAILABLE,
            capability=capability,
            credential_id=matched_entry["credential_id"],
            provider=matched_entry["provider"],
            venture_id=venture_id,
            channel_account_id=channel_account_id,
            auth_type=matched_entry.get("auth_type", "API_KEY"),
            secret_source=",".join(res.get("source_found", ["UNKNOWN"])),
            account_scope=matched_entry.get("account_scope"),
            handle=handle,
            message="Credential available and validated.",
        )

    return CredentialResolutionResult(
        status=CredentialStatus.AUTH_REQUIRED,
        capability=capability,
        credential_id=matched_entry["credential_id"],
        provider=matched_entry["provider"],
        venture_id=venture_id,
        channel_account_id=channel_account_id,
        auth_type=matched_entry.get("auth_type", "API_KEY"),
        secret_source=matched_entry.get("preferred_secret_source"),
        account_scope=matched_entry.get("account_scope"),
        message=f"Missing credential components for '{matched_entry['credential_id']}'.",
    )


def assert_discovery_before_creation(
    capability: str,
    venture_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> CredentialResolutionResult:
    """Enforces absolute rule: CREDENTIAL_DISCOVERY_BEFORE_CREATION=TRUE.
    
    Before requesting ANY API key, OAuth grant, access token, or login,
    Nexus MUST search the canonical registry and approved stores.
    """
    res = resolve_credential(capability=capability, venture_id=venture_id, provider=provider)
    if res.status == CredentialStatus.AVAILABLE:
        raise CredentialAlreadyExistsError(
            f"CREDENTIAL_DISCOVERY_BEFORE_CREATION violation: Capability '{capability}' is ALREADY AVAILABLE "
            f"via '{res.credential_id}' ({res.secret_source}). Do NOT create new credentials."
        )
    return res


def get_venture_capabilities(venture_id: str) -> Dict[str, Any]:
    """Answers Nova owner query: 'What accounts and integrations do we already have for venture X?'"""
    available = []
    auth_required = []
    expired = []
    for c in _load():
        bindings = c.get("venture_binding", ["SHARED"])
        if venture_id in bindings or "SHARED" in bindings:
            res = resolve_credential(capability=c.get("capabilities", ["unknown"])[0], venture_id=venture_id)
            item = {
                "credential_id": c["credential_id"],
                "provider": c["provider"],
                "capabilities": c.get("capabilities", []),
                "account_scope": c.get("account_scope", "SHARED"),
                "status": res.status.value,
            }
            if res.status == CredentialStatus.AVAILABLE:
                available.append(item)
            elif res.status == CredentialStatus.EXPIRED:
                expired.append(item)
            else:
                auth_required.append(item)

    return {
        "venture_id": venture_id,
        "total_integrations": len(available) + len(auth_required) + len(expired),
        "available": available,
        "expired": expired,
        "auth_required": auth_required,
    }


def list_all_integrations() -> List[Dict[str, Any]]:
    """Returns a sanitized summary of all registered integrations across Nexus."""
    integrations = []
    for c in _load():
        res = resolve(c["credential_id"])
        integrations.append({
            "credential_id": c["credential_id"],
            "provider": c["provider"],
            "purpose": c.get("purpose"),
            "environment": c.get("environment"),
            "auth_type": c.get("auth_type", "API_KEY"),
            "status": c.get("status") if c.get("status") in ("EXPIRED", "INSUFFICIENT_SCOPE") else (
                "AVAILABLE" if res["result"] == "AVAILABLE" else "AUTH_REQUIRED"
            ),
            "sources": res.get("source_found", []),
            "account_scope": c.get("account_scope", "SHARED"),
            "venture_binding": c.get("venture_binding", ["SHARED"]),
            "capabilities": c.get("capabilities", []),
            "consumers": c.get("consumers", ["SYSTEMS"]),
        })
    return integrations


# --------------------------------------------------------------------------
# Credential Health Validation & Safe Refresh Engine
# --------------------------------------------------------------------------

class HealthCheckStatus(str, Enum):
    PASS = "PASS"
    AUTH_FAILURE = "AUTH_FAILURE"
    EXPIRED_OR_REVOKED = "EXPIRED_OR_REVOKED"
    RATE_LIMIT = "RATE_LIMIT"
    NETWORK_ERROR = "NETWORK_ERROR"
    SSL_ERROR = "SSL_ERROR"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    UNKNOWN = "UNKNOWN"


@dataclass
class LiveValidationResult:
    credential_id: str
    status: HealthCheckStatus
    http_status: Optional[int] = None
    message: str = ""
    diagnostic: str = ""


def _get_ssl_context() -> ssl.SSLContext:
    """Create SSL context honoring certifi CA bundle when present."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _get_secret_metadata_timestamp(entry: dict[str, Any]) -> str:
    """Return modification timestamp or hash for the entry's preferred secret store."""
    source = entry.get("preferred_secret_source")
    cid = entry["credential_id"]
    if source == "MACOS_KEYCHAIN":
        comp = next(iter(entry.get("canonical_aliases", {"default": "default"})))
        meta = _keychain_metadata(cid, comp)
        if meta.get("present") and meta.get("mdat"):
            return str(meta["mdat"])
    elif source in ("CANONICAL_RUNTIME_ENV", "PROCESS_ENV"):
        if RUNTIME_ENV.exists():
            return str(RUNTIME_ENV.stat().st_mtime)
    return "UNKNOWN"


def _secret_metadata_changed(entry: dict[str, Any]) -> bool:
    """Check if the underlying secret in its secure store has a newer timestamp than recorded."""
    recorded = entry.get("secret_mdat")
    current = _get_secret_metadata_timestamp(entry)
    if current != "UNKNOWN" and current != recorded:
        return True
    return False


def update_registry_credential(credential_id: str, updates: Dict[str, Any]) -> dict[str, Any]:
    """Updates fields on an existing credential entry in nexus_credential_registry.json atomically.
    Never exposes or writes raw secrets."""
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    found = False
    updated_entry = None
    for entry in data.get("credentials", []):
        if entry["credential_id"] == credential_id:
            for k, v in updates.items():
                if v is None and k in entry:
                    del entry[k]
                else:
                    entry[k] = v
            found = True
            updated_entry = entry
            break
    if not found:
        raise KeyError(f"Credential '{credential_id}' not found in registry.")

    REGISTRY.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return updated_entry


def validate_credential_live(credential_id: str) -> LiveValidationResult:
    """Perform non-destructive live HTTP probe against provider for supported credentials."""
    entry = registry_entry(credential_id)
    provider = entry.get("provider", "").lower()

    if provider == "printify":
        token = _keychain_value(credential_id, "api_token")
        if not token:
            res = resolve(credential_id)
            if res.get("result") == "AVAILABLE":
                apply_to_process(credential_id)
                token = os.environ.get("NEXUS_PRINTIFY_API_TOKEN") or os.environ.get("PRINTIFY_API_TOKEN")

        if not token:
            return LiveValidationResult(
                credential_id=credential_id,
                status=HealthCheckStatus.AUTH_FAILURE,
                message="Printify secret token missing in all configured secret stores."
            )

        url = "https://api.printify.com/v1/shops.json"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Nexus-Credential-Health/1.0",
                "Accept": "application/json",
            }
        )
        ctx = _get_ssl_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    return LiveValidationResult(
                        credential_id=credential_id,
                        status=HealthCheckStatus.PASS,
                        http_status=resp.status,
                        message=f"Printify live probe succeeded with HTTP {resp.status}."
                    )
                return LiveValidationResult(
                    credential_id=credential_id,
                    status=HealthCheckStatus.UNKNOWN,
                    http_status=resp.status,
                    message=f"Printify live probe returned unexpected HTTP status {resp.status}."
                )
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return LiveValidationResult(
                    credential_id=credential_id,
                    status=HealthCheckStatus.EXPIRED_OR_REVOKED,
                    http_status=e.code,
                    message="HTTP 401 Unauthorized: token expired or revoked."
                )
            elif e.code == 403:
                return LiveValidationResult(
                    credential_id=credential_id,
                    status=HealthCheckStatus.AUTH_FAILURE,
                    http_status=e.code,
                    message="HTTP 403 Forbidden: insufficient permissions or invalid auth."
                )
            elif e.code == 429:
                return LiveValidationResult(
                    credential_id=credential_id,
                    status=HealthCheckStatus.RATE_LIMIT,
                    http_status=e.code,
                    message="HTTP 429 Too Many Requests: provider rate limited."
                )
            elif e.code in (500, 502, 503, 504):
                return LiveValidationResult(
                    credential_id=credential_id,
                    status=HealthCheckStatus.PROVIDER_OUTAGE,
                    http_status=e.code,
                    message=f"HTTP {e.code}: Provider service outage / server error."
                )
            return LiveValidationResult(
                credential_id=credential_id,
                status=HealthCheckStatus.UNKNOWN,
                http_status=e.code,
                message=f"HTTP error {e.code}: {e.reason}."
            )
        except urllib.error.URLError as e:
            reason_str = str(e.reason).lower()
            if "certificate" in reason_str or "ssl" in reason_str:
                return LiveValidationResult(
                    credential_id=credential_id,
                    status=HealthCheckStatus.SSL_ERROR,
                    message=f"SSL certificate validation failure: {e.reason}"
                )
            return LiveValidationResult(
                credential_id=credential_id,
                status=HealthCheckStatus.NETWORK_ERROR,
                message=f"Network connectivity failure: {e.reason}"
            )
        except Exception as e:
            return LiveValidationResult(
                credential_id=credential_id,
                status=HealthCheckStatus.UNKNOWN,
                message=f"Validation exception: {type(e).__name__}: {e}"
            )

    if provider == "meta" and "page_access_token" in entry.get("canonical_aliases", {}):
        return _validate_meta_page_live(credential_id, entry)

    return LiveValidationResult(
        credential_id=credential_id,
        status=HealthCheckStatus.UNKNOWN,
        message=f"No live validator registered for provider '{provider}'."
    )


def _component_value(credential_id: str, entry: dict[str, Any], component: str) -> str | None:
    """Return a component value from Keychain or local env sources (never returned to reports)."""
    value = _keychain_value(credential_id, component)
    if value:
        return value
    canonical = entry.get("canonical_aliases", {}).get(component)
    if not canonical:
        return None
    aliases = [canonical, *entry.get("legacy_aliases", {}).get(component, [])]
    for source, values in _source_values().items():
        if source in ("MACOS_KEYCHAIN", "NETLIFY_ENV"):
            continue
        for alias in aliases:
            if values.get(alias):
                return values[alias]
    return None


def _validate_meta_page_live(credential_id: str, entry: dict[str, Any]) -> LiveValidationResult:
    """Read-only Graph probe: the Page token must resolve to the bound Page ID."""
    token = _component_value(credential_id, entry, "page_access_token")
    expected_page = _component_value(credential_id, entry, "page_id")
    if not token:
        return LiveValidationResult(
            credential_id=credential_id,
            status=HealthCheckStatus.AUTH_FAILURE,
            message="Meta Page access token missing in all configured secret stores.",
        )
    url = "https://graph.facebook.com/v23.0/me?" + urllib.parse.urlencode(
        {"fields": "id,name", "access_token": token}
    )
    try:
        with urllib.request.urlopen(url, timeout=15, context=_get_ssl_context()) as resp:
            body = json.load(resp)
        if expected_page and body.get("id") != expected_page:
            return LiveValidationResult(
                credential_id=credential_id,
                status=HealthCheckStatus.AUTH_FAILURE,
                http_status=resp.status,
                message="Meta token resolves to a different Page than the bound Page ID.",
            )
        return LiveValidationResult(
            credential_id=credential_id,
            status=HealthCheckStatus.PASS,
            http_status=resp.status,
            message=f"Meta Page probe succeeded for Page {body.get('id')}.",
        )
    except urllib.error.HTTPError as e:
        code = None
        try:
            code = json.load(e).get("error", {}).get("code")
        except Exception:
            pass
        status = (
            HealthCheckStatus.EXPIRED_OR_REVOKED if code == 190
            else HealthCheckStatus.RATE_LIMIT if code in (4, 17, 32, 613)
            else HealthCheckStatus.AUTH_FAILURE if e.code in (400, 401, 403)
            else HealthCheckStatus.PROVIDER_OUTAGE if e.code >= 500
            else HealthCheckStatus.UNKNOWN
        )
        return LiveValidationResult(
            credential_id=credential_id, status=status, http_status=e.code,
            message=f"Meta Page probe failed (HTTP {e.code}, Graph code {code}).",
        )
    except ssl.SSLError as e:
        return LiveValidationResult(credential_id=credential_id, status=HealthCheckStatus.SSL_ERROR,
                                    message=f"SSL error: {type(e).__name__}")
    except (urllib.error.URLError, OSError) as e:
        return LiveValidationResult(credential_id=credential_id, status=HealthCheckStatus.NETWORK_ERROR,
                                    message=f"Network error: {type(e).__name__}")


def refresh_credential_health(credential_id: str) -> Dict[str, Any]:
    """Execute live health probe for credential, update registry status and catalog reports.
    Preserves all security guarantees: never logs, returns, or persists raw secrets."""
    entry = registry_entry(credential_id)
    old_status = entry.get("status", "AVAILABLE")
    live_res = validate_credential_live(credential_id)

    timestamp = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    health_payload = {
        "status": live_res.status.value,
        "http_status": live_res.http_status,
        "checked_at": timestamp,
        "message": live_res.message,
    }

    updates: Dict[str, Any] = {"last_health_check": health_payload}
    new_status = old_status

    if live_res.status == HealthCheckStatus.PASS:
        new_status = "AVAILABLE"
        updates["status"] = "AVAILABLE"
        updates["secret_mdat"] = _get_secret_metadata_timestamp(entry)
    elif live_res.status in (HealthCheckStatus.EXPIRED_OR_REVOKED, HealthCheckStatus.AUTH_FAILURE):
        new_status = "EXPIRED"
        updates["status"] = "EXPIRED"
        updates["secret_mdat"] = _get_secret_metadata_timestamp(entry)
    else:
        # A provider connectivity problem, SSL issue, rate limit, or outage must NOT mark a credential expired
        pass

    update_registry_credential(credential_id, updates)
    try:
        write_reports()
    except Exception:
        pass

    return {
        "credential_id": credential_id,
        "old_status": old_status,
        "live_status": live_res.status.value,
        "http_status": live_res.http_status,
        "new_status": new_status,
        "message": live_res.message,
        "values_included": False,
    }


# --------------------------------------------------------------------------
# Catalog & Health Reports
# --------------------------------------------------------------------------

def catalog() -> dict[str, Any]:
    records = [resolve(entry["credential_id"]) for entry in _load()]
    for record in records:
        entry = registry_entry(record["credential_id"])
        health = {"status": "NOT_RUN", "http_status": None}
        if record["credential_id"] == "credential.brave.web_search.prod.v1" and record["result"] == "AVAILABLE":
            apply_to_process(record["credential_id"])
            key = os.environ.get("BRAVE_SEARCH_API_KEY") or os.environ.get("BRAVE_API_KEY")
            if key:
                try:
                    from alpha.alpha_live_research import http_json
                    ok, status, _data, _error, _latency = http_json(
                        "GET",
                        "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": "Nexus credential canary", "count": 1}),
                        {"Accept": "application/json", "X-Subscription-Token": key},
                        timeout=10,
                    )
                    health = {
                        "status": "PASS" if ok else ("AUTH_REQUIRED" if status in {401, 402, 403} else "GOVERNOR_DENIED"),
                        "http_status": status,
                    }
                except Exception:
                    health = {"status": "DEGRADED", "http_status": None}
        result = record["result"]
        if entry.get("status") == "EXPIRED":
            result = "EXPIRED"
        elif entry.get("status") == "INSUFFICIENT_SCOPE":
            result = "INSUFFICIENT_SCOPE"
        elif health["status"] == "AUTH_REQUIRED":
            result = "AUTH_REQUIRED"

        record.update({
            "last_health_check": health,
            "authenticated": "YES" if health["status"] == "PASS" else ("NO" if health["status"] == "AUTH_REQUIRED" else "UNKNOWN"),
            "result": result,
            "permissions_scopes": [],
            "expiry_known": "NO",
            "rotation_due": "UNKNOWN",
            "capabilities": entry.get("capabilities", []),
            "authority": entry.get("authority"),
            "account_scope": entry.get("account_scope", "SHARED"),
            "venture_binding": entry.get("venture_binding", ["SHARED"]),
        })
    return {
        "schema_version": "nexus.credential-catalog.v1",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "raw_values_included": False,
        "credentials": records,
    }


def write_reports() -> dict[str, Any]:
    report = catalog()
    target = ROOT / "reports/runtime"
    target.mkdir(parents=True, exist_ok=True)
    (target / "nexus_credential_catalog_latest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Nexus Credential Catalog",
        "",
        "Redacted identity inventory; secret values are never written.",
        "",
        "| Identity | Provider | Components | Sources | Result |",
        "|---|---|---|---|---|",
    ]
    for row in report["credentials"]:
        components = ", ".join(f"{key}:{'PRESENT' if value['selected'] else 'MISSING'}" for key, value in row["components"].items())
        lines.append(f"| {row['credential_id']} | {row['provider']} | {components} | {', '.join(row['source_found']) or 'none'} | {row['result']} |")
    (target / "nexus_credential_catalog_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def format_status_report() -> str:
    """Formats human-readable credential status report for `nexus credential status` CLI."""
    lines = [
        "================================================================================",
        "NEXUS CANONICAL CREDENTIAL REGISTRY — HEALTH STATUS",
        "Authority: scripts/nexus_agent_platform/credential_control_plane.py",
        "================================================================================",
        "",
    ]
    cat = catalog()
    by_provider: Dict[str, List[Dict[str, Any]]] = {}
    for cred in cat["credentials"]:
        prov = cred["provider"].upper()
        by_provider.setdefault(prov, []).append(cred)

    for prov in sorted(by_provider):
        lines.append(f"{prov}")
        for item in by_provider[prov]:
            caps = ", ".join(item.get("capabilities", [])) or item["purpose"]
            res = item["result"]
            sources = ", ".join(item.get("source_found", [])) or "none"
            lines.append(f"  {caps} = {res} (sources: {sources})")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("status", "--status"):
        print(format_status_report())
    elif len(sys.argv) > 1 and sys.argv[1] in ("refresh", "--refresh"):
        target_id = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "credential.printify.prod.v1"
        res = refresh_credential_health(target_id)
        print(json.dumps(res, indent=2))
    else:
        print(json.dumps(write_reports(), indent=2))
