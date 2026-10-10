"""Build a secret-safe static inventory of executable external call sites.

This is intentionally a conservative source scanner, not a proof that arbitrary
dynamic code cannot make a network request. Dynamic/ambiguous sites are emitted
as UNKNOWN so the activation gate can fail closed.
"""
from __future__ import annotations

import hashlib
import json
import argparse
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh", ".yml", ".yaml"}
SKIP_PARTS = {
    ".git", "node_modules", "dist", "build", "coverage", ".venv-agent-platform",
    ".py314-incomplete", "__pycache__", ".pytest_cache", "vendor", "target",
    "artifacts", "reports", "logs", "cache", "caches", "test-results", "tmp",
}
SOURCE_DIRS = (
    "scripts", "src", "netlify", "supabase", "ops", "tests", "tools", "services",
    "plugins", "hermes_alpha", "prototype", "external_research", "nexus_research",
    "config", "configs", "infra", "deploy", "launchd", "skills", "test_fixtures", ".github",
)
MAX_SOURCE_BYTES = 2_000_000
SKIPPED_SOURCE_FILES: list[str] = []
PROVIDERS: dict[str, tuple[str, ...]] = {
    "OPENROUTER": ("openrouter.ai",),
    "OPENAI": ("api.openai.com", "openai.com/v1", "from openai import", "import openai"),
    "GROQ": ("api.groq.com", "from groq import", "import groq"),
    "GEMINI": ("generativelanguage.googleapis.com", "google.generativeai", "google-genai"),
    "ANTHROPIC": ("api.anthropic.com", "from anthropic import", "import anthropic"),
    "META": ("graph.facebook.com", "graph.instagram.com", "facebook.com/v", "instagram.com"),
    "RESEND": ("api.resend.com", "resend.com/emails"),
    "SMTP": ("smtplib", "sendmail(", "smtp."),
    "STRIPE": ("api.stripe.com", "stripe.", "from stripe"),
    "SUPABASE": ("supabase.co", "supabase.com", "supabase-py", "supabase-js"),
    "NETLIFY": ("api.netlify.com", "netlify deploy"),
    "CLOUDFLARE_R2": ("api.cloudflare.com", "r2.cloudflarestorage.com", "workers.dev"),
    "ORACLE": ("oraclecloud.com", "oci ", "oci."),
    "MODAL": ("modal.com", "modal.Function", "modal.App", "modal.Volume"),
    "HUGGING_FACE": ("huggingface.co", "huggingface_hub", "hf_hub_download"),
    "KAGGLE": ("kaggle.com", "kagglehub", "kaggle.api"),
    "TELEGRAM": ("api.telegram.org", "python-telegram-bot", "telegram.Bot"),
    "GOOGLE_WORKSPACE": ("googleapis.com", "googleapiclient", "gmail.googleapis.com"),
    "GITHUB": ("api.github.com", "gh api"),
    "ALPACA": ("alpaca.markets", "alpaca-py", "alpaca_trade_api"),
    "OANDA": ("oanda.com", "fxpractice.oanda.com", "fxtrade.oanda.com"),
    "PENPOT": ("penpot", "api.penpot.app"),
}
NETWORK_RE = re.compile(
    r"\b(?:fetch|axios\.(?:get|post|put|delete|request)|requests\.(?:get|post|put|delete|request)|"
    r"httpx\.(?:get|post|put|delete|request)|urllib\.request\.(?:urlopen|Request)|"
    r"urlopen|http_json|\.remote\(|\.submit\(|\.create\(|\.send(?:_message)?\(|"
    r"sendmail|SMTP|subprocess\.(?:run|Popen)|execFile|spawn)\b|\b(?:OpenAI|Anthropic|Groq|Client)\s*\("
)
FUNCTION_RE = re.compile(
    r"^\s*(?:async\s+)?(?:def|function)\s+([\w$]+)|^\s*(?:export\s+)?(?:const|let)\s+([\w$]+)\s*=\s*(?:async\s*)?(?:\([^\n]*\)|[\w$]+)\s*=>"
)
BROWSER_ACTION_RE = re.compile(r"(?:\.goto\(|\.click\(|\.fill\(|\.type\(|\.evaluate\(|\.press\(|\.submit\(|puppeteer|playwright\.chromium|webdriver\.)", re.I)


def _source_files(root: Path):
    for relative_root in SOURCE_DIRS:
        start = root / relative_root
        if not start.is_dir():
            continue
        for current, dirs, files in os.walk(start, followlinks=False):
            current_path = Path(current)
            dirs[:] = [name for name in dirs if name not in SKIP_PARTS and not name.startswith(".venv")]
            for name in files:
                path = current_path / name
                if path.suffix.lower() not in SOURCE_SUFFIXES:
                    continue
                try:
                    if path.stat().st_size > MAX_SOURCE_BYTES:
                        SKIPPED_SOURCE_FILES.append(path.relative_to(root).as_posix())
                        continue
                except OSError:
                    continue
                yield path
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES:
            try:
                if path.stat().st_size <= MAX_SOURCE_BYTES:
                    yield path
                else:
                    SKIPPED_SOURCE_FILES.append(path.name)
            except OSError:
                continue


