"""No-tool Research Room advisor using the already-running Oracle Ollama model."""
from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any


REMOTE_SCRIPT = r'''import json,sys,urllib.request
p=json.load(sys.stdin)
body=json.dumps({"model":"gemma3:4b","messages":p["messages"],"stream":False,"format":{"type":"object","properties":{"analysis":{"type":"string"},"new_questions":{"type":"array","items":{"type":"string"}},"risks":{"type":"array","items":{"type":"string"}},"opportunities":{"type":"array","items":{"type":"string"}},"recommended_actions":{"type":"array","items":{"type":"string"}}},"required":["analysis","new_questions","risks","opportunities","recommended_actions"],"additionalProperties":False},"options":{"num_predict":500,"num_ctx":3072,"temperature":0.2}}).encode()
req=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=body,headers={"Content-Type":"application/json"},method="POST")
with urllib.request.urlopen(req,timeout=90) as r: print(r.read().decode())
'''


class OracleLocalOllamaAdvisor:
    provider = "OLLAMA_LOCAL"
    model = "gemma3:4b"
    available = True
    free_or_metered = "FREE_ZERO_PRICED"
    input_price_per_token = 0.0
    output_price_per_token = 0.0
    max_output_tokens = 500

    def __init__(self, *, transport: Any = None):
        self.transport = transport or self._ssh_ollama

    @staticmethod
    def _ensure_zero_spend_policy(*, service: str = "shadow_advisor",
                                  job_type: str = "RESEARCH_ROOM_SHADOW_ADVISOR") -> None:
        from nexus_agent_platform.resource_spend_governor import default_store
        store = default_store()
        limits = {"rate": {"requests": 8, "operations": 8, "window_seconds": 60},
            "usage": {"requests": 20, "operations": 20, "tokens": 20000,
                "runtime_seconds": 2400, "bytes": 3000000},
            "money": {"per_job": 0, "per_day": 0, "per_month": 0}}
        for period in ("DAILY", "MONTHLY"):
            store.ensure_policy("OLLAMA_LOCAL", service, job_type, period,
                autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                soft_limits=limits, hard_limits=limits, concurrency_limit=1, state="NORMAL",
                approval_required=False)

    @staticmethod
    def _ssh_ollama(payload: dict[str, Any]) -> dict[str, Any]:
        from nexus_agent_platform.bridge.oracle_hermes_cli import ORACLE_HOST, ORACLE_USER, ORACLE_KEY, ORACLE_CONTAINER
        script = "python3 -c " + __import__("shlex").quote(REMOTE_SCRIPT)
        command = ["/usr/bin/ssh", "-i", ORACLE_KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2", "-o", "StrictHostKeyChecking=accept-new",
            f"{ORACLE_USER}@{ORACLE_HOST}", f"podman exec -i {ORACLE_CONTAINER} sh -lc {__import__('shlex').quote(script)}"]
        done = subprocess.run(command, input=json.dumps(payload, ensure_ascii=False), text=True,
            capture_output=True, timeout=100, check=False)
        if done.returncode != 0:
            detail = (done.stderr or "").strip().replace("\n", " ")[-320:]
            raise RuntimeError(f"ORACLE_LOCAL_OLLAMA_EXIT_{done.returncode}:{detail}")
        try:
            value = json.loads(done.stdout)
        except Exception as exc:
            raise ValueError("ORACLE_LOCAL_OLLAMA_INVALID_JSON_RESPONSE") from exc
        return value

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        job_id = os.environ.get("NEXUS_DURABLE_JOB_ID")
        correlation_id = os.environ.get("NEXUS_CORRELATION_ID")
        if not job_id or not correlation_id or not os.environ.get("NEXUS_DEPARTMENT"):
            raise RuntimeError("SHADOW_ADVISOR_GOVERNANCE_CONTEXT_REQUIRED")
        production_case = os.environ.get("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE") == "true"
        service = "research_room_controller" if production_case else "shadow_advisor"
        job_type = "RESEARCH_CASE_CONTINUATION" if production_case else "RESEARCH_ROOM_SHADOW_ADVISOR"
        self._ensure_zero_spend_policy(service=service, job_type=job_type)
        from nexus_agent_platform.provider_enforcement import execute
        messages = [
            {"role": "system", "content": "You are a specialist advisor in a Research Room. Use only this compact case context; no tools or external actions. Return concise valid JSON with analysis, new_questions (up to 2), risks (up to 2), opportunities, and recommended_actions (up to 2). Information gaps are findings, never reasons to stop Research."},
            {"role": "user", "content": json.dumps({"role": role, "objective": objective,
                "case_context": case_context}, ensure_ascii=False, default=str)},
        ]
        payload = {"messages": messages}
        started = time.monotonic()
        def operation():
            return self.transport(payload)
        # The governed call returns the raw local Ollama envelope.
        execute_result = execute("OLLAMA_LOCAL", service, "LOCAL_MODEL_INFERENCE",
            {"requests": 1, "operations": 1, "tokens": 700, "bytes": len(json.dumps(payload)),
             "cost": 0, "billable": False, "budget_period": "DAILY"}, operation,
            job_id=job_id, job_type=job_type, project_id=os.environ.get("NEXUS_PROJECT_ID"),
            correlation_id=correlation_id,
            purpose=(os.environ.get("NEXUS_RESEARCH_ROOM_CALL_ID") or f"research-room:{role}"),
            actual_usage=lambda value: {
                "requests": 1, "operations": 1, "tokens": int((value.get("prompt_eval_count") or 0) + (value.get("eval_count") or 0)),
                "runtime_seconds": round(float(value.get("total_duration") or 0) / 1_000_000_000, 3),
                "cost": 0, "bytes": len(json.dumps(value))})
        result = execute_result
        content = str(((result.get("message") or {}).get("content")) or "")
        try:
            parsed = json.loads(content)
        except Exception as exc:
            raise ValueError("ORACLE_LOCAL_OLLAMA_ADVISOR_RESPONSE_NOT_JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("ORACLE_LOCAL_OLLAMA_ADVISOR_RESPONSE_NOT_OBJECT")
        if not isinstance(parsed.get("analysis"), str) or not parsed["analysis"].strip():
            raise ValueError("ORACLE_LOCAL_OLLAMA_ADVISOR_ANALYSIS_MISSING")
        input_tokens = result.get("prompt_eval_count")
        output_tokens = result.get("eval_count")
        usage = {"input_tokens": input_tokens, "output_tokens": output_tokens,
            "total_tokens": (input_tokens + output_tokens) if isinstance(input_tokens, int) and isinstance(output_tokens, int) else None}
        return {"status": "COMPLETED", "provider": self.provider, "model": self.model,
            "usage": usage, "estimated_cost_usd": 0.0,
            "duration_ms": round((time.monotonic()-started)*1000, 2),
            "analysis": parsed.get("analysis"),
            "new_questions": parsed.get("new_questions") or parsed.get("questions") or [],
            "risks": parsed.get("risks") or [], "opportunities": parsed.get("opportunities") or [],
            "recommended_actions": parsed.get("recommended_actions") or [],
            "raw_usage": {k: result.get(k) for k in ("prompt_eval_count", "eval_count", "total_duration")}}


class IsolatedOracleOllamaAdvisor(OracleLocalOllamaAdvisor):
    """Supplies per-shadow-call governance identities without a durable queue job."""
    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        import hashlib
        digest = hashlib.sha256((str(case_context.get("case_id")) + role + objective).encode()).hexdigest()[:20]
        names = ("NEXUS_DURABLE_JOB_ID", "NEXUS_CORRELATION_ID", "NEXUS_DEPARTMENT",
                 "NEXUS_JOB_TYPE", "NEXUS_WORKFLOW_ID", "NEXUS_STEP_ID")
        previous = {name: os.environ.get(name) for name in names}
        os.environ.update({"NEXUS_DURABLE_JOB_ID": f"rrshadow_{digest}",
            "NEXUS_CORRELATION_ID": f"rrcorr_{digest}", "NEXUS_DEPARTMENT": "RESEARCH",
            "NEXUS_JOB_TYPE": "RESEARCH_ROOM_SHADOW_ADVISOR",
            "NEXUS_WORKFLOW_ID": "research-room-shadow", "NEXUS_STEP_ID": "advisor"})
        try:
            return super().ask(role=role, case_context=case_context, objective=objective)
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
