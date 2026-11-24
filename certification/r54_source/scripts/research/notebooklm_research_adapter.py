#!/usr/bin/env python3
"""NotebookLM-backed Research adapter.

One reusable processor for YouTube research sources.  It accepts a video URL and
a ``research_profile_id``, resolves the profile's NotebookLM notebook pool,
deduplicates the source inside that notebook, waits deterministically for
NotebookLM indexing, asks a source-scoped structured question, validates the
JSON, and returns a structured result with full provenance.

Design constraints this file enforces:

* The authenticated Python CLI only.  No Node CLI, no Hermes dependency, no
  Codex/OpenCode prompt per video.
* Every external process has a hard timeout, captured stdout/stderr, and child
  cleanup via a process group kill.
* NotebookLM is never hammered.  Concurrency is bounded by an exclusive lock,
  and every stage carries its own bounded retry budget.
* Continuation is owned by deterministic code.  AI output is data until the
  validator accepts it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_DIR = Path(__file__).resolve().parent
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

import research_profiles as rp

DEFAULT_CLI_CANDIDATES = (
    Path.home() / ".nexus/venvs/notebooklm-py/bin/notebooklm",
    Path("/Users/raymonddavis/.nexus/venvs/notebooklm-py/bin/notebooklm"),
)

FAILURE_TAXONOMY: dict[str, dict[str, Any]] = {
    "NOTEBOOK_AUTH_FAILED": {"stage": "auth", "retry": "none", "max_attempts": 1,
                             "terminal_after": "AUTH_INVALID"},
    "NOTEBOOK_CLI_UNAVAILABLE": {"stage": "auth", "retry": "none", "max_attempts": 1,
                                 "terminal_after": "CLI_MISSING"},
    "NOTEBOOK_NOT_FOUND": {"stage": "notebook_resolve", "retry": "bounded", "max_attempts": 2},
    "NOTEBOOK_CREATE_FAILED": {"stage": "notebook_resolve", "retry": "bounded", "max_attempts": 2},
    "NOTEBOOK_SOURCE_ADD_FAILED": {"stage": "source_add", "retry": "bounded", "max_attempts": 3},
    "NOTEBOOK_SOURCE_POOL_FULL": {"stage": "source_add", "retry": "none", "max_attempts": 1,
                                  "terminal_after": "POOL_CAP_REACHED"},
    "NOTEBOOK_LIMIT_REACHED": {"stage": "resource", "retry": "none", "max_attempts": 1,
                                "terminal_after": "RESOURCE_LIMIT_REACHED"},
    "NOTEBOOK_SOURCE_INDEX_TIMEOUT": {"stage": "source_index", "retry": "scheduled_recheck", "max_attempts": 4},
    "NOTEBOOK_SOURCE_INDEX_FAILED": {"stage": "source_index", "retry": "bounded", "max_attempts": 2,
                                     "terminal_after": "SOURCE_ERROR_STATE"},
    "NOTEBOOK_SOURCE_ID_NOT_RESOLVED": {"stage": "source_id", "retry": "scheduled_recheck", "max_attempts": 3},
    "NOTEBOOK_ASK_FAILED": {"stage": "ask", "retry": "bounded", "max_attempts": 3},
    "NOTEBOOK_ASK_TIMEOUT": {"stage": "ask", "retry": "scheduled_recheck", "max_attempts": 2},
    "NOTEBOOK_PROFILE_FIT_INVALID": {"stage": "profile_fit", "retry": "bounded", "max_attempts": 2},
    "RESEARCH_CASE_REQUIRED": {"stage": "notebook_resolve", "retry": "none", "max_attempts": 1,
                               "terminal_after": "CASE_ID_REQUIRED"},
    "NOTEBOOK_JSON_INVALID": {"stage": "extract", "retry": "bounded", "max_attempts": 2},
    "NOTEBOOK_QUALITY_CHECK_FAILED": {"stage": "quality", "retry": "bounded", "max_attempts": 2},
    "NOTEBOOK_SOURCE_CONTAMINATION": {"stage": "quality", "retry": "none", "max_attempts": 1,
                                      "terminal_after": "CROSS_SOURCE_LEAK"},
    "NOTEBOOK_PERSISTENCE_FAILED": {"stage": "persist", "retry": "bounded", "max_attempts": 3},
    "DEPARTMENT_HANDOFF_FAILED": {"stage": "handoff", "retry": "bounded", "max_attempts": 3},
    "RESOURCE_LIMIT_UNAVAILABLE": {"stage": "resource", "retry": "scheduled_recheck", "max_attempts": 2},
}

CITATION_PATTERN = re.compile(r"\[\d+\]")
MAX_PROFILE_FIT_CANDIDATES = 3
_NON_INFORMATION_SENTINELS = {"NOT_STATED", "NOT_APPLICABLE", "UNKNOWN"}
RESEARCH_GOVERNOR_JOB_TYPE = "NEXUS_RESEARCH_NOTEBOOKLM"
_RESEARCH_POLICY_READY = False


def _ensure_research_notebooklm_policy() -> None:
    """Add the bounded Research scope without reopening any existing stop."""
    global _RESEARCH_POLICY_READY
    if _RESEARCH_POLICY_READY:
        return
    from nexus_agent_platform.resource_spend_governor import default_store

    store = default_store()
    limits = {
        "rate": {"requests": 6, "operations": 6, "window_seconds": 60},
        "usage": {"bytes": 500000, "runtime_seconds": 900, "cost": 0},
        "money": {"per_job": 0, "per_day": 0, "per_month": 0},
    }
    for period in ("DAILY", "MONTHLY"):
        current = store.resolve_policy("NOTEBOOKLM", "research_discovery", RESEARCH_GOVERNOR_JOB_TYPE, period)
        # A scoped policy may already be HARD_STOP after genuine resource use.
        # Never reopen it by re-applying its initial NORMAL configuration.
        if not current or current.get("wildcard_fallback_used", False):
            store.ensure_policy("NOTEBOOKLM", "research_discovery", RESEARCH_GOVERNOR_JOB_TYPE,
                period, autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                soft_limits=limits, hard_limits=limits, concurrency_limit=1,
                resource_creation_limit=0, state="NORMAL", approval_required=False)
    # The durable worker's Research/Needle jobs also reserve their normal
    # Supabase control-plane envelope. Copy only the already-authorized
    # durable-worker limits into these exact job scopes; never infer a new
    # allowance from the disabled global default.
    for period in ("DAILY", "MONTHLY"):
        worker_policy = store.resolve_policy("SUPABASE", "durable_worker", "NEXUS_NOTEBOOKLM_RUNTIME_CANARY", period)
        if (not worker_policy or worker_policy.get("service") != "durable_worker"
                or worker_policy.get("state") != "NORMAL"
                or not worker_policy.get("autonomous_usage_allowed")):
            raise RuntimeError(f"RESEARCH_DURABLE_WORKER_POLICY_UNAVAILABLE:{period}")
        soft = worker_policy.get("soft_limits") or {}
        hard = worker_policy.get("hard_limits") or {}
        if isinstance(soft, str): soft = json.loads(soft)
        if isinstance(hard, str): hard = json.loads(hard)
        for job_type in ("NEXUS_NOTEBOOKLM_RUNTIME_CANARY", "NEEDLE_RESEARCH_READINESS_VERIFY",
                         "NEEDLE_RESEARCH_TARGETED_REPAIR"):
            store.ensure_policy("SUPABASE", "durable_worker", job_type, period,
                autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                soft_limits=soft, hard_limits=hard,
                concurrency_limit=int(worker_policy.get("concurrency_limit") or 1),
                resource_creation_limit=int(worker_policy.get("resource_creation_limit") or 0),
                state="NORMAL", approval_required=False)
    _RESEARCH_POLICY_READY = True


def interpret_trading_subtype(payload: dict[str, Any]) -> dict[str, Any]:
    subtype = payload.get("trading_subtype") if isinstance(payload, dict) else None
    if not isinstance(subtype, str) or not subtype.strip():
        raise ValueError("invalid trading_subtype")
    if subtype not in rp.TRADING_SUBTYPE_FIELDS:
        subtype = "unknown_trading"
    quotes = payload.get("evidence_quotes")
    if not isinstance(quotes, list) or not any(isinstance(q, str) and q.strip() for q in quotes):
        raise ValueError("subtype classification requires evidence quotes")
    signals = payload.get("secondary_signals", [])
    if not isinstance(signals, list) or any(s != "affiliate_opportunity" for s in signals):
        raise ValueError("unsupported secondary signal")
    content_mode = payload.get("content_mode")
    if not isinstance(content_mode, str) or not content_mode.strip():
        raise ValueError("content_mode is required")
    return {"trading_subtype": subtype, "content_mode": content_mode.strip()[:80],
            "secondary_signals": sorted(set(signals)),
            "evidence_quotes": [q.strip() for q in quotes if isinstance(q, str) and q.strip()][:6]}


def interpret_profile_fit(payload: dict[str, Any], candidate_profile_id: str) -> dict[str, Any]:
    """Validate one model fit decision; a NO is routing feedback, not failure."""
    if not isinstance(payload, dict) or payload.get("candidate_profile_id") != candidate_profile_id:
        raise ValueError("profile-fit response candidate_profile_id mismatch")
    fit = str(payload.get("fit") or "").upper()
    if fit not in {"YES", "NO"}:
        raise ValueError("profile-fit response fit must be YES or NO")
    quotes = payload.get("evidence_quotes")
    if not isinstance(quotes, list) or not any(str(row).strip() for row in quotes):
        raise ValueError("profile-fit response must include source evidence quotes")
    suggested = payload.get("suggested_profile_id")
    if fit == "YES":
        if suggested not in (None, ""):
            raise ValueError("a YES profile-fit response cannot suggest a different profile")
        return {"decision": "PROFILE_FIT", "candidate_profile_id": candidate_profile_id,
                "suggested_profile_id": None, "reason": str(payload.get("reason") or "")[:300],
                "evidence_quotes": [str(row).strip() for row in quotes if str(row).strip()][:5]}
    if suggested not in rp.PROFILES or suggested == candidate_profile_id:
        raise ValueError("a NO profile-fit response must suggest a different known profile")
    return {"decision": "PROFILE_MISMATCH", "candidate_profile_id": candidate_profile_id,
            "suggested_profile_id": suggested, "reason": str(payload.get("reason") or "")[:300],
            "evidence_quotes": [str(row).strip() for row in quotes if str(row).strip()][:5]}


def next_profile_candidate(suggested_profile_id: str | None, visited: set[str]) -> str | None:
    """Choose a new known candidate, honoring the source-fit recommendation first."""
    if suggested_profile_id in rp.PROFILES and suggested_profile_id not in visited:
        return suggested_profile_id
    return next((profile_id for profile_id in sorted(
        rp.PROFILES, key=lambda value: (rp.PROFILES[value].get("priority", 50), value)
    ) if profile_id not in visited), None)

MAX_CONCURRENT_NOTEBOOK_JOBS = max(1, int(os.environ.get("NEXUS_NOTEBOOK_MAX_CONCURRENCY", "1")))
MAX_BACKGROUND_SHELLS = max(1, int(os.environ.get("NEXUS_NOTEBOOK_MAX_BACKGROUND_SHELLS", "2")))

STAGE_TIMEOUTS = {
    "version": 60,
    "list": 180,
    "history": 30,
    "create": 180,
    "source_list": 180,
    "source_add": 240,
    "source_wait": int(os.environ.get("NEXUS_NOTEBOOK_INDEX_TIMEOUT_SECONDS", "900")),
    "ask": int(os.environ.get("NEXUS_NOTEBOOK_ASK_TIMEOUT_SECONDS", "300")),
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_cli() -> str:
    # Nexus workers must share the authenticated Python CLI and default
    # profile. Ignore NEXUS_NOTEBOOKLM_CLI and PATH shims: this host also has
    # an unrelated Node executable named `notebooklm`.
    for candidate in DEFAULT_CLI_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    # Keep the canonical target in the error message rather than silently
    # falling back to a PATH executable with a different profile store.
    return str(Path.home() / ".nexus/venvs/notebooklm-py/bin/notebooklm")


class NotebookLMError(RuntimeError):
    def __init__(self, failure_code: str, message: str, *, stage: str | None = None) -> None:
        super().__init__(message)
        self.failure_code = failure_code if failure_code in FAILURE_TAXONOMY else "NOTEBOOK_ASK_FAILED"
        self.stage = stage or FAILURE_TAXONOMY[self.failure_code]["stage"]


def failure_plan(failure_code: str) -> dict[str, Any]:
    return FAILURE_TAXONOMY[failure_code]


def retry_delay_seconds(failure_code: str, attempt: int) -> int:
    plan = failure_plan(failure_code)
    mode = plan["retry"]
    if mode == "scheduled_recheck":
        return min(15 * 60 * (2 ** max(0, attempt - 1)), 4 * 60 * 60)
    if mode == "bounded_no_backoff":
        return 60
    if mode == "none":
        return 0
    return min(60 * (2 ** max(0, attempt - 1)), 15 * 60)


def is_terminal(failure_code: str, attempt: int) -> bool:
    plan = failure_plan(failure_code)
    terminal_after = plan.get("terminal_after")
    if terminal_after:
        return True
    return attempt >= int(plan.get("max_attempts", 1))


def _json_from_stdout(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        raise ValueError("empty stdout")
    try:
        return json.loads(text)
    except ValueError:
        pass
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char in "[{":
            try:
                value, _ = decoder.raw_decode(text[index:])
                return value
            except ValueError:
                continue
    raise ValueError("no JSON object found in stdout")


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_VALID_ESCAPES = set('"\\/bfnrtu')
_BAD_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')


def repair_invalid_escapes(text: str) -> tuple[str, int]:
    """Drop backslashes that JSON does not define, keeping every valid escape.

    NotebookLM frequently emits LaTeX-flavoured escapes such as ``\\$180,000``
    or ``\\%`` inside string values, which makes an otherwise well-formed
    object unparseable.  Only *invalid* escapes are removed, so the repair
    cannot change the value of any validly escaped character.
    """
    repaired, count = _BAD_ESCAPE.subn("", text)
    return repaired, count


def extract_json_object(answer: str) -> dict[str, Any]:
    """Deterministically pull one JSON object out of a NotebookLM answer."""
    if not answer or not answer.strip():
        raise ValueError("empty answer")
    candidates: list[str] = []
    for match in _FENCE.finditer(answer):
        candidates.append(match.group(1).strip())
    candidates.append(answer.strip())
    decoder = json.JSONDecoder()
    for text in candidates:
        for candidate in (text, repair_invalid_escapes(text)[0]):
            for index, char in enumerate(candidate):
                if char == "{":
                    try:
                        value, _ = decoder.raw_decode(candidate[index:])
                    except ValueError:
                        continue
                    if isinstance(value, dict):
                        return value
    raise ValueError("no JSON object found in answer")


def normalize_payload(payload: dict[str, Any], schema: dict[str, Any] | None = None, *,
                      profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Coerce a returned object to the declared schema without inventing values."""
    schema = schema or (profile or {}).get("extraction_schema")
    if schema is None:
        raise ValueError("schema or profile with extraction_schema is required")
    properties: dict[str, dict[str, Any]] = schema["properties"]
    normalized: dict[str, Any] = {}
    for name, spec in properties.items():
        if name not in payload:
            continue
        value = payload[name]
        if spec["type"] == "array":
            if isinstance(value, list):
                items = [str(entry).strip() for entry in value if entry not in (None, "") and str(entry).strip()]
            elif value in (None, ""):
                items = []
            else:
                items = [str(value).strip()]
            normalized[name] = items
        elif spec["type"] == "number":
            if value in (None, ""):
                normalized[name] = None
            else:
                try:
                    normalized[name] = float(value)
                except (TypeError, ValueError):
                    normalized[name] = value
        else:
            if value in (None, ""):
                normalized[name] = None
            elif isinstance(value, (dict, list)):
                normalized[name] = json.dumps(value, sort_keys=True)
            else:
                normalized[name] = str(value).strip()
    return normalized