def _function_at(lines: list[str], index: int) -> str:
    for cursor in range(index, max(-1, index - 120), -1):
        match = FUNCTION_RE.match(lines[cursor])
        if match:
            return match.group(1) or match.group(2)
    return "module_scope"


def _action_type(text: str, provider: str) -> str:
    lower = text.lower()
    if provider == "BROWSER_EXTERNAL":
        return "BROWSER_WRITE_CANDIDATE" if re.search(r"send|submit|upload|publish|checkout|payment|trade|delete|approve|save|create", lower) else "BROWSER_INTERACTION_REVIEW"
    if re.search(r"(?:method\s*=\s*['\"]get['\"]|requests\.get|httpx\.get|urlopen|\bgetme\b|/models\b|/balance\b)", lower) and not re.search(r"\.post\(|sendmail|publish|checkout|create order|place order", lower):
        return "PROVIDER_READ"
    if re.search(r"send|publish|checkout|payment|trade|order|upload|delete|\.post\(|\.put\(|\.create\(", lower):
        return "EXTERNAL_WRITE_OR_RESOURCE_ACTION"
    return "UNKNOWN_ACTION"


def _governance(text: str, provider: str, relative: str, trusted_http_wrapper: bool = False, action_type: str = "UNKNOWN_ACTION") -> tuple[str, dict[str, bool]]:
    lowered = text.lower()
    legacy = any(bit in relative.lower() for bit in ("legacy", "archive", "quarantine", "snapshot"))
    active = not legacy
    has_job = trusted_http_wrapper or any(bit in text for bit in ("NEXUS_DURABLE_JOB_ID", "durable_job_id", "job_id"))
    has_corr = trusted_http_wrapper or any(bit in text for bit in ("correlation_id", "CORRELATION_ID", "correlationId"))
    has_governor = trusted_http_wrapper or any(bit in lowered for bit in ("resource_spend_governor", "governor", "authorize_provider", "execute_provider"))
    has_approval = any(bit in lowered for bit in ("approval", "approved", "ray_approval"))
    has_receipt = trusted_http_wrapper or any(bit in lowered for bit in ("footprint", "receipt", "usage_record", "provider_receipt"))
    flags = {
        "requires_job_id": True,
        "requires_correlation_id": True,
        "requires_governor": True,
        "requires_approval": action_type in {"BROWSER_WRITE_CANDIDATE", "EXTERNAL_WRITE_OR_RESOURCE_ACTION"},
        "active_or_legacy": active,
        "has_job_identity_evidence": has_job,
        "has_correlation_evidence": has_corr,
        "has_governor_evidence": has_governor,
        "has_approval_evidence": has_approval,
        "has_receipt_evidence": has_receipt,
    }
    if legacy:
        return "LEGACY_DISABLED", flags
    if has_job and has_corr and has_governor and has_receipt and (not flags["requires_approval"] or has_approval):
        return "GOVERNED", flags
    if has_governor or has_job:
        return "PARTIAL", flags
    return "BYPASS", flags


