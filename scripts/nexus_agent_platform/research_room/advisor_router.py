"""Provider-neutral advisor boundary; unavailable providers never block a case."""
from __future__ import annotations

import asyncio
import hashlib
import json
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from .context import PROMPT_VERSION, compact_context
from .usage import record_call

DEFAULT_PRIMARY_ADVISOR = "CHATGPT_PLAN"
RESEARCH_LOCAL_ADVISOR_DENYLIST = frozenset({"OLLAMA_LOCAL", "LOCAL_LLM", "LOCAL_MODEL_FALLBACK"})


class Advisor(Protocol):
    provider: str
    available: bool
    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]: ...


class UnavailableAdvisor:
    def __init__(self, provider: str):
        self.provider, self.available = provider, False

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        return {"status": "ADVISOR_UNAVAILABLE", "provider": self.provider,
                "analysis": None, "new_questions": [], "reason": "provider_not_connected"}


class HermesAdvisor(UnavailableAdvisor):
    """Nexus Hermes adapter boundary. Calls only when an explicit client is injected."""
    def __init__(self, client: Any = None):
        super().__init__("HERMES")
        self.client = client
        self.available = client is not None

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        if self.client is None:
            return super().ask(role=role, case_context=case_context, objective=objective)
        return self.client.ask(role=role, case_context=compact_context(case_context, role=role), objective=objective)


class OpenRouterAdvisor(HermesAdvisor):
    def __init__(self, client: Any = None):
        super().__init__(client)
        self.provider = "OPENROUTER"


class ChatGPTAdvisor(UnavailableAdvisor):
    """First-class connector boundary; no synthetic response is returned."""
    provider = "CHATGPT_PLAN"
    free_or_metered = "CHATGPT_PLAN_INCLUDED"
    def __init__(self, connector: Any = None):
        super().__init__("CHATGPT_PLAN")
        self.connector = connector
        self.available = connector is not None

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        if self.connector is None:
            return super().ask(role=role, case_context=case_context, objective=objective)
        package = (case_context if case_context.get("prompt_version") == PROMPT_VERSION
            else compact_context(case_context, role=role))
        return self.connector.ask(role=role, case_context=package, objective=objective)


class CodexTechnicalAdvisor(ChatGPTAdvisor):
    """Plan-backed Codex perspective reserved for explicitly technical work."""
    provider = "CODEX"

    def __init__(self, connector: Any = None):
        super().__init__(connector)
        self.provider = "CODEX"

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        result = super().ask(role="CODEX_TECHNICAL_ADVISOR:" + role,
            case_context=case_context, objective=objective)
        result["provider"] = "CODEX"
        result["cost_class"] = "CHATGPT_PLAN_INCLUDED"
        return result


def _configured_chatgpt_connector() -> Any:
    """Expose existing Codex CLI if installed; auth is verified by the real turn."""
    try:
        from .codex_chatgpt_advisor import CodexCliChatGPTConnector
        connector = CodexCliChatGPTConnector()
        if connector.is_installed():
            return connector
    except OSError:
        pass
    return None


class NexusGatewayAdvisor:
    """Adapter for Nexus' existing canonical LlmGatewayAdapter/model_router.

    It is explicit opt-in because a model call may consume governed provider
    resources. The response must be valid JSON; no fabricated fallback is
    presented as model output.
    """
    provider = "NEXUS_LLM_GATEWAY"
    def __init__(self, gateway: Any = None):
        self.gateway = gateway
        self.available = gateway is not None

    @classmethod
    def configured(cls) -> "NexusGatewayAdvisor":
        if __import__("os").getenv("NEXUS_RESEARCH_ROOM_ADVISOR_ENABLED", "").lower() != "true":
            return cls()
        from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter
        return cls(LlmGatewayAdapter("nexus_research_room_advisor"))

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        if self.gateway is None:
            return {"status": "ADVISOR_UNAVAILABLE", "provider": self.provider,
                    "reason": "provider_not_enabled"}
        prompt = case_context if case_context.get("prompt_version") == PROMPT_VERSION else compact_context(case_context, role=role)
        started = time.monotonic()
        response = asyncio.run(self.gateway.completion(model="canonical",
            messages=[{"role": "system", "content": "You are a domain advisor inside Nexus Research Room. Use only the supplied compact case context. Do not call tools, create or change jobs, trade, send messages, or perform external actions. Return JSON with analysis, new_questions, risks, opportunities, recommended_actions. You advise; you do not decide whether Research continues."},
                      {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, default=str)}],
            temperature=0.2, max_tokens=700, timeout=60, sensitivity="public_research",
            reasoning_class="LIGHT_REASONING", task_type="research"))
        if response.get("error"):
            raise RuntimeError(str(response.get("error_detail") or response["error"]))
        text = str(response.get("content") or "")
        if _looks_like_provider_error(text):
            raise RuntimeError("ADVISOR_PROVIDER_ERROR_RESPONSE:" + text[:500])
        parsed = parse_advisor_content(text)
        return {"status": "COMPLETED", "provider": response.get("provider") or self.provider,
                "model": response.get("model"), "usage": response.get("usage") or {},
                "estimated_cost_usd": (response.get("execution_metadata") or {}).get("estimated_cost",
                    response.get("estimated_cost")),
                "duration_ms": (response.get("execution_metadata") or {}).get("latency_ms",
                    (time.monotonic() - started) * 1000),
                "cost_class": (response.get("execution_metadata") or {}).get("cost_class",
                    response.get("cost_class")), **parsed}


