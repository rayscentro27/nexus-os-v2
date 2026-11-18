"""Plan-backed ChatGPT advisor through the authenticated Codex CLI session."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

from .advisor_router import parse_advisor_content


class CodexCliChatGPTConnector:
    """Uses existing ChatGPT plan auth; makes no API key or billing setup."""
    provider = "CHATGPT_PLAN"
    model = "gpt-6-luna"
    free_or_metered = "CHATGPT_PLAN_INCLUDED"
    available = True

    def __init__(self, *, executable: str = "codex", timeout_seconds: int | None = None):
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def is_installed(self) -> bool:
        return shutil.which(self.executable) is not None

    def is_authenticated(self) -> bool:
        executable = shutil.which(self.executable)
        if not executable:
            return False
        result = subprocess.run([executable, "login", "status"], capture_output=True,
            text=True, timeout=10, check=False)
        return result.returncode == 0 and "Logged in using ChatGPT" in (result.stdout + result.stderr)

    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        executable = shutil.which(self.executable)
        if not executable:
            raise RuntimeError("CODEX_CLI_NOT_INSTALLED")
        timeout_seconds = self.timeout_seconds or min(120, max(5, int(os.getenv("NEXUS_RESEARCH_CHATGPT_TIMEOUT_SECONDS", "45"))))
        prompt = self._prompt(role, case_context, objective)
        # Do not pass unrelated provider credentials into the advisor subprocess.
        child_env = {key: value for key, value in os.environ.items()
            if not re.search(r"(?i)(api.?key|token|secret|password|credential)", key)}
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory(prefix="nexus-rr-chatgpt-") as cwd:
            started = time.monotonic()
            try:
                result = subprocess.run([executable, "exec", "--model", self.model,
                    "--sandbox", "read-only", "-c", 'approval_policy="never"',
                    "-c", "mcp_servers={}", "--cd", cwd, "--skip-git-repo-check",
                    "--ephemeral", "--color", "never", "-"], input=prompt,
                    text=True, capture_output=True, timeout=timeout_seconds, check=False, env=child_env)
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("CHATGPT_PLAN_ADVISOR_TIMEOUT") from exc
        if result.returncode != 0:
            # CLI diagnostics can contain the prompt; retain only the final error line.
            error = next((line.strip() for line in reversed(result.stderr.splitlines())
                if line.strip().lower().startswith(("error:", "fatal:"))), "CODEX_PLAN_ADVISOR_FAILED")
            raise RuntimeError(error[:240])
        response = result.stdout.strip()
        if not response:
            raise RuntimeError("CHATGPT_PLAN_ADVISOR_EMPTY_RESPONSE")
        token_match = re.search(r"tokens used\s*\n\s*([\d,]+)", result.stderr, re.I)
        usage = {"total_tokens": int(token_match.group(1).replace(",", ""))} if token_match else {}
        parsed = parse_advisor_content(response)
        return {"status": "COMPLETED", "provider": self.provider, "model": self.model,
            "runtime": "CODEX_CLI_CHATGPT_PLAN", "usage": usage, "estimated_cost_usd": None,
            "cost_class": self.free_or_metered, "duration_ms": (time.monotonic()-started)*1000,
            "prompt_sent": prompt, "full_response": response, **parsed}

    @staticmethod
    def _prompt(role: str, context: dict[str, Any], objective: str) -> str:
        packet = {key: context.get(key) for key in (
            "original_objective", "source_summary", "source_claims", "source_references",
            "verified_findings", "unverified_findings", "contradictions", "answered_questions",
            "unresolved_questions", "prior_knowledge_summary", "test_results", "business_opportunity_report")}
        return ("You are the " + role + " in Nexus Research Room. Analyze only the compact packet below; do not use tools, "
            "perform actions, contact anyone, or change files. Preserve uncertainty and distinguish cited evidence from hypotheses. "
            "Return useful analysis with sections ADVISOR_ANALYSIS, NEW_QUESTIONS, RISKS, OPPORTUNITIES, "
            "RECOMMENDED_ACTIONS, CONFIDENCE, and EVIDENCE_NOTES.\nOBJECTIVE:\n" + objective[:5000] +
            "\nPACKET:\n" + json.dumps(packet, ensure_ascii=False, default=str)[:18000])
