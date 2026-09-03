"""Governed Mac-to-Oracle Hermes 0.20.6 transport.

This adapter owns transport only.  The remote command is fixed, the prompt is
carried on stdin, and no user text is interpolated into a shell command.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any


ORACLE_HOST = os.getenv("NEXUS_ORACLE_SSH_HOST", "161.153.40.41")
ORACLE_USER = os.getenv("NEXUS_ORACLE_SSH_USER", "opc")
ORACLE_KEY = os.path.expanduser(os.getenv("NEXUS_ORACLE_SSH_KEY", "~/.ssh/oracle_vm"))
ORACLE_CONTAINER = "nexus-hermes-0206"
ORACLE_HERMES = "/opt/hermes/.venv/bin/hermes"
ORACLE_HOME = "/opt/data/profiles/nova_nexus"
ORACLE_MODEL = "openai/gpt-4o-mini"
ORACLE_PROFILE = "nova_nexus"
ORACLE_TOOLSET = "nexus_mcp_remote"
SESSION_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


class OracleHermesUnavailable(RuntimeError):
    """Raised when the bounded Oracle transport cannot return a response."""


@dataclass(frozen=True)
class OracleHermesResult:
    response: str | None
    status: str
    error: str | None
    latency_ms: float
    runtime_host: str = "ORACLE"
    hermes_version: str = "0.20.6"
    profile: str = ORACLE_PROFILE
    provider: str = "openrouter"
    model: str = ORACLE_MODEL
    toolset: str = ORACLE_TOOLSET
    recovery: str = "NONE"


def _remote_command(toolset: str = ORACLE_TOOLSET) -> str:
    # This is intentionally constant: only the prompt travels over stdin.
    return (
        "podman exec -i nexus-hermes-0206 sh -lc "
        "'IFS= read -r session; prompt=$(cat); exec env HERMES_HOME=/opt/data/profiles/nova_nexus "
        "HERMES_PROFILE=nova_nexus /opt/hermes/.venv/bin/hermes "
        f"-z \"$prompt\" -m openai/gpt-4o-mini -t {toolset} "
        "--resume \"$session\" --pass-session-id --no-restore-cwd'"
    )


def _executive_prompt(message: str) -> str:
    """Carry the bounded executive contract across the Oracle process boundary."""
    lowered = message.casefold()
    strategic = any(term in lowered for term in ("should", "recommend", "opportunity", "focus", "what next", "what should happen", "compare"))
    if not strategic:
        return message
    priority_rules = ""
    if any(term in lowered for term in ("focus on today", "focus today", "prioritize today", "what should nexus focus")):
        priority_rules = (
            " This is a PRIORITY_REQUEST, not a status request: choose exactly one primary company focus "
            "from the current parent goals/objectives and unfinished work, rank it by business impact, "
            "customer/economic value, dependency, urgency, and evidence confidence, and explain why it "
            "comes first. Do not substitute a list of telemetry, available departments, opportunity counts, "
            "or runtime metadata. Mention a system issue only if it materially blocks the selected company "
            "outcome. State what Nexus will do next and what, if anything, Ray must decide."
        )
    pricing_rules = ""
    if any(term in lowered for term in ("$97", "pricing", "readiness assessment", "make it free")):
        pricing_rules = (
            " This is a DECISION_REQUEST about GoClear monetization: treat $97 as an unvalidated hypothesis. "
            "Do not use degraded telemetry, runtime health, model/provider status, or absence of clients as "
            "direct pricing evidence unless you establish a specific causal mechanism. Distinguish known "
            "facts, missing market/customer evidence, and judgment. Give a provisional recommendation only, "
            "include meaningful alternatives such as free basic assessment plus paid plan or low-cost entry, "
            "and keep the parent decision open. Safe internal Research, Alpha, Finance, Marketing, Clyde, "
            "and Opportunity follow-up is Nexus-owned: route it and tell Ray what Nexus is doing; do not ask "
            "whether Ray wants that internal research started."
        )
    return (
        "[NOVA EXECUTIVE REQUEST CONTRACT]\n"
        "Answer the user's parent question directly. For a strategic request, identify the parent decision, "
        "use only materially relevant current Nexus state/specialists, separate evidence from judgment and unknowns, "
        "compare disagreement when present, make one recommendation, and name one bounded next action. "
        "Do not call the same tool repeatedly; if a tool fails or returns no progress, synthesize from available evidence "
        "or state the exact unknown. A task/report/specialist response is not parent-goal completion.\n"
        + priority_rules + pricing_rules + "\n"
        "USER REQUEST:\n" + message[:7000]
    )


def _judgment_needs_correction(message: str, response: str) -> bool:
    """Detect two known judgment regressions without judging ordinary prose."""
    lowered = message.casefold()
    answer = response.casefold()
    if "focus on today" in lowered or "what should nexus focus" in lowered:
        # Priority answers receive one bounded editor pass. This avoids
        # relying on fragile phrase detection when a model has already
        # wrapped a status dump in an apparently executive heading.
        return True
    if any(term in lowered for term in ("$97", "pricing", "readiness assessment", "make it free")):
        return True
    return False


def _judgment_correction_prompt(message: str, response: str) -> str:
    lowered = message.casefold()
    if "focus on today" in lowered or "what should nexus focus" in lowered:
        instruction = (
            "Rewrite this as an executive PRIORITY answer. Select one actual company/objective focus, "
            "why it ranks first by outcome/impact/dependency/urgency, what outcome it advances, and what "
            "Nexus will do next. Do not make degraded telemetry, runtime status, department availability, "
            "or a pending approval the priority unless it directly blocks that selected outcome. Do not ask "
            "Ray to approve safe internal work; name a Ray decision only if an existing external boundary "
            "truly requires one. Answer directly and concisely."
        )
    else:
        instruction = (
            "Rewrite this as a careful GoClear pricing judgment. Do not use degraded telemetry, runtime "
            "health, or zero/missing clients as direct pricing evidence. State that $97 is unvalidated, "
            "separate known facts from unknown market evidence, give a provisional recommendation and a "
            "meaningful alternative, and keep the parent decision open. Route safe internal Research, Alpha, "
            "Finance, Marketing, Clyde, and Opportunity follow-up automatically; do not ask Ray whether to "
            "start it. State Ray's next action as none unless an external approval is actually needed."
        )
    return (
        "The draft below answered with an evidence or ownership error. " + instruction +
        "\nOriginal request: " + message[:5000] + "\nDraft to correct:\n" + response[:6000]
    )


def run_oracle_hermes(message: str, session_id: str, *, timeout_seconds: float = 180.0,
                      request_id: str | None = None) -> OracleHermesResult:
    if not isinstance(message, str) or not message.strip():
        raise OracleHermesUnavailable("empty_message")
    if not SESSION_RE.fullmatch(session_id or ""):
        raise OracleHermesUnavailable("invalid_session_id")
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise OracleHermesUnavailable("invalid_timeout")
    if not os.path.isfile(ORACLE_KEY) or not os.access(ORACLE_KEY, os.R_OK):
        return OracleHermesResult(None, "UNAVAILABLE", "ssh_key_missing", 0.0)
    started = time.monotonic()
    def invoke(prompt: str, toolset: str) -> tuple[subprocess.CompletedProcess[str], float]:
        command = [
            "/usr/bin/ssh", "-i", ORACLE_KEY, "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=2", "-o", "StrictHostKeyChecking=accept-new",
            f"{ORACLE_USER}@{ORACLE_HOST}", _remote_command(toolset),
        ]
        started = time.monotonic()
        completed = subprocess.run(
            command, input=f"{session_id}\n{prompt}", text=True, capture_output=True,
            timeout=timeout_seconds, check=False,
        )
        return completed, round((time.monotonic() - started) * 1000, 1)
    try:
        completed, elapsed = invoke(_executive_prompt(message), ORACLE_TOOLSET)
    except subprocess.TimeoutExpired:
        return OracleHermesResult(None, "UNAVAILABLE", "oracle_timeout", round((time.monotonic() - started) * 1000, 1))
    except OSError as exc:
        return OracleHermesResult(None, "UNAVAILABLE", type(exc).__name__, round((time.monotonic() - started) * 1000, 1))
    if completed.returncode != 0:
        return OracleHermesResult(None, "UNAVAILABLE", f"ssh_exit_{completed.returncode}", elapsed)
    response = completed.stdout.strip()
    if not response:
        return OracleHermesResult(None, "UNAVAILABLE", "empty_oracle_response", elapsed)
    halt = any(marker in response.lower() for marker in ("same_tool_failure_halt", "tool-call guardrail", "non-progressing attempts"))
    if halt:
        recovery_prompt = (
            "The previous method failed or stopped making progress while answering this request. "
            "Do not call the failed Nexus tool again in this recovery turn. Preserve any evidence "
            "already returned, distinguish known facts from unknowns, and answer the original request "
            "with a conditional recommendation or honest limitation. Original request: " + message[:5000]
        )
        try:
            recovered, recovery_elapsed = invoke(recovery_prompt, "skills")
        except subprocess.TimeoutExpired:
            return OracleHermesResult(None, "UNAVAILABLE", "oracle_recovery_timeout", elapsed, recovery="RECOVERY_TIMEOUT")
        if recovered.returncode == 0 and recovered.stdout.strip():
            recovered_text = recovered.stdout.strip()
            if not any(marker in recovered_text.lower() for marker in ("same_tool_failure_halt", "tool-call guardrail", "non-progressing attempts")):
                return OracleHermesResult(recovered_text, "SUCCEEDED", None, round(elapsed + recovery_elapsed, 1), recovery="SYNTHESIS_AFTER_TOOL_HALT")
        return OracleHermesResult(response, "SUCCEEDED", None, round(elapsed + recovery_elapsed, 1), recovery="RECOVERY_UNUSABLE")
    if _judgment_needs_correction(message, response):
        try:
            corrected, correction_elapsed = invoke(_judgment_correction_prompt(message, response), "skills")
        except subprocess.TimeoutExpired:
            return OracleHermesResult(response, "SUCCEEDED", None, elapsed, recovery="JUDGMENT_CORRECTION_TIMEOUT")
        if corrected.returncode == 0 and corrected.stdout.strip():
            corrected_text = corrected.stdout.strip()
            if not any(marker in corrected_text.casefold() for marker in ("same_tool_failure_halt", "tool-call guardrail", "non-progressing attempts")):
                return OracleHermesResult(corrected_text, "SUCCEEDED", None, round(elapsed + correction_elapsed, 1), recovery="JUDGMENT_CORRECTION")
    return OracleHermesResult(response, "SUCCEEDED", None, elapsed)
