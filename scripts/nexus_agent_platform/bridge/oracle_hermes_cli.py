"""Governed Mac-to-Oracle Hermes 0.20.6 transport.

This adapter owns transport only.  The remote command is fixed, the prompt is
carried on stdin, and no user text is interpolated into a shell command.
"""
from __future__ import annotations

import os
import re
import json
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
    try:
        from nova.executive_intelligence import is_casual_conversation, is_executive_attention_request, is_monetization_decision, is_opinion_request, is_priority_request
    except ModuleNotFoundError:
        from executive_intelligence import is_casual_conversation, is_executive_attention_request, is_monetization_decision, is_opinion_request, is_priority_request
    opinion = is_opinion_request(lowered)
    current_research = bool("research" in lowered and re.search(r"\b(still|running|active|heartbeat|scheduler|processing|status|doing)\b", lowered))
    priority = is_priority_request(lowered)
    attention = is_executive_attention_request(lowered)
    monetization = is_monetization_decision(lowered)
    strategic = opinion or current_research or priority or attention or monetization or any(term in lowered for term in ("should", "recommend", "opportunity", "what next", "what should happen", "compare"))
    if not strategic:
        # Keep casual conversation lightweight while carrying Nova's identity.
        if is_casual_conversation(lowered):
            return (
                "[NOVA LIGHT CONVERSATION]\n"
                "You are Hermes Nova, Ray Davis's conversational partner and executive interface to Nexus. "
                "Answer naturally and briefly in your own voice. You know Nexus is being built as an autonomous "
                "operating-company system with Research/Alpha, specialized departments, GoClear, and durable work. "
                "Do not turn a casual exchange into a report, use tools, or invent live facts.\n"
                "USER REQUEST:\n" + message[:3000]
            )
        return message
    priority_rules = ""
    if priority:
        priority_context = _bounded_priority_context()
        priority_rules = (
            " This is a PRIORITY_REQUEST, not a status request: choose exactly one primary company focus "
            "from the current parent goals/objectives and unfinished work, rank it by business impact, "
            "customer/economic value, dependency, urgency, and evidence confidence, and explain why it "
            "comes first. Do not substitute a list of telemetry, available departments, opportunity counts, "
            "or runtime metadata. Mention a system issue only if it materially blocks the selected company "
            "outcome. State what Nexus will do next and what, if anything, Ray must decide. "
            "Use the bounded objective context below; if it is stale or insufficient, say so rather than "
            "inventing a priority. Do not make generic system-health repair the company priority unless the "
            "context shows it directly blocks the selected outcome.\n"
            "BOUNDED PRIORITY CONTEXT:\n" + priority_context
        )
    attention_rules = ""
    if attention:
        attention_rules = (
            " This is an EXECUTIVE_ATTENTION_REQUEST. Interpret current Ray-owned review/approval state and "
            "answer what needs Ray, why now, the risk, your recommendation, the exact decision, and what happens "
            "if Ray does nothing. Do not expose approval IDs, condition keys, request metadata, timestamps, or "
            "filesystem paths unless Ray explicitly asks for diagnostics."
        )
    pricing_rules = ""
    if monetization:
        pricing_rules = (
            " This is a DECISION_REQUEST about GoClear monetization: treat $97 as an unvalidated hypothesis. "
            "Do not use degraded telemetry, runtime health, model/provider status, or absence of clients as "
            "direct pricing evidence unless you establish a specific causal mechanism. Distinguish known "
            "facts, missing market/customer evidence, and judgment. Give a provisional recommendation only, "
            "include meaningful alternatives such as free basic assessment plus paid plan or low-cost entry, "
            "and keep the parent decision open. Safe internal Research, Alpha, Finance, Marketing, Clyde, "
            "and Opportunity follow-up is Nexus-owned: route it and tell Ray what Nexus is doing; do not ask "
            "whether Ray wants that internal research started. No active clients only means no observed "
            "launch/customer sample; it is not evidence that willingness to pay is weak. Material market claims "
            "must name a current evidence/source reference from this turn; do not use vague phrases such as "
            "'market discussions' or 'previous analyses suggest' without traceable support. If verified "
            "competitor, customer, conversion, fulfillment-cost, or LTV evidence is absent, say so plainly."
        )
    opinion_rules = ""
    if opinion:
        opinion_rules = (
            " This is an OPINION_CONVERSATION. Answer naturally in Nova's own voice, grounded in the durable "
            "Nexus context: the autonomous company operating model, Research/Alpha intelligence core, "
            "Hermes executive interface, departments, GoClear commercial engine, economic engine, Trading "
            "laboratory, and Ray's shift from manually driving every task toward approving Nexus-created "
            "programs. Do not invoke specialists or produce a report; do not invent a current metric."
        )
    state_rules = ""
    if current_research:
        state_rules = (
            " This is a CURRENT_STATE_REQUEST. Answer the specific Research question by distinguishing "
            "heartbeat alive, scheduler enabled, process configured, dry-run mode, actual task processing, "
            "and recent activity. Do not collapse these states into a single running/not-running claim; use "
            "a fresh authoritative Nexus read and state unknowns plainly."
        )
    return (
        "[NOVA EXECUTIVE REQUEST CONTRACT]\n"
        "Answer the user's parent question directly. For a strategic request, identify the parent decision, "
        "use only materially relevant current Nexus state/specialists, separate evidence from judgment and unknowns, "
        "compare disagreement when present, make one recommendation, and name one bounded next action. "
        "Do not call the same tool repeatedly; if a tool fails or returns no progress, synthesize from available evidence "
        "or state the exact unknown. A task/report/specialist response is not parent-goal completion.\n"
        + priority_rules + attention_rules + pricing_rules + opinion_rules + state_rules + "\n"
        "USER REQUEST:\n" + message[:7000]
    )


