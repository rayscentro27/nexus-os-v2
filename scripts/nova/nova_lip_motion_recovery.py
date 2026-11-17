"""Reference-locked Nova lip compositing with motion-preserving inner mouth."""
from __future__ import annotations

import array
import json
import math
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "assets/nova/avatar/nova_reference.png"
FPS = 25
MAX_MOUTH_WIDTH_CHANGE_PERCENT = 5.0
MAX_LIP_HEIGHT_CHANGE_PERCENT = 5.0
MAX_MOUTH_CENTER_SHIFT_PX = 3.0

OUTER_LIPS = [
    (796.4, 649.0), (827.0, 643.5), (856.7, 641.0), (882.5, 647.1),
    (909.0, 643.2), (937.0, 648.3), (965.4, 655.7), (991.2, 666.2),
    (962.2, 702.2), (922.3, 726.5), (877.7, 733.5), (833.2, 723.9),
    (794.3, 696.5), (768.3, 658.2),
]
OUTER_BOUNDS = (768.35, 640.99, 991.21, 733.48)
MOUTH_CENTER = (879.78, 687.24)
RESTING_LIP_HEIGHT = 92.48
RESTING_MOUTH_WIDTH = 222.86

CANDIDATES: dict[str, dict[str, Any]] = {
    "A": {"name": "conservative", "inner_alpha": 0.45, "height_fraction": 0.55, "width_fraction": 0.50,
          "smoothing_mode": "existing_25_percent_1_2_1"},
    "B": {"name": "balanced", "inner_alpha": 0.52, "height_fraction": 0.65, "width_fraction": 0.46,
          "smoothing_mode": "reduced_10_percent_1_2_1"},
    "C": {"name": "strong_natural_articulation", "inner_alpha": 0.49, "height_fraction": 0.75, "width_fraction": 0.44,
          "smoothing_mode": "outer_identity_boundary_only_inner_unfiltered"},
}


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return json.loads(result.stdout)


def audio_rms_by_frame(video: Path, frames: int, rate: int = 16000) -> tuple[list[float], dict[str, Any]]:
    """Measure 40 ms RMS windows from the existing muxed source audio."""
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
         "-f", "s16le", "pipe:1"], capture_output=True, check=True, timeout=60,
    ).stdout
    samples = array.array("h")
    samples.frombytes(pcm[:len(pcm) - len(pcm) % 2])
    if not samples:
        raise ValueError("existing_musetalk_audio_track_empty")
    per_frame = round(rate / FPS)
    rms = []
    for i in range(frames):
        win = samples[i * per_frame:(i + 1) * per_frame]
        rms.append(math.sqrt(sum(v * v for v in win) / len(win)) / 32768 if win else 0.0)
    threshold = max(0.004, 0.035 * max(rms))
    return rms, {"sample_rate_hz": rate, "window_ms": 40, "threshold_rms_fs": threshold,
                 "active_frames": sum(v >= threshold for v in rms), "frame_count": frames,
                 "active_ratio": round(sum(v >= threshold for v in rms) / max(1, frames), 4),
                 "rms_peak": round(max(rms), 6), "rms_mean": round(sum(rms) / len(rms), 6)}


def _masks(reference: Image.Image, height_fraction: float, alpha: float,
           width_fraction: float = 0.50, center_y_offset: float = 0.0) -> tuple[tuple[int, int, int, int], Image.Image, Image.Image]:
    width, height = reference.size
    # Keep the articulation span narrow relative to Nova's measured outer lip width.
    aperture_width = round(width_fraction * RESTING_MOUTH_WIDTH)
    aperture_height = round(height_fraction * RESTING_LIP_HEIGHT)
    cx, cy = MOUTH_CENTER[0], MOUTH_CENTER[1] + center_y_offset
    aperture = (round(cx - aperture_width / 2), round(cy - aperture_height / 2),
                round(cx + aperture_width / 2), round(cy + aperture_height / 2))
    if aperture_width / RESTING_MOUTH_WIDTH > 0.55 or aperture_height / RESTING_LIP_HEIGHT > 0.76:
        raise ValueError("candidate_aperture_exceeds_outer_lip_identity_envelope")
    margin = 8
    bbox = (max(0, aperture[0] - margin), max(0, aperture[1] - margin),
            min(width, aperture[2] + margin), min(height, aperture[3] + margin))
    polygon = Image.new("L", reference.size, 0)
    ImageDraw.Draw(polygon).polygon(OUTER_LIPS, fill=255)
    inner = Image.new("L", reference.size, 0)
    ImageDraw.Draw(inner).ellipse(aperture, fill=round(alpha * 255))
    inner = ImageChops.multiply(inner, polygon).filter(ImageFilter.GaussianBlur(radius=2.0))
    outer_identity = ImageChops.subtract(polygon, inner)
    return bbox, inner.crop(bbox), outer_identity.crop(bbox)


