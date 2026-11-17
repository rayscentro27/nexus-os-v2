"""Private, bounded LivePortrait model canary; never used by Nova service."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

import modal

APP_NAME = "nexus-nova-liveportrait-private-canary"
CODE_REVISION = "9b294b3d0536135442ea73cb01e6cb3ca7029dd3"
WEIGHT_REVISION = "82a4fa6735ca58432b6ce39301b4b9ee066dea47"
REFERENCE_SHA256 = "a0e6a873726ea6831dcc2d8cdbbd603eeaad3324486f7e396c1bd33bb2ee825c"
GPU = "L4"

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0", "libsm6", "libxext6")
    .pip_install(
        "torch==2.3.0", "torchvision==0.18.0",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install(
        "numpy==1.26.4", "pyyaml==6.0.1", "opencv-python-headless==4.10.0.84",
        "scipy==1.13.1", "imageio==2.34.2", "lmdb==1.4.1", "tqdm==4.66.4",
        "rich==13.7.1", "ffmpeg-python==0.2.0", "onnx==1.16.1",
        "onnxruntime-gpu==1.18.0", "scikit-image==0.24.0",
        "albumentations==1.4.10", "matplotlib==3.9.0", "imageio-ffmpeg==0.5.1",
        "tyro==0.8.5", "pykalman==0.9.7", "pillow>=10.2.0",
        "huggingface_hub==0.30.2",
    )
    .run_commands(
        f"git clone https://github.com/KlingAIResearch/LivePortrait.git /opt/LivePortrait && git -C /opt/LivePortrait checkout {CODE_REVISION}",
        "python -c \"from huggingface_hub import snapshot_download; snapshot_download(repo_id='KlingTeam/LivePortrait', revision='" + WEIGHT_REVISION + "', local_dir='/opt/LivePortrait/pretrained_weights', allow_patterns=['liveportrait/*','insightface/models/buffalo_l/*'])\"",
    )
    .workdir("/opt/LivePortrait")
)


@app.function(image=image, gpu=GPU, timeout=1800, scaledown_window=120)
def idle_canary(reference_png: bytes, expected_reference_sha256: str) -> dict:
    """Run official LivePortrait on L4; constrain scale and restore mouth ROI."""
    import cv2
    import numpy as np
    import torch

    if expected_reference_sha256 != REFERENCE_SHA256:
        raise ValueError("reference_hash_not_approved")
    if hashlib.sha256(reference_png).hexdigest() != REFERENCE_SHA256:
        raise ValueError("reference_bytes_hash_mismatch")
    root = Path("/tmp/nova-liveportrait")
    root.mkdir(parents=True, exist_ok=True)
    source = root / "nova_reference.png"
    source.write_bytes(reference_png)
    driver = Path("/opt/LivePortrait/assets/examples/driving/d11.mp4")
    output_dir = root / "out"
    output_dir.mkdir(exist_ok=True)
    t0 = time.monotonic()
    device = torch.device("cuda:0")
    torch.cuda.synchronize()
    load_started = time.monotonic()
    from src.config.argument_config import ArgumentConfig
    from src.config.crop_config import CropConfig
    from src.config.inference_config import InferenceConfig
    from src.live_portrait_pipeline import LivePortraitPipeline
    args = ArgumentConfig(
        source=str(source), driving=str(driver), output_dir=str(output_dir),
        animation_region="all", driving_option="expression-friendly",
        driving_multiplier=0.18, flag_eye_retargeting=False,
        flag_lip_retargeting=False, flag_normalize_lip=False,
        flag_use_half_precision=True, flag_stitching=True,
        flag_pasteback=True, flag_do_crop=True,
        source_max_dim=1824,
    )
    inf = InferenceConfig(**{k: v for k, v in vars(args).items() if hasattr(InferenceConfig, k)})
    crop = CropConfig(**{k: v for k, v in vars(args).items() if hasattr(CropConfig, k)})
    pipeline = LivePortraitPipeline(inference_cfg=inf, crop_cfg=crop)
    torch.cuda.synchronize()
    model_load_seconds = time.monotonic() - load_started
    video_path, _ = pipeline.execute(args)
    torch.cuda.synchronize()
    render_seconds = time.monotonic() - t0 - model_load_seconds

    # The model provides all animated facial motion. Restore the exact approved
    # mouth pixels with a feathered boundary so model-generated lip changes do
    # not enter the idle portrait. No image geometry is invented by this step.
    reference = cv2.imread(str(source), cv2.IMREAD_COLOR)
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if abs(w / h - 1824 / 1376) > 0.01 or count < 200 or fps < 24.9:
        raise RuntimeError(f"model_video_contract_failed:{w}x{h}:{count}@{fps}")
    sx, sy = w / 1824, h / 1376
    x0, y0, x1, y1 = (round(744*sx), round(617*sy), round(1015*sx), round(758*sy))
    roi_mask = np.zeros((h, w), np.uint8)
    roi_mask[y0:y1, x0:x1] = 255
    alpha = cv2.GaussianBlur(roi_mask, (0, 0), 10).astype(np.float32) / 255.0
    alpha = alpha[..., None]
    silent = root / "nova_portrait_idle_canary.mp4"
    enc = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
        "-pix_fmt", "bgr24", "-s:v", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
        str(silent),
    ], stdin=subprocess.PIPE)
    frames = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        merged = np.clip(frame.astype(np.float32) * (1.0 - alpha) + reference.astype(np.float32) * alpha, 0, 255).astype(np.uint8)
        enc.stdin.write(merged.tobytes())
        frames += 1
    cap.release()
    enc.stdin.close()
    if enc.wait() != 0 or frames != count:
        raise RuntimeError("mouth_protection_encode_or_frame_count_failed")
    return {
        "path": str(silent), "video_bytes": silent.read_bytes(),
        "provider": "LivePortrait", "model_revision": CODE_REVISION,
        "weight_revision": WEIGHT_REVISION, "gpu": GPU,
        "reference_sha256": REFERENCE_SHA256,
        "driver_asset": "LivePortrait official d11.mp4 example; used only as motion input",
        "animation_region": "all", "driving_multiplier": 0.18,
        "mouth_roi_px": [x0, y0, x1, y1], "mouth_source_restored": True,
        "fps": fps, "frame_count": frames, "dimensions": [w, h],
        "model_load_seconds": model_load_seconds,
        "render_seconds": render_seconds,
        "gpu_active_seconds": time.monotonic() - t0,
        "video_sha256": hashlib.sha256(silent.read_bytes()).hexdigest(),
    }


@app.function(image=image, gpu=GPU, timeout=2400, scaledown_window=120)
def speaking_canary(candidate_b_video: bytes, reference_sha256: str,
                    render_interpolation: str = "linear") -> dict:
    """Animate a B-processed MuseTalk video; restore each original B mouth ROI."""
    import cv2
    import numpy as np
    import torch

    if reference_sha256 != REFERENCE_SHA256 or not candidate_b_video:
        raise ValueError("approved_reference_or_candidate_b_required")
    root = Path("/tmp/nova-liveportrait-speaking")
    root.mkdir(parents=True, exist_ok=True)
    source = root / "candidate_b.mp4"
    source.write_bytes(candidate_b_video)
    driver = Path("/opt/LivePortrait/assets/examples/driving/d11.mp4")
    output_dir = root / "out"
    output_dir.mkdir(exist_ok=True)
    t0 = time.monotonic()
    torch.cuda.synchronize()
    load_started = time.monotonic()
    from src.config.argument_config import ArgumentConfig
    from src.config.crop_config import CropConfig
    from src.config.inference_config import InferenceConfig
    from src.live_portrait_pipeline import LivePortraitPipeline
    if render_interpolation not in {"linear", "cubic", "lanczos4"}:
        raise ValueError("unsupported_render_interpolation")
    # The pinned project binds INTER_LINEAR as _transform_img's default
    # argument. This canary-only override tests paste-back resampling; all
    # model motion, weights, inputs, and movement controls remain unchanged.
    from src.utils import crop as crop_utils
    interpolation = {
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
        "lanczos4": cv2.INTER_LANCZOS4,
    }[render_interpolation]
    crop_utils._transform_img.__defaults__ = (interpolation, None)
    args = ArgumentConfig(
        source=str(source), driving=str(driver), output_dir=str(output_dir),
        animation_region="all", driving_option="expression-friendly",
        driving_multiplier=0.12, flag_eye_retargeting=False,
        flag_lip_retargeting=False, flag_normalize_lip=False,
        flag_use_half_precision=True, flag_stitching=True,
        flag_pasteback=True, flag_do_crop=True, source_max_dim=1824,
        audio_priority="source",
    )
    inf = InferenceConfig(**{k: v for k, v in vars(args).items() if hasattr(InferenceConfig, k)})
    crop = CropConfig(**{k: v for k, v in vars(args).items() if hasattr(CropConfig, k)})
    pipeline = LivePortraitPipeline(inference_cfg=inf, crop_cfg=crop)
    torch.cuda.synchronize()
    model_load_seconds = time.monotonic() - load_started
    model_video, _ = pipeline.execute(args)
    torch.cuda.synchronize()
    render_seconds = time.monotonic() - t0 - model_load_seconds

    original = cv2.VideoCapture(str(source))
    generated = cv2.VideoCapture(str(model_video))
    fps = original.get(cv2.CAP_PROP_FPS)
    count = int(original.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(original.get(cv2.CAP_PROP_FRAME_WIDTH)), int(original.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if (w, h, round(fps)) != (1824, 1376, 25) or count < 100:
        raise RuntimeError(f"candidate_b_source_contract_failed:{w}x{h}:{count}@{fps}")
    x0, y0, x1, y1 = 744, 617, 1015, 758
    mask = np.zeros((h, w), np.uint8)
    mask[y0:y1, x0:x1] = 255
    alpha = cv2.GaussianBlur(mask, (0, 0), 10).astype(np.float32)[..., None] / 255.0
    composed = root / "speaking_composed_silent.mp4"
    enc = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
        "-pix_fmt", "bgr24", "-s:v", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
        str(composed),
    ], stdin=subprocess.PIPE)
    frame_count = 0
    while True:
        ok_a, base = original.read()
        ok_b, motion = generated.read()
        if not ok_a or not ok_b:
            if ok_a != ok_b:
                raise RuntimeError("portrait_source_frame_count_mismatch")
            break
        frame = np.clip(motion.astype(np.float32) * (1.0-alpha) + base.astype(np.float32) * alpha, 0, 255).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
        frame_count += 1
    original.release(); generated.release(); enc.stdin.close()
    if enc.wait() != 0 or frame_count != count:
        raise RuntimeError("mouth_protected_speaking_encode_failed")
    # Candidate B remains the sole audio/timing source. Copy its stream packets.
    final_path = root / "nova_portrait_speaking_canary.mp4"
    proc = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(composed),
        "-i", str(source), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
        str(final_path),
    ], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError("candidate_b_audio_mux_failed:" + proc.stderr[-600:])
    torch.cuda.synchronize()
    return {
        "video_bytes": final_path.read_bytes(), "provider": "LivePortrait",
        "model_video_bytes": Path(model_video).read_bytes(),
        "model_revision": CODE_REVISION, "weight_revision": WEIGHT_REVISION,
        "gpu": GPU, "reference_sha256": reference_sha256,
        "source_video": "raw MuseTalk -> locked Candidate B",
        "driver_asset": "LivePortrait official d11.mp4 example; motion input only",
        "animation_region": "all", "driving_multiplier": 0.12,
        "pasteback_interpolation": render_interpolation,
        "mouth_source": "same-frame Candidate B pixels composited into protected mouth ROI",
        "audio_source": "Candidate B video; copied without re-encoding",
        "fps": fps, "frame_count": frame_count, "dimensions": [w,h],
        "model_load_seconds": model_load_seconds, "render_seconds": render_seconds,
        "gpu_active_seconds": time.monotonic()-t0,
        "video_sha256": hashlib.sha256(final_path.read_bytes()).hexdigest(),
    }
