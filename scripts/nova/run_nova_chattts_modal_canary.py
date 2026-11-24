#!/usr/bin/env python3
"""Run private ChatTTS synthesis on the existing authenticated Nova Modal app."""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MODAL_PROFILE", "goclearonline")

from scripts.nexus_agent_platform.nova_tts.adapter import synthesize  # noqa: E402

CANARY_DIR = ROOT / "artifacts/nova/chattts-canary"
AUDITION_DIR = ROOT / "artifacts/nova/chattts-auditions"
REPORT_PATH = ROOT / "reports/nova/NEXUS_NOVA_CHAT_TTS_MODAL_CANARY_2026-10-03.txt"
PRIMARY_TEXT = (
    "Hey Ray, everything looks good with Nexus. Research is active, Trading is "
    "testing a few new strategies, and I'll let you know if anything needs your attention."
)
AVATAR_TEXT = (
    "Hey Ray. Everything looks good with Nexus. I'm here, I'm listening, and "
    "I'll let you know if anything needs your attention."
)
SEEDS = [17011, 27023, 37031, 47041, 57047, 67051]
STYLE_SEEDS = [SEEDS[0], SEEDS[2], SEEDS[5]]
UTC_NOW = lambda: datetime.now(timezone.utc).isoformat()


def verify_wav(data: bytes) -> dict[str, Any]:
    with wave.open(io.BytesIO(data), "rb") as wav:
        channels, rate, frames = wav.getnchannels(), wav.getframerate(), wav.getnframes()
        width = wav.getsampwidth()
        if channels < 1 or rate < 8000 or frames < 1 or width not in {1, 2, 3, 4}:
            raise ValueError("wav_header_or_audio_parameters_invalid")
        duration = frames / rate
    return {"file_exists": True, "size_bytes": len(data), "size_gt_zero": len(data) > 0,
            "audio_readable": True, "container": "WAV", "channels": channels,
            "sample_rate": rate, "frames": frames, "sample_width_bytes": width,
            "duration_seconds": round(duration, 4),
            "sha256": hashlib.sha256(data).hexdigest()}


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def smooth_existing_mouth_stability(raw_video: Path, final_video: Path) -> dict[str, Any]:
    """Apply the previously validated 25 fps, 1:2:1, 25%, mouth-only recipe."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate", "-of", "json", str(raw_video)],
        capture_output=True, text=True, check=True, timeout=20,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    width, height = int(stream["width"]), int(stream["height"])
    frame_rate = stream["r_frame_rate"]
    if (width, height, frame_rate) != (1824, 1376, "25/1"):
        raise RuntimeError(f"musetalk_output_geometry_or_rate_unexpected:{width}x{height}@{frame_rate}")
    # Elliptical feather: full smoothing over the central 80% radius and a
    # 20% radial feather. The blended source remains at 25% temporal average.
    roi_width, roi_height = 320, 220
    mask = bytearray(roi_width * roi_height)
    for y in range(roi_height):
        dy = (y - roi_height / 2) / (roi_height / 2)
        row = y * roi_width
        for x in range(roi_width):
            dx = (x - roi_width / 2) / (roi_width / 2)
            radius2 = dx * dx + dy * dy
            alpha = 255 if radius2 <= 0.64 else (round(255 * (1 - radius2) / 0.36) if radius2 < 1 else 0)
            mask[row + x] = max(0, min(255, alpha))
    graph = (
        "[0:v]split=2[base][source];"
        "[source]crop=320:220:752:590,split=3[baseA][baseB][temporal];"
        "[temporal]tmix=frames=3:weights='1 2 1':scale=4[avg];"
        "[baseA][avg]blend=all_expr='0.75*A+0.25*B'[mixed];"
        "[1:v]format=gray[mask];"
        "[baseB][mixed][mask]maskedmerge[roi];"
        "[base][roi]overlay=752:590:shortest=1[outv]"
    )
    final_video.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nova-mouth-mask-") as temp_dir:
        mask_path = Path(temp_dir) / "mouth-mask.pgm"
        mask_path.write_bytes(f"P5\n{roi_width} {roi_height}\n255\n".encode() + bytes(mask))
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw_video),
             "-loop", "1", "-framerate", "25", "-i", str(mask_path),
             "-filter_complex", graph, "-map", "[outv]", "-map", "0:a?", "-r", "25",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "copy", "-shortest", str(final_video)],
            check=True, timeout=300,
        )
    out_probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height,r_frame_rate,codec_name:format=duration",
         "-of", "json", str(final_video)], capture_output=True, text=True, check=True, timeout=20,
    )
    return {"method": "three-frame 1:2:1 temporal average, 25 percent blend, feathered mouth-only oval",
            "mouth_region": {"center_x": 912, "center_y": 700, "width": 320, "height": 220,
                             "feather": "outer 20 percent of oval radius"},
            "fps": 25, "audio_stream": "copied from MuseTalk output without re-encoding",
            "output_probe": json.loads(out_probe.stdout)}


from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main() -> dict[str, Any]:
    for folder in (CANARY_DIR, AUDITION_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    fixed_outputs = [CANARY_DIR / "nova_chattts_canary.wav",
                     CANARY_DIR / "nova_chattts_avatar_source.wav",
                     CANARY_DIR / "nova_chattts_avatar_raw.mp4",
                     CANARY_DIR / "nova_chattts_avatar_test.mp4",
                     *(AUDITION_DIR / f"nova_chattts_{i:02d}.wav" for i in range(1, 7)),
                     *(AUDITION_DIR / f"nova_chattts_{i:02d}_style.wav" for i in (1, 3, 6))]
    collision = [str(p) for p in fixed_outputs if p.exists()]
    if REPORT_PATH.exists():
        collision.append(str(REPORT_PATH))
    if collision:
        raise FileExistsError("refusing_to_overwrite_existing_chattts_artifacts:" + ",".join(collision))

    result: dict[str, Any] = {
        "schema_version": "nexus.nova.chattts-modal-canary.v1",
        "started_at": UTC_NOW(),
        "provider": "ChatTTS",
        "usage_mode": "PRIVATE_NON_COMMERCIAL_TEST",
        "production_commercial_approved": False,
        "production_routing_allowed": False,
        "modal_auth_reused": True,
        "modal_profile": os.environ["MODAL_PROFILE"],
        "modal_app": "nexus-creative-gpu-worker",
        "gpu_type": "T4",
        "status": "STARTING",
        "basic_canary": None,
        "auditions": [],
        "style_tests": [],
        "avatar_test": None,
        "gpu_active_seconds": None,
        "estimated_gpu_cost_usd": None,
        "errors": [],
    }
    overall_start = time.monotonic()
    try:
        import modal
        from deploy.modal.nova_chattts_modal import app, ChatTTSGPU

        with modal.enable_output(), app.run():
            worker = ChatTTSGPU()
            setup_started = time.monotonic()
            metrics = worker.runtime_metrics.remote()
            setup_call_seconds = round(time.monotonic() - setup_started, 3)
            result["image_build_pass"] = True
            result["model_load_pass"] = bool(metrics.get("model_load_seconds"))
            result["model_load_seconds"] = metrics.get("model_load_seconds")
            result["cold_start_seconds"] = setup_call_seconds
            result["setup_gpu_name"] = metrics.get("gpu_name")
            if result["model_load_pass"] is not True or not str(metrics.get("gpu_name", "")).strip():
                raise RuntimeError("chattts_model_load_or_gpu_metrics_failed")
            canary_start = time.monotonic()
            canary = synthesize(
                PRIMARY_TEXT, provider="chattts", worker=worker,
                voice_config={"usage_mode": "PRIVATE_NON_COMMERCIAL_TEST", "speaker_seed": SEEDS[0]},
                output_path=CANARY_DIR / "nova_chattts_canary.wav",
            )
            canary_meta = {k: v for k, v in canary.items() if k not in {"audio_bytes", "modal"}}
            canary_meta.update(verify_wav(canary["audio_bytes"]))
            canary_meta["modal_execution"] = canary["modal"]
            canary_meta["first_modal_call_seconds"] = round(time.monotonic() - canary_start, 3)
            canary_meta["cold_start_seconds"] = setup_call_seconds
            canary_meta["real_time_factor"] = round(canary_meta["latency_ms"] / 1000 / canary_meta["duration"], 4)
            if canary["modal"].get("cuda_available") is not True or canary["modal"].get("gpu_name") == "NO_CUDA":
                raise RuntimeError("modal_inference_did_not_use_cuda_gpu")
            if canary_meta["audio_readable"] is not True or canary_meta["size_gt_zero"] is not True:
                raise RuntimeError("chattts_basic_canary_audio_verification_failed")
            result["basic_canary"] = canary_meta
            result["adapter_pass"] = True
            result["status"] = "BASIC_CANARY_PASS"

            for index, seed in enumerate(SEEDS, start=1):
                meta = synthesize(
                    PRIMARY_TEXT, provider="chattts", worker=worker,
                    voice_config={"usage_mode": "PRIVATE_NON_COMMERCIAL_TEST", "speaker_seed": seed},
                    output_path=AUDITION_DIR / f"nova_chattts_{index:02d}.wav",
                )
                row = {k: v for k, v in meta.items() if k not in {"audio_bytes", "modal"}}
                row.update(verify_wav(meta["audio_bytes"]))
                row["modal_execution"] = meta["modal"]
                row["seed_index"] = index
                result["auditions"].append(row)

            # No listening claim is made. These 3 controlled follow-up seeds
            # span the candidate set and retain their exact seed for replay.
            for index, seed in ((1, SEEDS[0]), (3, SEEDS[2]), (6, SEEDS[5])):
                meta = synthesize(
                    PRIMARY_TEXT, provider="chattts", worker=worker,
                    voice_config={"usage_mode": "PRIVATE_NON_COMMERCIAL_TEST",
                                  "speaker_seed": seed, "style": "restrained_pause"},
                    output_path=AUDITION_DIR / f"nova_chattts_{index:02d}_style.wav",
                )
                row = {k: v for k, v in meta.items() if k not in {"audio_bytes", "modal"}}
                row.update(verify_wav(meta["audio_bytes"]))
                row["modal_execution"] = meta["modal"]
                row["seed_index"] = index
                result["style_tests"].append(row)

            avatar_audio = synthesize(
                AVATAR_TEXT, provider="chattts", worker=worker,
                voice_config={"usage_mode": "PRIVATE_NON_COMMERCIAL_TEST", "speaker_seed": SEEDS[0]},
                output_path=CANARY_DIR / "nova_chattts_avatar_source.wav",
            )
            result["avatar_audio"] = {k: v for k, v in avatar_audio.items()
                                      if k not in {"audio_bytes", "modal"}}
            result["avatar_audio"].update(verify_wav(avatar_audio["audio_bytes"]))
            result["avatar_audio"]["modal_execution"] = avatar_audio["modal"]
            metrics = worker.runtime_metrics.remote()
            result["modal_runtime_metrics"] = metrics

        import modal
        from deploy.modal.nova_musetalk_canary import MAX_AUDIO_BYTES, MAX_IMAGE_BYTES
        ref_path = ROOT / "assets/nova/avatar/nova_reference.png"
        cache_path = ROOT / "artifacts/nova/avatar-canary/nova-identity-cache.pt"
        if not ref_path.is_file() or not cache_path.is_file():
            raise FileNotFoundError("approved_nova_reference_or_identity_cache_missing")
        ref_bytes, cache_bytes = ref_path.read_bytes(), cache_path.read_bytes()
        if len(ref_bytes) > MAX_IMAGE_BYTES or len(avatar_audio["audio_bytes"]) > MAX_AUDIO_BYTES:
            raise ValueError("musetalk_input_size_limit_exceeded")
        expected_hash = hashlib.sha256(ref_bytes).hexdigest()
        raw_video_path = CANARY_DIR / "nova_chattts_avatar_raw.mp4"
        final_video_path = CANARY_DIR / "nova_chattts_avatar_test.mp4"
        render = modal.Function.from_name("nexus-creative-gpu-worker", "nova_live_avatar").remote(
            ref_bytes, avatar_audio["audio_bytes"], cache_bytes, expected_hash,
            f"chattts-private-{int(time.time())}",
        )
        if render.get("status") != "SUCCESS" or not isinstance(render.get("video_bytes"), bytes):
            raise RuntimeError("existing_nova_musetalk_function_render_failed:" + str(render.get("status")))
        write_exclusive(raw_video_path, render["video_bytes"])
        stability = smooth_existing_mouth_stability(raw_video_path, final_video_path)
        result["avatar_test"] = {
            "status": "PASS", "path": str(final_video_path.relative_to(ROOT)),
            "raw_path": str(raw_video_path.relative_to(ROOT)),
            "provider": "Modal", "function": "nexus-creative-gpu-worker/nova_live_avatar",
            "gpu_type": render.get("gpu_type"), "runtime_seconds": render.get("runtime_seconds"),
            "reference_sha256": render.get("reference_sha256"),
            "identity_cache_reused": render.get("identity_cache_reused"),
            "musetalk_commit": render.get("musetalk_commit"), "mouth_stability": stability,
        }
        result["gpu_active_seconds"] = round(
            float(metrics.get("container_active_seconds", 0)) +
            float(render.get("runtime_seconds", 0)), 3)
        result["gpu_type"] = "T4"
        # Modal's currently published T4 task rate is $0.000164/GPU-second;
        # this is an estimate, with CPU/memory/storage/network excluded.
        result["estimated_gpu_cost_usd"] = round(result["gpu_active_seconds"] * 0.000164, 6)
        warm_rtfs = [float(row["modal_execution"]["rtf"]) for row in result["auditions"]]
        result["warm_rtf_median"] = sorted(warm_rtfs)[len(warm_rtfs) // 2]
        # This implementation returns completed WAV buffers rather than a
        # live stream. A warm RTF <= 0.75 is near-interactive, never certified
        # fully interactive because first-call wake/load still applies.
        result["latency_class"] = "NEAR_INTERACTIVE" if result["warm_rtf_median"] <= 0.75 else "TOO_SLOW"
        result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "FAILED"
        result["errors"].append(f"{type(exc).__name__}: {str(exc)[:1600]}")
    result["completed_at"] = UTC_NOW()

    lines = [
        "NEXUS NOVA CHAT-TTS MODAL PRIVATE CANARY",
        f"Generated: {result['completed_at']}",
        "",
        "LICENSE / MODE GUARD",
        "PROVIDER=ChatTTS",
        "USAGE_MODE=PRIVATE_NON_COMMERCIAL_TEST",
        "PRODUCTION_COMMERCIAL_APPROVED=NO",
        "Model weights license: CC-BY-NC-4.0 (confirmed from the Hugging Face model card).",
        "Upstream ChatTTS README says released model is for academic purposes only.",
        "No customer-facing, marketing, paid-product, or production traffic is permitted.",
        "",
        f"MODAL_AUTH_REUSED={'YES' if result['modal_auth_reused'] else 'NO'}",
        f"MODAL_APP={result['modal_app']}",
        f"MODAL_GPU_SELECTED={result['gpu_type']}",
        f"CHAT_TTS_MODAL_IMAGE_BUILD_PASS={'YES' if result.get('image_build_pass') else 'NO'}",
        f"CHAT_TTS_MODEL_LOAD_PASS={'YES' if result.get('model_load_pass') else 'NO'}",
        f"CHAT_TTS_ADAPTER_PASS={'YES' if result.get('adapter_pass') else 'NO'}",
        f"CHAT_TTS_REAL_CANARY_PASS={'YES' if (result.get('basic_canary') or {}).get('audio_readable') else 'NO'}",
        f"CHAT_TTS_REAL_CANARY_PATH={CANARY_DIR / 'nova_chattts_canary.wav' if result.get('basic_canary') else 'NONE'}",
        f"CHAT_TTS_RTF={(result.get('basic_canary') or {}).get('real_time_factor', 'NOT_MEASURED')}",
        "",
        f"CHAT_TTS_AUDITIONS_CREATED={'YES' if len(result['auditions']) == 6 else 'NO'}",
        f"CHAT_TTS_AUDITION_COUNT={len(result['auditions'])}",
        f"CHAT_TTS_CONVERSATIONAL_STYLE_PASS={'YES' if len(result['style_tests']) == 3 else 'NO'}",
        f"CHAT_TTS_MUSETALK_COMPATIBILITY_PASS={'YES' if (result.get('avatar_test') or {}).get('status') == 'PASS' else 'NO'}",
        f"CHAT_TTS_AVATAR_TEST_PATH={(result.get('avatar_test') or {}).get('path', 'NONE')}",
        f"CHAT_TTS_LATENCY_CLASS={result.get('latency_class', 'NOT_CLASSIFIED')}",
        f"GPU_TYPE={result['gpu_type']}",
        f"GPU_ACTIVE_SECONDS={result.get('gpu_active_seconds', 'NOT_AVAILABLE')}",
        f"ESTIMATED_MODAL_COST=${result.get('estimated_gpu_cost_usd', 'NOT_AVAILABLE')} USD (GPU only estimate)",
        "",
        "CANARY DETAILS",
    ]
    if result.get("basic_canary"):
        m = result["basic_canary"]
        lines += [f"FILE_EXISTS={m['file_exists']}", f"SIZE_GT_ZERO={m['size_gt_zero']}",
                  f"AUDIO_READABLE={m['audio_readable']}", f"AUDIO_FORMAT={m['audio_format']}",
                  f"SAMPLE_RATE={m['sample_rate']}", f"DURATION_SECONDS={m['duration']}",
                  f"MODEL_ACTUALLY_USED={m['modal_execution']['model']}",
                  f"GPU_NAME={m['modal_execution']['gpu_name']}",
                  f"FIRST_MODAL_CALL_SECONDS={m['first_modal_call_seconds']}",
                  f"COLD_START_SECONDS={m['cold_start_seconds']}",
                  f"MODEL_LOAD_SECONDS={m['modal_execution']['model_load_seconds']}",
                  f"SYNTHESIS_SECONDS={m['latency_ms'] / 1000:.3f}"]
    if result["auditions"]:
        lines += ["", "AUDITIONS"]
        for row in result["auditions"]:
            audition_path = AUDITION_DIR / f"nova_chattts_{row['seed_index']:02d}.wav"
            lines += [f"{row['seed_index']:02d}: {audition_path}",
                      f"  seed={row['speaker_seed']} duration={row['duration']:.3f}s sample_rate={row['sample_rate']} "
                      f"synthesis={row['latency_ms']/1000:.3f}s remote_call={row['remote_call_seconds']:.3f}s "
                      f"RTF={row['modal_execution']['rtf']}"]
    if result["style_tests"]:
        lines += ["", "RESTRAINED STYLE TESTS", "Controls use [oral_2][laugh_0][break_2]; no added laugh/breath effect."]
        for row in result["style_tests"]:
            lines.append(f"Seed {row['seed_index']} (speaker seed {row['speaker_seed']}): "
                         f"open \"$HOME/nexus-os-v2-canonical/artifacts/nova/chattts-auditions/"
                         f"nova_chattts_{row['seed_index']:02d}_style.wav\"")
    if result.get("avatar_test"):
        lines += ["", "MUSE TALK COMPATIBILITY", json.dumps(result["avatar_test"], indent=2),
                  "The existing deployed MuseTalk function was called by name; its image/code were not rebuilt or changed.",
                  "Lip-stability postprocess kept: 25 fps, 1:2:1 three-frame average, 25% blend, mouth-only feathered oval."]
    lines += ["", "EXACT OPEN COMMANDS"]
    if result.get("basic_canary"):
        lines.append(f'open "$HOME/nexus-os-v2-canonical/artifacts/nova/chattts-canary/nova_chattts_canary.wav"')
    for i in range(1, 7):
        path = AUDITION_DIR / f"nova_chattts_{i:02d}.wav"
        if path.is_file(): lines.append(f'open "$HOME/nexus-os-v2-canonical/artifacts/nova/chattts-auditions/nova_chattts_{i:02d}.wav"')
    for i in (1, 3, 6):
        path = AUDITION_DIR / f"nova_chattts_{i:02d}_style.wav"
        if path.is_file(): lines.append(f'open "$HOME/nexus-os-v2-canonical/artifacts/nova/chattts-auditions/nova_chattts_{i:02d}_style.wav"')
    if (result.get("avatar_test") or {}).get("status") == "PASS":
        lines.append(f'open "$HOME/nexus-os-v2-canonical/{result["avatar_test"]["path"]}"')
    if result["errors"]:
        lines += ["", "ERRORS", *result["errors"]]
    lines += ["", "NOVA_PRODUCTION_TTS_PROVIDER=UNDECIDED",
              "CHAT_TTS_STATUS=PRIVATE_TEST_PROVIDER",
              "REMAINING_BLOCKERS=" + ("Inspect/listen to samples; ChatTTS is non-commercial only and cannot be promoted to production." if result["status"] == "PASS" else "Resolve the recorded Modal/image/model/runtime error, then rerun the bounded private canary."),
              "FINAL_STATUS=" + result["status"]]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    result.pop("avatar_audio", None)
    metadata_path = CANARY_DIR / "NOVA_CHAT_TTS_MODAL_CANARY.json"
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("\n".join(lines))
    print(f"METADATA_PATH={metadata_path}")
    return result


if __name__ == "__main__":
    main()