def _temporal(current: Image.Image, previous: Image.Image | None, following: Image.Image | None,
              strength: float) -> Image.Image:
    if strength <= 0.0 or previous is None and following is None:
        return current
    p = previous or current
    n = following or current
    average_121 = Image.blend(current, Image.blend(p, n, 0.5), 0.5)
    return Image.blend(current, average_121, strength)


def _composite_frame(reference: Image.Image, source: Image.Image, bbox: tuple[int, int, int, int],
                     inner_mask: Image.Image, voiced: bool) -> Image.Image:
    # The measured outer-lip identity ring is 100% reference. Only the inner
    # articulation mask receives generated pixels; pauses return to neutral.
    if not voiced:
        return reference
    result = reference.copy()
    patch = Image.composite(source.crop(bbox), reference.crop(bbox), inner_mask)
    result.paste(patch, (bbox[0], bbox[1]))
    return result


def render_candidate(raw_video: Path, output_video: Path, candidate: dict[str, Any],
                     reference_path: Path = REFERENCE) -> dict[str, Any]:
    if not raw_video.is_file() or not output_video.parent.exists():
        raise FileNotFoundError("raw_render_and_precreated_output_directory_required")
    if output_video.exists():
        raise FileExistsError(f"refusing_to_overwrite_candidate:{output_video}")
    ref = Image.open(reference_path).convert("RGB")
    width, height = ref.size
    raw_probe = _probe(raw_video)
    video_stream = next((s for s in raw_probe["streams"] if s.get("codec_type") == "video"), None)
    if not video_stream or (int(video_stream["width"]), int(video_stream["height"])) != ref.size:
        raise ValueError("raw_musetalk_and_reference_geometry_mismatch")
    rate_num, rate_den = (int(p) for p in video_stream["r_frame_rate"].split("/"))
    if rate_den == 0 or abs(rate_num / rate_den - FPS) > 0.01:
        raise ValueError("raw_musetalk_fps_mismatch")
    frame_count = int(video_stream.get("nb_frames") or round(float(video_stream["duration"]) * FPS))
    audio_rms, audio_stats = audio_rms_by_frame(raw_video, frame_count)
    bbox, inner_mask, outer_identity_mask = _masks(ref, float(candidate["height_fraction"]),
                                                    float(candidate["inner_alpha"]),
                                                    float(candidate.get("width_fraction", 0.50)),
                                                    float(candidate.get("center_y_offset_px", 0.0)))
    smoothing_modes = {
        "existing_25_percent_1_2_1": 0.25,
        "reduced_10_percent_1_2_1": 0.10,
        "outer_identity_boundary_only_inner_unfiltered": 0.0,
    }
    if candidate["smoothing_mode"] not in smoothing_modes:
        raise ValueError("unknown_candidate_smoothing_mode")
    smoothing_strength = smoothing_modes[candidate["smoothing_mode"]]
    output_video.parent.mkdir(parents=True, exist_ok=True)
    frame_bytes = width * height * 3
    decoder = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(raw_video), "-an", "-vsync", "0", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "pipe:1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s:v", f"{width}x{height}", "-r", str(FPS), "-i", "pipe:0", "-i", str(raw_video),
         "-map", "0:v:0", "-map", "1:a:0", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", str(output_video)],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    previous: Image.Image | None = None
    current: Image.Image | None = None
    count = voiced_count = rest_count = 0
    frame_motion: list[float] = []
    aperture_deviation: list[float] = []
    prior_patch: Image.Image | None = None
    try:
        while True:
            data = decoder.stdout.read(frame_bytes)
            if not data:
                break
            if len(data) != frame_bytes:
                raise RuntimeError("truncated_raw_musetalk_frame")
            following = Image.frombytes("RGB", ref.size, data)
            if current is None:
                current = following
                continue
            source = _temporal(current, previous, following, smoothing_strength)
            voiced = count < len(audio_rms) and audio_rms[count] >= audio_stats["threshold_rms_fs"]
            frame = _composite_frame(ref, source, bbox, inner_mask, voiced)
            patch = frame.crop(bbox)
            if prior_patch is not None:
                stat = ImageStat.Stat(ImageChops.difference(patch, prior_patch))
                frame_motion.append(sum(stat.mean) / 3)
            aperture_deviation.append(sum(ImageStat.Stat(ImageChops.difference(patch, ref.crop(bbox))).mean) / 3)
            encoder.stdin.write(frame.tobytes())
            count += 1
            voiced_count += int(voiced)
            rest_count += int(not voiced)
            prior_patch = patch
            previous, current = current, following
        if current is not None:
            source = _temporal(current, previous, None, smoothing_strength)
            voiced = count < len(audio_rms) and audio_rms[count] >= audio_stats["threshold_rms_fs"]
            frame = _composite_frame(ref, source, bbox, inner_mask, voiced)
            patch = frame.crop(bbox)
            if prior_patch is not None:
                frame_motion.append(sum(ImageStat.Stat(ImageChops.difference(patch, prior_patch)).mean) / 3)
            aperture_deviation.append(sum(ImageStat.Stat(ImageChops.difference(patch, ref.crop(bbox))).mean) / 3)
            encoder.stdin.write(frame.tobytes())
            count += 1
            voiced_count += int(voiced)
            rest_count += int(not voiced)
        encoder.stdin.close()
        decoder.stdout.close()
        decode_err, encode_err = decoder.stderr.read().decode(errors="replace"), encoder.stderr.read().decode(errors="replace")
        if decoder.wait() != 0:
            raise RuntimeError("raw_frame_decode_failed:" + decode_err[-400:])
        if encoder.wait() != 0:
            raise RuntimeError("candidate_encode_failed:" + encode_err[-400:])
    finally:
        for proc in (decoder, encoder):
            if proc.poll() is None:
                proc.kill(); proc.wait()
    if count != frame_count or output_video.stat().st_size <= 0:
        raise RuntimeError(f"candidate_frame_count_or_file_invalid:{count}/{frame_count}")
    return {
        "candidate": candidate["name"], "inner_alpha": candidate["inner_alpha"],
        "original_contribution_inner_min": round(1 - float(candidate["inner_alpha"]), 2),
        "outer_lip_identity_contribution": 1.0,
        "inner_height_fraction_of_resting_lip_height": candidate["height_fraction"],
        "inner_width_fraction_of_reference_outer_lip": candidate.get("width_fraction", 0.50),
        "aperture_center_y_offset_px": candidate.get("center_y_offset_px", 0.0),
        "inner_aperture_xyxy": list(bbox), "frame_count": count, "fps": FPS,
        "voiced_audio_frames": voiced_count, "rest_frames": rest_count,
        "audio_activity": audio_stats, "smoothing_mode": candidate["smoothing_mode"],
        "temporal_smoothing_strength": smoothing_strength,
        "temporal_processing_scope": "inner aperture only; source frame order preserved",
        "motion_mean_rgb_delta_per_pixel": round(sum(frame_motion) / max(1, len(frame_motion)), 4),
        "motion_peak_rgb_delta_per_pixel": round(max(frame_motion, default=0.0), 4),
        "aperture_deviation_mean_rgb": round(sum(aperture_deviation) / max(1, len(aperture_deviation)), 4),
        "video_size_bytes": output_video.stat().st_size,
    }