def _matches_type(value: Any, spec: dict[str, Any]) -> bool:
    """Check one extracted value against the profile's declared field type."""
    declared = spec.get("type")
    if declared == "array":
        return isinstance(value, list)
    if declared == "string":
        return value is None or isinstance(value, str)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "number":
        return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "null":
        return value is None
    return True


def grounding_quotes(payload: dict[str, Any]) -> list[str]:
    """Return the model's verbatim support quotes; deterministically required."""
    value = payload.get(rp.GROUNDING_FIELD)
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if entry not in (None, "") and str(entry).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def quality_report(*, raw_payload: dict[str, Any], record: dict[str, Any], profile: dict[str, Any], answer: str,
                   scoped_source_id: str, references: list[dict[str, Any]],
                   notebook_source_ids: dict[str, str]) -> dict[str, Any]:
    """Deterministic acceptance gate.  No AI decision is involved."""
    checks: dict[str, Any] = {}
    schema = profile["extraction_schema"]
    properties = schema["properties"]
    missing_fields = sorted(name for name in schema.get("required", []) if name not in raw_payload)
    wrong_type = sorted(
        name for name, spec in properties.items()
        if name in raw_payload and not _matches_type(raw_payload[name], spec)
    )
    checks["missing_schema_fields"] = missing_fields
    checks["schema_fields_present"] = not missing_fields
    checks["wrong_typed_fields"] = wrong_type
    checks["schema_types_valid"] = not wrong_type

    def meaningful(value: Any) -> bool:
        if isinstance(value, list):
            return any(str(item).strip().upper() not in _NON_INFORMATION_SENTINELS for item in value)
        return value not in (None, "", [], {}) and str(value).strip().upper() not in _NON_INFORMATION_SENTINELS

    for name, spec in sorted(properties.items()):
        value = record.get(name)
        checks[f"field:{name}"] = meaningful(value)
    empty = [name for name, spec in properties.items()
             if spec["type"] == "array" and not meaningful(record.get(name))]
    required_lists = profile["quality_checks"].get("min_non_empty_list_fields", [])
    required_fields = profile["quality_checks"].get("required_meaningful_fields", [])
    missing_required = [name for name in required_lists + required_fields if not meaningful(record.get(name))]
    checks["required_lists_present"] = not missing_required
    checks["required_meaningful_fields_present"] = not missing_required

    ratio = round(len(empty) / max(1, len(properties)), 4)
    checks["empty_ratio"] = ratio
    checks["empty_ratio_within_cap"] = ratio <= float(profile["quality_checks"].get("max_empty_ratio", 0.6))

    quotes = grounding_quotes(raw_payload)
    checks["grounding_quote_count"] = len(quotes)
    checks["grounding_quotes_present"] = len(quotes) >= 1
    markers = len(CITATION_PATTERN.findall(answer or ""))
    checks["inline_citation_marker_count"] = markers

    cited_source_ids = sorted({str(ref.get("source_id")) for ref in references if ref.get("source_id")})
    foreign = [sid for sid in cited_source_ids if sid != scoped_source_id]
    checks["scoped_source_id"] = scoped_source_id
    checks["cited_source_ids"] = cited_source_ids
    checks["cross_source_citations"] = foreign
    checks["contamination_free"] = not foreign

    failures: list[str] = []
    if missing_fields:
        failures.append("missing_required_fields:" + ",".join(missing_fields))
    if wrong_type:
        failures.append("wrong_typed_fields:" + ",".join(wrong_type))
    if missing_required:
        failures.append("required_list_fields_empty:" + ",".join(sorted(missing_required)))
    if not checks["empty_ratio_within_cap"]:
        failures.append(f"empty_ratio_exceeded:{ratio}")
    if not checks["grounding_quotes_present"]:
        failures.append("grounding_quotes_absent")
    if not checks["contamination_free"]:
        failures.append("cross_source_citations:" + ",".join(foreign))
    if not any(checks[f"field:{name}"] for name in properties):
        failures.append("no_populated_field")
    checks["grounding_quotes"] = quotes[:6]
    return {"passed": not failures, "checks": checks, "failures": failures}