def _judgment_needs_correction(message: str, response: str) -> bool:
    """Detect two known judgment regressions without judging ordinary prose."""
    lowered = message.casefold()
    answer = response.casefold()
    try:
        from nova.executive_intelligence import is_priority_request
    except ModuleNotFoundError:
        from executive_intelligence import is_priority_request
    if is_priority_request(lowered):
        # Priority answers receive one bounded editor pass. This avoids
        # relying on fragile phrase detection when a model has already
        # wrapped a status dump in an apparently executive heading.
        return True
    try:
        from nova.executive_intelligence import is_monetization_decision
    except ModuleNotFoundError:
        from executive_intelligence import is_monetization_decision
    if is_monetization_decision(lowered):
        return True
    return False


def _bounded_priority_context() -> str:
    """Return existing objective context small enough for an executive turn."""
    try:
        from nexus_agent_platform.nova_company_context import build_company_context
        context = build_company_context()
        payload = {
            "freshness": context.get("freshness"),
            "current_status": context.get("current_status"),
            "business": context.get("business"),
            "active_work": [
                {k: row.get(k) for k in ("title", "status", "objective_id", "next_action") if k in row}
                for row in (context.get("active_work") or [])[:8] if isinstance(row, dict)
            ],
            "recommended_priorities": (context.get("recommended_priorities") or [])[:5],
            "source_count": len(context.get("sources") or []),
        }
        return json.dumps(payload, ensure_ascii=False, default=str)[:7000]
    except Exception as exc:
        return json.dumps({"status": "UNAVAILABLE", "reason": type(exc).__name__})


def _judgment_correction_prompt(message: str, response: str) -> str:
    lowered = message.casefold()
    try:
        from nova.executive_intelligence import is_priority_request
    except ModuleNotFoundError:
        from executive_intelligence import is_priority_request
    if is_priority_request(lowered):
        instruction = (
            "Rewrite this as an executive PRIORITY answer. Select one actual company/objective focus, "
            "why it ranks first by outcome/impact/dependency/urgency, what outcome it advances, and what "
            "Nexus will do next. Do not make degraded telemetry, runtime status, department availability, "
            "or a pending approval the priority unless it directly blocks that selected outcome. Do not ask "
            "Ray to approve safe internal work; name a Ray decision only if an existing external boundary "
            "truly requires one. Do not infer customer impact or urgency from degraded telemetry alone. "
            "Use this bounded objective context when selecting the focus:\n" + _bounded_priority_context() +
            "\nAnswer directly and concisely."
        )
    else:
        instruction = (
            "Rewrite this as a careful GoClear pricing judgment. Do not use degraded telemetry, runtime "
            "health, or zero/missing clients as direct pricing evidence. State that $97 is unvalidated, "
            "separate known facts from unknown market evidence, give a provisional recommendation and a "
            "meaningful alternative, and keep the parent decision open. Do not lean toward free or paid as "
            "a validated conclusion when the relevant evidence is absent; recommend a bounded comparison/test "
            "or research program instead. Route safe internal Research, Alpha, "
            "Finance, Marketing, Clyde, and Opportunity follow-up automatically; do not ask Ray whether to "
            "start it. State Ray's next action as none unless an external approval is actually needed. Do not "
            "use vague market claims without a named traceable source. No active clients means no observed "
            "test, not negative willingness-to-pay evidence; absent source-backed pricing evidence must be "
            "described as unknown."
        )
    return (
        "The draft below answered with an evidence or ownership error. " + instruction +
        "\nOriginal request: " + message[:5000] + "\nDraft to correct:\n" + response[:6000]
    )


