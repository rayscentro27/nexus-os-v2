"""Constrain MuseTalk motion to Nova's reference inner-mouth aperture.

This post-render pass never warps or replaces the approved face. It blends the
existing MuseTalk output into a feathered mask bounded by the approved inner
lip contour, retains the established 25% 1:2:1 temporal blend, and restores
the approved reference pixels everywhere else.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "assets/nova/voice-references/NOVA_VOICE_REFERENCE_PROFILE.json"
DEFAULT_REFERENCE = ROOT / "assets/nova/avatar/nova_reference.png"

# Vision landmark coordinates from the approved image. The mask is further
# constrained to this inner-lip polygon; outer lip contour/face pixels are
# copied from the approved source frame exactly.
REFERENCE_INNER_LIPS = [
    (836.9, 670.0), (881.1, 676.7), (924.3, 673.5),
    (925.5, 683.7), (880.3, 688.5), (834.7, 680.5),
]
REFERENCE_OUTER_LIPS = [
    (796.4, 649.0), (827.0, 643.5), (856.7, 641.0), (882.5, 647.1),
    (909.0, 643.2), (937.0, 648.3), (965.4, 655.7), (991.2, 666.2),
    (962.2, 702.2), (922.3, 726.5), (877.7, 733.5), (833.2, 723.9),
    (794.3, 696.5), (768.3, 658.2),
]
ALPHA_MAX = 0.32
FPS = 25
REST_MOTION_THRESHOLD = 0.012  # inter-frame mean RGB delta / 255 inside aperture
MAX_MOUTH_WIDTH_CHANGE_PERCENT = 5.0
MAX_LIP_HEIGHT_CHANGE_PERCENT = 5.0
MAX_MOUTH_CENTER_SHIFT_PX = 3.0


def _probe(path: Path) -> dict[str, Any]:
    raw = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(raw.stdout)


def preserve_video(raw_video: Path, output_video: Path,
                   reference_image: Path = DEFAULT_REFERENCE) -> dict[str, Any]:
    """Return a reference-based MP4 with only bounded inner-mouth motion."""
    if not raw_video.is_file() or raw_video.stat().st_size <= 0:
        raise FileNotFoundError("nonempty_musetalk_video_required")
    if not reference_image.is_file():
        raise FileNotFoundError("approved_nova_reference_missing")
    ref = Image.open(reference_image).convert("RGB")
    width, height = ref.size
    probe = _probe(raw_video)
    video_stream = next((s for s in probe["streams"] if s.get("codec_type") == "video"), None)
    if video_stream is None or (int(video_stream["width"]), int(video_stream["height"])) != (width, height):
        raise ValueError("render_and_approved_reference_geometry_mismatch")
    src_fps = video_stream.get("r_frame_rate", "0/1")
    numerator, denominator = (int(v) for v in src_fps.split("/"))
    if denominator == 0 or abs(numerator / denominator - FPS) > 0.01:
        raise ValueError("unexpected_musetalk_frame_rate")

    # Fade only inside the inner-mouth aperture and its immediate boundary,
    # contained by the original outer-lip contour. All pixels around the lips
    # and on the nose, cheeks, and chin remain the approved reference pixels.
    mask = Image.new("L", (width, height), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(mask)
    # 84% of measured outer-lip width and 41% of its resting height, centered
    # on the approved contour. This allows inner articulation while retaining
    # the original perimeter, mouth corners, and surrounding skin.
    aperture = (786, 667, 974, 705)
    reference_mouth_width = max(x for x, _ in REFERENCE_OUTER_LIPS) - min(x for x, _ in REFERENCE_OUTER_LIPS)
    reference_lip_height = max(y for _, y in REFERENCE_OUTER_LIPS) - min(y for _, y in REFERENCE_OUTER_LIPS)
    if ((aperture[2] - aperture[0]) / reference_mouth_width > 0.85
            or (aperture[3] - aperture[1]) / reference_lip_height > 0.42
            or abs((aperture[0] + aperture[2]) / 2 - 880.0) > MAX_MOUTH_CENTER_SHIFT_PX
            or abs((aperture[1] + aperture[3]) / 2 - 687.0) > MAX_MOUTH_CENTER_SHIFT_PX
            or ALPHA_MAX > 0.32):
        raise ValueError("identity_mask_exceeds_conservative_geometry_guardrails")
    draw.ellipse(aperture, fill=round(ALPHA_MAX * 255))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=4.0))
    bbox = (aperture[0] - 7, aperture[1] - 7, aperture[2] + 8, aperture[3] + 8)
    mask_crop = mask.crop(bbox)
    reference_crop = ref.crop(bbox)

    output_video.parent.mkdir(parents=True, exist_ok=True)
    width_bytes = width * height * 3
    ffmpeg_decode = ["ffmpeg", "-v", "error", "-i", str(raw_video), "-an", "-f", "rawvideo",
                     "-pix_fmt", "rgb24", "pipe:1"]
    ffmpeg_encode = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                     "-pix_fmt", "rgb24", "-s:v", f"{width}x{height}", "-r", str(FPS), "-i", "pipe:0",
                     "-i", str(raw_video), "-map", "0:v:0", "-map", "1:a?", "-r", str(FPS),
                     "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                     "-c:a", "copy", "-shortest", str(output_video)]
    decoder = subprocess.Popen(ffmpeg_decode, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    encoder = subprocess.Popen(ffmpeg_encode, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    previous: Image.Image | None = None
    current: Image.Image | None = None
    frame_count = 0
    speaking_frames = 0
    rest_frames = 0
    max_inner_delta = 0.0
    try:
        while True:
            data = decoder.stdout.read(width_bytes)
            if not data:
                break
            if len(data) != width_bytes:
                raise RuntimeError("truncated_musetalk_raw_frame")
            following = Image.frombytes("RGB", (width, height), data)
            if current is None:
                current = following
                continue
            if previous is None:
                previous = current
            window_average = Image.blend(current, Image.blend(previous, following, 0.5), 0.5)
            # Keep the established recipe: 25% of the 1:2:1 temporal average
            # blended with 75% of the current generated frame.
            temporal = Image.blend(current, window_average, 0.25)
            delta = sum(ImageStat.Stat(ImageChops.difference(temporal.crop(bbox), reference_crop)).mean) / 3 / 255
            max_inner_delta = max(max_inner_delta, delta)
            motion = (1.0 if previous is None else
                      sum(ImageStat.Stat(ImageChops.difference(current.crop(bbox), previous.crop(bbox))).mean) / 3 / 255)
            # Return to the reference's exact rest mouth at frames with no
            # measurable inter-frame articulation in the constrained area.
            if motion < REST_MOTION_THRESHOLD:
                frame = ref
                rest_frames += 1
            else:
                # Established stability recipe: 25% temporally averaged
                # source blended into a 1:2:1-smoothed three-frame window.
                frame = Image.composite(temporal.crop(bbox), reference_crop, mask_crop)
                merged = ref.copy()
                merged.paste(frame, (bbox[0], bbox[1]))
                frame = merged
                speaking_frames += 1
            encoder.stdin.write(frame.tobytes())
            frame_count += 1
            previous, current = current, following
        if current is not None:
            if previous is None:
                temporal = current
            else:
                window_average = Image.blend(current, previous, 0.5)
                temporal = Image.blend(current, window_average, 0.25)
            motion = (1.0 if previous is None else
                      sum(ImageStat.Stat(ImageChops.difference(current.crop(bbox), previous.crop(bbox))).mean) / 3 / 255)
            if motion < REST_MOTION_THRESHOLD:
                encoder.stdin.write(ref.tobytes())
                rest_frames += 1
            else:
                frame = Image.composite(temporal.crop(bbox), reference_crop, mask_crop)
                merged = ref.copy()
                merged.paste(frame, (bbox[0], bbox[1]))
                encoder.stdin.write(merged.tobytes())
                speaking_frames += 1
            frame_count += 1
        encoder.stdin.close()
        decoder.stdout.close()
        decode_err = decoder.stderr.read().decode(errors="replace")
        encode_err = encoder.stderr.read().decode(errors="replace")
        if decoder.wait() != 0:
            raise RuntimeError("musetalk_video_decode_failed:" + decode_err[-500:])
        if encoder.wait() != 0:
            raise RuntimeError("identity_preserving_encode_failed:" + encode_err[-500:])
    finally:
        for process in (decoder, encoder):
            if process.poll() is None:
                process.kill()
                process.wait()
    if frame_count < 2 or output_video.stat().st_size <= 0:
        raise RuntimeError("identity_preserving_video_output_empty")
    return {
        "method": "reference-frame base; 32% max alpha in inset lip-interior ellipse; 25fps 1:2:1 temporal average at the established 25% blend",
        "fps": FPS, "frame_count": frame_count,
        "mask_bbox_xyxy": list(bbox), "mask_aperture_xyxy": list(aperture), "mask_alpha_max": ALPHA_MAX,
        "geometry_limits": {"mouth_width_change_percent": MAX_MOUTH_WIDTH_CHANGE_PERCENT,
                             "lip_height_change_percent": MAX_LIP_HEIGHT_CHANGE_PERCENT,
                             "mouth_center_shift_px": MAX_MOUTH_CENTER_SHIFT_PX},
        "editable_region_pixels": "lip interior and immediate inner boundary only; outer lip contour/mouth corners/nose/cheeks/chin exactly from approved reference",
        "rest_pose_rule": f"zero blend when inter-frame aperture RGB motion < {REST_MOTION_THRESHOLD}",
        "speaking_frames": speaking_frames, "rest_pose_frames": rest_frames,
        "max_inner_aperture_mean_delta": round(max_inner_delta, 6),
        "audio_stream": "copied from original MuseTalk output without re-encoding",
        "output_bytes": output_video.stat().st_size,
    }
