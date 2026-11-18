#!/usr/bin/env python3
"""Create three bounded Nova lip-motion variants from an existing render/audio."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.nova.nova_lip_motion_recovery import CANDIDATES, MOUTH_CENTER, RESTING_LIP_HEIGHT, RESTING_MOUTH_WIDTH, frame_series, render_candidate

RAW = ROOT / "artifacts/nova/identity-preservation/nova_lip_identity_canary_raw.mp4"
CURRENT = ROOT / "artifacts/nova/identity-preservation/nova_lip_identity_canary.mp4"
OUT = ROOT / "artifacts/nova/lip-motion-recovery"
REPORT = ROOT / "reports/nova/NEXUS_NOVA_LIP_MOTION_RECOVERY_2026-10-03.txt"
METRICS = OUT / "nova_lip_motion_metrics.json"
FILES = {k: OUT / f"nova_lip_motion_{k}.mp4" for k in "ABC"}


def stream_info(path: Path) -> dict[str, Any]:
    data = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout)
    v = next(s for s in data["streams"] if s.get("codec_type") == "video")
    a = next(s for s in data["streams"] if s.get("codec_type") == "audio")
    return {"video_duration_seconds": float(v["duration"]), "audio_duration_seconds": float(a["duration"]),
            "container_duration_seconds": float(data["format"]["duration"]),
            "video_start_seconds": float(v.get("start_time", 0)), "audio_start_seconds": float(a.get("start_time", 0)),
            "fps": v["r_frame_rate"], "frame_count": int(v.get("nb_frames", 0)),
            "audio_sample_rate_hz": int(a["sample_rate"]), "video_codec": v["codec_name"],
            "audio_codec": a["codec_name"]}


def audio_packet_hash(path: Path) -> str:
    audio = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-c:a", "copy", "-f", "data", "pipe:1"],
        capture_output=True, check=True, timeout=30,
    ).stdout
    return hashlib.sha256(audio).hexdigest()


def output_path_for(key: str) -> str:
    return str(FILES[key])


def main() -> dict[str, Any]:
    if not RAW.is_file() or not CURRENT.is_file():
        raise FileNotFoundError("verified_existing_raw_and_current_canary_required")
    if REPORT.exists() or METRICS.exists() or any(path.exists() for path in FILES.values()):
        raise FileExistsError("refusing_to_overwrite_existing_lip_motion_recovery_artifact")
    OUT.mkdir(parents=True, exist_ok=True)
    raw_info = stream_info(RAW)
    raw_audio_hash = audio_packet_hash(RAW)
    metrics: dict[str, Any] = {
        "schema_version": "nexus.nova.lip-motion-recovery.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_raw_musetalk": str(RAW.relative_to(ROOT)),
        "source_audio": "audio track reused from raw MuseTalk MP4; no TTS synthesis or audio timing changes",
        "reference_image": "assets/nova/avatar/nova_reference.png",
        "identity_limits": {"mouth_width_change_percent": 5.0, "lip_height_change_percent": 5.0,
                            "mouth_center_shift_px": 3.0},
        "identity_split": {"outer_lip_identity_alpha": 0.0,
                           "generated_outer_lip_contour": "none; reference pixels retained",
                           "generated_face_outside_inner_aperture": "none; reference pixels retained",
                           "inner_aperture_width_fraction_of_reference_outer_lip": {k: CANDIDATES[k]["width_fraction"] for k in "ABC"}},
        "audio_video_sync": {"raw": raw_info, "current_previous_postprocess": stream_info(CURRENT),
                             "raw_audio_packet_sha256": raw_audio_hash, "candidates": {}},
        "current_motion": frame_series(CURRENT),
        "raw_motion": frame_series(RAW),
        "candidates": {},
    }
    for key in "ABC":
        output = FILES[key]
        generated = render_candidate(RAW, output, CANDIDATES[key])
        cand = CANDIDATES[key]
        aperture_w = round(cand["width_fraction"] * RESTING_MOUTH_WIDTH)
        aperture_h = round(cand["height_fraction"] * RESTING_LIP_HEIGHT)
        cx, cy = MOUTH_CENTER
        dy = cand.get("center_y_offset_px", 0.0)
        bounds = (round(cx-aperture_w/2), round(cy+dy-aperture_h/2), round(cx+aperture_w/2), round(cy+dy+aperture_h/2))
        observed = frame_series(output, articulation_bounds=bounds)
        sync = stream_info(output)
        packet_hash = audio_packet_hash(output)
        sync_ok = (
            sync["fps"] == "25/1" and sync["frame_count"] == raw_info["frame_count"]
            and abs(sync["video_start_seconds"] - raw_info["video_start_seconds"]) <= 0.001
            and abs(sync["audio_start_seconds"] - raw_info["audio_start_seconds"]) <= 0.001
            and abs(sync["audio_duration_seconds"] - raw_info["audio_duration_seconds"]) < 0.002
            and packet_hash == raw_audio_hash
        )
        metrics["audio_video_sync"]["candidates"][key] = {**sync, "audio_packet_sha256": packet_hash,
                                                             "post_process_sync_ok": sync_ok}
        metrics["candidates"][key] = {**generated, **observed, "path": str(output.relative_to(ROOT)),
                                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                                      "sync_ok": sync_ok}
    METRICS.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    m = metrics["current_motion"]
    raw_sync_ok = (raw_info["fps"] == "25/1" and raw_info["video_start_seconds"] == raw_info["audio_start_seconds"]
                   and abs(raw_info["audio_duration_seconds"] - raw_info["video_duration_seconds"]) < 0.04)
    lines = [
        "NOVA LIP MOTION RECOVERY — CONTROLLED INNER-MOUTH CANARIES",
        f"Generated: {metrics['created_at']}", "", "SOURCE / SYNC",
        f"Raw source: {RAW.relative_to(ROOT)}",
        f"Raw source timing: {json.dumps(raw_info, sort_keys=True)}",
        f"Previous post-process timing: {json.dumps(metrics['audio_video_sync']['current_previous_postprocess'], sort_keys=True)}",
        f"RAW_MUSETALK_SYNC_OK={raw_sync_ok}", "",
        "CURRENT FAILURE MEASUREMENT",
        f"Current canary mouth motion (mean adjacent-frame RGB delta/pixel): {m['mouth_motion_mean_rgb_delta_per_pixel']}",
        f"Current canary inner-mouth motion: {m['inner_mouth_motion_mean_rgb_delta_per_pixel']}",
        f"Current canary outer-lip motion: {m['outer_lip_motion_mean_rgb_delta_per_pixel']}",
        f"Current canary jaw-region motion: {m['jaw_motion_mean_rgb_delta_per_pixel']}",
        f"Current canary audio-active frames: {m['audio_activity']['active_frames']}/{m['audio_activity']['frame_count']}",
        f"Current canary audio↔inner-motion correlation: {m['audio_mouth_motion_correlation']}", "",
        "IDENTITY / MOTION DESIGN",
        "Outer lip identity region: approved Nova reference image retained; generated contribution 0%.",
        "Inner mouth articulation: generated pixels composited per frame inside a narrow ellipse clipped to the measured lip polygon; candidate-specific width, height and alpha are recorded below.",
        "All pixels outside that inner aperture come from the approved image. Pause restoration uses source audio RMS, never small mouth motion; voiced frames are not replaced or dropped.",
        "MuseTalk source frame order/timing is kept. Audio packets are copied byte-for-byte; no TTS rerun.",
        "A/B/C use their recorded per-candidate inner alpha, vertical aperture and temporal smoothing. Outer lip contour and all surrounding face pixels remain reference-locked.", "",
        "CANDIDATES",
    ]
    for key in "ABC":
        row = metrics["candidates"][key]
        path = output_path_for(key)
        lines += [f"CANDIDATE_{key}=artifacts/nova/lip-motion-recovery/nova_lip_motion_{key}.mp4",
                  f"INNER_GENERATED_ALPHA_{key}={row['inner_alpha']}",
                  f"INNER_HEIGHT_FRACTION_{key}={row['inner_height_fraction_of_resting_lip_height']}",
                  f"INNER_WIDTH_FRACTION_{key}={row['inner_width_fraction_of_reference_outer_lip']}",
                  f"AUDIO_ACTIVE_FRAMES_{key}={row['audio_activity']['active_frames']}/{row['audio_activity']['frame_count']}",
                  f"MOUTH_MOTION_{key}={row['mouth_motion_mean_rgb_delta_per_pixel']}",
                  f"INNER_MOUTH_MOTION_{key}={row['inner_mouth_motion_mean_rgb_delta_per_pixel']}",
                  f"OUTER_LIP_MOTION_{key}={row['outer_lip_motion_mean_rgb_delta_per_pixel']}",
                  f"JAW_MOTION_{key}={row['jaw_motion_mean_rgb_delta_per_pixel']}",
                  f"AUDIO_MOUTH_MOTION_CORRELATION_{key}={row['audio_mouth_motion_correlation']}",
                  f"AUDIO_INNER_APERTURE_CORRELATION_{key}={row['audio_inner_aperture_correlation']}",
                  f"POST_PROCESS_SYNC_OK_{key}={row['sync_ok']}", f"OPEN_COMMAND_{key}=open \"{path}\""]
    lines += ["", "No automatic final selection. Waiting for Ray's visual review."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
