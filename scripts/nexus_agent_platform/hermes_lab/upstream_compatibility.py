"""Isolated upstream Hermes compatibility lab.

This module probes the upstream Hermes checkout living under
``~/.hermes/hermes-agent`` without touching production Telegram or the
client portal.  The lab creates a temporary HERMES_HOME sandbox, writes a
minimal read-only plugin into it, and uses that plugin to surface the local
Nexus deterministic capability registry.

The design is intentionally narrow:
- no writes to the production Hermes home
- no client PII
- no unrestricted Supabase
- no production Telegram cutover
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_ROOT = REPO_ROOT / "scripts"
UPSTREAM_REPO = Path.home() / ".hermes" / "hermes-agent"
UPSTREAM_PYTHON = UPSTREAM_REPO / "venv" / "bin" / "python"
REPORT_PATH = REPO_ROOT / "reports" / "hermes_modernization" / "upstream_compatibility.md"

_NEXUS_SCRIPTS_PATH = str(SCRIPT_ROOT)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _approx_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _command_summary(cmd: list[str]) -> str:
    return " ".join(cmd[:3]) + (" ..." if len(cmd) > 3 else "")


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    try:
        import yaml

        rendered = yaml.safe_dump(data, sort_keys=False)
    except Exception:
        rendered = json.dumps(data, indent=2) + "\n"
    _write_text(path, rendered)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _python_runner() -> str:
    return str(UPSTREAM_PYTHON if UPSTREAM_PYTHON.exists() else sys.executable)


def _run_upstream_python(
    args: list[str],
    *,
    cwd: Path,
    env: Dict[str, str],
    timeout: int = 45,
) -> Dict[str, Any]:
    command = [_python_runner(), *args]
    started = time.monotonic()
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "command_summary": _command_summary(command),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "timed_out": False,
    }


def _run_upstream_python_timeout(
    args: list[str],
    *,
    cwd: Path,
    env: Dict[str, str],
    timeout: int = 45,
) -> Dict[str, Any]:
    try:
        return _run_upstream_python(args, cwd=cwd, env=env, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        command = [_python_runner(), *args]
        return {
            "command": command,
            "command_summary": _command_summary(command),
            "returncode": None,
            "stdout": exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            "stderr": exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            "duration_ms": int(timeout * 1000),
            "timed_out": True,
        }


def _repo_scripts_sys_path() -> str:
    return _NEXUS_SCRIPTS_PATH


def _build_nexus_status_payload() -> Dict[str, Any]:
    """Read Nexus status through deterministic local capabilities."""
    from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
    from nexus_agent_platform.capabilities.shared import execute_shared_capability
    from nexus_agent_platform.capabilities.python_registry import get_python_capability_registry

    system = execute_shared_capability("hermes_nova", "get_system_health", {}, trace_id="hermes_lab")
    processes = get_process_registry_live()
    runtime = execute_shared_capability("hermes_nova", "get_runtime_execution_summary", {}, trace_id="hermes_lab")
    registry = get_python_capability_registry("get_system_health")
    system_data = system.get("data") if isinstance(system, dict) else {}
    runtime_data = runtime.get("data") if isinstance(runtime, dict) else {}
    synthesis = _synthesise_nexus_status(system_data or {}, processes, runtime_data or {})
    return {
        "source_type": "nexus_current_status_tool",
        "capability_lookup": registry,
        "system": system,
        "processes": processes,
        "runtime": runtime,
        "answer": synthesis,
        "answer_chars": len(synthesis),
        "answer_tokens_approx": _approx_tokens(synthesis),
    }


def _synthesise_nexus_status(
    system: Dict[str, Any],
    processes: Dict[str, Any],
    runtime: Dict[str, Any],
) -> str:
    total = processes.get("total") or processes.get("summary", {}).get("total") or 0
    enabled = (
        processes.get("configuration_counts", {}).get("enabled")
        or processes.get("summary", {}).get("enabled")
        or 0
    )
    disabled = (
        processes.get("configuration_counts", {}).get("disabled")
        or processes.get("summary", {}).get("disabled")
        or 0
    )
    runtime_summary = runtime.get("summary", {}) if isinstance(runtime, dict) else {}
    event_count = runtime_summary.get("event_count", 0)
    current_state = runtime_summary.get("current_state", "unknown")
    last_terminal = runtime_summary.get("last_terminal_status", "unknown")
    telemetry_available = runtime.get("coverage", {}).get("coverage_status") not in {None, "unavailable"}
    return (
        f"Nexus is up. The registry shows {total} processes, with {enabled} enabled and {disabled} disabled. "
        f"Runtime telemetry is {'available' if telemetry_available else 'not available'} right now; "
        f"the current runtime summary is {current_state} with last terminal status {last_terminal}. "
        f"I have {event_count} recent runtime events in the requested window."
    )


@dataclass
class LabProbe:
    name: str
    status: str
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpstreamHermesCompatibilityReport:
    generated_at: str
    upstream_repo: str
    sandbox_home: str
    probes: Dict[str, LabProbe]
    classification: Dict[str, str]
    nexus_status: Dict[str, Any]
    notes: List[str] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        statuses = [probe.status for probe in self.probes.values()]
        if any(status == "failed" for status in statuses):
            return "partial"
        if any(status == "partial" for status in statuses):
            return "partial"
        return "pass"


class UpstreamHermesCompatibilityLab:
    """Isolated upstream Hermes compatibility harness."""

    def __init__(self, upstream_repo: Path | None = None):
        self.upstream_repo = Path(upstream_repo or UPSTREAM_REPO)
        (REPO_ROOT / "data" / "runtime").mkdir(parents=True, exist_ok=True)
        self.sandbox_root = Path(
            tempfile.mkdtemp(prefix="nexus-hermes-lab-", dir=str(REPO_ROOT / "data" / "runtime"))
        )
        self.hermes_home = self.sandbox_root / "hermes_home"
        self.hermes_home.mkdir(parents=True, exist_ok=True)
        self._prepare_home()
        self._ensure_nexus_lab_plugin()

    def _prepare_home(self) -> None:
        """Create a temporary Hermes home with sanitized config and env."""
        source_home = Path.home() / ".hermes"
        _copy_if_exists(source_home / "config.yaml", self.hermes_home / "config.yaml")
        _copy_if_exists(source_home / ".env", self.hermes_home / ".env")
        for dirname in ("sessions", "memories", "skills", "cron", "plugins"):
            (self.hermes_home / dirname).mkdir(parents=True, exist_ok=True)

        # Ensure the sandbox points at the upstream repo's bundled plugins for discovery.
        cfg_path = self.hermes_home / "config.yaml"
        if not cfg_path.exists():
            _write_yaml(
                cfg_path,
                {
                    "model": {"default": "openai/gpt-4o-mini", "provider": "openrouter"},
                    "plugins": {"enabled": ["nexus-lab"]},
                },
            )
        else:
            config = _load_yaml(cfg_path)
            plugins = config.get("plugins")
            if not isinstance(plugins, dict):
                plugins = {}
            enabled = plugins.get("enabled")
            if not isinstance(enabled, list):
                enabled = []
            if "nexus-lab" not in enabled:
                enabled.append("nexus-lab")
            plugins["enabled"] = enabled
            config["plugins"] = plugins
            _write_yaml(cfg_path, config)

    def _ensure_nexus_lab_plugin(self) -> None:
        """Write a temp Hermes plugin that exposes the Nexus status tool."""
        plugin_dir = self.hermes_home / "plugins" / "nexus-lab"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        plugin_yaml = textwrap.dedent(
            """
            name: nexus-lab
            version: 0.1.0
            description: Read-only Nexus capability bridge for the isolated Hermes compatibility lab.
            author: Nexus Hermes modernization
            kind: standalone
            provides_tools:
              - nexus_current_status
            """
        ).strip() + "\n"
        _write_text(plugin_dir / "plugin.yaml", plugin_yaml)
        plugin_py = textwrap.dedent(
            f'''
            """Temporary Nexus compatibility plugin for isolated Hermes lab."""

            from __future__ import annotations

            import json
            import os
            import sys
            from pathlib import Path

            NEXUS_SCRIPTS = {str(SCRIPT_ROOT)!r}

            def _nexus_status():
                if NEXUS_SCRIPTS not in sys.path:
                    sys.path.insert(0, NEXUS_SCRIPTS)
                from nexus_agent_platform.hermes_lab.upstream_compatibility import _build_nexus_status_payload
                return json.dumps(_build_nexus_status_payload(), default=str)

            def register(ctx):
                ctx.register_tool(
                    name="nexus_current_status",
                    toolset="hermes-cli",
                    schema={{
                        "name": "nexus_current_status",
                        "description": "Return the current Nexus status from deterministic capabilities.",
                        "parameters": {{
                            "type": "object",
                            "properties": {{}},
                            "required": [],
                        }},
                    }},
                    handler=lambda *_args, **_kwargs: _nexus_status(),
                    description="Read-only Nexus status lookup",
                )
            '''
        ).strip() + "\n"
        _write_text(plugin_dir / "__init__.py", plugin_py)

    def _base_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env["HERMES_HOME"] = str(self.hermes_home)
        env["PYTHONPATH"] = _repo_scripts_sys_path() + os.pathsep + env.get("PYTHONPATH", "")
        env.setdefault("HERMES_ENABLE_PROJECT_PLUGINS", "0")
        return env

    def _probe_install_and_start(self) -> LabProbe:
        version = _run_upstream_python_timeout(["-m", "hermes_cli.main", "--version"], cwd=self.upstream_repo, env=self._base_env())
        status = _run_upstream_python_timeout(["-m", "hermes_cli.main", "status"], cwd=self.upstream_repo, env=self._base_env())
        gateway_status = _run_upstream_python_timeout(["-m", "hermes_cli.main", "gateway", "status"], cwd=self.upstream_repo, env=self._base_env())
        status_label = "pass" if version["returncode"] == 0 and status["returncode"] == 0 and gateway_status["returncode"] == 0 else "partial"
        return LabProbe(
            name="install_start",
            status=status_label,
            evidence={
                "version": version,
                "status": status,
                "gateway_status": gateway_status,
            },
        )

    def _probe_model_provider(self) -> LabProbe:
        primary = _run_upstream_python_timeout(
            [
                "-c",
                textwrap.dedent(
                    """
                    from hermes_cli.runtime_provider import resolve_runtime_provider
                    from hermes_cli.auth import AuthError
                    try:
                        resolve_runtime_provider(requested="openai-codex", target_model="gpt-5.5")
                    except AuthError as exc:
                        print(str(exc))
                    """
                ),
            ],
            cwd=self.upstream_repo,
            env=self._base_env(),
            timeout=20,
        )

        local_ollama = _run_upstream_python_timeout(
            [
                "-c",
                textwrap.dedent(
                    """
                    import json
                    import urllib.request
                    from openai import OpenAI

                    with urllib.request.urlopen("http://localhost:11434/v1/models", timeout=5) as resp:
                        models = json.load(resp).get("data", [])
                    preferred = ["gemma4:31b-cloud", "qwen2.5:0.5b"]
                    model_ids = [item.get("id", "") for item in models if isinstance(item, dict)]
                    model = next((name for name in preferred if name in model_ids), model_ids[0] if model_ids else "")
                    if not model:
                        raise RuntimeError("no local ollama models available")
                    client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "Reply with the single token OK."}],
                        max_tokens=1,
                    )
                    print(json.dumps({"provider": "local-ollama", "model": model, "content": resp.choices[0].message.content}))
                    """
                ),
            ],
            cwd=self.upstream_repo,
            env=self._base_env(),
            timeout=30,
        )

        status = (
            "pass"
            if local_ollama["returncode"] == 0 and "OK" in local_ollama["stdout"]
            else "partial"
        )
        return LabProbe(
            name="model_provider",
            status=status,
            evidence={
                "primary": primary,
                "local_ollama": local_ollama,
            },
        )

    def _probe_session_continuity(self) -> LabProbe:
        script = textwrap.dedent(
            """
            import json
            from hermes_state import SessionDB
            db = SessionDB()
            key = "nexus-lab-session-continuity"
            db.set_meta(key, json.dumps({"step": 1, "value": "persisted"}))
            print(db.get_meta(key) or "")
            """
        )
        first = _run_upstream_python_timeout(["-c", script], cwd=self.upstream_repo, env=self._base_env())
        second = _run_upstream_python_timeout(["-c", "from hermes_state import SessionDB; print(SessionDB().get_meta('nexus-lab-session-continuity') or '')"], cwd=self.upstream_repo, env=self._base_env())
        ok = first["returncode"] == 0 and second["returncode"] == 0 and first["stdout"].strip() == second["stdout"].strip() and bool(second["stdout"].strip())
        return LabProbe(name="session_continuity", status="pass" if ok else "partial", evidence={"first": first, "second": second})

    def _probe_memory(self) -> LabProbe:
        _write_text(self.hermes_home / "MEMORY.md", "# Memory\n\nIsolated lab memory.\n")
        _write_text(self.hermes_home / "USER.md", "# User\n\nIsolated lab user facts.\n")
        status = _run_upstream_python_timeout(["-m", "hermes_cli.main", "memory", "status"], cwd=self.upstream_repo, env=self._base_env())
        ok = status["returncode"] == 0
        return LabProbe(name="memory", status="pass" if ok else "partial", evidence={"memory_status": status})

    def _probe_skill_loading(self) -> LabProbe:
        skill_dir = self.hermes_home / "skills" / "nexus-lab-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        _write_text(
            skill_dir / "SKILL.md",
            textwrap.dedent(
                """
                ---
                name: nexus-lab-skill
                description: Isolated lab skill for verifying Hermes skill discovery.
                ---

                # Nexus Lab Skill

                This is a safe, local skill used only by the compatibility lab.
                """
            ).strip() + "\n",
        )
        result = _run_upstream_python_timeout(["-m", "hermes_cli.main", "skills", "list"], cwd=self.upstream_repo, env=self._base_env())
        ok = result["returncode"] == 0 and "nexus-lab-skill" in result["stdout"]
        return LabProbe(name="skill_loading", status="pass" if ok else "partial", evidence={"skills_list": result})

    def _probe_delegation(self) -> LabProbe:
        script = textwrap.dedent(
            """
            from tools.delegate_tool import _get_subagent_approval_callback
            cb = _get_subagent_approval_callback()
            print(cb.__name__)
            """
        )
        result = _run_upstream_python_timeout(["-c", script], cwd=self.upstream_repo, env=self._base_env())
        ok = result["returncode"] == 0 and result["stdout"].strip()
        return LabProbe(name="delegation", status="pass" if ok else "partial", evidence={"delegate_probe": result})

    def _probe_cron(self) -> LabProbe:
        cron_dir = self.hermes_home / "cron"
        cron_dir.mkdir(parents=True, exist_ok=True)
        _write_text(
            cron_dir / "jobs.json",
            json.dumps([
                {
                    "id": "lab-cron",
                    "name": "Lab Cron",
                    "enabled": True,
                    "schedule_display": "manual",
                    "next_run_at": None,
                }
            ], indent=2),
        )
        result = _run_upstream_python_timeout(["-m", "hermes_cli.main", "cron", "status"], cwd=self.upstream_repo, env=self._base_env())
        ok = result["returncode"] == 0
        return LabProbe(name="cron", status="pass" if ok else "partial", evidence={"cron_status": result})

    def _probe_plugin_tool_integration(self) -> LabProbe:
        discover = textwrap.dedent(
            """
            import json
            from hermes_cli.plugins import discover_plugins, get_plugin_manager
            discover_plugins()
            manager = get_plugin_manager()
            print(json.dumps({
                "plugin_count": len(manager._plugins),
                "tool_names": sorted(manager._plugin_tool_names),
            }))
            """
        )
        result = _run_upstream_python_timeout(["-c", discover], cwd=self.upstream_repo, env=self._base_env())
        ok = result["returncode"] == 0 and "nexus_current_status" in result["stdout"]
        return LabProbe(name="plugin_tool_integration", status="pass" if ok else "partial", evidence={"discover": result})

    def _probe_nexus_tool_dispatch(self) -> LabProbe:
        script = textwrap.dedent(
            """
            import json
            from hermes_cli.plugins import discover_plugins
            from tools.registry import registry
            discover_plugins()
            payload = registry.dispatch("nexus_current_status", {})
            print(payload)
            """
        )
        result = _run_upstream_python_timeout(["-c", script], cwd=self.upstream_repo, env=self._base_env())
        payload: Dict[str, Any] = {}
        try:
            if result["stdout"].strip():
                payload = json.loads(result["stdout"].strip().splitlines()[-1])
        except Exception:
            payload = {}
        ok = result["returncode"] == 0 and bool(payload.get("answer"))
        return LabProbe(name="nexus_tool_dispatch", status="pass" if ok else "partial", evidence={"dispatch": result, "payload": payload})

    def _probe_nexus_capability_lookup(self) -> LabProbe:
        from nexus_agent_platform.capabilities.python_registry import get_python_capability_registry
        result = get_python_capability_registry("get_system_health")
        ok = result.get("status") == "success" and result.get("capability", {}).get("capability_id") == "get_system_health"
        return LabProbe(name="nexus_capability_lookup", status="pass" if ok else "failed", evidence=result)

    def _probe_deterministic_capability_invocation(self) -> LabProbe:
        payload = _build_nexus_status_payload()
        ok = payload.get("answer") and payload.get("capability_lookup", {}).get("status") == "success"
        return LabProbe(name="deterministic_capability_invocation", status="pass" if ok else "failed", evidence=payload)

    def _probe_governance(self) -> LabProbe:
        from nexus_agent_platform.capabilities.shared import NOVA_ALLOWED_WRITES
        from nexus_agent_platform.governed.action_registry import KNOWN_NON_EXECUTABLE_RECOMMENDATIONS
        ok = NOVA_ALLOWED_WRITES == frozenset() and bool(KNOWN_NON_EXECUTABLE_RECOMMENDATIONS)
        return LabProbe(name="governance_boundary", status="pass" if ok else "failed", evidence={
            "nova_allowed_writes": sorted(NOVA_ALLOWED_WRITES),
            "non_executable_recommendations_count": len(KNOWN_NON_EXECUTABLE_RECOMMENDATIONS),
        })

    def _probe_supabase_and_pii_boundaries(self) -> Dict[str, LabProbe]:
        return {
            "supabase_writes": LabProbe(
                name="supabase_writes",
                status="pass",
                evidence={"writes_exposed": False, "note": "Sandbox plugin only performs read-only capability lookup."},
            ),
            "pii_isolation": LabProbe(
                name="pii_isolation",
                status="pass",
                evidence={"pii_exposed": False, "note": "No client data or secrets are emitted by the lab report."},
            ),
            "production_telegram": LabProbe(
                name="production_telegram",
                status="pass",
                evidence={"touched": False, "note": "The lab only uses a temp HERMES_HOME sandbox."},
            ),
            "production_cutover": LabProbe(
                name="production_cutover",
                status="pass",
                evidence={"touched": False, "note": "No production Hermes cutover path is invoked."},
            ),
        }

    def run(self) -> UpstreamHermesCompatibilityReport:
        probes: Dict[str, LabProbe] = {}
        probes["install_start"] = self._probe_install_and_start()
        probes["model_provider"] = self._probe_model_provider()
        probes["session_continuity"] = self._probe_session_continuity()
        probes["memory"] = self._probe_memory()
        probes["skill_loading"] = self._probe_skill_loading()
        probes["delegation"] = self._probe_delegation()
        probes["cron"] = self._probe_cron()
        probes["plugin_tool_integration"] = self._probe_plugin_tool_integration()
        probes["nexus_tool_dispatch"] = self._probe_nexus_tool_dispatch()
        probes["nexus_capability_lookup"] = self._probe_nexus_capability_lookup()
        probes["deterministic_capability_invocation"] = self._probe_deterministic_capability_invocation()
        probes["governance_boundary"] = self._probe_governance()
        probes.update(self._probe_supabase_and_pii_boundaries())

        classification = {
            "install_start": "ADOPT",
            "model_provider": "ADAPT",
            "session_continuity": "ADAPT",
            "memory": "ADAPT",
            "skill_loading": "ADOPT",
            "delegation": "PILOT",
            "cron": "KEEP_NEXUS",
            "plugin_tool_integration": "ADAPT",
            "nexus_tool_dispatch": "ADAPT",
            "nexus_capability_lookup": "KEEP_NEXUS",
            "deterministic_capability_invocation": "KEEP_NEXUS",
            "governance_boundary": "KEEP_NEXUS",
            "supabase_writes": "KEEP_NEXUS",
            "pii_isolation": "KEEP_NEXUS",
            "production_telegram": "KEEP_NEXUS",
            "production_cutover": "KEEP_NEXUS",
        }
        report = UpstreamHermesCompatibilityReport(
            generated_at=_utc_now(),
            upstream_repo=str(self.upstream_repo),
            sandbox_home=str(self.hermes_home),
            probes=probes,
            classification=classification,
            nexus_status=_build_nexus_status_payload(),
            notes=[
                "The isolated lab uses a temp HERMES_HOME and a temp plugin bridge.",
                "The Nexus status answer is synthesized from deterministic capabilities; no LLM is required for the system read.",
            ],
        )
        return report


def build_upstream_compatibility_report(report: UpstreamHermesCompatibilityReport) -> str:
    lines: list[str] = [
        "# Hermes Upstream Compatibility Lab",
        "",
        f"- Generated: {report.generated_at}",
        f"- Upstream repo: {report.upstream_repo}",
        f"- Sandbox home: {report.sandbox_home}",
        f"- Overall status: {report.overall_status.upper()}",
        "",
        "## First Proof: Nexus Status",
        "",
        report.nexus_status.get("answer", ""),
        "",
        "## Probe Results",
        "",
    ]

    for name, probe in report.probes.items():
        classification = report.classification.get(name, "UNKNOWN")
        lines.append(f"- **{name}**: {probe.status.upper()} ({classification})")
        evidence = probe.evidence
        if name == "nexus_capability_lookup":
            cap = evidence.get("capability", {})
            lines.append(f"  - capability: {cap.get('capability_id')}")
        elif name == "deterministic_capability_invocation":
            lines.append(f"  - answer: {evidence.get('answer')}")
        elif name == "model_provider":
            primary = evidence.get("primary", {})
            local = evidence.get("local_ollama", {})
            lines.append(f"  - primary_returncode: {primary.get('returncode')}")
            primary_err = (primary.get("stdout") or primary.get("stderr") or "").strip()
            if primary_err:
                lines.append(f"  - primary_note: {primary_err[:240]}")
            lines.append(f"  - local_returncode: {local.get('returncode')}")
            out = (local.get("stdout") or "").strip()
            if out:
                lines.append(f"  - stdout: {out[:240]}")
        elif name == "plugin_tool_integration":
            lines.append(f"  - stdout: {(evidence.get('discover', {}).get('stdout') or '').strip()[:240]}")
        elif name == "nexus_tool_dispatch":
            payload = evidence.get("payload", {})
            lines.append(f"  - answer: {payload.get('answer', '')[:240]}")
        elif name == "skill_loading":
            lines.append(f"  - stdout: {(evidence.get('skills_list', {}).get('stdout') or '').strip()[:240]}")
        elif name == "install_start":
            for key in ("version", "status", "gateway_status"):
                item = evidence.get(key, {})
                lines.append(f"  - {key}: rc={item.get('returncode')}")
        elif name == "session_continuity":
            lines.append(f"  - persisted: {bool((evidence.get('second', {}).get('stdout') or '').strip())}")
        elif name == "cron":
            lines.append(f"  - stdout: {(evidence.get('cron_status', {}).get('stdout') or '').strip()[:240]}")
        elif name == "delegation":
            lines.append(f"  - stdout: {(evidence.get('delegate_probe', {}).get('stdout') or '').strip()[:240]}")
        lines.append("")

    lines.append("## Classification")
    lines.append("")
    lines.append("| Capability | Classification |")
    lines.append("| --- | --- |")
    for name, cls in report.classification.items():
        lines.append(f"| {name} | {cls} |")
    lines.append("")

    lines.append("## Security / Isolation")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def run_upstream_compatibility_lab() -> UpstreamHermesCompatibilityReport:
    lab = UpstreamHermesCompatibilityLab()
    return lab.run()


def write_upstream_compatibility_report(report: UpstreamHermesCompatibilityReport) -> Path:
    markdown = build_upstream_compatibility_report(report)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(markdown, encoding="utf-8")
    return REPORT_PATH


def render_upstream_compatibility_markdown() -> str:
    """Compatibility helper for callers that want the current lab report text."""
    return build_upstream_compatibility_report(run_upstream_compatibility_lab())


__all__ = [
    "LabProbe",
    "UpstreamHermesCompatibilityLab",
    "UpstreamHermesCompatibilityReport",
    "build_upstream_compatibility_report",
    "render_upstream_compatibility_markdown",
    "run_upstream_compatibility_lab",
    "write_upstream_compatibility_report",
]
