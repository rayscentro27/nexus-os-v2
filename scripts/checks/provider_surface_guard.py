#!/usr/bin/env python3
"""Discover provider-like executable source files and fail on unregistered surfaces.

The source scan complements the reviewed-file hash lock: a new executable file
that introduces a network/provider boundary must be represented in the caller
registry. The hash lock continues to detect edits within previously reviewed
files.
"""
from __future__ import annotations
import ast, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "reports/remediation/provider_caller_registry_20261009.json"
LOCK = ROOT / "configs/provider_surface_hash_lock_20261009.json"
SECRET_REGISTRY = ROOT / "reports/remediation/local_secret_consumer_registry_20261009.json"
ALLOWED = {"GOVERNED", "DISABLED_FAIL_CLOSED", "LEGACY_DISABLED", "NOT_APPLICABLE",
           "TEST_OR_MOCK", "STATIC_FALSE_POSITIVE", "DEAD_UNREACHABLE", "BYPASS"}
SOURCE_ROOTS = ("scripts", "src", "netlify/functions", "supabase/functions", "workers", ".github/workflows")
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".yml", ".yaml"}
IGNORE_PARTS = {"__pycache__", "node_modules", "dist", "build", "coverage", ".venv", "venv", "fixtures", "mocks"}
IGNORE_NAME_PARTS = ("test_", ".test.", ".spec.", "_fixture.", "_mock.")
SCAN_PATTERNS = (
    re.compile(r"\b(?:requests|httpx|aiohttp)\.(?:get|post|put|patch|delete|request)\s*\(\s*[rubf]*['\"]https?://", re.I),
    re.compile(r"\b(?:fetch|axios\.(?:get|post|put|patch|delete|request))\s*\(\s*[rubf]*['\"]https?://", re.I),
    re.compile(r"\b(?:urllib\.request\.(?:Request|urlopen))\s*\(\s*[rubf]*['\"]https?://", re.I),
    re.compile(r"\b(?:new\s+)?(?:OpenAI|AsyncOpenAI|Anthropic|GoogleGenerativeAI|Stripe)\s*\("),
    re.compile(r"\b(?:openai|anthropic|stripe|boto3|modal|oci|huggingface_hub)\.(?:[A-Za-z_]\w*\.)*(?:create|complete|responses|messages|chat|send|post|upload|deploy|run|launch|invoke)\s*\("),
    re.compile(r"\bsubprocess\.(?:run|Popen|call|check_call|check_output)\s*\([^\n]{0,240}['\"](?:curl|wget|wrangler|netlify|supabase|oci|modal|kaggle)\b", re.I),
    re.compile(r"\bpage\.(?:goto|click|fill|check|select_option)\s*\(\s*['\"]https?://", re.I),
)
PROVIDER_HOST = re.compile(r"https?://(?:api\.|.*\.(?:openai|openrouter|groq|googleapis|google|facebook|tiktok|resend|stripe|telegram|supabase|netlify|cloudflare|modal|oracle|huggingface|kaggle|alpaca|oanda|pexels|firecrawl))", re.I)
# These modules are the reviewed boundaries themselves. Their direct transport
# is expected because the enforcement decision occurs around the call.
ENFORCEMENT_WRAPPERS = {
    "scripts/nexus_agent_platform/provider_enforcement.py",
    "scripts/activation/governed_http.py",
}


def _ignored(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = set(path.parts)
    return bool(parts & IGNORE_PARTS) or any(part in rel.lower() for part in IGNORE_NAME_PARTS)


def discover_provider_files(root: Path = ROOT) -> set[str]:
    found: set[str] = set()
    for source_root in SOURCE_ROOTS:
        base = root / source_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            if _ignored(path, root):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if path.relative_to(root).as_posix() in ENFORCEMENT_WRAPPERS:
                continue
            # Direct network expressions are only relevant here when the
            # same source file references a provider endpoint. SDK and cloud
            # CLI calls are intrinsically provider-like.
            direct_network = _python_network_call(text) if path.suffix == ".py" else any(pattern.search(text) for pattern in SCAN_PATTERNS[:3])
            sdk_or_cli = direct_network if path.suffix == ".py" else any(pattern.search(text) for pattern in SCAN_PATTERNS[3:])
            if (direct_network and PROVIDER_HOST.search(text)) or sdk_or_cli:
                found.add(path.relative_to(root).as_posix())
    return found


def _python_network_call(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"get", "post", "put", "patch", "delete", "request", "urlopen", "Request"}:
            if not node.args:
                continue
            first = node.args[0]
            value = first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else ""
            if value.startswith(("http://", "https://")) and PROVIDER_HOST.search(value):
                return True
            if not value and PROVIDER_HOST.search(text):
                return True
        if isinstance(func, ast.Name) and func.id in {"OpenAI", "AsyncOpenAI", "Anthropic", "GoogleGenerativeAI", "Stripe"}:
            return True
        if isinstance(func, ast.Attribute) and func.attr in {"run", "Popen", "call", "check_call", "check_output"} and node.args:
            command = node.args[0]
            if isinstance(command, (ast.List, ast.Tuple)):
                items = [x.value for x in command.elts if isinstance(x, ast.Constant) and isinstance(x.value, str)]
                if items and items[0] in {"curl", "wget", "wrangler", "netlify", "supabase", "oci", "modal", "kaggle"}:
                    return True
    return False


def unregistered_provider_files(root: Path, registered_files: set[str]) -> list[str]:
    local = {name for name in registered_files if not name.startswith(("github:", "http://", "https://"))}
    return sorted(discover_provider_files(root) - local)

def check() -> dict:
    registry = json.loads(REGISTRY.read_text())
    lock = json.loads(LOCK.read_text())
    secret_registry = json.loads(SECRET_REGISTRY.read_text())
    drift = []
    for name, expected in lock["files"].items():
        path = ROOT / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            drift.append(name)
    bad_status = [row.get("caller_id") for row in registry["callers"]
                  if row.get("current_governance") not in ALLOWED]
    registered_files = {row.get("file") for row in registry["callers"] if isinstance(row.get("file"), str)}
    discovered_provider_files = discover_provider_files()
    unregistered = unregistered_provider_files(ROOT, registered_files)
    unscoped_bypass = [row.get("caller_id") for row in registry["callers"]
        if row.get("current_governance") == "BYPASS"
        and (row.get("classification_bucket") != "FINITE_EXTERNAL_BLOCKER" or not row.get("external_blocker_id"))]
    partial = [row.get("caller_id") for row in registry["callers"] if row.get("current_governance") == "PARTIAL"]
    unknown = [row.get("caller_id") for row in registry["callers"] if row.get("current_governance") == "UNKNOWN"]
    mapped_secret_callers = {row.get("caller_id") for row in secret_registry.get("provider_caller_mappings", [])}
    missing_secret_mappings = [row.get("caller_id") for row in registry["callers"]
        if row.get("classification_bucket") and row.get("caller_id") not in mapped_secret_callers]
    return {"ok": not (drift or bad_status or unscoped_bypass or partial or unknown or unregistered),
            "locked_source_drift": drift, "invalid_status": bad_status,
            "unscoped_bypass": unscoped_bypass, "partial": partial, "unknown": unknown,
            "discovered_provider_files": len(discovered_provider_files),
            "unregistered_provider_files": unregistered,
            "missing_secret_mappings": missing_secret_mappings,
            "known_external_blockers": [r["caller_id"] for r in registry["callers"]
                if r.get("classification_bucket") == "FINITE_EXTERNAL_BLOCKER"]}

if __name__ == "__main__":
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