def _conversation_needs_correction(message: str, response: str) -> bool:
    """Catch generic Nova conversation without routing it through specialists."""
    lowered = message.casefold()
    answer = response.casefold()
    try:
        from nova.executive_intelligence import is_opinion_request
    except ModuleNotFoundError:
        from executive_intelligence import is_opinion_request
    opinion = is_opinion_request(lowered)
    try:
        from nova.executive_intelligence import is_casual_conversation
    except ModuleNotFoundError:
        from executive_intelligence import is_casual_conversation
    casual = is_casual_conversation(lowered)
    if opinion:
        # A valid opinion should demonstrate at least two durable Nexus anchors.
        anchors = sum(term in answer for term in ("research", "alpha", "goclear", "trading", "department", "operating", "ray"))
        return True
    if casual:
        # All lightweight social turns receive one bounded voice editor. This
        # is still a no-tool path; it prevents a generic base-model reply from
        # becoming the Nova personality by accident.
        return True
    return False


def _conversation_correction_prompt(message: str, response: str) -> str:
    lowered = message.casefold()
    if "what do you think" in lowered or "where this is going" in lowered:
        instruction = (
            "Answer as Nova's grounded opinion, not generic AI commentary. Keep it conversational and concise. "
            "Discuss the actual Nexus direction: an autonomous operating-company architecture, Research and Alpha, "
            "specialist departments, GoClear as the first business proving ground, Hermes Nova as Ray's interface, "
            "and the shift from prompt-by-prompt work toward durable goals/programs and verified outcomes. Include "
            "at least three of those explicit Nexus anchors and give a direct judgment about whether the direction "
            "is sound. Include one Nexus-specific constructive risk or thing to protect. Use durable context only; do not invent "
            "current metrics, current feedback, or claims that a product is running successfully. Avoid generic "
            "praise and do not hand the conversation back with a question. Keep it conversational rather than a report."
        )
    else:
        instruction = (
            "Reply naturally as Hermes Nova to Ray. Be warm, brief, and recognizable as his Nexus partner; avoid "
            "generic support-assistant phrases such as 'I'm here and ready to assist' or 'How can I help you today?'. "
            "Acknowledge the conversation in your own words and, where natural, lightly ground it in the ongoing "
            "Nexus work. Do not use tools, report headings, or claim live facts."
        )
    return instruction + "\nUser message: " + message[:3000] + "\nDraft to improve: " + response[:4000]


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
    if _conversation_needs_correction(message, response):
        try:
            corrected, correction_elapsed = invoke(_conversation_correction_prompt(message, response), "skills")
        except subprocess.TimeoutExpired:
            return OracleHermesResult(response, "SUCCEEDED", None, elapsed, recovery="CONVERSATION_CORRECTION_TIMEOUT")
        if corrected.returncode == 0 and corrected.stdout.strip():
            corrected_text = corrected.stdout.strip()
            if not any(marker in corrected_text.casefold() for marker in ("same_tool_failure_halt", "tool-call guardrail", "non-progressing attempts")):
                return OracleHermesResult(corrected_text, "SUCCEEDED", None, round(elapsed + correction_elapsed, 1), recovery="CONVERSATION_CORRECTION")
    return OracleHermesResult(response, "SUCCEEDED", None, elapsed)