def frame_series(path: Path, reference_path: Path = REFERENCE,
                 articulation_bounds: tuple[int, int, int, int] | None = None) -> dict[str, Any]:
    """Measure lip ROI motion/deviation and audio-energy correlation in a muxed video."""
    ref = Image.open(reference_path).convert("RGB")
    w, h = ref.size
    stream = next(s for s in _probe(path)["streams"] if s.get("codec_type") == "video")
    count = int(stream.get("nb_frames") or round(float(stream["duration"]) * FPS))
    rms, audio_stats = audio_rms_by_frame(path, count)
    # Fixed regions let the old render and all new variants share one measure.
    mouth_box = (760, 630, 1005, 750)
    inner_box = (820, 655, 950, 716)
    jaw_box = (780, 735, 1000, 835)
    lips_outer_mask = Image.new("L", ref.size, 0)
    ImageDraw.Draw(lips_outer_mask).polygon(OUTER_LIPS, fill=255)
    articulation = Image.new("L", ref.size, 0)
    if articulation_bounds is None:
        # The previous frozen canary used a 188x38 px core ellipse.
        articulation_bounds = (786, 667, 974, 705)
    ImageDraw.Draw(articulation).ellipse(articulation_bounds, fill=255)
    lips_outer_mask = ImageChops.subtract(lips_outer_mask, articulation)
    generated_frame_count = 0
    previous_full: Image.Image | None = None
    prev_mouth: Image.Image | None = None
    prev_inner: Image.Image | None = None
    prev_jaw: Image.Image | None = None
    motions: list[float] = []; inner_motion: list[float] = []; outer_motion: list[float] = []; jaw_motion: list[float] = []
    mouth_deviation: list[float] = []
    output = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        bytes_per_frame = w * h * 3
        while data := output.stdout.read(bytes_per_frame):
            if len(data) != bytes_per_frame:
                break
            im = Image.frombytes("RGB", ref.size, data)
            mouth, inner, jaw = im.crop(mouth_box), im.crop(inner_box), im.crop(jaw_box)
            if prev_mouth is not None:
                motions.append(sum(ImageStat.Stat(ImageChops.difference(mouth, prev_mouth)).mean) / 3)
                inner_motion.append(sum(ImageStat.Stat(ImageChops.difference(inner, prev_inner)).mean) / 3)
                jaw_motion.append(sum(ImageStat.Stat(ImageChops.difference(jaw, prev_jaw)).mean) / 3)
                # The outer contour/ring is source locked. Compare only its polygon pixels.
                diff = ImageChops.difference(im, previous_full)
                outer_motion.append(sum(ImageStat.Stat(diff, mask=lips_outer_mask).mean) / 3)
            mouth_deviation.append(sum(ImageStat.Stat(ImageChops.difference(inner, ref.crop(inner_box))).mean) / 3)
            prev_mouth, prev_inner, prev_jaw, previous_full = mouth, inner, jaw, im
            generated_frame_count += 1
    finally:
        output.stdout.close()
        err = output.stderr.read().decode(errors="replace")
        rc = output.wait()
        if rc != 0:
            raise RuntimeError("candidate_motion_probe_failed:" + err[-400:])
    def pearson(a: list[float], b: list[float]) -> float | None:
        n = min(len(a), len(b))
        if n < 2: return None
        a, b = a[:n], b[:n]; ma, mb = sum(a) / n, sum(b) / n
        va = sum((x - ma) ** 2 for x in a); vb = sum((x - mb) ** 2 for x in b)
        if not va or not vb: return None
        return round(sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb), 4)
    rms_for_motion = rms[1:1 + len(inner_motion)]
    return {
        "frame_count": generated_frame_count, "audio_activity": audio_stats,
        "mouth_motion_mean_rgb_delta_per_pixel": round(sum(motions) / max(1, len(motions)), 4),
        "mouth_motion_peak_rgb_delta_per_pixel": round(max(motions, default=0.0), 4),
        "inner_mouth_motion_mean_rgb_delta_per_pixel": round(sum(inner_motion) / max(1, len(inner_motion)), 4),
        "outer_lip_motion_mean_rgb_delta_per_pixel": round(sum(outer_motion) / max(1, len(outer_motion)), 4),
        "jaw_motion_mean_rgb_delta_per_pixel": round(sum(jaw_motion) / max(1, len(jaw_motion)), 4),
        "audio_mouth_motion_correlation": pearson(rms_for_motion, inner_motion),
        "audio_inner_aperture_correlation": pearson(rms[:len(mouth_deviation)], mouth_deviation),
        "inner_aperture_deviation_mean_rgb": round(sum(mouth_deviation) / max(1, len(mouth_deviation)), 4),
    }
