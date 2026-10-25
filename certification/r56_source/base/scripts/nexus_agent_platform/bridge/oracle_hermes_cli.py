"""Governed Mac-to-Oracle Hermes 0.20.6 transport.

This adapter owns transport only.  The remote command is fixed, the prompt is
carried on stdin, and no user text is interpolated into a shell command.
"""
from __future__ import annotations

import os
import re
import json
import shlex
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
NOVA_MODEL_PROVIDER = "openai-codex"
NOVA_MODEL = "gpt-5.6-terra"
# Interactive Research Room uses a smaller, faster model on the same already
# authenticated Codex subscription. Keep Nova's own default route unchanged.
RESEARCH_ROOM_MODEL = os.getenv("NEXUS_RESEARCH_ROOM_MODEL", "gpt-5.4-mini")
RESEARCH_ROOM_MODELS = {"gpt-5.4-mini", "gpt-5.4", "gpt-5.5"}
NOVA_MODEL_COST_CLASS = "EXISTING_BUDGET"
NOVA_LOCAL_MODEL = "gemma3:4b"
ORACLE_MODEL = NOVA_MODEL
ORACLE_PROFILE = "nova_nexus"
ORACLE_CONTAINER = "nexus-hermes-0206"
NOVA_MODEL_MAX_TURNS = 4
NOVA_MODEL_RUN_BUDGET_SECONDS = 60
NOVA_MODEL_MAX_PROVIDER_INVOCATIONS = 3
# Hermes -t is an explicit allowlist. MCP server IDs are sourced from Nova's
# explicit approved-server registry and intersected with the enabled Hermes
# profile. The native public web toolset remains separately approved.
try:
    from nova.approved_mcp_registry import oracle_toolset
    ORACLE_TOOLSET = oracle_toolset()
except Exception:
    ORACLE_TOOLSET = "nexus_mcp_remote,you-com,web"
SESSION_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")

REMOTE_STATELESS_SCRIPT = r'''import json,os,subprocess,sys,tempfile
prompt=sys.stdin.read()
binary="/opt/hermes/.venv/bin/hermes"
model=os.environ.get("NEXUS_RESEARCH_ROOM_MODEL","gpt-5.4-mini")
if model not in {"gpt-5.4-mini","gpt-5.4","gpt-5.5"}: raise SystemExit("RESEARCH_ROOM_MODEL_NOT_ALLOWLISTED")
usage_path=None
try:
    fd,usage_path=tempfile.mkstemp(prefix="nexus-research-room-usage-",suffix=".json",dir="/tmp")
    os.close(fd)
    env=os.environ.copy(); env.update({"HERMES_HOME":"/opt/data/profiles/nova_nexus","HERMES_PROFILE":"nova_nexus"})
    command=[binary,"-z",prompt,"--safe-mode","--model",model,"--provider","openai-codex","--usage-file",usage_path]
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=24,check=False,env=env)
        usage={}
        if os.path.exists(usage_path):
            try:
                with open(usage_path,encoding="utf-8") as stream: usage=json.load(stream)
            except Exception: pass
        print(json.dumps({"returncode":result.returncode,"text":result.stdout.strip(),"stderr":result.stderr[-1200:],"usage":usage}))
    except subprocess.TimeoutExpired as exc:
        print(json.dumps({"returncode":124,"text":"","stderr":"HERMES_ONESHOT_TIMEOUT","usage":{}}))
finally:
    if usage_path and os.path.exists(usage_path): os.unlink(usage_path)
'''


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
    provider: str = NOVA_MODEL_PROVIDER
    model: str = ORACLE_MODEL
    toolset: str = ORACLE_TOOLSET
    recovery: str = "NONE"
    # Native Hermes session ID.  The caller's stable interface key remains
    # the correlation/session identity exposed by Nexus; this is the durable
    # SQLite-backed Hermes row created/resolved by --continue.
    hermes_session_id: str | None = None
    usage: dict[str, Any] | None = None


