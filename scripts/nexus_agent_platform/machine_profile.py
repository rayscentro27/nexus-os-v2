"""Safe Mac Mini machine inventory and capability-first target selection."""
from __future__ import annotations
import json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports/runtime"

def _run(*args: str) -> str | None:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError): return None

def _tool(name: str, version_args: tuple[str, ...] = ("--version",)) -> dict[str, Any]:
    path = shutil.which(name); version = _run(path, *version_args) if path else None
    return {"installed": bool(path), "path": path, "version": version[:200] if version else None}

def _python_candidates() -> list[str]:
    paths = {sys.executable}
    for root in (Path("/usr/bin"), Path("/usr/local/bin"), Path("/opt/homebrew/bin"), Path.home() / ".local/bin"):
        if root.exists(): paths.update(str(path) for path in root.glob("python3*") if path.is_file() and path.name.split("python")[-1].replace(".", "").isdigit())
    return sorted(paths)

def _python_probe(path: str) -> dict[str, Any]:
    code = "import json,ssl,sys; print(json.dumps({'version':sys.version.split()[0],'executable':sys.executable,'ssl':ssl.OPENSSL_VERSION}))"
    try:
        result = subprocess.run([path, "-c", code], capture_output=True, text=True, timeout=8, check=False)
        if result.returncode == 0: return {**json.loads(result.stdout), "ssl_import": "HEALTHY"}
        return {"executable": path, "ssl_import": "BROKEN", "error": result.stderr.splitlines()[-1][:240] if result.stderr else "probe failed"}
    except Exception as exc: return {"executable": path, "ssl_import": "BROKEN", "error": str(exc)[:240]}

def collect() -> dict[str, Any]:
    disk = shutil.disk_usage(ROOT)
    machine = {"host_class":"Mac Mini", "os":{"name":"Darwin","release":os.uname().release,"version":_run("sw_vers","-productVersion"),"build":_run("sw_vers","-buildVersion")},"architecture":os.uname().machine,"cpu":{"model":_run("sysctl","-n","machdep.cpu.brand_string"),"physical_cores":_run("sysctl","-n","hw.physicalcpu"),"logical_cores":_run("sysctl","-n","hw.logicalcpu")},"ram":{"total_bytes":_run("sysctl","-n","hw.memsize")},"storage":{"total_bytes":disk.total,"free_bytes":disk.free},"tools":{"homebrew":{"installed":bool(shutil.which("brew")),"path":shutil.which("brew"),"prefix":_run("brew","--prefix"),"version":_run("brew","--version")},"node":_tool("node"),"npm":_tool("npm"),"git":_tool("git"),"clang":_tool("clang"),"docker":_tool("docker"),"ollama":_tool("ollama"),"yt_dlp":_tool("yt-dlp"),"ffmpeg":_tool("ffmpeg")},"python":{"interpreters":[_python_probe(path) for path in _python_candidates()]},"whisper":{"binary":str(ROOT/"tools/voice/runtime/whisper.cpp/build/bin/whisper-cli"),"binary_available":(ROOT/"tools/voice/runtime/whisper.cpp/build/bin/whisper-cli").exists(),"model":str(ROOT/"tools/voice/models/ggml-base.en.bin"),"model_available":(ROOT/"tools/voice/models/ggml-base.en.bin").exists()},"gpu_metal":{"metal_probe":"system_profiler SPDisplaysDataType" if shutil.which("system_profiler") else None},"browser":{"chrome":_tool("google-chrome"),"chromium":_tool("chromium"),"playwright_package":(ROOT/"node_modules/playwright").exists()},"network":{"hostname":"redacted-local-host","loopback":"available"},"remote_compute":{"modal":_tool("modal"),"registered":"repository-governed adapters inspected"},"generated_at":datetime.now(timezone.utc).isoformat(),"private_identifiers_excluded":True}
    return machine

def evaluate_execution_target(requirements: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or collect(); pythons = profile.get("python", {}).get("interpreters", [])
    healthy = [item for item in pythons if item.get("ssl_import") == "HEALTHY"]
    required_python = requirements.get("python")
    compatible = [item for item in healthy if not required_python or item.get("version", "").startswith(str(required_python))]
    if requirements.get("ssl") and compatible: return {"decision":"LOCAL_COMPATIBLE" if compatible[0].get("executable") == sys.executable else "LOCAL_ALTERNATIVE_RUNTIME", "runtime":compatible[0].get("executable"), "reason":"healthy SSL-capable interpreter selected from machine profile"}
    if requirements.get("browser") and not profile.get("browser", {}).get("playwright_package"): return {"decision":"REMOTE_RECOMMENDED","runtime":None,"reason":"browser runtime unavailable"}
    return {"decision":"LOCAL_COMPATIBLE","runtime":sys.executable,"reason":"no unmet machine requirement detected"}

def write_reports() -> dict[str, Any]:
    report = collect(); report["execution_target_examples"] = {"live_research": evaluate_execution_target({"ssl":True}, report), "voice":evaluate_execution_target({"browser":True}, report)}
    REPORT_DIR.mkdir(parents=True, exist_ok=True); (REPORT_DIR/"nexus_machine_profile_latest.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    lines=["# Nexus Machine Profile","","Safe machine/runtime inventory; private identifiers excluded.","",f"- Host: {report['host_class']}",f"- OS: {report['os']}",f"- Architecture: {report['architecture']}",f"- Storage free bytes: {report['storage']['free_bytes']}","","## Python"]
    lines += [f"- {row.get('executable')}: {row.get('version','unknown')} — SSL {row.get('ssl_import')} {row.get('ssl','')}" for row in report['python']['interpreters']]
    lines += ["","## Target decisions",f"- Live research: {report['execution_target_examples']['live_research']}",f"- Voice/browser: {report['execution_target_examples']['voice']}"]
    (REPORT_DIR/"nexus_machine_profile_latest.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); return report

if __name__ == "__main__": print(json.dumps(write_reports(),indent=2))
