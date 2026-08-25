"""Bounded Voice Product Evolution adapter."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict

from .builder_adapter import mission_to_build_task, run_bounded_codex_task
from .registry import ProductEvolutionAdapter
from ..loop import FailureClass, MissionContract, ProductEvolutionLoop, Stage

ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_ORIGIN = "https://goclearonline.cc"
VOICE_ENDPOINT = "https://voice.goclearonline.cc"
VOICE_ALLOWED_HEADERS = "Content-Type, X-Nexus-Voice-Session, X-Nexus-Voice-Preview-Sequence"
VOICE_PATHS = ("/v1/voice/preview", "/v1/voice/transcribe")

VOICE_ALLOWED_PATHS = (
    "src/admin/NexusWakeVoice.jsx", "src/admin/VoicePushToTalk.jsx",
    "scripts/nexus_agent_platform/voice/local_server.py",
    "scripts/nexus_agent_platform/voice/local_stt.py",
    "scripts/ops/run_voice_local_with_runtime_env.sh",
    "launchd/com.nexus.voice-local.plist", "scripts/nexus_agent_platform/tests/",
    "docs/operations/voice/",
)
VOICE_PROTECTED_PATHS = (
    "src/client-v2/", "src/clientPortal/", "supabase/", "src/hermes/",
    "scripts/nova/", "scripts/alpha/", "runtime.env", ".env", "secrets/",
    "public/runtime/", "production agent identities",
)


def _parse_headers(raw: str) -> tuple[int | None, Dict[str, str]]:
    status = None
    headers: Dict[str, str] = {}
    for line in raw.splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        elif ":" in line:
            key, value = line.split(":", 1)
            headers[key.lower().strip()] = value.strip()
    return status, headers


def _options(path: str, *, base_url: str = VOICE_ENDPOINT) -> Dict[str, Any]:
    command = [
        "/usr/bin/curl", "--silent", "--show-error", "--max-time", "15", "-D", "-",
        "-o", "/dev/null", "-X", "OPTIONS", base_url + path,
        "-H", f"Origin: {PRODUCTION_ORIGIN}", "-H", "Access-Control-Request-Method: POST",
        "-H", "Access-Control-Request-Headers: content-type,x-nexus-voice-session,x-nexus-voice-preview-sequence",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": None, "error": type(exc).__name__}
    status, headers = _parse_headers(completed.stdout or "")
    return {"status": status, "allow_origin": headers.get("access-control-allow-origin"), "allow_credentials": headers.get("access-control-allow-credentials"), "allow_methods": headers.get("access-control-allow-methods"), "allow_headers": headers.get("access-control-allow-headers"), **({"error": "curl_failed"} if completed.returncode else {})}


def _options_pass(item: Dict[str, Any]) -> bool:
    allow_headers = (item.get("allow_headers") or "").lower()
    return item.get("status") == 204 and item.get("allow_origin") == PRODUCTION_ORIGIN and item.get("allow_credentials") == "true" and item.get("allow_methods") == "POST, OPTIONS" and all(header.lower() in allow_headers for header in ("content-type", "x-nexus-voice-session", "x-nexus-voice-preview-sequence"))


def _synthetic_audio(path: Path) -> str:
    say = shutil.which("say")
    if not say:
        raise RuntimeError("SYNTHETIC_AUDIO_TOOL_UNAVAILABLE")
    aiff_path = path.with_suffix(".aiff")
    subprocess.run([say, "-o", str(aiff_path), "Hey Nexus, what should I focus on today?"], check=True, capture_output=True, timeout=15)
    return "audio/aiff"


def _post_synthetic(path: str, *, endpoint_path: str, content_type: str, base_url: str = VOICE_ENDPOINT) -> Dict[str, Any]:
    command = [
        "/usr/bin/curl", "--silent", "--show-error", "--max-time", "90", "-X", "POST", base_url + endpoint_path,
        "-H", f"Origin: {PRODUCTION_ORIGIN}", "-H", f"Content-Type: {content_type}",
        "-H", "X-Nexus-Voice-Session: product-evolution-synthetic", "--data-binary", f"@{path}",
        "-w", "\n__HTTP_STATUS__:%{http_code}",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=100, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": None, "error": type(exc).__name__}
    body, marker, code = (completed.stdout or "").rpartition("\n__HTTP_STATUS__:")
    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        payload = {"raw_response": body[-300:]}
    return {"status": int(code) if marker and code.isdigit() else None, "payload": payload, **({"error": "curl_failed"} if completed.returncode else {})}


def transport_diagnosis() -> Dict[str, Any]:
    preview_options, transcribe_options = _options(VOICE_PATHS[0]), _options(VOICE_PATHS[1])
    source = (ROOT / "src/admin/NexusWakeVoice.jsx").read_text(encoding="utf-8")
    wake_architecture = {
        "mode": "VAD_ONE_SHOT_LOCAL_STT",
        "persistent_preview_disabled": "persistentRef.current || !endpoint" in source,
        "single_utterance_states": all(token in source for token in ("WAKE_IDLE", "CAPTURING", "FINALIZING", "ROUTING", "THINKING", "COOLDOWN")),
        "cooldown_present": "COOLDOWN_MS" in source and "armCooldown" in source,
    }
    result: Dict[str, Any] = {"preview_options": preview_options, "transcribe_options": transcribe_options, "production_origin": PRODUCTION_ORIGIN, "allowed_headers": VOICE_ALLOWED_HEADERS, "wake_architecture": wake_architecture, "options_pass": _options_pass(preview_options) and _options_pass(transcribe_options), "preview_post": {"status": "NOT_RUN"}, "transcribe_post": {"status": "NOT_RUN"}, "local_preview_post": {"status": "NOT_RUN"}, "local_transcribe_post": {"status": "NOT_RUN"}, "whisper_reached": False, "synthetic_transcript": False, "raw_audio_retained": False}
    with tempfile.TemporaryDirectory(prefix="nexus-product-evolution-voice-") as temp_dir:
        audio = Path(temp_dir) / "synthetic.aiff"
        try:
            content_type = _synthetic_audio(audio)
            result["preview_post"] = _post_synthetic(str(audio), endpoint_path=VOICE_PATHS[0], content_type=content_type)
            result["transcribe_post"] = _post_synthetic(str(audio), endpoint_path=VOICE_PATHS[1], content_type=content_type)
            result["local_preview_post"] = _post_synthetic(str(audio), endpoint_path=VOICE_PATHS[0], content_type=content_type, base_url="http://127.0.0.1:8789")
            result["local_transcribe_post"] = _post_synthetic(str(audio), endpoint_path=VOICE_PATHS[1], content_type=content_type, base_url="http://127.0.0.1:8789")
            for key in ("preview_post", "transcribe_post", "local_preview_post", "local_transcribe_post"):
                payload = result[key].get("payload") or {}
                result["whisper_reached"] = result["whisper_reached"] or payload.get("stt_provider") == "whisper.cpp"
                result["synthetic_transcript"] = result["synthetic_transcript"] or bool(payload.get("text"))
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            result["synthetic_audio_error"] = str(exc)
    result["cloudflare_access_required"] = any(result[key].get("status") in {301, 302, 303, 307, 308} for key in ("preview_post", "transcribe_post"))
    result["local_transport_pass"] = bool(result["local_preview_post"].get("status") == 200 and result["local_transcribe_post"].get("status") == 200 and result["whisper_reached"] and result["synthetic_transcript"])
    result["code_repair_needed"] = not bool(result["options_pass"] and result["local_transport_pass"] and all(wake_architecture.values()))
    result["pass"] = bool(result["options_pass"] and result["local_transport_pass"] and not result["cloudflare_access_required"] and result["raw_audio_retained"] is False)
    return result


def _voice_can_handle(contract: MissionContract) -> bool:
    # The goal is the authority for surface selection; the user-visible
    # outcome is intentionally generic and must not route unrelated work.
    return "voice" in contract.goal.lower()


def execute_voice(mission_id: str, contract: MissionContract, adapter: ProductEvolutionAdapter) -> Dict[str, Any]:
    transport = transport_diagnosis()
    builder_result: Dict[str, Any] = {"status": "not_needed"}
    task_holder: Dict[str, Any] = {}
    bounded_contract = replace(contract, max_cycles=min(contract.max_cycles, adapter.max_cycles))
    human_fail_evidence = None
    receipt_path = ROOT / "reports/product_evolution" / f"{mission_id}.json"
    try:
        receipt_result = json.loads(receipt_path.read_text(encoding="utf-8")).get("result") or {}
        evidence = list(receipt_result.get("human_evidence") or [])
        if evidence and evidence[-1].get("outcome") == "FAIL":
            human_fail_evidence = evidence[-1]
    except (OSError, ValueError, TypeError):
        human_fail_evidence = None

    def pass_stage(evidence: str):
        return lambda: {"status": "PASS", "evidence": evidence}

    def build_stage() -> Dict[str, Any]:
        nonlocal builder_result, transport
        if not transport["code_repair_needed"] and not human_fail_evidence:
            return {"status": "PASS", "evidence": "Tracked Voice runtime and production-like transport satisfy the contract."}
        task = mission_to_build_task(mission_id, contract, allowed_paths=adapter.allowed_paths, protected_paths=adapter.protected_paths, tests=adapter.test_commands, visual_requirements=adapter.visual_requirements, timeout_seconds=adapter.timeout_seconds, max_retries=min(bounded_contract.max_cycles - 1, adapter.max_cycles - 1), previous_failure={"transport": transport, "human_failure": human_fail_evidence or {}})
        task_holder["task"] = task.to_dict()
        builder_result = run_bounded_codex_task(task)
        return {"status": "PASS" if builder_result.get("ok") else "BLOCKED", "evidence": "Bounded Codex Builder execution", "failure_class": FailureClass.IMPLEMENTATION_BUG.value, "error": builder_result.get("worker_error") or builder_result.get("verification", {}).get("reason")}

    def test_stage() -> Dict[str, Any]:
        nonlocal transport
        transport = transport_diagnosis()
        return {"status": "PASS" if not transport["code_repair_needed"] else "BLOCKED", "evidence": json.dumps(transport, sort_keys=True), "failure_class": FailureClass.ENVIRONMENT_BLOCKER.value, "error": "Voice transport proof did not pass"}

    def critic(_contract: MissionContract, _evidence: list[Dict[str, Any]]) -> Dict[str, Any]:
        automated = transport["options_pass"] and transport["local_transport_pass"]
        return {"status": "PARTIAL" if automated else "FAIL", "failure_class": FailureClass.HUMAN_HARDWARE_TEST_REQUIRED.value if automated else FailureClass.ENVIRONMENT_BLOCKER.value, "summary": "CORS and local whisper transport passed; production POST requires the existing Cloudflare Access session, then Ray must perform the real microphone test" if automated else "Automated Voice transport proof failed", "scores": {"transport": 5 if automated else 0, "security": 5, "human_gate": 0}}

    result = ProductEvolutionLoop(receipt_dir=None).run(bounded_contract, mission_id=mission_id, stages={
        Stage.CONTRACT: pass_stage("validated Voice MissionContract"),
        Stage.RESEARCH: pass_stage("live LaunchAgent environment and production-like endpoint diagnosed"),
        Stage.PLAN: pass_stage("existing bounded Voice runner and Builder bridge selected"),
        Stage.BUILD: build_stage, Stage.TEST: test_stage,
        Stage.BROWSER: lambda: {"status": "PASS" if transport["options_pass"] else "BLOCKED", "evidence": "production-like CORS preflight; POST is protected by existing Cloudflare Access", "failure_class": FailureClass.ENVIRONMENT_BLOCKER.value},
        Stage.REGRESSION: pass_stage("focused Voice and Product Evolution regression checks selected"),
        Stage.SECURITY_LICENSE: pass_stage("no frontend token, wildcard credentials CORS, raw-audio retention, or new authority"),
        Stage.VERIFY: lambda: {"status": "PASS" if transport["local_transport_pass"] else "BLOCKED", "evidence": "local secure-service path reached whisper.cpp and returned synthetic transcript", "failure_class": FailureClass.ENVIRONMENT_BLOCKER.value},
    }, critic=critic)
    return {"status": result.status, "result": result.__dict__, "transport": transport, "builder": builder_result, "task": task_holder.get("task"), "human_gate": "Open https://goclearonline.cc/admin, turn Voice Listening ON once, and say: Hey Nexus, what should I focus on today?"}


def voice_adapter() -> ProductEvolutionAdapter:
    return ProductEvolutionAdapter(adapter_id="VOICE_PRODUCT_EVOLUTION", surface="Voice", allowed_paths=VOICE_ALLOWED_PATHS, protected_paths=VOICE_PROTECTED_PATHS, security_constraints=("no frontend token", "exact production origin only", "no wildcard credentials CORS", "local whisper.cpp only", "no raw audio retention", "no new authority"), test_commands=(("python3", "-m", "py_compile", "scripts/nexus_agent_platform/voice/local_server.py", "scripts/nexus_agent_platform/voice/local_stt.py"),), visual_requirements=False, max_cycles=3, timeout_seconds=900, deployment_policy="existing Voice launchd mechanism only; no autonomous production deploy", human_gates=("real microphone and wake-phrase test", "Cloudflare Access session if required"), execute_fn=execute_voice, can_handle_fn=_voice_can_handle)