def scan_repository(root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in _source_files(root):
        if path.name == "provider_caller_inventory.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = text.splitlines()
        trusted_http_wrapper = (
            ("def http_json" in text and "provider_enforcement import execute" in text and "governed_request" in text)
            or "governed_http_json" in text
            or "from alpha.alpha_live_research import http_json" in text
        )
        for index, line in enumerate(lines):
            if not NETWORK_RE.search(line) and not BROWSER_ACTION_RE.search(line):
                continue
            window_start, window_end = max(0, index - 3), min(len(lines), index + 4)
            window = "\n".join(lines[window_start:window_end])
            lowered = window.lower()
            providers = [name for name, needles in PROVIDERS.items() if any(needle.lower() in lowered for needle in needles)]
            relative = path.relative_to(root).as_posix()
            browser_scope = relative.startswith(("tests/e2e/", "scripts/ui/", "scripts/creative/", "scripts/voice/", "scripts/marketing/"))
            if browser_scope and BROWSER_ACTION_RE.search(line):
                providers.append("BROWSER_EXTERNAL")
            if not providers:
                continue
            fn = _function_at(lines, index)
            body_start = index
            while body_start > 0 and index - body_start < 160:
                if FUNCTION_RE.match(lines[body_start]):
                    break
                body_start -= 1
            declaration_indent = len(lines[body_start]) - len(lines[body_start].lstrip())
            body_end = len(lines)
            for cursor in range(body_start + 1, len(lines)):
                match = FUNCTION_RE.match(lines[cursor])
                if match and (len(lines[cursor]) - len(lines[cursor].lstrip())) <= declaration_indent:
                    body_end = cursor
                    break
            body = "\n".join(lines[body_start:body_end])
            for provider in providers:
                key = (relative, fn, provider)
                row = grouped.get(key)
                if row is None:
                    delegates = (
                        trusted_http_wrapper and ("http_json(" in body or "governed_http_json" in body)
                        or ("provider_enforcement" in body and re.search(r"\bexecute(?:_async|_telegram_delivery)?\s*\(", body) is not None)
                    )
                    action_type = _action_type(body, provider)
                    edge_disabled = relative in {
                        "supabase/functions/hermes-chat/index.ts",
                        "supabase/functions/goclear-followup-trigger/index.ts",
                        "supabase/functions/goclear-marketing-send/index.ts",
                        "supabase/functions/create-stripe-checkout/index.ts",
                        "supabase/functions/create-invited-checkout/index.ts",
                    } and "governed_durable_job_required" in text and "provider_execution_disabled" in text or (
                        relative == "supabase/functions/hermes-chat/index.ts" and "if (provider !== 'none')" in text
                    )
                    governance, evidence = _governance(body, provider, relative, delegates, action_type)
                    if edge_disabled:
                        governance = "LEGACY_DISABLED"
                    digest = hashlib.sha256("|".join(key).encode()).hexdigest()[:16]
                    row = {
                        "caller_id": f"caller.{digest}",
                        "file": relative,
                        "function": fn,
                        "language": path.suffix.lower().lstrip("."),
                        "department": _department(relative),
                        "provider": provider,
                        "action_type": action_type,
                        "spend_capable": provider in {"OPENROUTER", "OPENAI", "GROQ", "GEMINI", "ANTHROPIC", "RESEND", "SMTP", "STRIPE", "ORACLE", "MODAL", "HUGGING_FACE", "KAGGLE", "CLOUDFLARE_R2", "ALPACA", "OANDA"},
                        "write_capable": provider in {"SUPABASE", "META", "RESEND", "SMTP", "STRIPE", "TELEGRAM", "GITHUB", "NETLIFY", "CLOUDFLARE_R2", "ORACLE", "MODAL", "ALPACA", "OANDA"},
                        "publish_capable": provider in {"META", "TELEGRAM", "BROWSER_EXTERNAL"},
                        "resource_creation_capable": provider in {"ORACLE", "MODAL", "CLOUDFLARE_R2", "NETLIFY"},
                        "current_governance": governance,
                        "test_coverage": "UNKNOWN",
                        "governance_evidence": evidence,
                        "line_numbers": [],
                    }
                    grouped[key] = row
                row["line_numbers"].append(index + 1)
    rows = list(grouped.values())
    for row in rows:
        row["line_numbers"] = sorted(set(row["line_numbers"]))
        row["test_coverage"] = _test_coverage(root, row["file"])
    return sorted(rows, key=lambda row: (row["provider"], row["file"], row["function"]))


def _department(relative: str) -> str:
    parts = Path(relative).parts
    known = {"research": "Research", "marketing": "Marketing", "creative": "Creative", "trading": "Trading", "finance": "Finance", "alpha": "Alpha", "nova": "Nova", "telegram": "Telegram", "social": "Social", "operations": "Operations"}
    return next((known[p.lower()] for p in parts if p.lower() in known), "Shared/Infrastructure")


@lru_cache(maxsize=8)
def _test_sources(root_text: str) -> tuple[tuple[str, str], ...]:
    root = Path(root_text)
    tests = root / "tests"
    found = []
    if not tests.exists():
        return ()
    for current, dirs, files in os.walk(tests, followlinks=False):
        dirs[:] = [name for name in dirs if name not in SKIP_PARTS and not name.startswith(".venv")]
        for name in files:
            path = Path(current) / name
            if path.suffix in {".py", ".ts", ".tsx", ".js"}:
                try:
                    found.append((path.name.lower(), path.read_text(errors="ignore").lower()))
                except OSError:
                    continue
    return tuple(found)


def _test_coverage(root: Path, relative: str) -> str:
    stem = Path(relative).stem
    needle = stem.lower()
    if any(needle in filename or needle in content for filename, content in _test_sources(str(root))):
        return "FOUND"
    return "NOT_FOUND"


def inventory_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {name: 0 for name in ("GOVERNED", "PARTIAL", "BYPASS", "NOT_APPLICABLE", "LEGACY_DISABLED", "UNKNOWN")}
    for row in rows:
        counts[row["current_governance"]] += 1
    return {"entry_points": len(rows), **{f"{name.lower()}_count": value for name, value in counts.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = scan_repository(args.repo)
    payload = {"schema_version": 1, "inventory_type": "static_provider_caller_inventory", "repo": str(args.repo), "summary": inventory_summary(rows), "callers": rows, "excluded_oversized_source_files": sorted(set(SKIPPED_SOURCE_FILES)), "limitations": ["Dynamic URLs and runtime-generated SDK clients can evade static detection.", "Source files over 2 MB are listed as excluded and remain UNKNOWN until reviewed.", "A governance marker in source is evidence only; runtime policy still requires tests and path review."]}
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