def _reasoning_limits(reasoning_class: str) -> dict[str, int]:
    if reasoning_class == "LIGHT_REASONING":
        return {"max_turns": 1, "run_budget_seconds": 25, "max_provider_invocations": 1, "estimated_tokens": 2000}
    if reasoning_class == "STRONG_REASONING":
        return {"max_turns": NOVA_MODEL_MAX_TURNS, "run_budget_seconds": NOVA_MODEL_RUN_BUDGET_SECONDS,
            "max_provider_invocations": NOVA_MODEL_MAX_PROVIDER_INVOCATIONS, "estimated_tokens": 8000}
    raise OracleHermesUnavailable("unsupported_codex_reasoning_class")


def _container_command(toolset: str = ORACLE_TOOLSET, model: str = NOVA_MODEL,
                       provider: str = NOVA_MODEL_PROVIDER, reasoning_class: str = "STRONG_REASONING",
                       stateless: bool = False) -> str:
    # Use only the existing authenticated Codex subscription for tool turns.
    # Ollama Gemma 3 4B was verified locally but rejected Hermes tool schemas
    # with HTTP 400, so it is not a sufficient tool-routing model. Never fall
    # through to the metered OpenRouter default.
    expected_stateless_model = RESEARCH_ROOM_MODEL
    if stateless:
        model = expected_stateless_model
    if (provider, model) != (NOVA_MODEL_PROVIDER, NOVA_MODEL) and not (
            stateless and provider == "openai-codex" and model in RESEARCH_ROOM_MODELS):
        raise OracleHermesUnavailable("model_route_not_allowlisted")
    limits = _reasoning_limits(reasoning_class)
    if stateless:
        # Research Room turns are self-contained and must not resume a named
        # Hermes session: those names can resolve to an empty CLI session.
        # Safe mode disables profile tools/MCP and emits machine-readable usage.
        return (
            "set -e; export NEXUS_RESEARCH_ROOM_MODEL=" + shlex.quote(RESEARCH_ROOM_MODEL) + "; "
            "/opt/hermes/.venv/bin/hermes auth status openai-codex | grep -Fq 'logged in'; "
            "exec python3 -c " + shlex.quote(REMOTE_STATELESS_SCRIPT)
        )
    return (
        "set -e; /opt/hermes/.venv/bin/hermes auth status openai-codex | grep -Fq 'logged in'; "
        "IFS= read -r session; prompt=$(cat); printf \"%s\" \"$prompt\" | exec env "
        "NEXUS_MCP_CONVERSATION_ID=\"$session\" HERMES_HOME=/opt/data/profiles/nova_nexus "
        "HERMES_PROFILE=nova_nexus /opt/hermes/.venv/bin/hermes chat -Q --query-file - "
        f"-m {model} --provider {provider} -t {toolset} --max-turns {limits['max_turns']} "
        f"--run-budget {limits['run_budget_seconds']} --continue \"$session\" "
        "--create-if-missing --pass-session-id --no-restore-cwd"
    )


def _remote_command(toolset: str = ORACLE_TOOLSET, model: str = NOVA_MODEL,
                    provider: str = NOVA_MODEL_PROVIDER, reasoning_class: str = "STRONG_REASONING",
                    stateless: bool = False) -> str:
    # This is intentionally constant: only the session title and prompt travel
    # over stdin.  ``--resume`` only accepts an already-existing native ID;
    # interface sessions are durable names, so ``chat --continue
    # --create-if-missing`` is the native create-or-resume contract.
    return "podman exec -i " + ORACLE_CONTAINER + " sh -lc " + shlex.quote(_container_command(toolset, model, provider, reasoning_class, stateless))


def _local_podman_command(toolset: str = ORACLE_TOOLSET, reasoning_class: str = "STRONG_REASONING",
                          stateless: bool = False) -> list[str]:
    return ["podman", "exec", "-i", ORACLE_CONTAINER, "sh", "-lc",
            _container_command(toolset, reasoning_class=reasoning_class, stateless=stateless)]