@dataclass
class AdapterConfig:
    cli: str = field(default_factory=resolve_cli)
    profile: str = "default"
    lock_path: Path = ROOT / "state/notebooklm_research.lock"


class NotebookLMResearchAdapter:
    """The single NotebookLM processor used by every Research video claim."""

    def __init__(self, config: AdapterConfig | None = None) -> None:
        self.config = config or AdapterConfig()
        self.stats: dict[str, Any] = {"subprocesses": 0, "peak_background_shells": 0, "failures": []}
        self._read_operation_sequence = 0

    # -- process control ---------------------------------------------------

    @contextmanager
    def _job_slot(self) -> Iterator[None]:
        """Serialise NotebookLM work and never exceed the shell budget."""
        import fcntl

        self.config.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config.lock_path.open("w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            active = self.stats["peak_background_shells"]
            self.stats["peak_background_shells"] = max(active, MAX_BACKGROUND_SHELLS if MAX_BACKGROUND_SHELLS else 0)
            self.stats["active_jobs"] = self.stats.get("active_jobs", 0) + 1
            try:
                yield
            finally:
                self.stats["active_jobs"] = max(0, self.stats.get("active_jobs", 1) - 1)
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _run(self, args: list[str], *, stage: str, timeout: int | None = None,
             failure_code: str = "NOTEBOOK_ASK_FAILED") -> str:
        """Run one CLI invocation with a hard timeout and full child cleanup."""
        command = [self.config.cli, "-p", self.config.profile, *args]
        limit = timeout or STAGE_TIMEOUTS.get(stage, 180)
        self.stats["subprocesses"] = self.stats.get("subprocesses", 0) + 1

        def run_cli() -> subprocess.CompletedProcess[str]:
            started = time.monotonic()
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=limit,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
                setattr(completed, "_nexus_runtime_seconds", round(time.monotonic() - started, 3))
                return completed
            except subprocess.TimeoutExpired:
                self.stats["failures"].append({"stage": stage, "code": "TIMEOUT", "timeout_seconds": limit})
                raise NotebookLMError(
                    "NOTEBOOK_ASK_TIMEOUT" if stage == "ask" else "NOTEBOOK_SOURCE_INDEX_TIMEOUT",
                    f"{stage} exceeded hard timeout of {limit}s", stage=stage,
                ) from None
            except FileNotFoundError:
                self.stats["failures"].append({"stage": stage, "code": "CLI_MISSING"})
                raise NotebookLMError("NOTEBOOK_CLI_UNAVAILABLE", f"notebooklm CLI not found: {self.config.cli}",
                                      stage=stage) from None

        try:
            # The governed Research durable worker sets these values. Standalone
            # doctor/list utilities remain available outside the Research lane.
            if os.environ.get("NEXUS_DEPARTMENT", "").upper() == "RESEARCH":
                from nexus_agent_platform.provider_enforcement import execute, provider_scope_active
                if not provider_scope_active("NOTEBOOKLM", "research_discovery"):
                    job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
                    correlation_id = os.environ.get("NEXUS_CORRELATION_ID")
                    if not job_id or not correlation_id:
                        from nexus_agent_platform.resource_spend_governor import GovernanceDenied
                        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "DURABLE_RESEARCH_CONTEXT_REQUIRED")
                    _ensure_research_notebooklm_policy()
                    arg_bytes = len(json.dumps(args, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                    estimate = {"requests": 1, "operations": 1, "bytes": min(180000, max(8192, arg_bytes + 48000)),
                                "runtime_seconds": min(limit, 60), "billable": False, "cost": 0.0}
                    action_hash = hashlib.sha256(json.dumps(args, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()[:20]
                    purpose=f"notebooklm:{job_id}:{stage}:{action_hash}"
                    if stage in {"version","list","history","source_list","source_wait","ask","research_discover"}:
                        # Bounded reads and question submissions are retry-safe
                        # but must each remain separately accounted. Keep
                        # corpus mutations idempotency-protected.
                        self._read_operation_sequence += 1
                        attempt=os.environ.get("NEXUS_JOB_ATTEMPT_COUNT","0")
                        purpose += f":attempt:{attempt}:read:{self._read_operation_sequence}"
                    scoped_job_type=os.environ.get("NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE") or RESEARCH_GOVERNOR_JOB_TYPE
                    completed = execute("NOTEBOOKLM", "research_discovery", f"NOTEBOOKLM_{stage.upper()}", estimate,
                        run_cli, job_id=job_id, job_type=scoped_job_type,
                        project_id=os.environ.get("NEXUS_PROJECT_ID") or "NEXUS",
                        correlation_id=correlation_id,
                        purpose=purpose,
                        actual_usage=lambda result: {"requests": 1, "operations": 1,
                            "bytes": arg_bytes + len((result.stdout or "").encode("utf-8")) +
                                     len((result.stderr or "").encode("utf-8")),
                            "runtime_seconds": min(limit, float(getattr(result, "_nexus_runtime_seconds", 0))), "cost": 0.0})
                else:
                    completed = run_cli()
            else:
                completed = run_cli()
        except Exception:
            raise
        if completed.returncode != 0:
            combined = (completed.stderr or "") + "\n" + (completed.stdout or "")
            lowered = combined.lower()
            if any(token in lowered for token in ("not authenticated", "login", "401", "403", "unauthorized",
                                                  "auth expired", "storage_state")):
                raise NotebookLMError("NOTEBOOK_AUTH_FAILED", f"auth failure in {stage}: {combined[:300]}", stage=stage)
            self.stats["failures"].append({"stage": stage, "code": f"EXIT_{completed.returncode}"})
            raise NotebookLMError(failure_code, f"{stage} failed rc={completed.returncode}: {combined[:400]}",
                                  stage=stage)
        return completed.stdout or ""

    def _run_json(self, args: list[str], *, stage: str, timeout: int | None = None,
                  failure_code: str = "NOTEBOOK_ASK_FAILED") -> Any:
        stdout = self._run(args, stage=stage, timeout=timeout, failure_code=failure_code)
        try:
            return _json_from_stdout(stdout)
        except ValueError as exc:
            self.stats["failures"].append({"stage": stage, "code": "JSON_UNPARSEABLE"})
            raise NotebookLMError(failure_code, f"{stage} did not return JSON: {exc}", stage=stage) from None

    # -- capability probe --------------------------------------------------

    def cli_version(self) -> str:
        stdout = self._run(["--version"], stage="version", timeout=STAGE_TIMEOUTS["version"])
        return stdout.strip()

    def notebooks(self, *, timeout_seconds: int | None = None) -> list[dict[str, Any]]:
        payload = self._run_json(["list", "--json"], stage="list", timeout=timeout_seconds,
                                 failure_code="NOTEBOOK_AUTH_FAILED")
        return list(payload.get("notebooks", [])) if isinstance(payload, dict) else []

    def sources(self, notebook_id: str, *, timeout_seconds: int | None = None) -> list[dict[str, Any]]:
        payload = self._run_json(
            ["source", "list", "-n", notebook_id, "--json"],
            stage="source_list", timeout=timeout_seconds, failure_code="NOTEBOOK_SOURCE_ADD_FAILED",
        )
        return list(payload.get("sources", [])) if isinstance(payload, dict) else []

    # -- notebook pool -----------------------------------------------------

    def resolve_notebook(self, pool_id: str) -> dict[str, Any]:
        pool = rp.NOTEBOOK_POOLS.get(pool_id)
        if pool is None:
            raise NotebookLMError("NOTEBOOK_NOT_FOUND", f"unknown notebook pool: {pool_id}")
        notebooks = self.notebooks()
        for notebook in notebooks:
            if str(notebook.get("title")) == pool["title"]:
                return {"notebook_id": notebook["id"], "title": notebook["title"], "pool_id": pool_id,
                        "created": False, "max_sources": pool.get("max_sources", 30)}
        if not pool.get("create_if_missing"):
            raise NotebookLMError("NOTEBOOK_NOT_FOUND", f"pool notebook absent and creation disabled: {pool_id}")
        payload = self._run_json(["create", "--json", pool["title"]], stage="create",
                                 failure_code="NOTEBOOK_CREATE_FAILED")
        notebook = payload.get("notebook") if isinstance(payload, dict) else None
        notebook_id = (notebook or {}).get("id") or (payload.get("id") if isinstance(payload, dict) else None)
        if not notebook_id:
            raise NotebookLMError("NOTEBOOK_CREATE_FAILED", f"create did not return a notebook id for {pool_id}")
        return {"notebook_id": notebook_id, "title": pool["title"], "pool_id": pool_id, "created": True,
                "max_sources": pool.get("max_sources", 30)}

    def resolve_case_notebook(self, case_id: str, *, title: str, max_sources: int = 5,
                              timeout_seconds: int | None = None) -> dict[str, Any]:
        """Create or reuse one bounded NotebookLM workspace for a Research case."""
        token = re.sub(r"[^A-Za-z0-9_-]", "", str(case_id))[:32]
        if not token:
            raise NotebookLMError("NOTEBOOK_CREATE_FAILED", "research case id is required", stage="create")
        notebook_title = f"Nexus Research Case {token}"
        for notebook in self.notebooks(timeout_seconds=timeout_seconds):
            if str(notebook.get("title") or "") == notebook_title:
                return {"notebook_id": notebook["id"], "title": notebook_title,
                        "pool_id": "case:" + token, "created": False,
                        "max_sources": max(1, min(int(max_sources), 5)), "case_id": case_id}
        payload = self._run_json(["create", "--json", notebook_title], stage="create",
                                 failure_code="NOTEBOOK_CREATE_FAILED")
        notebook = payload.get("notebook") if isinstance(payload, dict) else None
        notebook_id = (notebook or {}).get("id") or (payload.get("id") if isinstance(payload, dict) else None)
        if not notebook_id:
            raise NotebookLMError("NOTEBOOK_CREATE_FAILED", "case workspace creation returned no notebook id", stage="create")
        return {"notebook_id": notebook_id, "title": notebook_title,
                "pool_id": "case:" + token, "created": True,
                "max_sources": max(1, min(int(max_sources), 5)), "case_id": case_id,
                "case_topic": str(title)[:240]}

    # -- source lifecycle --------------------------------------------------

    @staticmethod
    def video_id_of(url: str) -> str:
        for pattern in (r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})",
                        r"^([A-Za-z0-9_-]{11})$"):
            match = re.search(pattern, url or "")
            if match:
                return match.group(1)
        return hashlib.sha256((url or "").encode()).hexdigest()[:11]

    def find_existing_source(self, sources: list[dict[str, Any]], *, video_id: str, title: str) -> dict[str, Any] | None:
        for source in sources:
            if video_id and video_id in str(source.get("url") or ""):
                return source
        normalized = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
        if normalized:
            for source in sources:
                candidate = re.sub(r"[^a-z0-9]+", " ", str(source.get("title") or "").lower()).strip()
                if candidate and (candidate == normalized or candidate.startswith(normalized[:40])
                                  or normalized.startswith(candidate[:40])):
                    return source
        return None

    def add_source(self, notebook_id: str, url: str, *, video_title: str) -> dict[str, Any]:
        host = url.split("/", 3)[2].lower().removeprefix("www.").removeprefix("m.") if "://" in url else ""
        source_type = "youtube" if host in {"youtube.com", "youtu.be"} else "url"
        payload = self._run_json(
            ["source", "add", "-n", notebook_id, "--type", source_type, "--json", url],
            stage="source_add", failure_code="NOTEBOOK_SOURCE_ADD_FAILED",
        )
        source = payload.get("source") if isinstance(payload, dict) else None
        if not isinstance(source, dict) or not source.get("id"):
            raise NotebookLMError("NOTEBOOK_SOURCE_ADD_FAILED", f"source add returned no source id for {url}")
        return source

    def add_case_artifact_source(self, notebook_id: str, artifact_path: str | Path, *, title: str) -> dict[str, Any]:
        """Attach a bounded, repository-local generated case artifact as a NotebookLM file source."""
        path = Path(artifact_path).expanduser()
        resolved = path.resolve(strict=True)
        root = ROOT.resolve()
        if root not in resolved.parents or path.is_symlink():
            raise NotebookLMError("NOTEBOOK_SOURCE_ADD_FAILED", "case artifact must be a regular file inside the Nexus checkout")
        if resolved.suffix.lower() not in {".md", ".txt", ".json"} or not resolved.is_file():
            raise NotebookLMError("NOTEBOOK_SOURCE_ADD_FAILED", "case artifact must be a Markdown, text, or JSON file")
        if resolved.stat().st_size > 2_000_000:
            raise NotebookLMError("NOTEBOOK_SOURCE_ADD_FAILED", "case artifact exceeds the 2 MB ingestion bound")
        payload = self._run_json(
            ["source", "add", "-n", notebook_id, "--type", "file", "--title", str(title)[:180],
             "--json", str(resolved)],
            stage="source_add", failure_code="NOTEBOOK_SOURCE_ADD_FAILED",
        )
        source = payload.get("source") if isinstance(payload, dict) else None
        if not isinstance(source, dict) or not source.get("id"):
            raise NotebookLMError("NOTEBOOK_SOURCE_ADD_FAILED", "artifact upload returned no source id")
        ready = self.wait_for_source(notebook_id, str(source["id"]))
        return {**source, "index_status": ready.get("status"), "artifact_path": str(resolved),
                "artifact_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}

    def wait_for_source(self, notebook_id: str, source_id: str, *, timeout_seconds: int | None = None) -> dict[str, Any]:
        timeout_seconds = timeout_seconds or STAGE_TIMEOUTS["source_wait"]
        payload = self._run_json(
            ["source", "wait", source_id, "-n", notebook_id, "--json",
             "--timeout", str(timeout_seconds)],
            stage="source_wait", timeout=timeout_seconds + 30,
            failure_code="NOTEBOOK_SOURCE_INDEX_TIMEOUT",
        )
        status = str(payload.get("status", "")) if isinstance(payload, dict) else ""
        if status == "ready":
            return {"source_id": source_id, "status": status, "status_code": payload.get("status_code")}
        raise NotebookLMError("NOTEBOOK_SOURCE_INDEX_FAILED", f"source indexing ended in state {status!r}",
                              stage="source_index")

    def ask_source_scoped(self, notebook_id: str, source_id: str, prompt: str, *,
                          timeout_seconds: int | None = None) -> dict[str, Any]:
        """Ask inside NotebookLM's persisted, UI-visible current conversation.

        The selected source ID is the isolation boundary. The CLI's successful
        JSON ask response is the primary turn receipt: it contains the returned
        answer to this exact submitted prompt. Notebook history is an optional
        audit view; fetching the entire history must never gate case progress.
        """
        prompt_path = ROOT / "state/notebooklm_prompts" / f"{hashlib.sha256(prompt.encode()).hexdigest()[:16]}.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        try:
            payload = self._run_json(
                ["ask", "-n", notebook_id, "-s", source_id, "--json",
                 "--prompt-file", str(prompt_path)],
                stage="ask", timeout=timeout_seconds or STAGE_TIMEOUTS["ask"],
                failure_code="NOTEBOOK_ASK_FAILED",
            )
        finally:
            prompt_path.unlink(missing_ok=True)
        if not isinstance(payload, dict) or not payload.get("answer"):
            raise NotebookLMError("NOTEBOOK_ASK_FAILED", "ask returned no answer")
        return self._turn_receipt(notebook_id, prompt, payload)

    def ask_notebook(self, notebook_id: str, prompt: str) -> dict[str, Any]:
        """Ask across the sources in a case-scoped notebook for synthesis.

        Unlike ``ask_source_scoped``, this is intentionally multi-source. The
        caller must validate that returned citations belong to this notebook.
        """
        prompt_path = ROOT / "state/notebooklm_prompts" / f"{hashlib.sha256(prompt.encode()).hexdigest()[:16]}.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        try:
            payload = self._run_json(
                ["ask", "-n", notebook_id, "--json",
                 "--prompt-file", str(prompt_path)],
                stage="ask", timeout=STAGE_TIMEOUTS["ask"], failure_code="NOTEBOOK_ASK_FAILED",
            )
        finally:
            prompt_path.unlink(missing_ok=True)
        if not isinstance(payload, dict) or not payload.get("answer"):
            raise NotebookLMError("NOTEBOOK_ASK_FAILED", "notebook synthesis returned no answer")
        return self._turn_receipt(notebook_id, prompt, payload)

    @staticmethod
    def _turn_receipt(notebook_id: str, prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Correlate a real CLI ask response without a full-history read.

        `ask --json` returns only after the submitted prompt has been answered.
        The prompt digest, notebook id, returned conversation id (when supplied),
        response digest, timestamp, and complete response form a bounded durable
        receipt. A later history audit can enrich this receipt asynchronously.
        """
        answer = str(payload["answer"])
        conversation_id = payload.get("conversation_id") or payload.get("conversationId")
        response_id = (payload.get("response_id") or payload.get("responseId") or
                       payload.get("turn_id") or payload.get("turnId"))
        correlation = str(response_id or hashlib.sha256(
            f"{notebook_id}:{prompt}:{answer}:{utcnow()}".encode()).hexdigest()[:24])
        references = payload.get("references") or []
        return {"answer": answer, "notebook_id": notebook_id,
                "conversation_id": str(conversation_id) if conversation_id else None,
                "references": references if isinstance(references, list) else [],
                "turn_number": payload.get("turn_number") or payload.get("turn"),
                "submission_attempted": True, "submission_confirmed": True,
                "response_received": True,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "response_sha256": hashlib.sha256(answer.encode()).hexdigest(),
                "response_received_at": utcnow(),
                "response_reference": str(response_id or f"ask-json:{correlation}"),
                "correlation_id": correlation,
                "verification_method": "NOTEBOOKLM_ASK_JSON_RESPONSE",
                "history_audit_status": "DEFERRED_NON_BLOCKING"}

    def verify_visible_turn(self, notebook_id: str, question: str, answer: str) -> dict[str, Any]:
        """Optional bounded audit for a turn already verified by ask --json."""
        # JSON history already carries full answer bodies. --show-all forces a
        # second full rendering path in some CLI versions and can hang on long
        # case conversations. Keep the normal machine-readable response.
        payload = self._run_json(["history", "-n", notebook_id, "--json", "--limit", "4"],
                                 stage="history", timeout=STAGE_TIMEOUTS["history"],
                                 failure_code="NOTEBOOK_HISTORY_FAILED")
        pairs = payload.get("qa_pairs") if isinstance(payload, dict) else None
        normalize = lambda value: " ".join(str(value or "").split())
        wanted_q, wanted_a = normalize(question), normalize(answer)
        match = next((row for row in reversed(pairs or [])
                      if normalize(row.get("question")) == wanted_q
                      and normalize(row.get("answer")) == wanted_a), None)
        conversation_id = payload.get("conversation_id") if isinstance(payload, dict) else None
        if not match or not conversation_id:
            self.stats["failures"].append({"stage": "history", "code": "TURN_NOT_VISIBLE"})
            raise NotebookLMError("NOTEBOOK_RESPONSE_NOT_VISIBLE",
                                  "NotebookLM returned an answer but the exact Q&A turn was absent from persisted notebook history",
                                  stage="history")
        return {"conversation_id": str(conversation_id),
                "turn_number": match.get("turn") or len(pairs or []),
                "history_count": len(pairs or [])}

    def check_profile_fit(self, notebook_id: str, source_id: str, candidate_profile_id: str,
                          *, video_title: str) -> dict[str, Any]:
        """Run the source-scoped preflight before any extraction contract."""
        prompt = rp.build_profile_fit_prompt(candidate_profile_id, video_title=video_title)
        ask = self.ask_source_scoped(notebook_id, source_id, prompt)
        references = ask.get("references") or []
        foreign = {str(row.get("source_id")) for row in references
                   if row.get("source_id") and str(row.get("source_id")) != source_id}
        if foreign:
            raise NotebookLMError("NOTEBOOK_SOURCE_CONTAMINATION",
                                  "profile-fit response cited a source outside its explicit source scope",
                                  stage="profile_fit")
        try:
            decision = interpret_profile_fit(extract_json_object(ask["answer"]), candidate_profile_id)
        except (ValueError, TypeError) as exc:
            raise NotebookLMError("NOTEBOOK_PROFILE_FIT_INVALID", str(exc), stage="profile_fit") from None
        decision["conversation_id"] = ask["conversation_id"]
        return decision

    def classify_trading_subtype(self, notebook_id: str, source_id: str, *, video_title: str,
                                 video_description: str = "") -> dict[str, Any]:
        prompt = rp.build_trading_subtype_classification_prompt(
            video_title=video_title, video_description=video_description)
        ask = self.ask_source_scoped(notebook_id, source_id, prompt)
        if any(str(row.get("source_id")) != source_id for row in ask.get("references", [])
               if row.get("source_id")):
            raise NotebookLMError("NOTEBOOK_SOURCE_CONTAMINATION", "subtype classifier cited a foreign source")
        try:
            result = interpret_trading_subtype(extract_json_object(ask["answer"]))
        except (ValueError, TypeError) as exc:
            raise NotebookLMError("NOTEBOOK_JSON_INVALID", f"invalid Trading subtype classification: {exc}") from None
        result["conversation_id"] = ask["conversation_id"]
        return result

    def _source_for_profile(self, *, profile_id: str, video_url: str, video_id: str,
                            video_title: str, research_case_id: str | None = None) -> tuple[dict[str, Any], str, str, dict[str, str], bool]:
        """Resolve/dedupe/index this video in its case workspace or legacy pool."""
        pool = rp.pool_for(profile_id)
        notebook = (self.resolve_case_notebook(research_case_id, title=video_title)
                    if research_case_id else self.resolve_notebook(pool["pool_id"]))
        sources = self.sources(notebook["notebook_id"])
        notebook_source_ids = {str(row["id"]): str(row.get("title", ""))
                               for row in sources if row.get("id")}
        existing = self.find_existing_source(sources, video_id=video_id, title=video_title)
        added = existing is None
        if existing is not None:
            source_id = str(existing["id"])
        else:
            if len(sources) >= int(notebook.get("max_sources") or 30):
                raise NotebookLMError(
                    "NOTEBOOK_SOURCE_POOL_FULL",
                    f"pool {pool['pool_id']} holds {len(sources)} sources at cap {notebook['max_sources']}",
                )
            source = self.add_source(notebook["notebook_id"], video_url, video_title=video_title)
            source_id = str(source["id"])
            notebook_source_ids[source_id] = str(source.get("title") or video_title)
        indexed = self.wait_for_source(notebook["notebook_id"], source_id)
        source_title = str(indexed.get("title") or notebook_source_ids.get(source_id) or video_title)
        return notebook, source_id, source_title, notebook_source_ids, added

    # -- top-level ---------------------------------------------------------

    def process_video(self, *, video_url: str, research_profile_id: str, video_title: str = "",
                      video_description: str = "", channel: str = "",
                      observed_at: str | None = None, research_case_id: str | None = None) -> dict[str, Any]:
        if not research_case_id and os.environ.get("NEXUS_NOTEBOOK_LEGACY_DIAGNOSTIC") != "1":
            raise NotebookLMError("RESEARCH_CASE_REQUIRED",
                                  "Production NotebookLM work requires a durable research_case_id; legacy profile-pool access is diagnostic-only.",
                                  stage="notebook_resolve")
        started = time.monotonic()
        initial_profile_id = research_profile_id
        video_id = self.video_id_of(video_url)
        provenance: dict[str, Any] = {
            "adapter": "notebooklm_research_adapter",
            "adapter_version": "1.0.0",
            "notebooklm_profile": self.config.profile,
            "profile_digest": rp.profile_digest(),
            "research_profile_id": research_profile_id,
            "video_id": video_id,
            "video_url": video_url,
            "video_title": video_title,
            "channel": channel,
            "research_case_id": research_case_id,
            "observed_at": observed_at or utcnow(),
        }
        fit_history: list[dict[str, Any]] = []
        visited: set[str] = set()
        with self._job_slot():
            candidate_id = initial_profile_id
            for _ in range(min(MAX_PROFILE_FIT_CANDIDATES, len(rp.PROFILES))):
                if candidate_id in visited:
                    candidate_id = next_profile_candidate(None, visited) or ""
                if not candidate_id or candidate_id in visited:
                    break
                visited.add(candidate_id)
                profile = rp.get_profile(candidate_id)
                pool = rp.pool_for(candidate_id)
                notebook, source_id, source_title, notebook_source_ids, source_added = self._source_for_profile(
                    profile_id=candidate_id, video_url=video_url, video_id=video_id, video_title=video_title,
                    research_case_id=research_case_id,
                )
                fit = self.check_profile_fit(notebook["notebook_id"], source_id, candidate_id,
                                             video_title=source_title)
                fit_history.append({
                    "profile_id": candidate_id,
                    "decision": fit["decision"],
                    "suggested_profile_id": fit.get("suggested_profile_id"),
                    "reason": fit.get("reason"),
                    "evidence_quotes": fit.get("evidence_quotes", []),
                    "conversation_id": fit.get("conversation_id"),
                    "notebook_id": notebook["notebook_id"],
                    "source_id": source_id,
                    "source_added": source_added,
                })
                if fit["decision"] == "PROFILE_FIT":
                    break
                suggested = fit.get("suggested_profile_id")
                candidate_id = next_profile_candidate(suggested, visited) or ""
            else:
                candidate_id = ""

            if not fit_history or fit_history[-1]["decision"] != "PROFILE_FIT":
                provenance["profile_fit_history"] = fit_history
                provenance["elapsed_seconds"] = round(time.monotonic() - started, 3)
                return {"status": "PROFILE_MISMATCH", "routing_status": "PROFILE_MISMATCH",
                        "research_profile_id": initial_profile_id,
                        "profile_fit_history": fit_history, "provenance": provenance}

            selected_profile_id = fit_history[-1]["profile_id"]
            profile = rp.get_profile(selected_profile_id)
            pool = rp.pool_for(selected_profile_id)
            if research_case_id:
                pool = {**pool, "pool_id": "case:" + re.sub(r"[^A-Za-z0-9_-]", "", str(research_case_id))[:32],
                        "title": notebook.get("title")}
            provenance["initial_profile_id"] = initial_profile_id
            provenance["research_profile_id"] = selected_profile_id
            provenance["profile_reclassified"] = selected_profile_id != initial_profile_id
            provenance["profile_fit_history"] = fit_history
            provenance["notebook_id"] = notebook["notebook_id"]
            provenance["notebook_title"] = notebook["title"]
            provenance["notebook_pool"] = pool["pool_id"]
            provenance["notebook_created"] = notebook["created"]
            provenance["notebook_scope"] = "RESEARCH_CASE" if research_case_id else "PROFILE_POOL_LEGACY"
            provenance["source_id"] = source_id
            provenance["source_title"] = source_title
            provenance["source_status"] = "ready"
            provenance["source_added"] = source_added
            provenance["source_dedupe"] = "added_new" if source_added else "existing_source_reused"
            provenance["source_indexed_at"] = utcnow()

            top_level_profile = (rp.TRADING_PARENT_PROFILE if selected_profile_id in rp.TRADING_PROFILE_IDS
                                 else selected_profile_id)
            subtype_info: dict[str, Any] = {}
            if selected_profile_id in rp.TRADING_PROFILE_IDS:
                subtype_info = self.classify_trading_subtype(
                    notebook["notebook_id"], source_id, video_title=source_title,
                    video_description=video_description)
                subtype = subtype_info["trading_subtype"]
                active_contract = rp.trading_contract(subtype)
                prompt = rp.build_trading_subtype_prompt(subtype=subtype, video_title=source_title)
                provenance.update({
                    "top_level_profile": top_level_profile,
                    "trading_subtype": subtype,
                    "content_mode": subtype_info["content_mode"],
                    "question_contract_id": f"trading.{subtype}.v1",
                    "subtype_classification": subtype_info,
                    "secondary_signals": subtype_info["secondary_signals"],
                    "subtype_classifier_conversation_id": subtype_info.get("conversation_id"),
                })
            else:
                active_contract = profile
                prompt = rp.build_prompt(profile, video_title=source_title)
                provenance.update({"top_level_profile": top_level_profile, "trading_subtype": None,
                                   "content_mode": None, "question_contract_id": selected_profile_id,
                                   "secondary_signals": []})
            provenance["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
            provenance["prompt_profile"] = active_contract["profile_id"]
            provenance["profile_digest"] = rp.profile_digest(active_contract)
            ask = self.ask_source_scoped(notebook["notebook_id"], source_id, prompt)
            provenance["conversation_id"] = ask["conversation_id"]
            provenance["source_scope_method"] = "CLI_SOURCE_ID"

        try:
            record = extract_json_object(ask["answer"])
        except ValueError as exc:
            provenance["elapsed_seconds"] = round(time.monotonic() - started, 3)
            return self._failure("NOTEBOOK_JSON_INVALID", str(exc), provenance)

        normalized = normalize_payload(record, active_contract["extraction_schema"])
        provenance["raw_field_count"] = len(record)
        provenance["citation_count"] = len(CITATION_PATTERN.findall(ask["answer"]))

        try:
            validated = json.loads(json.dumps(normalized))
        except (TypeError, ValueError) as exc:
            provenance["elapsed_seconds"] = round(time.monotonic() - started, 3)
            return self._failure("NOTEBOOK_JSON_INVALID", f"payload not serialisable: {exc}", provenance)

        quality = quality_report(raw_payload=record, record=validated, profile=active_contract, answer=ask["answer"],
                                 scoped_source_id=source_id, references=ask["references"],
                                 notebook_source_ids=notebook_source_ids)
        provenance["quality"] = quality
        provenance["elapsed_seconds"] = round(time.monotonic() - started, 3)

        if not quality["checks"]["contamination_free"]:
            return self._failure("NOTEBOOK_SOURCE_CONTAMINATION", "cited sources outside the scoped source",
                                 provenance)
        if not quality["passed"]:
            return self._failure("NOTEBOOK_QUALITY_CHECK_FAILED", "; ".join(quality["failures"]), provenance)

        findings = [f"{name}: {value}" for name, value in sorted(validated.items()) if value not in (None, [], {}, "")]
        return {
            "status": "EXTRACTED",
            "research_profile_id": selected_profile_id,
            "top_level_profile": top_level_profile,
            "trading_subtype": subtype_info.get("trading_subtype"),
            "content_mode": subtype_info.get("content_mode"),
            "question_contract_id": provenance.get("question_contract_id"),
            "secondary_signals": subtype_info.get("secondary_signals", []),
            "notebook_pool": pool["pool_id"],
            "video_id": video_id,
            "video_url": video_url,
            "record": validated,
            "summary": validated.get("timeframe") or validated.get("topic_summary") or validated.get("setup_description")
                      or "; ".join(findings[:2]) or video_title or video_id,
            "key_findings": findings,
            "evidence": [provenance["source_title"] or video_title or video_id, provenance.get("source_id")],
            "target_departments": profile["target_departments"],
            "provenance": provenance,
            "quality": quality,
        }

    def _failure(self, failure_code: str, message: str, provenance: dict[str, Any]) -> dict[str, Any]:
        plan = failure_plan(failure_code)
        self.stats["failures"].append({"stage": plan["stage"], "code": failure_code, "detail": message[:300]})
        return {
            "status": "FAILED",
            "failure_code": failure_code,
            "failure_stage": plan["stage"],
            "retry_policy": plan["retry"],
            "max_attempts": plan["max_attempts"],
            "error": message[:500],
            "provenance": provenance,
        }


_DEFAULT_ADAPTER: NotebookLMResearchAdapter | None = None


def get_adapter() -> NotebookLMResearchAdapter:
    global _DEFAULT_ADAPTER
    if _DEFAULT_ADAPTER is None:
        _DEFAULT_ADAPTER = NotebookLMResearchAdapter()
    return _DEFAULT_ADAPTER


def process_youtube_for_research(*, video_url: str, title: str = "", description: str = "",
                                 channel: str = "", research_profile_id: str | None = None,
                                 adapter: NotebookLMResearchAdapter | None = None,
                                 research_case_id: str | None = None) -> dict[str, Any]:
    """Classify then extract.  Continuation decisions stay with the caller."""
    classification = rp.classify_profile(title=title, description=description, channel=channel,
                                         override=research_profile_id)
    active = adapter or get_adapter()
    outcome = active.process_video(video_url=video_url, research_profile_id=classification["profile_id"],
                                   video_title=title, video_description=description, channel=channel,
                                   research_case_id=research_case_id)
    selected = outcome.get("research_profile_id") or classification["profile_id"]
    outcome["classification"] = {
        **classification,
        "initial_profile_id": classification["profile_id"],
        "profile_id": selected,
        "selected_profile_id": selected,
        "reclassified": selected != classification["profile_id"],
        "profile_fit_history": outcome.get("profile_fit_history") or
                              (outcome.get("provenance") or {}).get("profile_fit_history", []),
    }
    return outcome


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NotebookLM Research adapter probe")
    parser.add_argument("--version")
    parser.add_argument("--url")
    parser.add_argument("--title", default="")
    parser.add_argument("--channel", default="")
    parser.add_argument("--profile-id")
    parser.add_argument("--research-case-id")
    parser.add_argument("--legacy-diagnostic", action="store_true",
                        help="Explicitly allow legacy profile-pool compatibility for migration or manual diagnostics only")
    args = parser.parse_args()

    cli = NotebookLMResearchAdapter()
    if args.version:
        print(json.dumps({"cli_version": cli.cli_version(), "notebooks": len(cli.notebooks())}, indent=2))
        raise SystemExit(0)
    if args.url:
        if not args.research_case_id and not args.legacy_diagnostic:
            parser.error("--research-case-id is required unless --legacy-diagnostic is explicit")
        if args.legacy_diagnostic:
            os.environ["NEXUS_NOTEBOOK_LEGACY_DIAGNOSTIC"] = "1"
        print(json.dumps(process_youtube_for_research(video_url=args.url, title=args.title, channel=args.channel,
                                                      research_profile_id=args.profile_id, adapter=cli,
                                                      research_case_id=args.research_case_id),
                         indent=2, default=str))
        raise SystemExit(0)
    parser.print_help()
