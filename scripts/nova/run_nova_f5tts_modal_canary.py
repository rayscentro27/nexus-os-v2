#!/usr/bin/env python3
"""Run the bounded private F5-TTS reference-conditioned Nova canary."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["MODAL_PROFILE"] = "goclearonline"

import modal  # noqa: E402
from deploy.modal.nova_f5tts_modal import (  # noqa: E402
    app, F5TTSWorker, USAGE_MODE, F5_CODE_LICENSE, F5_MODEL_LICENSE,
    PRODUCTION_COMMERCIAL_APPROVED, GPU,
)

REFERENCE = ROOT / "assets/nova/voice-references/nova_primary_voice_reference.mp3"
WORKING_DIR = ROOT / "artifacts/nova/f5tts/reference"
WORKING_AUDIO = WORKING_DIR / "nova_primary_voice_reference.wav"
TRANSCRIPT = ROOT / "assets/nova/voice-references/nova_primary_voice_reference_transcript.txt"
CANARY_DIR = ROOT / "artifacts/nova/f5tts-canary"
AUDITION_DIR = ROOT / "artifacts/nova/f5tts-auditions"
TARGET = (
    "Hey Ray, everything looks good with Nexus. Research is active, Trading is "
    "testing a few new strategies, and I'll let you know if anything needs your attention."
)
L4_USD_PER_SECOND = 0.000222


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def probe_audio(path: Path) -> dict:
    raw = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,sample_rate,channels,duration,bits_per_sample",
         "-show_entries", "format=duration,size", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    ).stdout
    result = json.loads(raw)
    if not result.get("streams") or int(result.get("format", {}).get("size", 0)) <= 0:
        raise RuntimeError(f"audio_probe_failed:{path}")
    return result


def save_audio(path: Path, result: dict) -> dict:
    if result.get("status") != "SUCCESS" or not result.get("audio_wav"):
        raise RuntimeError("f5_synthesis_failed")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing_to_overwrite:{path}")
    audio = result["audio_wav"]
    path.write_bytes(audio)
    probe = probe_audio(path)
    return {k: v for k, v in result.items() if k != "audio_wav"} | {
        "path": str(path.relative_to(ROOT)),
        "file_size_bytes": len(audio),
        "sha256": sha256(audio),
        "probe": probe,
    }


from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main() -> dict:
    for path in (CANARY_DIR / "nova_f5tts_reference_canary.wav",
                 AUDITION_DIR / "nova_f5tts_A.wav", AUDITION_DIR / "nova_f5tts_B.wav"):
        if path.exists():
            raise FileExistsError(f"refusing_to_overwrite:{path}")
    if not REFERENCE.is_file() or REFERENCE.stat().st_size == 0:
        raise FileNotFoundError(REFERENCE)
    if F5_CODE_LICENSE != "MIT" or F5_MODEL_LICENSE != "CC-BY-NC-4.0" or PRODUCTION_COMMERCIAL_APPROVED:
        raise RuntimeError("f5_license_guard_failed")

    WORKING_DIR.mkdir(parents=True, exist_ok=True)
    CANARY_DIR.mkdir(parents=True, exist_ok=True)
    AUDITION_DIR.mkdir(parents=True, exist_ok=True)
    if not WORKING_AUDIO.exists():
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", str(REFERENCE),
             "-map_metadata", "0", "-acodec", "pcm_s16le", str(WORKING_AUDIO)],
            check=True, timeout=60,
        )
    source_hash = sha256(REFERENCE.read_bytes())
    working_probe = probe_audio(WORKING_AUDIO)

    timings: list[float] = []
    records: dict[str, dict] = {}
    start_all = time.monotonic()
    first_call_started = start_all
    asr_metadata: dict = {}
    runtime_metadata: dict = {}
    with modal.enable_output(), app.run():
        worker = F5TTSWorker()
        if TRANSCRIPT.exists():
            reference_text = TRANSCRIPT.read_text(encoding="utf-8").strip()
            if not reference_text:
                raise RuntimeError("existing_reference_transcript_is_empty")
            asr_metadata = {"transcript_reused": True}
        else:
            asr_metadata = worker.transcribe_reference.remote(WORKING_AUDIO.read_bytes())
            reference_text = asr_metadata.get("transcript", "").strip()
            if not reference_text:
                raise RuntimeError("reference_transcript_missing_from_asr")
            if TRANSCRIPT.exists():
                raise FileExistsError(f"refusing_to_overwrite:{TRANSCRIPT}")
            TRANSCRIPT.write_text(reference_text + "\n", encoding="utf-8")
        if TARGET not in reference_text and len(reference_text) < 4:
            raise RuntimeError("reference_transcript_unusable")

        # The canary is the first true gen_text inference using both persisted
        # primary audio and the exact reference transcript.
        canary_result = worker.synthesize_reference.remote(
            WORKING_AUDIO.read_bytes(), reference_text, TARGET,
        )
        first_call_seconds = round(time.monotonic() - first_call_started, 3)
        canary_path = CANARY_DIR / "nova_f5tts_reference_canary.wav"
        records["canary"] = save_audio(canary_path, canary_result)
        timings.append(float(canary_result["latency_seconds"]))

        # Three explicitly warm baseline repetitions; keep the first one as A.
        for index in range(3):
            result = worker.synthesize_reference.remote(
                WORKING_AUDIO.read_bytes(), reference_text, TARGET, speed=1.0,
            )
            timings.append(float(result["latency_seconds"]))
            if index == 0:
                records["A"] = save_audio(AUDITION_DIR / "nova_f5tts_A.wav", result)
        # F5 exposes inference speed. B uses a small slowdown only; no warmth or
        # speaker-identity control is claimed. No separate conversational style
        # control is exposed by this pinned inference API, so C is omitted.
        result_b = worker.synthesize_reference.remote(
            WORKING_AUDIO.read_bytes(), reference_text, TARGET, speed=0.96,
        )
        records["B"] = save_audio(AUDITION_DIR / "nova_f5tts_B.wav", result_b)
        runtime_metadata = worker.runtime_metrics.remote()

    total_seconds = round(time.monotonic() - start_all, 3)
    # Keep the measured three warm repetitions explicitly in the receipt.
    # The first is A; the remaining two are not saved as audition artifacts.
    # Re-read their timings from the per-call list: item 0 is canary.
    warm_times = timings[1:4]
    warm_sorted = sorted(warm_times)
    warm_p50 = warm_sorted[1]
    audio_duration = float(records["canary"]["duration_seconds"])
    transcript_hash = sha256(reference_text.encode("utf-8"))
    receipt = {
        "schema_version": "nexus.nova.f5tts-reference-canary.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": "F5-TTS",
        "code_license": F5_CODE_LICENSE,
        "model_license": F5_MODEL_LICENSE,
        "usage_mode": USAGE_MODE,
        "production_commercial_approved": False,
        "reference_source": str(REFERENCE.relative_to(ROOT)),
        "reference_source_sha256": source_hash,
        "reference_working_audio": str(WORKING_AUDIO.relative_to(ROOT)),
        "reference_working_audio_sha256": sha256(WORKING_AUDIO.read_bytes()),
        "reference_audio_duration_seconds": float(working_probe["format"]["duration"]),
        "reference_sample_rate": working_probe["streams"][0]["sample_rate"],
        "reference_transcript_path": str(TRANSCRIPT.relative_to(ROOT)),
        "reference_transcript": reference_text,
        "reference_transcript_sha256": transcript_hash,
        "reference_conditioning": {
            "reference_audio_actually_used": records["canary"]["reference_sha256"] == sha256(WORKING_AUDIO.read_bytes()),
            "reference_text_actually_used": records["canary"]["reference_text_sha256"] == transcript_hash,
            "new_text_actually_generated": records["canary"]["generated_text_sha256"] == sha256(TARGET.encode()),
            "target_text": TARGET,
        },
        "modal": {"app": "nexus-creative-gpu-worker", "gpu": GPU, **runtime_metadata},
        "f5_revisions": {
            "code": "SWivid/F5-TTS@283252563dbf91be625e0c27926acfaac449186c",
            "model": "SWivid/F5-TTS@84e5a410d9cead4de2f847e7c9369a6440bdfaca",
        },
        "first_remote_call_elapsed_seconds_including_modal_start_and_transcript": first_call_seconds,
        "total_run_seconds": total_seconds,
        "warm_synthesis_seconds": warm_times,
        "warm_synthesis_p50_seconds": warm_p50,
        "warm_rtf_p50": round(warm_p50 / audio_duration, 4),
        "audio_duration_seconds": audio_duration,
        "estimated_l4_gpu_cost_usd": round(float(runtime_metadata["container_active_seconds"]) * L4_USD_PER_SECOND, 6),
        "canary": records["canary"],
        "auditions": {k: v for k, v in records.items() if k in {"A", "B"}},
        "audition_count": 2,
        "C_omitted_reason": "Pinned F5 inference API exposes speed but no restrained conversational prosody control; no unsupported style control was fabricated.",
        "fidelity_review": {
            "status": "WAITING_RAY_LISTENING_REVIEW",
            "speaker_identity_scoring": False,
            "claim": "No biometric identity verification is performed; acoustic fidelity requires human listening review.",
        },
        "avatar_test": {"status": "NOT_RUN_BY_TTS_STAGE"},
        "modal_call_ids": [r.get("request_id") for r in [records["canary"], records["A"], records["B"]]],
    }
    if not all(receipt["reference_conditioning"].values()):
        raise RuntimeError("f5_reference_conditioning_receipt_check_failed")
    receipt_path = CANARY_DIR / "nova_f5tts_canary_receipt.json"
    if receipt_path.exists():
        raise FileExistsError(f"refusing_to_overwrite:{receipt_path}")
    # Keep successful voice evidence if the optional avatar guard rejects.
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    # One bounded MuseTalk render, followed only by the already-locked local
    # Candidate B color pass and its existing fail-closed regression guard.
    from deploy.modal.nova_musetalk_canary import app as avatar_app, render_cached
    from scripts.nova.nova_lip_color_pipeline import apply_candidate_b
    ref_image = ROOT / "assets/nova/avatar/nova_reference.png"
    identity_cache = ROOT / "artifacts/nova/avatar-canary/nova-identity-cache.pt"
    avatar_path = CANARY_DIR / "nova_f5tts_candidate_b_avatar_test.mp4"
    raw_avatar_path = CANARY_DIR / "nova_f5tts_candidate_b_avatar_raw.mp4"
    regression_path = CANARY_DIR / "nova_f5tts_candidate_b_regression.json"
    for output_path in (avatar_path, raw_avatar_path, regression_path):
        if output_path.exists():
            raise FileExistsError(f"refusing_to_overwrite:{output_path}")
    image_bytes = ref_image.read_bytes()
    image_hash = sha256(image_bytes)
    expected_image_hash = "a0e6a873726ea6831dcc2d8cdbbd603eeaad3324486f7e396c1bd33bb2ee825c"
    cache_bytes = identity_cache.read_bytes()
    if image_hash != expected_image_hash or sha256(cache_bytes) != "e969fc2753a35869ef3259e477f1337bd35367c135c5170d1371cd75cd820f8b":
        raise RuntimeError("approved_nova_avatar_identity_assets_hash_mismatch")
    request_id = "nova-f5tts-" + uuid.uuid4().hex
    with modal.enable_output(), avatar_app.run():
        avatar_raw_result = render_cached.remote(
            image_bytes, (AUDITION_DIR / "nova_f5tts_A.wav").read_bytes(),
            cache_bytes, image_hash, request_id,
        )
    if avatar_raw_result.get("status") != "SUCCESS" or not avatar_raw_result.get("video_bytes"):
        raise RuntimeError("f5_candidate_b_raw_musetalk_render_failed")
    raw_avatar_path.write_bytes(avatar_raw_result["video_bytes"])
    try:
        lip_receipt = apply_candidate_b(raw_avatar_path, avatar_path)
        guard_pass = lip_receipt.get("selection") == "B" and lip_receipt.get("frame_timestamps_equal") is True
        if guard_pass:
            regression_path.write_text(json.dumps(lip_receipt, indent=2) + "\n", encoding="utf-8")
            avatar_status = "PASS_REAL_MUSETALK_PLUS_LOCKED_B"
        else:
            avatar_status = "FAIL_CANDIDATE_B_REGRESSION_GUARD"
    except RuntimeError as exc:
        message = str(exc)
        marker = "nova_lip_regression_guard_failed:"
        failure = json.loads(message.split(marker, 1)[1]) if marker in message else {"error": message}
        lip_receipt = {"status": "FAIL", **failure}
        guard_pass = False
        avatar_status = "FAIL_CANDIDATE_B_REGRESSION_GUARD"
        regression_path.write_text(json.dumps(lip_receipt, indent=2) + "\n", encoding="utf-8")
    receipt["avatar_test"] = {
        "status": avatar_status,
        "raw_musetalk_path": str(raw_avatar_path.relative_to(ROOT)),
        "final_video_path": str(avatar_path.relative_to(ROOT)),
        "request_id": request_id,
        "musetalk_runtime_seconds": avatar_raw_result.get("runtime_seconds"),
        "lip_pipeline_receipt": str(regression_path.relative_to(ROOT)),
        "candidate_b_regression_guard_pass": guard_pass,
        "guard_result": lip_receipt,
    }
    receipt["estimated_l4_gpu_cost_usd"] = round(
        (float(runtime_metadata["container_active_seconds"]) * L4_USD_PER_SECOND)
        + (float(avatar_raw_result.get("runtime_seconds", 0)) * 0.000164), 6
    )
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS_REAL_MODAL_REFERENCE_CONDITIONED_CANARY",
        "reference_transcript": reference_text,
        "canary": records["canary"]["path"],
        "sample_rate": records["canary"]["sample_rate"],
        "duration_seconds": audio_duration,
        "warm_synthesis_seconds": warm_times,
        "warm_rtf_p50": receipt["warm_rtf_p50"],
        "auditions": [records[k]["path"] for k in ("A", "B")],
        "gpu_active_seconds": runtime_metadata["container_active_seconds"],
        "estimated_gpu_cost_usd": receipt["estimated_l4_gpu_cost_usd"],
        "receipt": str(receipt_path.relative_to(ROOT)),
    }, indent=2))
    return receipt


if __name__ == "__main__":
    main()