class OpenRouterHostedAdvisor:
    """Fast direct hosted route used for normal interactive advisor turns."""
    provider = "OPENROUTER"
    health_key = "OPENROUTER_DIRECT"
    runtime = "DIRECT_API"
    model = "google/gemini-2.5-flash-lite"
    input_price_per_token = 0.0000001
    output_price_per_token = 0.0000004
    max_output_tokens = 700
    available = True
    free_or_metered = "METERED"

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        import os
        import requests
        from scripts.ops.nexus_runtime_env import load_runtime_env
        load_runtime_env(allowed_keys={"OPENROUTER_API_KEY"})
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_AUTH_UNAVAILABLE")
        prompt = ("You are a bounded Research Room advisor. Read and reason from the user's supplied input first; "
            "search is optional and must be requested only when a specific material uncertainty needs outside evidence. "
            "Return any such requests as tool_requests with question_id and question; do not claim search results until supplied. "
            "Use only the supplied compact case packet and public evidence notes. "
            "Consider its objective, source summary, current findings, prior Nexus knowledge, questions, answered questions, "
            "unresolved items, contradictions, and test results. Return JSON with ADVISOR_ANALYSIS, NEW_QUESTIONS, RISKS, "
            "OPPORTUNITIES, RECOMMENDED_ACTIONS, CONFIDENCE, EVIDENCE_NOTES, and TOOL_REQUESTS. "
            "Do not call tools or take actions.\nOBJECTIVE: " + objective[:1800] +
            "\nROLE: " + role[:120] + "\nCASE CONTEXT: " + json.dumps(case_context, ensure_ascii=False, default=str)[:10000])
        def invoke() -> dict[str, Any]:
            started = time.monotonic()
            timeout = min(12.0, max(2.0, float(os.getenv("NEXUS_RESEARCH_MODEL_TIMEOUT_SECONDS", "8"))))
            response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2, "max_tokens": self.max_output_tokens, "allow_fallbacks": False,
                    "usage": {"include": True}}, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices") or []
            content = ((choices[0].get("message") or {}).get("content") if choices else None)
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("OPENROUTER_EMPTY_ADVISOR_RESPONSE")
            raw = payload.get("usage") or {}
            usage = {"input_tokens": raw.get("prompt_tokens"),
                "output_tokens": raw.get("completion_tokens"), "total_tokens": raw.get("total_tokens")}
            cost = raw.get("cost")
            if not isinstance(cost, (int, float)) and all(isinstance(usage[k], (int, float)) for k in ("input_tokens", "output_tokens")):
                cost = (float(usage["input_tokens"]) * self.input_price_per_token +
                    float(usage["output_tokens"]) * self.output_price_per_token)
            return {"status": "COMPLETED", "provider": self.provider, "runtime": self.runtime,
                "model": payload.get("model") or self.model, "provider_request_id": payload.get("id"), "usage": usage,
                "estimated_cost_usd": cost, "duration_ms": (time.monotonic()-started)*1000,
                "prompt_sent": prompt, "full_response": content,
                **parse_advisor_content(content)}
        return _execute_shadow_openrouter(case_context, role, invoke, model=self.model,
            input_price=self.input_price_per_token, output_price=self.output_price_per_token,
            max_output_tokens=self.max_output_tokens)


class OpenRouterFreeAdvisor(OpenRouterHostedAdvisor):
    """Tested zero-priced route, preferred before any metered route."""
    health_key = "OPENROUTER_FREE_LIQUID"
    model = "liquid/lfm-2.5-2.6b:free"
    input_price_per_token = 0.0
    output_price_per_token = 0.0
    max_output_tokens = 1200
    free_or_metered = "FREE_ZERO_PRICED"

    def __init__(self, model: str | None = None):
        selected = str(model or type(self).model).strip()
        if not selected.endswith(":free"):
            raise ValueError("OPENROUTER_RESEARCH_FALLBACK_MUST_BE_ZERO_PRICED")
        self.model = selected

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        import os
        import requests
        from scripts.ops.nexus_runtime_env import load_runtime_env
        load_runtime_env(allowed_keys={"OPENROUTER_API_KEY"})
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_AUTH_UNAVAILABLE")
        packet = {key: case_context.get(key) for key in (
            "provided_input", "original_request", "source_summary", "source_claims", "source_references",
            "findings", "questions", "prior_knowledge_summary", "unresolved_questions", "unresolved_items",
            "test_results", "business_opportunity_report")}
        prompt = ("You are a concise independent Research Room advisor. Analyze the supplied input before requesting tools. "
            "Search is optional. If specific outside evidence is needed, return tool_requests with question_id and question. "
            "Identify the decision, material claims, available evidence, uncertainty, risks, alternatives, and a useful next step. "
            "Do not assume this is a business-opportunity comparison. Use only supplied context and label unknowns. "
            "Return valid JSON with analysis, new_questions, risks, opportunities, recommended_actions, evidence_notes, confidence, and tool_requests.\n"
            "OBJECTIVE: " + objective[:1000] + "\nROLE: " + role[:100] + "\nPACKET: " +
            json.dumps(packet, ensure_ascii=False, default=str)[:5000])
        def invoke() -> dict[str, Any]:
            started = time.monotonic()
            timeout = min(12.0, max(2.0, float(os.getenv("NEXUS_RESEARCH_MODEL_TIMEOUT_SECONDS", "8"))))
            response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2, "max_tokens": 850, "allow_fallbacks": False,
                    "usage": {"include": True}}, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            choices = payload.get("choices") or []
            content = ((choices[0].get("message") or {}).get("content") if choices else None)
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("OPENROUTER_FREE_EMPTY_ADVISOR_RESPONSE")
            raw = payload.get("usage") or {}
            usage = {"input_tokens": raw.get("prompt_tokens"), "output_tokens": raw.get("completion_tokens"),
                "total_tokens": raw.get("total_tokens")}
            return {"status": "COMPLETED", "provider": self.provider, "runtime": self.runtime,
                "model": payload.get("model") or self.model, "provider_request_id": payload.get("id"),
                "usage": usage, "estimated_cost_usd": 0.0, "duration_ms": (time.monotonic()-started)*1000,
                "prompt_sent": prompt, "full_response": content, **parse_advisor_content(content)}
        return _execute_shadow_openrouter(case_context, role, invoke, model=self.model,
            input_price=0.0, output_price=0.0, max_output_tokens=850)


class StrongOpenRouterAdvisor(OpenRouterHostedAdvisor):
    """Higher-capability, higher-cost model reserved for justified hard cases."""
    health_key = "OPENROUTER_STRONG"
    model = "google/gemini-2.5-pro"
    input_price_per_token = 0.00000125
    output_price_per_token = 0.00001
    max_output_tokens = 450
    free_or_metered = "STRONG_METERED"


