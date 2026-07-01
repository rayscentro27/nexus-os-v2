#!/usr/bin/env python3
"""
Hermes Model Infrastructure Inventory (read-only, no installs, no secrets).

Writes JSON + MD reports to reports/.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def _run(cmd, timeout=10):
    """Run a command, return (stdout, stderr, returncode). Never raises."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except FileNotFoundError:
        return "", "command not found", 127
    except subprocess.TimeoutExpired:
        return "", "timed out", 124


# ── 1. Ollama ─────────────────────────────────────────────────────────────────

def _check_ollama():
    info: dict = {}

    stdout, _, rc = _run(["which", "ollama"])
    info["installed"] = rc == 0
    info["binary"] = stdout or None

    stdout, _, rc = _run(["ollama", "list"])
    info["running"] = rc == 0
    info["models_raw"] = stdout if rc == 0 else None

    models: list[str] = []
    if stdout:
        for line in stdout.splitlines()[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
    info["models"] = models

    # endpoint probe (read-only curl)
    endpoint = "http://127.0.0.1:11434/api/tags"
    stdout, _, rc = _run(["curl", "-s", "--max-time", "3", endpoint])
    info["endpoint_responding"] = False
    info["endpoint"] = endpoint
    if rc == 0:
        try:
            data = json.loads(stdout)
            info["endpoint_responding"] = True
            info["endpoint_model_count"] = len(data.get("models", []))
        except (json.JSONDecodeError, KeyError):
            pass

    return info


# ── 2. Mac Mini hardware ─────────────────────────────────────────────────────

def _check_mac_mini():
    info: dict = {}
    info["platform"] = sys.platform

    stdout, _, _ = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    info["cpu"] = stdout or None

    stdout, _, _ = _run(["sysctl", "-n", "hw.memsize"])
    if stdout:
        try:
            info["ram_bytes"] = int(stdout)
            info["ram_gb"] = round(int(stdout) / (1024 ** 3), 1)
        except ValueError:
            info["ram_bytes"] = None
    else:
        info["ram_bytes"] = None
        info["ram_gb"] = None

    stdout, _, _ = _run(["sysctl", "-n", "hw.ncpu"])
    info["cpu_cores"] = int(stdout) if stdout.isdigit() else None

    stdout, _, _ = _run(["sw_vers", "-productVersion"])
    info["macos_version"] = stdout or None

    stdout, _, _ = _run(["system_profiler", "SPHardwareDataType"])
    info["model_identifier"] = None
    if stdout:
        for line in stdout.splitlines():
            if "Model Identifier" in line:
                info["model_identifier"] = line.split(":", 1)[1].strip()
                break

    return info


# ── 3. Hermes model gateway ───────────────────────────────────────────────────

def _check_hermes_gateway():
    info: dict = {}
    project_root = Path(__file__).resolve().parents[2]

    # Look for edge-function directories (Supabase edge functions pattern)
    candidates = [
        project_root / "supabase" / "functions",
        project_root / "edge-functions",
        project_root / "gateway",
        project_root / "hermes-gateway",
    ]
    edge_dirs_found: list[str] = []
    for c in candidates:
        if c.is_dir():
            edge_dirs_found.append(str(c.relative_to(project_root)))
    info["edge_function_dirs"] = edge_dirs_found or None

    # Env var presence check (names only, never values)
    gateway_env_names = [
        "HERMES_API_KEY",
        "HERMES_MODEL_ENDPOINT",
        "OLLAMA_HOST",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "GATEWAY_PORT",
    ]
    env_presence = {}
    for name in gateway_env_names:
        env_presence[name] = os.environ.get(name) is not None
    info["env_var_presence"] = env_presence

    return info


# ── 4. Oracle CLI ─────────────────────────────────────────────────────────────

def _check_oracle_cli():
    info: dict = {}

    stdout, _, rc = _run(["which", "oci"])
    info["installed"] = rc == 0
    info["binary"] = stdout or None

    oci_dir = Path.home() / ".oci"
    info["config_exists"] = (oci_dir / "config").is_file()
    info["config_path"] = str(oci_dir / "config") if info["config_exists"] else None

    # Parse profiles from config (names only)
    profiles: list[str] = []
    config_path = oci_dir / "config"
    if config_path.is_file():
        try:
            current_section = None
            for line in config_path.read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    current_section = stripped[1:-1].strip()
                    if current_section:
                        profiles.append(current_section)
        except Exception:
            pass
    info["profiles"] = profiles or None

    stdout, _, rc = _run(["oci", "--version"])
    info["oci_version"] = stdout if rc == 0 else None

    return info


# ── 5. Oracle VM / nexus-llm-worker ──────────────────────────────────────────

def _check_oracle_vm():
    info: dict = {}
    reports_dir = REPORTS_DIR

    # Look for existing watch reports
    watch_reports: list[str] = []
    if reports_dir.is_dir():
        for p in sorted(reports_dir.glob("*oracle*watch*.json")):
            watch_reports.append(p.name)
        for p in sorted(reports_dir.glob("*nexus*llm*.json")):
            if p.name not in watch_reports:
                watch_reports.append(p.name)

    info["watch_report_files"] = watch_reports or None
    info["nexus_llm_worker_status"] = None

    # Try to read the most recent relevant report for worker status
    for fname in reversed(watch_reports):
        rpath = reports_dir / fname
        try:
            data = json.loads(rpath.read_text())
            # Dig for worker status in nested structures
            status = (
                data.get("worker_status")
                or data.get("nexus_llm_worker", {}).get("status")
                or data.get("status")
            )
            if status:
                info["nexus_llm_worker_status"] = status
                info["latest_watch_report"] = fname
                break
        except (json.JSONDecodeError, OSError):
            continue

    return info


# ── Report generation ─────────────────────────────────────────────────────────

def _build_json_report() -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    report = {
        "report": "hermes_model_infrastructure_inventory",
        "generated_utc": ts,
        "read_only": True,
        "ollama": _check_ollama(),
        "mac_mini": _check_mac_mini(),
        "hermes_gateway": _check_hermes_gateway(),
        "oracle_cli": _check_oracle_cli(),
        "oracle_vm": _check_oracle_vm(),
    }
    return report


def _build_md(report: dict) -> str:
    lines = [
        "# Hermes Model Infrastructure Inventory",
        "",
        f"**Generated (UTC):** {report['generated_utc']}",
        "",
        "---",
        "",
    ]

    # Ollama
    o = report["ollama"]
    lines.append("## Ollama")
    lines.append(f"- Installed: {o['installed']}")
    lines.append(f"- Binary: `{o.get('binary') or 'n/a'}`")
    lines.append(f"- Running: {o['running']}")
    lines.append(f"- Models: {', '.join(o['models']) if o['models'] else 'none'}")
    lines.append(f"- Endpoint responding: {o['endpoint_responding']}")
    lines.append("")

    # Mac Mini
    m = report["mac_mini"]
    lines.append("## Mac Mini")
    lines.append(f"- CPU: {m.get('cpu') or 'n/a'}")
    lines.append(f"- RAM: {m.get('ram_gb') or 'n/a'} GB")
    lines.append(f"- Cores: {m.get('cpu_cores') or 'n/a'}")
    lines.append(f"- macOS: {m.get('macos_version') or 'n/a'}")
    lines.append(f"- Model: {m.get('model_identifier') or 'n/a'}")
    lines.append("")

    # Hermes Gateway
    g = report["hermes_gateway"]
    lines.append("## Hermes Model Gateway")
    dirs = g.get("edge_function_dirs")
    lines.append(f"- Edge function dirs: {', '.join(dirs) if dirs else 'none found'}")
    lines.append("- Env var presence (names only):")
    for k, v in g.get("env_var_presence", {}).items():
        lines.append(f"  - `{k}`: {'present' if v else 'absent'}")
    lines.append("")

    # Oracle CLI
    oc = report["oracle_cli"]
    lines.append("## Oracle CLI")
    lines.append(f"- Installed: {oc['installed']}")
    lines.append(f"- Version: {oc.get('oci_version') or 'n/a'}")
    lines.append(f"- Config: {oc['config_exists']}")
    profiles = oc.get("profiles")
    lines.append(f"- Profiles: {', '.join(profiles) if profiles else 'none'}")
    lines.append("")

    # Oracle VM
    vm = report["oracle_vm"]
    lines.append("## Oracle VM / nexus-llm-worker")
    lines.append(f"- Watch reports found: {len(vm.get('watch_report_files') or [])}")
    lines.append(f"- Worker status: {vm.get('nexus_llm_worker_status') or 'unknown'}")
    lines.append(f"- Latest watch report: {vm.get('latest_watch_report') or 'n/a'}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*This report is read-only. No secrets are printed. "
        "Only env var presence (True/False) is shown.*"
    )
    return "\n".join(lines) + "\n"


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report = _build_json_report()

    json_path = REPORTS_DIR / "hermes_model_infrastructure_inventory_latest.json"
    md_path = REPORTS_DIR / "hermes_model_infrastructure_inventory_latest.md"

    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(_build_md(report))

    print(f"JSON report: {json_path}")
    print(f"MD report:   {md_path}")


if __name__ == "__main__":
    main()
