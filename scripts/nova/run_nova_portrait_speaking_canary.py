#!/usr/bin/env python3
"""Run F5 A -> MuseTalk -> Candidate B -> private LivePortrait test canary."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["MODAL_PROFILE"] = "goclearonline"

import modal
from deploy.modal.nova_f5tts_modal import app as f5_app, F5TTSWorker, USAGE_MODE
from deploy.modal.nova_musetalk_canary import app as avatar_app, render_cached
from deploy.modal.nova_portrait_renderer_canary import app as portrait_app, speaking_canary, REFERENCE_SHA256
from scripts.nova.nova_lip_color_pipeline import apply_candidate_b, _packets, _probe, _video_timestamps

TEXT = "Hey Ray. Everything looks good with Nexus. I'm here, I'm listening, and I'll let you know if anything needs your attention."
OUT = ROOT / "artifacts/nova/portrait-renderer"
REF_IMG = ROOT / "assets/nova/avatar/nova_reference.png"
REF_WAV = ROOT / "artifacts/nova/f5tts/reference/nova_primary_voice_reference.wav"
TRANSCRIPT = ROOT / "assets/nova/voice-references/nova_primary_voice_reference_transcript.txt"
CACHE = ROOT / "artifacts/nova/avatar-canary/nova-identity-cache.pt"


from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main() -> dict:
    paths = {
        "voice": OUT / "nova_portrait_speaking_A.wav",
        "raw": OUT / "nova_portrait_speaking_raw_musetalk.mp4",
        "candidate_b": OUT / "nova_portrait_speaking_candidate_b.mp4",
        "guard": OUT / "nova_portrait_speaking_candidate_b_guard.json",
        "final": OUT / "nova_portrait_speaking_canary.mp4",
        "receipt": OUT / "nova_portrait_speaking_canary.json",
    }
    if any(p.exists() for p in paths.values()):
        raise FileExistsError("refusing_to_overwrite_portrait_speaking_canary_artifact")
    image_bytes = REF_IMG.read_bytes()
    image_sha = hashlib.sha256(image_bytes).hexdigest()
    if image_sha != REFERENCE_SHA256:
        raise RuntimeError("approved_nova_reference_hash_mismatch")
    ref_bytes = REF_WAV.read_bytes()
    transcript = TRANSCRIPT.read_text(encoding="utf-8").strip()
    transcript_sha = hashlib.sha256(transcript.encode()).hexdigest()
    f5_record: dict = {}
    with modal.enable_output(), f5_app.run():
        worker = F5TTSWorker()
        result = worker.synthesize_reference.remote(
            ref_bytes, transcript, TEXT, speed=1.0,
            usage_mode=USAGE_MODE, production_requested=False,
        )
        f5_record = {k: v for k,v in result.items() if k != "audio_wav"}
        if (result.get("status") != "SUCCESS" or
            result.get("reference_sha256") != hashlib.sha256(ref_bytes).hexdigest() or
            result.get("reference_text_sha256") != transcript_sha or
            result.get("generated_text_sha256") != hashlib.sha256(TEXT.encode()).hexdigest()):
            raise RuntimeError("f5_reference_conditioning_check_failed")
        audio = result["audio_wav"]
        paths["voice"].write_bytes(audio)

    cache_bytes = CACHE.read_bytes()
    with modal.enable_output(), avatar_app.run():
        rendered = render_cached.remote(image_bytes, audio, cache_bytes, image_sha, str(uuid.uuid4()))
    if rendered.get("status") != "SUCCESS" or rendered.get("reference_sha256") != image_sha:
        raise RuntimeError("musetalk_raw_render_failed")
    raw_bytes = rendered.pop("video_bytes")
    paths["raw"].write_bytes(raw_bytes)
    diag = apply_candidate_b(paths["raw"], paths["candidate_b"], diagnostic_path=paths["guard"])

    with modal.enable_output(), portrait_app.run():
        motion = speaking_canary.remote(paths["candidate_b"].read_bytes(), image_sha)
    final_bytes = motion.pop("video_bytes")
    paths["final"].write_bytes(final_bytes)

    in_probe, out_probe = _probe(paths["candidate_b"]), _probe(paths["final"])
    bi = next(s for s in in_probe["streams"] if s.get("codec_type")=="video")
    vi = next(s for s in out_probe["streams"] if s.get("codec_type")=="video")
    audio_equal = _packets(paths["candidate_b"],"a") == _packets(paths["final"],"a")
    same_frames = len(_video_timestamps(paths["candidate_b"])) == len(_video_timestamps(paths["final"]))
    receipt = {
        "schema_version": "nexus.nova.liveportrait-speaking-canary.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "test_only": True, "commercial_use_approved": False,
        "text": TEXT,
        "reference_sha256": image_sha,
        "f5": {k:f5_record.get(k) for k in ("provider","model","voice","reference_sha256","reference_text_sha256","generated_text_sha256","sample_rate","duration_seconds","latency_seconds","speed","gpu","usage_mode","production_commercial_approved")},
        "musetalk": {k:rendered.get(k) for k in ("gpu_type","runtime_seconds","musetalk_commit","identity_cache_reused")},
        "candidate_b_guard": diag,
        "portrait_renderer": motion,
        "regression": {
            "candidate_b_guard_pass": diag.get("guard_result", {}).get("status") == "PASS",
            "frame_count_equal": same_frames,
            "fps_equal": bi.get("r_frame_rate") == vi.get("r_frame_rate"),
            "dimensions_equal": [bi.get("width"),bi.get("height")] == [vi.get("width"),vi.get("height")],
            "audio_packets_equal": audio_equal,
        },
        "artifacts": {k:str(v.relative_to(ROOT)) for k,v in paths.items() if k!="receipt"},
    }
    paths["receipt"].write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))
    return receipt


if __name__ == "__main__":
    main()