class HermesOpenRouterAdvisor:
    """Bounded Hermes one-shot advisor routed to the existing OpenRouter key.

    The API key crosses only the encrypted SSH stdin stream and is never placed
    in a command argument, environment dump, or log. Hermes remains the runtime;
    OpenRouter is the underlying metered model provider.
    """
    provider = "OPENROUTER"
    runtime = "HERMES"
    model = "google/gemini-2.5-flash-lite"
    health_key = "HERMES_OPENROUTER"
    available = True

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        import os
        import subprocess
        from pathlib import Path
        from scripts.ops.nexus_runtime_env import load_runtime_env

        load_runtime_env(allowed_keys={"OPENROUTER_API_KEY"})
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_AUTH_UNAVAILABLE")
        host = os.getenv("NEXUS_ORACLE_SSH_HOST", "161.153.40.41")
        user = os.getenv("NEXUS_ORACLE_SSH_USER", "opc")
        key_path = os.path.expanduser(os.getenv("NEXUS_ORACLE_SSH_KEY", "~/.ssh/oracle_vm"))
        if not Path(key_path).is_file():
            raise RuntimeError("HERMES_SSH_KEY_UNAVAILABLE")
        prompt = ("You are a bounded Research Room advisor. Use the supplied source and objective. "
            "Return concise JSON with analysis, new_questions, risks, opportunities, recommended_actions. "
            "Do not call tools or take actions.\nOBJECTIVE: " + objective[:1800] +
            "\nROLE: " + role[:120] + "\nCASE CONTEXT: " + json.dumps(case_context, ensure_ascii=False, default=str)[:10000])
        script = r'''import json,os,subprocess,tempfile,sys
payload=json.load(sys.stdin); key=payload["api_key"]; prompt=payload["prompt"]
env=os.environ.copy(); env.update({"OPENROUTER_API_KEY":key,"HERMES_HOME":"/opt/data/profiles/nova_nexus","HERMES_PROFILE":"nova_nexus"})
fd,path=tempfile.mkstemp(prefix="rr-usage-",suffix=".json",dir="/tmp"); os.close(fd)
try:
 cmd=["/opt/hermes/.venv/bin/hermes","-z",prompt,"--safe-mode","--model","google/gemini-2.5-flash-lite","--provider","openrouter","--usage-file",path]
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=22,check=False,env=env)
  try: usage=json.load(open(path,encoding="utf-8"))
  except Exception: usage={}
  print(json.dumps({"returncode":r.returncode,"text":r.stdout.strip(),"stderr":r.stderr[-500:],"usage":usage}))
 except subprocess.TimeoutExpired: print(json.dumps({"returncode":124,"text":"","stderr":"HERMES_ONESHOT_TIMEOUT","usage":{}}))
finally:
 try: os.unlink(path)
 except OSError: pass
'''
        remote = "podman exec -i nexus-hermes-0206 python3 -c " + shlex.quote(script)
        started = time.monotonic()
        def invoke() -> dict[str, Any]:
            try:
                completed = subprocess.run(["/usr/bin/ssh", "-i", key_path, "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=accept-new",
                    f"{user}@{host}", remote], input=json.dumps({"api_key": api_key, "prompt": prompt}),
                    text=True, capture_output=True, timeout=30, check=False)
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("HERMES_OPENROUTER_TIMEOUT") from exc
            if completed.returncode:
                raise RuntimeError("HERMES_SSH_EXIT_" + str(completed.returncode) + ":" + completed.stderr[-360:])
            try:
                envelope = json.loads(completed.stdout.strip())
            except ValueError as exc:
                raise RuntimeError("HERMES_INVALID_RESPONSE_ENVELOPE") from exc
            if envelope.get("returncode") != 0 or not str(envelope.get("text") or "").strip():
                raise RuntimeError(str(envelope.get("stderr") or "HERMES_PROVIDER_CALL_FAILED")[:500])
            parsed = parse_advisor_content(envelope["text"])
            raw_usage = envelope.get("usage") or {}
            usage = {name: raw_usage[name] for name in ("input_tokens", "output_tokens", "total_tokens")
                     if isinstance(raw_usage.get(name), (int, float))}
            cost = None
            if all(k in usage for k in ("input_tokens", "output_tokens")):
                cost = float(usage["input_tokens"]) * 0.0000001 + float(usage["output_tokens"]) * 0.0000004
            return {"status": "COMPLETED", "provider": self.provider, "runtime": self.runtime,
                "model": self.model, "usage": usage, "estimated_cost_usd": cost,
                "duration_ms": (time.monotonic() - started) * 1000, **parsed}

        return _execute_shadow_openrouter(case_context, role, invoke, model=self.model,
            input_price=0.0000001, output_price=0.0000004, max_output_tokens=700)