def _ensure_nova_subscription_model_policy() -> None:
    """Govern bounded, zero-spend owner turns without a cumulative lifetime cap.

    The governor's DAILY/MONTHLY usage accounting is cumulative across all
    reservations; it does not reset by calendar window. Keep a rolling rate
    guard here and rely on the governor's per-job envelope for each bounded
    conversation turn. Paid/autonomous spend remains disabled.
    """
    from nexus_agent_platform.resource_spend_governor import default_store
    store = default_store()
    hard = {
        "rate": {"requests": 36, "operations": 36, "window_seconds": 60},
        "usage": {},
        "money": {"per_job": 0, "per_day": 0, "per_month": 0},
    }
    soft = {
        "rate": {"requests": 24, "operations": 24, "window_seconds": 60},
        "usage": {},
        "money": {"per_job": 0, "per_day": 0, "per_month": 0},
    }
    store.ensure_policy("OPENAI_CODEX", "subscription_model", "NOVA_TELEGRAM_OWNER_TURN", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        soft_limits=soft, hard_limits=hard, concurrency_limit=1, state="NORMAL", approval_required=False)
    store.ensure_policy("OPENAI_CODEX", "subscription_model", "NOVA_TELEGRAM_OWNER_TURN", "MONTHLY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        soft_limits=soft, hard_limits=hard, concurrency_limit=1, state="NORMAL", approval_required=False)


def _ensure_department_subscription_model_policy() -> None:
    """Add a bounded zero-spend envelope for other routed Nexus reasoning jobs."""
    from nexus_agent_platform.resource_spend_governor import default_store
    store = default_store()
    hard = {"rate": {"requests": 12, "operations": 12, "window_seconds": 60},
        "usage": {"requests": 120, "operations": 120, "tokens": 240_000,
            "runtime_seconds": 3_600, "bytes": 20_000_000},
        "money": {"per_job": 0, "per_day": 0, "per_month": 0}}
    soft = {"rate": {"requests": 8, "operations": 8, "window_seconds": 60},
        "usage": {"requests": 80, "operations": 80, "tokens": 160_000,
            "runtime_seconds": 2_400, "bytes": 12_000_000},
        "money": {"per_job": 0, "per_day": 0, "per_month": 0}}
    for period in ("DAILY", "MONTHLY"):
        store.ensure_policy("OPENAI_CODEX", "subscription_model", "*", period,
            autonomous_usage_allowed=True, autonomous_spend_allowed=False,
            soft_limits=soft, hard_limits=hard, concurrency_limit=2, state="NORMAL",
            approval_required=False)
        # Needle and its one bounded same-notebook repair use this existing
        # subscription route, but receive explicit job scopes so they do not
        # rely on the provider-wide job wildcard.
        for job_type in ("NEEDLE_RESEARCH_READINESS_VERIFY", "NEEDLE_RESEARCH_TARGETED_REPAIR"):
            store.ensure_policy("OPENAI_CODEX", "subscription_model", job_type, period,
                autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                soft_limits=soft, hard_limits=hard, concurrency_limit=1, state="NORMAL",
                approval_required=False)


def _executive_prompt(message: str) -> str:
    """Carry the bounded executive contract across the Oracle process boundary."""
    lowered = message.casefold()
    semantic_plan = {}
    capability_context = ""
    try:
        from nova.semantic_orchestration import resolve_owner_request
        from nova.live_capability_registry import capability_context_for_request
        semantic_plan = resolve_owner_request(message)
        capability_context = capability_context_for_request(message)
    except Exception as exc:
        # Discovery failure is visible to Hermes as an unknown capability
        # surface; it must never become an affirmative availability claim.
        capability_context = json.dumps({"live_registry": "UNAVAILABLE", "error": type(exc).__name__})
    try:
        from nova.executive_intelligence import is_casual_conversation, is_executive_attention_request, is_monetization_decision, is_opinion_request, is_priority_request
    except ModuleNotFoundError:
        from executive_intelligence import is_casual_conversation, is_executive_attention_request, is_monetization_decision, is_opinion_request, is_priority_request
    opinion = is_opinion_request(lowered)
    current_research = bool("research" in lowered and re.search(r"\b(still|running|active|heartbeat|scheduler|processing|status|doing)\b", lowered))
    objective_id_request = bool(re.search(r"\bobjective_id\s*[=:]\s*[A-Za-z0-9_.:-]{3,160}", message, re.I))
    priority = is_priority_request(lowered)
    attention = is_executive_attention_request(lowered)
    monetization = is_monetization_decision(lowered)
    casual = is_casual_conversation(lowered)
    if casual and not capability_context and not objective_id_request:
        return (
            "[NOVA LIGHT CONVERSATION]\n"
            "You are Hermes Nova, Ray Davis's conversational partner and executive interface to Nexus. "
            "You know Nexus is an autonomous operating-company system with Research, Alpha, and specialist departments. "
            "Answer naturally and briefly in your own voice. Do not turn casual conversation into a report, "
            "use tools, or invent live facts. Preserve the current conversation context.\n"
            "USER REQUEST:\n" + message[:3000]
        )
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
            "and recent activity. Do not collapse these states into a single running/not-running claim. Call "
            "nexus_get_research_state for the current Research queue and use its queue projection; do not call "
            "the generic nexus_get_work_items tool as a substitute. Distinguish ASSIGNED, MONITORED, "
            "DEMAND_DISCOVERY, and GENERAL_DISCOVERY counts and state unknowns plainly."
        )
    orchestration_rules = (
        " Treat each message as an owner goal expressed in ordinary language, not as a command syntax. "
        "Resolve references such as 'that', 'the second one', or 'continue' from this Hermes conversation "
        "and current durable Nexus state; ask one concise question only when the referent is genuinely ambiguous. "
        "Plan internally: desired outcome, relevant existing objective, evidence, capabilities, dependencies, "
        "sequence, approval boundary, and next action. Select tools from their live schemas and descriptions. "
        "Use a Nexus department or Hermes executor for work; never present your own reasoning as a department result. "
        "When a durable assignment action exists, use that governed action once and report its real receipt/ID. "
        "A request to have, ask, assign, or delegate work to Research, Systems, or Alpha is an execution request, "
        "even when it mentions a capability such as NotebookLM. Do not answer it with a capability description. "
        "For multiple requested departments, submit each supported bounded assignment under the same parent "
        "objective/correlation and report each actual job ID and returned state; preserve exact routing errors. "
        "NotebookLM remains Research-owned and is never a direct Nova operation. "
        "When no supported executor exists, state the specific capability gap and preserve the request. "
        "For current state, Google, browser, or provider questions, make the relevant live read before answering. "
        "For capability questions, use the attached fresh registry and distinguish discovered, configured, authenticated, "
        "connected, and successfully tested. Do not imply that installation or configuration proves a working call. "
        "For multi-capability work, coordinate only the steps supported by discovered executors and continue after "
        "independent steps when one dependency is unavailable. On failure, explain what failed, what remains intact, "
        "what happens next, and whether Ray needs to act. Approved non-Nexus MCP servers are a separate execution "
        "class from Nexus internal executors: select them from the live server/tool registry and use their actual "
        "schemas; do not reject an approved MCP action merely because no Nexus executor has the same tool. Before a "
        "write, obey the candidate's evaluated policy and metadata. Report a write as complete only when the tool "
        "result contains a receipt ID; echo the actual resource ID and receipt ID exactly."
    )
    # Only durable objective identifiers create objective-scoped read context.
    # Natural-language assignment text often contains phrases such as
    # "objective: investigate"; treating that verb as an ID suppresses the
    # assignment action and sends Hermes down the read-only path.
    objective_match = re.search(r"\bobjective_id\s*[=:]\s*([A-Za-z0-9_.:-]{3,160})", message, re.I)
    objective_contract = ""
    if objective_match:
        objective_id = objective_match.group(1)
        objective_contract = (
            " This is an OBJECTIVE_SCOPED_RESEARCH_REQUEST. Resolve objective_id=" + objective_id +
            " first. Call nexus_get_research_state with that exact objective_id, then call "
            "nexus_get_alpha_review with the same objective_id. Do not use a global latest Research read, "
            "historical CRJ/affiliate summaries, or fuzzy text matching. Your answer must explicitly state "
            "RESOLVED_OBJECTIVE_ID, LATEST_RESEARCH_PACKAGE, LATEST_ALPHA_RECEIPT, MISSING_EVIDENCE, and "
            "CURRENT_NEXT_ACTION. If any are unavailable, say exactly which field is unavailable."
        )
    return (
        "[NOVA EXECUTIVE REQUEST CONTRACT]\n"
        "Answer the user's parent question directly. For a strategic request, identify the parent decision, "
        "use only materially relevant current Nexus state/specialists, separate evidence from judgment and unknowns, "
        "compare disagreement when present, make one recommendation, and name one bounded next action. "
        "Do not call the same tool repeatedly; if a tool fails or returns no progress, synthesize from available evidence "
        "or state the exact unknown. A task/report/specialist response is not parent-goal completion.\n"
        + orchestration_rules
        + "\nSEMANTIC INTENT HYPOTHESIS (validate against the owner's full request):\n"
        + json.dumps(semantic_plan, ensure_ascii=False, default=str)
        + ("\n" + capability_context if capability_context else "")
        + priority_rules + attention_rules + pricing_rules + opinion_rules + state_rules + objective_contract + "\n"
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


def _objective_grounding_context(message: str) -> str:
    """Resolve exact objective evidence before the remote model turn.

    The remote MCP remains the interactive read surface. This compact
    transport context is a safety bridge for Hermes tool calls that omit the
    newly supported objective argument; it is a projection of canonical
    records, not an LLM-generated summary.
    """
    match = re.search(r"(?:objective_id|objective)\s*[=:]\s*([A-Za-z0-9_.:-]{3,160})", message, re.I)
    if not match:
        return ""
    try:
        from nexus_agent_platform.research_evidence_bridge import resolve_objective
        state = resolve_objective(match.group(1))
        package = state.get("research_package") or {}
        source = package.get("source") or {}
        alpha = state.get("alpha_evaluation") or {}
        receipt = state.get("alpha_receipt") or {}
        payload = {
            "authority": "Nexus canonical objective-scoped evidence bridge",
            "objective_id": state.get("objective_id"),
            "status": state.get("status"),
            "research_package_id": package.get("research_package_id"),
            "research_status": package.get("status"),
            "source": {k: source.get(k) for k in ("source_id", "source_title", "source_type", "source_url", "processing_status")},
            "research_next_action": state.get("current_next_action"),
            "open_questions": [q.get("question") for q in (package.get("questions") or [])[:5]],
            "alpha_receipt_id": receipt.get("receipt_id"),
            "alpha_decision": alpha.get("decision"),
            "alpha_evaluation_id": alpha.get("evaluation_id"),
            "alpha_followup_work_id": receipt.get("followup_work_id"),
            "alpha_required_followup": alpha.get("required_followup"),
            "missing_evidence": state.get("missing_evidence", []),
        }
        return json.dumps(payload, ensure_ascii=False, default=str)[:10000]
    except Exception as exc:
        return json.dumps({"authority": "Nexus canonical objective-scoped evidence bridge",
                           "status": "UNAVAILABLE", "reason": type(exc).__name__})


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


def _run_oracle_hermes_unchecked(message: str, session_id: str, *, timeout_seconds: float = 180.0,
                      request_id: str | None = None, pre_context: str | None = None,
                      structured_task: bool = False, reasoning_class: str = "STRONG_REASONING",
                      stateless_task: bool = False) -> OracleHermesResult:
    if not isinstance(message, str) or not message.strip():
        raise OracleHermesUnavailable("empty_message")
    if not SESSION_RE.fullmatch(session_id or ""):
        raise OracleHermesUnavailable("invalid_session_id")
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise OracleHermesUnavailable("invalid_timeout")
    local_podman = os.getenv("NEXUS_HERMES_TRANSPORT", "").strip().lower() == "local_podman"
    if not local_podman and (not os.path.isfile(ORACLE_KEY) or not os.access(ORACLE_KEY, os.R_OK)):
        return OracleHermesResult(None, "UNAVAILABLE", "ssh_key_missing", 0.0)
    started = time.monotonic()
    def invoke(prompt: str, toolset: str) -> tuple[subprocess.CompletedProcess[str], float]:
        # Correction/recovery invocations are still part of this user turn;
        # carry the same context authority snapshot into every model call.
        contextual_prompt = prompt
        if pre_context and pre_context not in contextual_prompt:
            contextual_prompt += "\n\n" + pre_context[:26000]
        command = (_local_podman_command(toolset, reasoning_class, stateless_task) if local_podman else [
            "/usr/bin/ssh", "-i", ORACLE_KEY, "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=2", "-o", "StrictHostKeyChecking=accept-new",
            f"{ORACLE_USER}@{ORACLE_HOST}", _remote_command(toolset, reasoning_class=reasoning_class,
                stateless=stateless_task),
        ])
        started = time.monotonic()
        completed = subprocess.run(
            command, input=(contextual_prompt if stateless_task else f"{session_id}\n{contextual_prompt}"), text=True, capture_output=True,
            timeout=timeout_seconds, check=False,
        )
        return completed, round((time.monotonic() - started) * 1000, 1)
    try:
        prompt = message if structured_task else _executive_prompt(message)
        objective_context = None if structured_task else _objective_grounding_context(message)
        if objective_context:
            prompt += (
                "\n\nAUTHORITATIVE OBJECTIVE-SCOPED EVIDENCE (read before answering; do not replace "
                "with global latest Research/Alpha state):\n" + objective_context +
                "\nUse only this objective lineage for the requested answer. If the interactive MCP result "
                "disagrees, report the disagreement and prefer this exact objective-scoped canonical bridge."
            )
        if pre_context:
            prompt += "\n\n" + pre_context[:26000]
        if len(prompt) > 24_000:
            return OracleHermesResult(None, "UNAVAILABLE", "local_model_input_limit", round((time.monotonic() - started) * 1000, 1))
        completed, elapsed = invoke(prompt, ORACLE_TOOLSET)
    except subprocess.TimeoutExpired:
        return OracleHermesResult(None, "UNAVAILABLE", "oracle_timeout", round((time.monotonic() - started) * 1000, 1))
    except OSError as exc:
        return OracleHermesResult(None, "UNAVAILABLE", type(exc).__name__, round((time.monotonic() - started) * 1000, 1))
    if completed.returncode != 0:
        # Preserve a bounded, secret-redacted stderr excerpt so adapters can
        # distinguish remote CLI/provider errors from transport failures.
        detail = re.sub(r"(?i)(authorization:\s*bearer\s+)[^\s]+", r"\1[REDACTED]",
            (completed.stderr or "").strip())
        detail = re.sub(r"(?i)(api[_ -]?key|token|password)(\s*[:=]\s*)[^\s,;]+",
            r"\1\2[REDACTED]", detail)
        detail = re.sub(r"\s+", " ", detail)[-360:]
        stdout_errors = [line.strip() for line in (completed.stdout or "").splitlines()
            if re.search(r"(?i)error|failed|exception|denied|unavailable|traceback|timeout|HTTP\s+4\d\d|HTTP\s+5\d\d", line)]
        stdout_detail = re.sub(r"\s+", " ", " ".join(stdout_errors))[-240:]
        error = f"ssh_exit_{completed.returncode}" + (f":{detail}" if detail else "")
        if stdout_detail:
            error += f"; output_error={stdout_detail}"
        return OracleHermesResult(None, "UNAVAILABLE", error, elapsed)
    response = completed.stdout.strip()
    usage: dict[str, Any] | None = None
    if stateless_task:
        try:
            envelope = json.loads(response)
        except ValueError:
            return OracleHermesResult(None, "UNAVAILABLE", "invalid_hermes_oneshot_envelope", elapsed)
        response = str(envelope.get("text") or "").strip()
        raw_usage = envelope.get("usage") or {}
        usage = {key: raw_usage[key] for key in ("input_tokens", "output_tokens", "total_tokens")
                 if isinstance(raw_usage.get(key), (int, float))}
        if int(envelope.get("returncode", 1) or 0) != 0:
            error_detail = str(envelope.get("stderr") or envelope.get("returncode"))
            error_detail = re.sub(r"(?i)(authorization:\s*bearer\s+)[^\s]+", r"\1[REDACTED]", error_detail)
            error_detail = re.sub(r"(?i)(api[_ -]?key|token|password)(\s*[:=]\s*)[^\s,;]+", r"\1\2[REDACTED]", error_detail)
            return OracleHermesResult(None, "UNAVAILABLE", "hermes_oneshot_failed:" + re.sub(r"\s+", " ", error_detail)[-360:], elapsed, usage=usage)
        # Hermes 0.20.6 can exit successfully while writing an API error to
        # stdout. Do not let a provider rejection become an apparent answer.
        if re.search(r"(?i)(HTTP\s*4\d\d|model is not supported|provider error|API request failed|\"error\"\s*:)", response):
            return OracleHermesResult(None, "UNAVAILABLE", "hermes_provider_rejected:" + response[:300], elapsed, usage=usage)
    if not response:
        return OracleHermesResult(None, "UNAVAILABLE", "empty_oracle_response", elapsed)
    native_session_match = re.search(r"session_id:\s*([A-Za-z0-9_.:-]+)", completed.stderr or "")
    native_session_id = native_session_match.group(1) if native_session_match else None
    if structured_task:
        return OracleHermesResult(response, "SUCCEEDED", None, elapsed, hermes_session_id=native_session_id, usage=usage)
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
                return OracleHermesResult(recovered_text, "SUCCEEDED", None, round(elapsed + recovery_elapsed, 1), recovery="SYNTHESIS_AFTER_TOOL_HALT", hermes_session_id=native_session_id)
        return OracleHermesResult(response, "SUCCEEDED", None, round(elapsed + recovery_elapsed, 1), recovery="RECOVERY_UNUSABLE")
    if _judgment_needs_correction(message, response):
        try:
            corrected, correction_elapsed = invoke(_judgment_correction_prompt(message, response), "skills")
        except subprocess.TimeoutExpired:
            return OracleHermesResult(response, "SUCCEEDED", None, elapsed, recovery="JUDGMENT_CORRECTION_TIMEOUT")
        if corrected.returncode == 0 and corrected.stdout.strip():
            corrected_text = corrected.stdout.strip()
            if not any(marker in corrected_text.casefold() for marker in ("same_tool_failure_halt", "tool-call guardrail", "non-progressing attempts")):
                return OracleHermesResult(corrected_text, "SUCCEEDED", None, round(elapsed + correction_elapsed, 1), recovery="JUDGMENT_CORRECTION", hermes_session_id=native_session_id)
    if _conversation_needs_correction(message, response):
        try:
            corrected, correction_elapsed = invoke(_conversation_correction_prompt(message, response), "skills")
        except subprocess.TimeoutExpired:
            return OracleHermesResult(response, "SUCCEEDED", None, elapsed, recovery="CONVERSATION_CORRECTION_TIMEOUT")
        if corrected.returncode == 0 and corrected.stdout.strip():
            corrected_text = corrected.stdout.strip()
            if not any(marker in corrected_text.casefold() for marker in ("same_tool_failure_halt", "tool-call guardrail", "non-progressing attempts")):
                return OracleHermesResult(corrected_text, "SUCCEEDED", None, round(elapsed + correction_elapsed, 1), recovery="CONVERSATION_CORRECTION", hermes_session_id=native_session_id)
    return OracleHermesResult(response, "SUCCEEDED", None, elapsed, hermes_session_id=native_session_id, usage=usage)


def run_oracle_hermes(message: str, session_id: str, *, timeout_seconds: float = 180.0,
                      request_id: str | None = None, pre_context: str | None = None,
                      structured_task: bool = False, reasoning_class: str = "STRONG_REASONING",
                      governor_purpose: str | None = None, stateless_task: bool = False) -> OracleHermesResult:
    """Governor boundary for every Oracle Hermes SSH invocation."""
    from nexus_agent_platform.provider_enforcement import execute
    from nexus_agent_platform.resource_spend_governor import GovernanceDenied
    if not SESSION_RE.fullmatch(session_id or ""):
        raise OracleHermesUnavailable("invalid_session_id")
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise OracleHermesUnavailable("invalid_timeout")
    limits = _reasoning_limits(reasoning_class)
    if not os.environ.get("NEXUS_DURABLE_JOB_ID"):
        return OracleHermesResult(None, "UNAVAILABLE", "governor_durable_job_id_required", 0.0)
    if not os.environ.get("NEXUS_CORRELATION_ID") or not os.environ.get("NEXUS_DEPARTMENT"):
        return OracleHermesResult(None, "UNAVAILABLE", "governor_correlation_or_department_required", 0.0)
    # Nova's existing Codex subscription transport is registered in the same
    # canonical model router used by department reasoning. Keep Hermes as the
    # specialized executor, while the router owns provider eligibility.
    try:
        import sys
        from pathlib import Path
        scripts_dir = str(Path(__file__).resolve().parents[3] / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import model_router
        decision = model_router.select_reasoning_model(agent_key="nova", task_type="reasoning",
            sensitivity="unknown_sensitive", reasoning_class=reasoning_class, allow_free_tier=False)
        selected = decision.get("route") or {}
        if (decision.get("decision") != "selected" or decision.get("provider") != NOVA_MODEL_PROVIDER
                or decision.get("model") != NOVA_MODEL):
            return OracleHermesResult(None, "UNAVAILABLE", "canonical_model_route_unavailable", 0.0)
    except Exception as exc:
        return OracleHermesResult(None, "UNAVAILABLE", "canonical_model_router_" + type(exc).__name__, 0.0)
    local_podman = os.getenv("NEXUS_HERMES_TRANSPORT", "").strip().lower() == "local_podman"
    existing_subscription_model = NOVA_MODEL_PROVIDER == "openai-codex"
    # This route uses an already-authenticated subscription, not per-token API
    # billing. Reserve a bounded allowance and account for usage, while leaving
    # autonomous spend disabled (three invocations × four turns maximum).
    estimate = {"requests": limits["max_turns"] * limits["max_provider_invocations"],
        "operations": limits["max_turns"] * limits["max_provider_invocations"],
        "runtime_seconds": limits["run_budget_seconds"] * limits["max_provider_invocations"],
        "tokens": limits["estimated_tokens"], "cost": 0.0, "billable": False, "budget_period": "DAILY"}
    if not existing_subscription_model:
        # Preserve fail-closed accounting for the legacy metered SSH route.
        estimate["billable"] = True
        estimate.pop("cost", None)
        estimate["provider"] = "ORACLE"
        try: estimate["cost"] = float(os.environ["NEXUS_ORACLE_ESTIMATED_COST_PER_JOB"])
        except (KeyError, ValueError): pass
    job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
    try:
        if existing_subscription_model:
            _ensure_nova_subscription_model_policy()
            _ensure_department_subscription_model_policy()
        provider = "OPENAI_CODEX" if existing_subscription_model else "ORACLE"
        service = "subscription_model" if existing_subscription_model else "hermes_worker"
        job_type = os.environ.get("NEXUS_JOB_TYPE", "NOVA_TELEGRAM_OWNER_TURN") if existing_subscription_model else os.environ.get("NEXUS_JOB_TYPE", "ORACLE_HERMES")
        return execute(provider, service, "SUBSCRIPTION_MODEL_INFERENCE" if existing_subscription_model else "REMOTE_WORKER", estimate,
            lambda: _run_oracle_hermes_unchecked(message, session_id, timeout_seconds=timeout_seconds,
                request_id=request_id, pre_context=pre_context, structured_task=structured_task,
                reasoning_class=reasoning_class, stateless_task=stateless_task),
            job_id=job_id, job_type=job_type,
            correlation_id=request_id or session_id,
            purpose=governor_purpose,
            actual_usage=lambda result: {"requests": estimate["requests"], "operations": estimate["operations"],
                "runtime_seconds": max(0.0, float(result.latency_ms or 0) / 1000),
                **({"tokens": (result.usage or {}).get("total_tokens", estimate["tokens"]), "cost": 0.0} if existing_subscription_model else
                   ({"cost": estimate["cost"]} if "cost" in estimate else {}))})
    except GovernanceDenied as exc:
        return OracleHermesResult(None, "UNAVAILABLE", "governor_" + exc.code.lower(), 0.0)
