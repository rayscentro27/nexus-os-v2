#!/usr/bin/env python3
"""Private Candidate A F5 confirmation and locked Candidate B avatar check."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import textwrap
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["MODAL_PROFILE"] = "goclearonline"

import modal  # noqa: E402
from deploy.modal.nova_f5tts_modal import (  # noqa: E402
    F5TTSWorker, USAGE_MODE, F5_CODE_LICENSE, F5_MODEL_LICENSE,
    PRODUCTION_COMMERCIAL_APPROVED, GPU,
    F5_CODE_REVISION, F5_MODEL_REVISION, VOCODER_REVISION,
    app as f5_app,
)

CONFIG = ROOT / "configs/nova_tts/f5_candidate_a_private_test.json"
TRANSCRIPT = ROOT / "assets/nova/voice-references/nova_primary_voice_reference_transcript.txt"
REF_WAV = ROOT / "artifacts/nova/f5tts/reference/nova_primary_voice_reference.wav"
REF_MP3 = ROOT / "assets/nova/voice-references/nova_primary_voice_reference.mp3"
OUT_DIR = ROOT / "artifacts/nova/f5tts-final"
CANARY_DIR = ROOT / "artifacts/nova/f5tts-canary"
TARGET = "Hey Ray, everything looks good with Nexus. Research is active, Trading is testing a few new strategies, and I'll let you know if anything needs your attention."
OUTPUT = OUT_DIR / "nova_f5tts_A_confirmed.wav"
RAW_VIDEO = OUT_DIR / "nova_f5tts_A_candidate_b_raw.mp4"
FINAL_VIDEO = OUT_DIR / "nova_f5tts_A_candidate_b_avatar.mp4"
RECEIPT = OUT_DIR / "nova_f5tts_A_confirmation_receipt.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main() -> None:
    config = json.loads(CONFIG.read_text())
    ref_audio = REF_WAV.read_bytes()
    ref_text = TRANSCRIPT.read_text(encoding="utf-8").strip()
    if not ref_text.startswith("Hi, Ray.") or "Rae" in ref_text:
        raise RuntimeError("corrected_reference_transcript_check_failed")
    if sha(ref_audio) != config["reference_working_audio_sha256"]:
        raise RuntimeError("reference_working_audio_hash_mismatch")
    if sha(REF_MP3.read_bytes()) != config["reference_audio_sha256"]:
        raise RuntimeError("primary_reference_hash_mismatch")
    if sha(ref_text.encode()) != config["reference_transcript_sha256"]:
        raise RuntimeError("reference_transcript_hash_mismatch")
    if F5_CODE_LICENSE != "MIT" or F5_MODEL_LICENSE != "CC-BY-NC-4.0" or PRODUCTION_COMMERCIAL_APPROVED:
        raise RuntimeError("private_noncommercial_license_guard_failed")
    if any(p.exists() for p in (OUTPUT, RAW_VIDEO, FINAL_VIDEO, RECEIPT)):
        raise FileExistsError("refusing_to_overwrite_confirmation_or_avatar_artifacts")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with modal.enable_output(), f5_app.run():
        worker = F5TTSWorker()
        result = worker.synthesize_reference.remote(
            ref_audio, ref_text, TARGET, speed=float(config["inference"]["speed"]),
            usage_mode=USAGE_MODE, production_requested=False,
        )
        runtime = worker.runtime_metrics.remote()
    if result.get("status") != "SUCCESS" or not result.get("audio_wav"):
        raise RuntimeError("candidate_a_confirmation_synthesis_failed")
    checks = {
        "REFERENCE_AUDIO_USED": result.get("reference_sha256") == sha(ref_audio),
        "REFERENCE_TEXT_USED": result.get("reference_text_sha256") == sha(ref_text.encode()),
        "NEW_TEXT_ACTUALLY_GENERATED": result.get("generated_text_sha256") == sha(TARGET.encode()),
        "CANDIDATE_A_SETTINGS_REUSED": result.get("speed") == 1.0 and result.get("model", "").startswith("F5TTS_v1_Base@"),
        "LICENSE_GUARD": result.get("usage_mode") == "PRIVATE_NON_COMMERCIAL_TEST" and result.get("production_commercial_approved") is False,
    }
    if not all(checks.values()):
        raise RuntimeError("candidate_a_conditioning_or_settings_check_failed:" + json.dumps(checks))
    OUTPUT.write_bytes(result["audio_wav"])
    if OUTPUT.stat().st_size == 0:
        raise RuntimeError("empty_confirmation_audio")

    avatar = {"status": "NOT_RUN", "guard_pass": False}
    if OUTPUT.stat().st_size:
        from deploy.modal.nova_musetalk_canary import app as avatar_app, render_cached
        image_path = ROOT / "assets/nova/avatar/nova_reference.png"
        cache_path = ROOT / "artifacts/nova/avatar-canary/nova-identity-cache.pt"
        image_bytes, cache_bytes = image_path.read_bytes(), cache_path.read_bytes()
        expected_image = "a0e6a873726ea6831dcc2d8cdbbd603eeaad3324486f7e396c1bd33bb2ee825c"
        expected_cache = "e969fc2753a35869ef3259e477f1337bd35367c135c5170d1371cd75cd820f8b"
        if sha(image_bytes) != expected_image or sha(cache_bytes) != expected_cache:
            raise RuntimeError("approved_avatar_asset_hash_mismatch")
        request_id = "nova-f5-a-confirmed-" + uuid.uuid4().hex
        with modal.enable_output(), avatar_app.run():
            raw = render_cached.remote(image_bytes, OUTPUT.read_bytes(), cache_bytes, sha(image_bytes), request_id)
        if raw.get("status") != "SUCCESS" or not raw.get("video_bytes"):
            raise RuntimeError("raw_musetalk_render_failed")
        RAW_VIDEO.write_bytes(raw["video_bytes"])
        lip_code = textwrap.dedent(r'''import json,sys
        from pathlib import Path
        import subprocess
        import scripts.nova.nova_lip_color_pipeline as pipeline
        original_run=pipeline.subprocess.run
        def draining_run(args,*a,**kw):
         if isinstance(args,(list,tuple)) and args and args[0]=='swift':
          timeout=kw.pop('timeout',None);kw.pop('capture_output',None);kw.pop('text',None)
          p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,**kw)
          try: out,err=p.communicate(timeout=timeout)
          except Exception: p.kill();p.communicate();raise
          return subprocess.CompletedProcess(args,p.returncode,out,err)
         return original_run(args,*a,**kw)
        pipeline.subprocess.run=draining_run
        from scripts.nova.nova_lip_color_pipeline import apply_candidate_b
        raw,final,receipt=map(Path,sys.argv[1:])
        try:
         data=apply_candidate_b(raw,final); out={"status":"PASS","guard_pass":True,"receipt":data}
        except RuntimeError as exc:
         marker="nova_lip_regression_guard_failed:"; msg=str(exc)
         detail=json.loads(msg.split(marker,1)[1]) if marker in msg else {"error":msg}
         out={"status":"FAIL_CANDIDATE_B_GUARD","guard_pass":False,"receipt":detail,"final_video_created":final.is_file()}
        receipt.write_text(json.dumps(out,indent=2)+"\\n")
        print(json.dumps(out))
        ''')
        lip_run = subprocess.run(["python3", "-c", lip_code, str(RAW_VIDEO), str(FINAL_VIDEO), str(OUT_DIR / "nova_f5tts_A_candidate_b_regression.json")], cwd=ROOT, capture_output=True, text=True, timeout=1800)
        if lip_run.returncode:
            avatar = {"status": "LOCAL_CANDIDATE_B_PROCESSING_ERROR", "guard_pass": False, "error": lip_run.stderr[-1500:]}
        else:
            avatar = json.loads(lip_run.stdout.strip().splitlines()[-1])

    record = {
        "schema_version": "nexus.nova.f5-candidate-a-confirmation.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider": "F5_TTS", "voice": "F5_CANDIDATE_A",
        "usage_mode": "PRIVATE_NON_COMMERCIAL_TEST", "commercial_production_approved": False,
        "config_path": str(CONFIG.relative_to(ROOT)), "config_sha256": sha(CONFIG.read_bytes()),
        "reference_audio_path": str(REF_MP3.relative_to(ROOT)),
        "reference_audio_sha256": sha(REF_MP3.read_bytes()),
        "reference_working_audio_sha256": sha(ref_audio),
        "reference_transcript_path": str(TRANSCRIPT.relative_to(ROOT)),
        "reference_transcript_sha256": sha(ref_text.encode()), "reference_transcript": ref_text,
        "target_text": TARGET, "reference_audio_used": checks["REFERENCE_AUDIO_USED"],
        "reference_text_used": checks["REFERENCE_TEXT_USED"],
        "new_text_generated": checks["NEW_TEXT_ACTUALLY_GENERATED"],
        "candidate_a_settings_reused": checks["CANDIDATE_A_SETTINGS_REUSED"],
        "f5_code_revision": F5_CODE_REVISION, "f5_model_revision": F5_MODEL_REVISION,
        "vocoder_revision": VOCODER_REVISION, "gpu": GPU,
        "synthesis": {k: v for k, v in result.items() if k != "audio_wav"},
        "audio_path": str(OUTPUT.relative_to(ROOT)), "audio_sha256": sha(OUTPUT.read_bytes()),
        "audio_size_bytes": OUTPUT.stat().st_size, "runtime": runtime,
        "avatar_path": str(FINAL_VIDEO.relative_to(ROOT)) if FINAL_VIDEO.exists() else None,
        "avatar_raw_path": str(RAW_VIDEO.relative_to(ROOT)) if RAW_VIDEO.exists() else None,
        "avatar": avatar,
    }
    RECEIPT.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"confirmation": str(OUTPUT.relative_to(ROOT)), "audio_sha256": record["audio_sha256"],
                      "synthesis_seconds": result.get("latency_seconds"), "sample_rate": result.get("sample_rate"),
                      "duration_seconds": result.get("duration_seconds"), "avatar": avatar,
                      "receipt": str(RECEIPT.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