def _execute_shadow_openrouter(case_context: dict[str, Any], role: str, invoke: Any, *,
                               model: str, input_price: float, output_price: float,
                               max_output_tokens: int) -> dict[str, Any]:
    """One governed, capped OpenRouter action in an isolated shadow identity."""
    import os
    from nexus_agent_platform.resource_spend_governor import default_store
    from nexus_agent_platform.provider_enforcement import execute
    store = default_store()
    free_route = input_price == 0.0 and output_price == 0.0 and model.endswith(":free")
    service = "research_room_advisor_free" if free_route else "research_room_advisor"
    production_case = os.environ.get("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE") == "true"
    # The zero-priced route has a separate bounded token/request envelope. It
    # cannot spend money and does not inherit the metered route's exhausted
    # token circuit; all metered calls remain under the existing hard limits.
    hard = {"rate": {"requests": 2, "operations": 2, "window_seconds": 60},
        "usage": {"requests": 12, "operations": 12, "tokens": 30000, "runtime_seconds": 180, "bytes": 1000000},
        "money": {"per_job": 0.05, "per_day": 0.05, "per_month": 0.50}}
    soft = {"rate": {"requests": 2, "operations": 2, "window_seconds": 60},
        "usage": {"requests": 8, "operations": 8, "tokens": 24000, "runtime_seconds": 120, "bytes": 1000000},
        "money": {"per_job": 0.01, "per_day": 0.03, "per_month": 0.25}}
    case_id = str(case_context.get("case_id", "research-room-case"))
    prior = {name: os.environ.get(name) for name in ("NEXUS_DURABLE_JOB_ID", "NEXUS_CORRELATION_ID",
        "NEXUS_DURABLE_EXECUTION_ID", "NEXUS_DEPARTMENT", "NEXUS_JOB_TYPE", "NEXUS_JOB_BUDGET")}
    if production_case:
        job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
        if not job_id or not os.environ.get("NEXUS_CORRELATION_ID"):
            raise RuntimeError("PRODUCTION_ADVISOR_GOVERNANCE_CONTEXT_REQUIRED")
        job_type = os.environ.get("NEXUS_JOB_TYPE", "RESEARCH_CASE_CONTINUATION")
    else:
        job_id = "rr-shadow-" + case_id
        job_type = "RESEARCH_ROOM_SHADOW_ADVISOR"
        os.environ.update({"NEXUS_DURABLE_JOB_ID": job_id, "NEXUS_CORRELATION_ID": job_id,
            "NEXUS_DURABLE_EXECUTION_ID": "shadow-" + case_id, "NEXUS_DEPARTMENT": "RESEARCH",
            "NEXUS_JOB_TYPE": job_type,
            "NEXUS_JOB_BUDGET": json.dumps({"max_requests": 30, "max_response_bytes": 2000000,
                "max_tokens": 30000, "max_runtime_seconds": 90, "max_estimated_cost": 0.025})})
    try:
        if free_route:
            free_hard = {"rate": {"requests": 2, "operations": 2, "window_seconds": 60},
                "usage": {"requests": 4, "operations": 4, "tokens": 8000, "runtime_seconds": 180, "bytes": 1000000},
                "money": {"per_job": 0.01, "per_day": 0.01, "per_month": 0.05}}
            free_soft = {"rate": {"requests": 1, "operations": 1, "window_seconds": 60},
                "usage": {"requests": 2, "operations": 2, "tokens": 4000, "runtime_seconds": 90, "bytes": 500000},
                "money": {"per_job": 0.0, "per_day": 0.0, "per_month": 0.0}}
            store.ensure_policy("OPENROUTER", service, job_type, "DAILY",
                autonomous_usage_allowed=True, autonomous_spend_allowed=False, soft_limits=free_soft,
                hard_limits=free_hard, concurrency_limit=1, state="NORMAL", approval_required=False)
        else:
            store.ensure_policy("OPENROUTER", service, job_type, "DAILY",
                autonomous_usage_allowed=True, autonomous_spend_allowed=not production_case, soft_limits=soft,
                hard_limits=({**hard, "money": {"per_job": 0, "per_day": 0, "per_month": 0}}
                    if production_case else hard), concurrency_limit=1, state="NORMAL",
                approval_required=production_case)
        # Prompt is capped at 10,000 characters; reserve from that bound and
        # the provider's output cap, with a 25% estimation margin.
        prompt_tokens = 2500
        estimate_cost = round((prompt_tokens * input_price + max_output_tokens * output_price) * 1.25, 8)
        return execute("OPENROUTER", service, "MODEL_INFERENCE",
            {"requests": 1, "operations": 1, "tokens": prompt_tokens + max_output_tokens, "runtime_seconds": 30,
             "cost": estimate_cost, "billable": True, "budget_period": "DAILY"}, invoke,
            job_id=job_id, job_type=job_type,
            correlation_id=os.environ.get("NEXUS_CORRELATION_ID") or job_id,
            purpose=f"shadow-advisor:{case_id}:{role}",
            actual_usage=lambda value: {"requests": 1, "operations": 1,
                "tokens": int((value.get("usage") or {}).get("total_tokens", prompt_tokens + max_output_tokens)),
                "runtime_seconds": max(0.0, float(value.get("duration_ms", 0)) / 1000),
                "cost": value.get("estimated_cost_usd", estimate_cost)})
    finally:
        if not production_case:
            for name, value in prior.items():
                if value is None: os.environ.pop(name, None)
                else: os.environ[name] = value


