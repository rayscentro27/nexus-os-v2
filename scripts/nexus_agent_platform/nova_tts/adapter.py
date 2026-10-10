"""Provider-neutral Nova TTS interface.

ChatTTS is deliberately private-test-only. This adapter refuses production or
commercial use and does not alter Nexus's configured production provider.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
GUARD_PATH = ROOT / "configs/nova_tts/chattts_private_test.json"


def _guard() -> dict[str, Any]:
    guard = json.loads(GUARD_PATH.read_text(encoding="utf-8"))
    if (guard.get("provider") != "ChatTTS"
            or guard.get("registration") != "PRIVATE_TEST_PROVIDER"
            or guard.get("usage_mode") != "PRIVATE_NON_COMMERCIAL_TEST"
            or guard.get("production_commercial_approved") is not False
            or guard.get("customer_facing_allowed") is not False
            or guard.get("marketing_allowed") is not False
            or guard.get("paid_product_allowed") is not False
            or guard.get("production_routing_allowed") is not False):
        raise RuntimeError("chattts_private_noncommercial_guard_invalid")
    return guard


def synthesize(
    text: str,
    *,
    provider: str = "chattts",
    voice_config: Mapping[str, Any] | None = None,
    worker: Any | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Synthesize to WAV bytes through a Modal worker; never a production route.

    `worker` is an active Modal ChatTTS class handle supplied by the bounded
    canary runner. If omitted, this function opens its own one-shot Modal app
    context, so consumers still use a provider-neutral call shape.
    """
    guard = _guard()
    config = dict(voice_config or {})
    if provider.lower() != "chattts":
        raise ValueError("this_private_adapter_only_supports_chattts")
    if config.get("usage_mode", "PRIVATE_NON_COMMERCIAL_TEST") != "PRIVATE_NON_COMMERCIAL_TEST":
        raise PermissionError("chattts_is_private_noncommercial_test_only")
    if any(config.get(key) for key in ("production", "customer_facing", "marketing", "paid_product")):
        raise PermissionError("chattts_production_or_commercial_routing_denied")
    seed = int(config.get("speaker_seed", 1701))
    style = config.get("style", "default")
    if style not in {"default", "restrained_pause"}:
        raise ValueError("unsupported_chattts_style")

    own_context = worker is None
    call_started = time.monotonic()
    import os
    from nexus_agent_platform.provider_enforcement import execute
    job_id=os.environ.get("NEXUS_DURABLE_JOB_ID")
    estimate={"requests":1,"gpu_seconds":float(os.environ.get("NEXUS_MODAL_GPU_SECONDS_ESTIMATE","1")),"billable":True}
    try: estimate["cost"]=float(os.environ["NEXUS_MODAL_ESTIMATED_COST_PER_JOB"])
    except (KeyError,ValueError): pass
    def invoke():
        if own_context:
            import modal
            from deploy.modal.nova_chattts_modal import app, ChatTTSGPU
            with modal.enable_output(), app.run():
                return ChatTTSGPU().synthesize.remote(text, seed, style, guard["usage_mode"], False)
        return worker.synthesize.remote(text, seed, style, guard["usage_mode"], False)
    result=execute("MODAL","CHAT_TTS","GPU_GENERATION",estimate,invoke,job_id=job_id,
        job_type=os.environ.get("NEXUS_JOB_TYPE","NOVA_TTS"),
        correlation_id=os.environ.get("NEXUS_CORRELATION_ID") or job_id,
        actual_usage=lambda value:{"requests":1,"gpu_seconds":float(value.get("synthesis_seconds") or estimate["gpu_seconds"]),**({"cost":estimate["cost"]} if "cost" in estimate else {})},
        external_ref=lambda value:str(value.get("request_id") or "") or None)
    remote_call_seconds = round(time.monotonic() - call_started, 3)

    if not isinstance(result, dict) or result.get("status") != "SUCCESS":
        raise RuntimeError("chattts_modal_synthesis_failed")
    audio = result.get("audio_wav")
    if not isinstance(audio, bytes) or not audio.startswith(b"RIFF") or len(audio) < 44:
        raise RuntimeError("chattts_modal_audio_bytes_invalid")
    path = Path(output_path) if output_path is not None else None
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(audio)
    return {
        "audio_path": str(path) if path is not None else None,
        "audio_bytes": audio,
        "audio_format": "wav",
        "sample_rate": int(result["sample_rate"]),
        "duration": float(result["duration_seconds"]),
        "latency_ms": float(result["synthesis_seconds"]) * 1000,
        "remote_call_seconds": remote_call_seconds,
        "provider": guard["provider"],
        "registration": guard["registration"],
        "usage_mode": guard["usage_mode"],
        "model": result["model"],
        "speaker_seed": seed,
        "style": style,
        "request_id": result["request_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "modal": {key: value for key, value in result.items() if key != "audio_wav"},
    }