def parse_advisor_content(text: str) -> dict[str, Any]:
    """Keep usable model analysis even when the provider ignores JSON format."""
    value = str(text or "").strip()
    if _looks_like_provider_error(value):
        raise ValueError("ADVISOR_PROVIDER_ERROR_RESPONSE")
    candidates = [value]
    if value.startswith("```"):
        candidates.append(value.strip("`\n "))
        fenced = value.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        candidates.append(fenced)
    left, right = value.find("{"), value.rfind("}")
    if left >= 0 and right > left:
        candidates.append(value[left:right + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(parsed, dict):
            if not parsed.get("analysis"):
                parsed["analysis"] = value[:4000]
            return parsed
    if not value:
        raise ValueError("ADVISOR_RESPONSE_EMPTY")
    sections = {}
    current = None
    for line in value.splitlines():
        heading = line.strip().strip("#* ").rstrip(":").upper().replace(" ", "_")
        canonical = {"ADVISOR_ANALYSIS": "analysis", "NEW_QUESTIONS": "new_questions",
            "RISKS": "risks", "OPPORTUNITIES": "opportunities", "RECOMMENDED_ACTIONS": "recommended_actions",
            "CONFIDENCE": "confidence", "EVIDENCE_NOTES": "evidence_notes"}.get(heading)
        if canonical:
            current = canonical
            sections.setdefault(current, [])
            continue
        if current and line.strip():
            sections[current].append(line.strip())
    parsed = {key: "\n".join(rows)[:1800] for key, rows in sections.items()}
    for key in ("new_questions", "risks", "opportunities", "recommended_actions", "evidence_notes"):
        if key in parsed:
            parsed[key] = [row.lstrip("-*•0123456789. ").strip() for row in parsed[key].splitlines()
                if row.strip()]
    parsed.setdefault("analysis", value[:4000])
    parsed["response_format"] = "LABELED_TEXT" if sections else "PLAIN_TEXT"
    return parsed


def _looks_like_provider_error(text: str) -> bool:
    value = str(text or "").strip()
    return bool(value and (
        value.startswith(("HTTP 4", "HTTP 5", "Error code:"))
        or " model is not supported when using Codex " in value
        or value.startswith("API request failed")
        or value.startswith("{\"error\"")
    ))


class AdvisorRouter:
    def __init__(self, providers: list[Advisor] | None = None, attempt_recorder: Any = None,
                 free_only: bool = False, technical_provider: Advisor | None = None):
        self.attempt_recorder = attempt_recorder
        self.free_only = free_only
        self.technical_provider = technical_provider
        self._provider_attempt_started_at: dict[str, str] = {}
        if providers is not None:
            self.providers = providers
        else:
            connector = _configured_chatgpt_connector()
            self.technical_provider = self.technical_provider or CodexTechnicalAdvisor(connector)
            free_models = [OpenRouterFreeAdvisor.model]
            free_models.extend(str(value).strip() for value in
                __import__("os").getenv("NEXUS_RESEARCH_OPENROUTER_FREE_FALLBACK_MODELS", "").split(",")
                if str(value).strip())
            # One primary free model plus at most one explicitly configured
            # alternate prevents unbounded model fan-out.
            free_models = list(dict.fromkeys(model for model in free_models if model.endswith(":free")))[:2]
            self.providers = [ChatGPTAdvisor(connector),
                *(OpenRouterFreeAdvisor(model) for model in free_models),
                NexusGatewayAdvisor.configured(), OpenRouterHostedAdvisor(), HermesOpenRouterAdvisor()]
        self.providers = [provider for provider in self.providers
            if str(getattr(provider, "provider", "")).upper() not in RESEARCH_LOCAL_ADVISOR_DENYLIST
            and "OLLAMA" not in type(provider).__name__.upper()
            and "LOCAL_LLM" not in type(provider).__name__.upper()]
        if free_only:
            allowed_classes = {"FREE_ZERO_PRICED", "CHATGPT_PLAN_INCLUDED"}
            allowed_providers = {"CHATGPT_PLAN", "CHATGPT_CONNECTOR", "OPENROUTER", "CODEX"}
            self.providers = [provider for provider in self.providers
                if getattr(provider, "free_or_metered", "") in allowed_classes
                and str(getattr(provider, "provider", "")).upper() in allowed_providers
                and "LOCAL" not in str(getattr(provider, "provider", "")).upper()
                and "OLLAMA" not in type(provider).__name__.upper()
                and (getattr(provider, "free_or_metered", "") != "FREE_ZERO_PRICED"
                    or (str(getattr(provider, "provider", "")).upper() == "OPENROUTER"
                        and str(getattr(provider, "model", "")).endswith(":free")))]

    @staticmethod
    def _zero_new_spend_provider(provider: Any) -> bool:
        name = str(getattr(provider, "provider", "")).upper()
        route_class = getattr(provider, "free_or_metered", "METERED")
        return (name in {"CHATGPT_PLAN", "CHATGPT_CONNECTOR", "CODEX"}
                and route_class == "CHATGPT_PLAN_INCLUDED") or (
                name == "OPENROUTER" and route_class == "FREE_ZERO_PRICED"
                and str(getattr(provider, "model", "")).endswith(":free"))

    def _record_attempt(self, *, provider: Any, role: str, status: str,
                        error: str | None = None, cost: float | None = None,
                        attempt_id: str | None = None) -> str | None:
        if not self.attempt_recorder:
            return None
        provider_attempt_id = attempt_id or "rradvroute_" + uuid.uuid4().hex[:16]
        route_class = getattr(provider, "free_or_metered", "METERED")
        incremental_cost = cost
        if incremental_cost is None and route_class in {"FREE_ZERO_PRICED", "CHATGPT_PLAN_INCLUDED"}:
            incremental_cost = 0.0
        failure_code = None
        if error:
            detail = str(error)
            failure_code = ("GOVERNANCE_DENIED" if "governance" in detail.casefold() else
                "TIMEOUT" if "timeout" in detail.casefold() else type(error).__name__)
        row = {"attempt_id": provider_attempt_id, "provider_attempt_id": provider_attempt_id,
            "provider": getattr(provider, "provider", "UNKNOWN"),
            "model": getattr(provider, "model", None), "role": role, "status": status,
            "result": status, "error_code": failure_code,
            "error_summary": str(error)[:300] if error else None,
            "incremental_cost": incremental_cost, "cost": cost}
        now = datetime.now(timezone.utc).isoformat()
        if status == "STARTED":
            self._provider_attempt_started_at[provider_attempt_id] = now
            row["started_at"] = now
        else:
            row["started_at"] = self._provider_attempt_started_at.get(provider_attempt_id)
            row["completed_at"] = now
        try:
            return self.attempt_recorder(row) or provider_attempt_id
        except Exception as exc:
            raise RuntimeError("ADVISOR_ATTEMPT_PERSISTENCE_FAILED") from exc

    @staticmethod
    def _reserve_plan_included_research(provider: Any, attempt_id: str | None):
        """Require the durable zero-spend policy before a production plan call.

        Disposable Research state is deliberately separate from provider
        governance.  Production Research Room calls therefore resolve policy
        through the configured governor store, while tests may inject a local
        store with the same scoped policy contract.
        """
        import os
        if (not attempt_id or not os.environ.get("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE")
                or str(getattr(provider, "provider", "")).upper() != "CHATGPT_PLAN"
                or getattr(provider, "free_or_metered", "") != "CHATGPT_PLAN_INCLUDED"):
            return None
        job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
        if not job_id:
            from nexus_agent_platform.resource_spend_governor import GovernanceDenied
            raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "DURABLE_JOB_ID_REQUIRED")
        from nexus_agent_platform.resource_spend_governor import default_store
        governor = default_store()
        reservation = governor.reserve("CHATGPT_PLAN", "RESEARCH_ADVISOR",
            "RESEARCH_ROOM_ADVISOR", attempt_id,
            {"requests": 1, "cost": 0.0, "billable": False},
            purpose="plan-included-research-advisor")
        return governor, reservation

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        failures = []
        providers = list(self.providers)
        metadata = case_context.get("metadata") or {}
        specialist = str(metadata.get("advisor_specialist") or metadata.get("advisor_preference") or "").upper()
        research_type = str(metadata.get("research_type") or metadata.get("room_category") or "").upper()
        technical_request = bool(metadata.get("technical_analysis_required")) or specialist == "CODEX" or research_type in {
            "CODE", "CODEX", "REPOSITORY", "SYSTEMS", "TECHNICAL", "TECHNICAL_RESEARCH"}
        if (technical_request and self.technical_provider is not None
                and self.technical_provider.available
                and (not self.free_only or self._zero_new_spend_provider(self.technical_provider))):
            providers = [self.technical_provider,
                *[provider for provider in providers if provider is not self.technical_provider]]
        daily_spend_known = isinstance(metadata.get("daily_research_spend_usd"), (int, float))
        if metadata.get("daily_research_spend_usd") is None:
            daily_spend = _current_daily_research_spend()
            if daily_spend is not None:
                metadata["daily_research_spend_usd"] = daily_spend
                daily_spend_known = True
        complexity = str(metadata.get("research_complexity") or "").upper()
        high_value = bool(metadata.get("high_value_case")) or complexity in {"HIGH", "CRITICAL"} or any(
            marker in str(objective).casefold() for marker in ("contradictory evidence", "material advisor disagreement", "high-value decision"))
        if high_value and not daily_spend_known:
            # Do not escalate to the more expensive model without visibility
            # into the scoped daily spend; use the proven default route.
            high_value = False
        if high_value:
            strong = next((p for p in providers if isinstance(p, StrongOpenRouterAdvisor)), None)
            if strong is None:
                strong = StrongOpenRouterAdvisor()
            if strong is not None:
                providers = [p for p in providers if p is not strong] + [strong]
        fallback_model_used = "NONE"
        for provider_index, provider in enumerate(providers):
            if provider.available:
                route_key = getattr(provider, "health_key", provider.provider)
                health = case_context.setdefault("provider_health", {}).get(route_key, {})
                until = health.get("cooldown_until")
                if until:
                    try:
                        if datetime.fromisoformat(str(until).replace("Z", "+00:00")) > datetime.now(timezone.utc):
                            failures.append({"status": "ADVISOR_DEPRIORITIZED", "provider": provider.provider,
                                "reason": "provider_cooldown_active"})
                            self._record_attempt(provider=provider, role=role,
                                status="SKIPPED_COOLDOWN", error="provider_cooldown_active")
                            continue
                    except ValueError:
                        pass
                context = compact_context(case_context, role=role)
                context["case_id"] = str(case_context.get("case_id") or "research-room-case")
                source_report = case_context.get("source_report") or {}
                source_hash = source_report.get("source_content_hash") or hashlib.sha256(
                    json.dumps(case_context.get("source_references", []),
                        sort_keys=True, default=str).encode()).hexdigest()
                cache_material = {"case_id": case_context.get("case_id"),
                    "source_hash": source_hash,
                    "question": objective, "role": role, "provider": provider.provider,
                    "model": getattr(provider, "model", "AUTO"), "prompt_version": PROMPT_VERSION}
                cache_key = hashlib.sha256(json.dumps(cache_material, sort_keys=True).encode()).hexdigest()
                cached = case_context.setdefault("advisor_cache", {}).get(cache_key)
                if cached is not None:
                    result = dict(cached)
                    record_call(case_context, provider=result.get("provider", provider.provider),
                        model=result.get("model"), role=role, usage={}, cost_usd=0,
                        duration_ms=0, purpose="cached:" + role, cache_hit=True)
                    result["cache_hit"] = True
                    return result
                # Soft budgets stop additional paid calls, never the room.
                # Reuse still gets first priority above; participants and the
                # deterministic synthesizer continue with persisted evidence.
                ledger = case_context.get("model_usage") or {}
                spent = ledger.get("estimated_total_cost_usd", 0)
                try:
                    spent = float(spent)
                except (TypeError, ValueError):
                    spent = 0.0
                metadata = case_context.get("metadata") or {}
                case_target = float(metadata.get("per_case_soft_target_usd", 0.01))
                daily_target = float(metadata.get("daily_research_soft_target_usd", 0.03))
                call_target = float(metadata.get("per_call_soft_target_usd", 0.01))
                daily_spent = float(metadata.get("daily_research_spend_usd", 0.0) or 0.0)
                input_price = float(getattr(provider, "input_price_per_token", 0.0000001))
                output_price = float(getattr(provider, "output_price_per_token", 0.0000004))
                output_cap = int(getattr(provider, "max_output_tokens", 700))
                input_bound = max(1, (len(json.dumps(context, ensure_ascii=False, default=str)) + 500) // 4)
                projected_cost = (input_bound * input_price + output_cap * output_price) * 1.25
                cheaper_default_available = any(candidate.available and
                    getattr(candidate, "model", None) == OpenRouterHostedAdvisor.model
                    for candidate in providers[provider_index + 1:])
                metered = getattr(provider, "free_or_metered", "METERED") == "METERED"
                if metered and (spent + projected_cost > case_target or daily_spent + projected_cost > daily_target):
                    failures.append({"status": "COST_BUDGET_PRESSURE", "provider": provider.provider,
                        "model": getattr(provider, "model", None), "reason": "soft_research_target_would_be_exceeded",
                        "projected_cost_usd": round(projected_cost, 8)})
                    case_context.setdefault("cost_routing", {}).update({
                        "state": "SOFT_TARGET_REACHED", "action": "SELECT_CHEAPER_ROUTE_OR_SYNTHESIZE",
                        "case_spend_usd": spent, "daily_spend_usd": daily_spent,
                        "projected_call_cost_usd": round(projected_cost, 8),
                        "paid_call_skipped": not cheaper_default_available})
                    if cheaper_default_available:
                        self._record_attempt(provider=provider, role=role,
                            status="SKIPPED_COST_GUARD", error="soft_research_budget_would_be_exceeded",
                            cost=round(projected_cost, 8))
                        continue
                    self._record_attempt(provider=provider, role=role,
                        status="SKIPPED_COST_GUARD", error="soft_research_budget_would_be_exceeded",
                        cost=round(projected_cost, 8))
                    return {"status": "COST_BUDGET_PRESSURE", "provider": "NONE", "analysis": None,
                        "new_questions": [], "reason": "soft_research_budget_reached",
                        "cost_routing": dict(case_context.get("cost_routing") or {}),
                        "provider_failures": failures}
                if metered and projected_cost > call_target:
                    failures.append({"status": "COST_BUDGET_PRESSURE", "provider": provider.provider,
                        "model": getattr(provider, "model", None), "reason": "per_call_soft_target_would_be_exceeded",
                        "projected_cost_usd": round(projected_cost, 8)})
                    case_context.setdefault("cost_routing", {}).update({
                        "state": "SOFT_TARGET_REACHED", "action": "SELECT_CHEAPER_ROUTE_OR_SYNTHESIZE",
                        "projected_call_cost_usd": round(projected_cost, 8), "per_call_target_usd": call_target})
                    # Strong models may yield to the already configured default.
                    if cheaper_default_available:
                        self._record_attempt(provider=provider, role=role,
                            status="SKIPPED_COST_GUARD", error="per_call_soft_target_would_be_exceeded",
                            cost=round(projected_cost, 8))
                        continue
                    self._record_attempt(provider=provider, role=role,
                        status="SKIPPED_COST_GUARD", error="per_call_soft_target_would_be_exceeded",
                        cost=round(projected_cost, 8))
                    return {"status": "COST_BUDGET_PRESSURE", "provider": "NONE", "analysis": None,
                        "new_questions": [], "reason": "per_call_soft_target_would_be_exceeded",
                        "cost_routing": dict(case_context.get("cost_routing") or {}),
                        "provider_failures": failures}
                started = time.monotonic()
                provider_attempt_id = self._record_attempt(provider=provider, role=role, status="STARTED")
                plan_reservation = None
                try:
                    plan_reservation = self._reserve_plan_included_research(provider, provider_attempt_id)
                    result = provider.ask(role=role, case_context=context, objective=objective)
                    if (str(result.get("status") or "").upper() in {
                            "ADVISOR_UNAVAILABLE", "FAILED", "TIMEOUT", "ERROR"}
                            or not str(result.get("analysis") or "").strip()):
                        raise RuntimeError(str(result.get("reason") or "ADVISOR_EMPTY_OR_UNAVAILABLE"))
                    result.setdefault("provider", provider.provider)
                    route_class = getattr(provider, "free_or_metered", "METERED")
                    route_tier = {"FREE_ZERO_PRICED": 1, "CHATGPT_PLAN_INCLUDED": 2,
                        "SUBSCRIPTION_INCLUDED": 3, "METERED": 4, "STRONG_METERED": 5,
                        "BACKGROUND_FALLBACK": 6}.get(route_class, 4)
                    selected_free = route_class == "FREE_ZERO_PRICED"
                    selected_chatgpt = route_class == "CHATGPT_PLAN_INCLUDED"
                    free_already_used = any(row.get("status") == "COMPLETED"
                        and row.get("provider") == "OPENROUTER"
                        and str(row.get("model", "")).endswith(":free")
                        for row in case_context.get("advisor_comments", []))
                    routing = {
                        "tier": route_tier,
                        "why_route_selected": ("authenticated zero-priced hosted route tested usable"
                            if selected_free else "existing ChatGPT plan-backed Codex CLI route"
                            if selected_chatgpt else "lowest-cost sufficient configured metered route after earlier tiers unavailable or unsuitable"),
                        "why_free_route_not_used": next((x.get("reason", x.get("status")) for x in failures
                            if x.get("provider") == "OPENROUTER" and str(x.get("model", "")).endswith(":free")),
                            "NOT_APPLICABLE_SELECTED_FREE_ROUTE" if selected_free else
                            ("free route already supplied a distinct Advisor 1 response; use the next tier for perspective diversity"
                                if free_already_used else
                            (case_context.get("provider_health", {}).get("OPENROUTER_FREE_LIQUID", {}).get("last_failure")
                                or "free route unavailable or degraded"))),
                        "why_chatgpt_route_not_used": ("NOT_APPLICABLE_SELECTED_CHATGPT_PLAN_ROUTE" if selected_chatgpt else
                            next((x.get("reason", x.get("status")) for x in failures
                                if x.get("provider") in {"CHATGPT_CONNECTOR", "CHATGPT_PLAN"}),
                                "ChatGPT route unavailable, previously used, or not eligible in this participant turn")),
                        "why_subscription_route_not_used": ("NOT_APPLICABLE_SELECTED_SUBSCRIPTION_ROUTE" if route_tier == 3 else
                            "no other configured subscription-included advisor runtime was available"),
                    }
                    result["routing_decision"] = routing
                    record_call(case_context, provider=result.get("provider", provider.provider),
                        model=result.get("model"), role=role, usage=result.get("usage"),
                        cost_usd=result.get("estimated_cost_usd"),
                        duration_ms=float(result.get("duration_ms") or ((time.monotonic()-started)*1000)),
                        purpose=role, runtime=result.get("runtime"),
                        fallback_model_used=result.get("model") if failures else None,
                        provider_request_id=result.get("provider_request_id"))
                    case_context["model_usage"]["calls"][-1].update(routing)
                    self._record_attempt(provider=provider, role=role, status="COMPLETED",
                        cost=result.get("estimated_cost_usd"), attempt_id=provider_attempt_id)
                    case_context.setdefault("provider_health", {})[route_key] = {"state": "AVAILABLE",
                        "last_success": datetime.now(timezone.utc).isoformat(), "cooldown_until": None}
                    result["cache_hit"] = False
                    case_context.setdefault("advisor_cache", {})[cache_key] = dict(result)
                    return result
                except Exception as exc:
                    # Preserve provider failure as evidence and fall through.
                    reason = f"{type(exc).__name__}: {exc}"
                    if str(exc) == "ADVISOR_ATTEMPT_PERSISTENCE_FAILED":
                        raise
                    self._record_attempt(provider=provider, role=role,
                        status="TIMEOUT" if "timeout" in reason.casefold() else "FAILED",
                        error=reason, attempt_id=provider_attempt_id)
                    if (str(getattr(provider, "provider", "")).upper() == "CHATGPT_PLAN"
                            and any(code in reason for code in ("USAGE_NOT_AUTHORIZED",
                                "HUMAN_APPROVAL_REQUIRED", "UNKNOWN_PAID_PROVIDER", "POLICY_DENIED"))):
                        failure_call = record_call(case_context, provider=provider.provider,
                            model=getattr(provider, "model", None), role=role, usage={}, cost_usd=0,
                            duration_ms=float((time.monotonic()-started)*1000), purpose=role,
                            runtime=getattr(provider, "runtime", None), count_for_totals=False)
                        failure_call.update({"result_state": "AUTHORIZATION_REQUIRED",
                            "failure_reason": reason[:500]})
                        return {"status": "AUTHORIZATION_REQUIRED", "provider": "NONE",
                            "analysis": None, "new_questions": [], "reason": reason[:300],
                            "provider_failures": failures + [{"status": "POLICY_DENIED",
                                "provider": provider.provider, "reason": reason[:300]}]}
                    if "governance" in reason.casefold() or "hard_stop" in reason.casefold() or "budget" in reason.casefold():
                        failure_call = record_call(case_context, provider=provider.provider,
                            model=getattr(provider, "model", None), role=role, usage={}, cost_usd=0,
                            duration_ms=float((time.monotonic()-started)*1000), purpose=role,
                            runtime=getattr(provider, "runtime", None), count_for_totals=False)
                        failure_call.update({"result_state": "COST_BUDGET_PRESSURE", "failure_reason": reason[:500]})
                        case_context.setdefault("cost_routing", {}).update({
                            "state": "SOFT_TARGET_REACHED", "action": "REUSE_OR_SYNTHESIZE_WITH_AVAILABLE_EVIDENCE",
                            "paid_call_skipped": True})
                        case_context.setdefault("provider_health", {})[route_key] = {
                            "state": "AVAILABLE", "budget_pressure": True,
                            "last_budget_pressure": datetime.now(timezone.utc).isoformat()}
                        if self.free_only and provider_index + 1 < len(providers):
                            failures.append({"status": "PROVIDER_POLICY_BLOCKED",
                                "provider": provider.provider, "reason": reason[:300]})
                            continue
                        return {"status": "COST_BUDGET_PRESSURE", "provider": "NONE", "analysis": None,
                            "new_questions": [], "reason": reason[:300],
                            "cost_routing": dict(case_context.get("cost_routing") or {}), "provider_failures": failures + [
                                {"status": "COST_BUDGET_PRESSURE", "provider": provider.provider,
                                 "reason": reason[:300]}]}
                    failure_call = record_call(case_context, provider=provider.provider,
                        model=getattr(provider, "model", None), role=role, usage={}, cost_usd=None,
                        duration_ms=float((time.monotonic()-started)*1000), purpose=role,
                        runtime=getattr(provider, "runtime", None), timeout="timeout" in str(exc).casefold())
                    failure_call.update({"result_state": "FAILED", "failure_reason": reason[:500]})
                    case_context.setdefault("provider_health", {})[route_key] = {
                        "state": "TIMED_OUT" if "timeout" in reason.casefold() else "DEGRADED",
                        "last_failure": reason[:300],
                        "cooldown_until": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
                    }
                    failures.append({"status": "ADVISOR_UNAVAILABLE", "provider": provider.provider,
                                     "reason": reason})
                    fallback_model_used = getattr(provider, "model", None) or provider.provider
                    continue
                finally:
                    if plan_reservation:
                        governor, reservation = plan_reservation
                        governor.reconcile(reservation["reservation_id"], {"requests": 1, "cost": 0.0})
        return {"status": "ADVISOR_UNAVAILABLE", "provider": "NONE", "analysis": None,
                "new_questions": [], "reason": "no_connected_advisor", "provider_failures": failures}


def select_domain(context: dict[str, Any]) -> str:
    """Late-bind expertise after the source is understood; unknown is allowed."""
    source = context.get("source_report") or {}
    text = " ".join(str(value or "") for value in (
        context.get("original_request"), source.get("title"), source.get("text"),
        context.get("metadata", {}).get("category"))).casefold()
    for domain, terms in (
        ("TRADING", ("trading", "strategy", "futures", "backtest", "indicator")),
        ("FUNDING", ("funding", "credit", "lender", "grant")),
        ("BUSINESS", ("business", "opportunity", "customer", "pricing", "marketplace")),
        ("MARKETING", ("marketing", "campaign", "audience", "promotion")),
        ("TECHNICAL", ("api", "software", "integration", "code", "system")),
        ("OPERATIONS", ("fulfillment", "workflow", "operations", "logistics")),
        ("CREATIVE", ("design", "creative", "brand", "logo")),
    ):
        if any(term in text for term in terms):
            return domain
    return "GENERAL"


def _current_daily_research_spend() -> float | None:
    """Read reconciled plus active spend in this exact Research Room scope."""
    from datetime import datetime, timezone
    boundary = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        from nexus_agent_platform.resource_spend_governor import LocalGovernorStore, default_store
        store = default_store()
        if isinstance(store, LocalGovernorStore):
            with store.connect() as db:
                rows = db.execute("SELECT estimate,actual,status,created_at FROM reservations WHERE provider=? "
                    "AND service=? AND job_type=? AND budget_period='DAILY' AND status IN ('ACTIVE','RECONCILED')",
                    ("OPENROUTER", "research_room_advisor", "RESEARCH_ROOM_SHADOW_ADVISOR")).fetchall()
            total = 0.0
            for row in rows:
                try:
                    created = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
                    if created < boundary: continue
                    actual = json.loads(row["actual"] or "{}")
                    estimate = json.loads(row["estimate"] or "{}")
                    total += float(actual.get("cost", estimate.get("cost", 0)) or 0)
                except (TypeError, ValueError, json.JSONDecodeError):
                    return None
            return total
        start = boundary.isoformat().replace("+", "%2B")
        rows = store._request("nexus_resource_reservations?provider=eq.OPENROUTER&service=eq.research_room_advisor"
            "&job_type=eq.RESEARCH_ROOM_SHADOW_ADVISOR&budget_period=eq.DAILY&status=in.(ACTIVE,RECONCILED)"
            f"&created_at=gte.{start}&select=estimate,actual,status") or []
        return sum(float(((row.get("actual") or {}).get("cost"))
            if isinstance((row.get("actual") or {}).get("cost"), (int, float))
            else ((row.get("estimate") or {}).get("cost") or 0)) for row in rows)
    except Exception:
        # Unknown soft usage keeps the fast default; the scoped hard governor
        # still authorizes every paid request and enforces the hard boundary.
        return None


def lead_advisor_plan(case: dict[str, Any], *, purpose: str = "domain understanding") -> dict[str, Any]:
    """Cheap, explicit cost guidance; it never blocks Research progress."""
    has_prior = bool(case.get("prior_nexus_knowledge"))
    existing_calls = int((case.get("model_usage") or {}).get("total_model_calls", 0))
    return {"next_participant": "DOMAIN_ADVISOR" if not case.get("advisor_comments") else "FACT_CHECKER",
        "purpose": purpose, "expected_information_gain": "MEDIUM" if not has_prior else "LOW_TO_MEDIUM",
        "estimated_cost_class": "LOW", "reuse_existing_context": True,
        "need_new_model_call": not bool(case.get("advisor_comments")) and existing_calls == 0}
