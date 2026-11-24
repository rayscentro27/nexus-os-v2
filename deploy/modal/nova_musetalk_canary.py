"""Bounded, one-shot MuseTalk render canary in the existing Creative Modal app.

This is an execution entrypoint, not a scheduler or persistent service. It
accepts exactly one approved reference and one short audio buffer, validates
the image digest, renders a video, and returns the artifact bytes.
"""
from __future__ import annotations

import hashlib
import json
import os
import importlib.metadata
import argparse
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import modal

APP_NAME = "nexus-creative-gpu-worker"
MUSE_TALK_COMMIT = "0a89dec45a0192b824e3cf4daf96c239440c5ed8"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_CACHE_BYTES = 64 * 1024 * 1024
app = modal.App(APP_NAME)

runtime = (
    modal.Image.from_registry(
        "nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04@sha256:f6913f3c02f297877f6859d12ff330043c0be668fdad86868c29a239a5a82151",
        add_python="3.10",
    )
    .apt_install(
        "git=1:2.34.1-1ubuntu1.17",
        "ffmpeg=7:4.4.2-0ubuntu0.22.04.1",
        "libgl1=1.4.0-1",
        "libglib2.0-0=2.72.4-0ubuntu2.10",
    )
    .pip_install(
        "torch==2.0.1",
        "torchvision==0.15.2",
        "torchaudio==2.0.2",
        index_url="https://download.pytorch.org/whl/cu118",
        extra_index_url="https://pypi.org/simple",
    )
    .pip_install(
        "diffusers==0.30.2",
        "accelerate==0.28.0",
        "numpy==1.23.5",
        "opencv-python==4.9.0.80",
        "soundfile==0.12.1",
        "transformers==4.39.2",
        "huggingface_hub==0.30.2",
        "librosa==0.11.0",
        "einops==0.8.1",
        "omegaconf==2.3.0",
        "ffmpeg-python==0.2.0",
        "moviepy==1.0.3",
        "gdown==5.2.0",
        "tqdm==4.67.1",
        "openmim==0.3.9",
    )
    .pip_install("wheel==0.45.1")
    .pip_install("chumpy==0.70", extra_options="--no-build-isolation")
    .run_commands(
        "mim install mmengine==0.10.7",
        "mim install mmcv==2.0.1",
        "mim install mmdet==3.1.0",
        "mim install mmpose==1.1.0",
        f"git clone https://github.com/TMElyralab/MuseTalk.git /opt/MuseTalk && git -C /opt/MuseTalk checkout {MUSE_TALK_COMMIT}",
        "python - <<'PY'\nfrom huggingface_hub import hf_hub_download\nfrom pathlib import Path\nimport shutil\nroot=Path('/opt/MuseTalk/models')\nfiles=[('TMElyralab/MuseTalk','musetalkV15/musetalk.json','musetalkV15/musetalk.json'),('TMElyralab/MuseTalk','musetalkV15/unet.pth','musetalkV15/unet.pth'),('stabilityai/sd-vae-ft-mse','config.json','sd-vae/config.json'),('stabilityai/sd-vae-ft-mse','diffusion_pytorch_model.bin','sd-vae/diffusion_pytorch_model.bin'),('openai/whisper-tiny','config.json','whisper/config.json'),('openai/whisper-tiny','pytorch_model.bin','whisper/pytorch_model.bin'),('openai/whisper-tiny','preprocessor_config.json','whisper/preprocessor_config.json'),('yzd-v/DWPose','dw-ll_ucoco_384.pth','dwpose/dw-ll_ucoco_384.pth'),('ByteDance/LatentSync','latentsync_syncnet.pt','syncnet/latentsync_syncnet.pt')]\nfor repo,name,dest in files:\n p=hf_hub_download(repo_id=repo,filename=name)\n out=root/dest; out.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,out)\n print(repo,name,out)\nPY",
        "mkdir -p /opt/MuseTalk/models/face-parse-bisent && gdown --id 154JgKpzCPW82qINcVieuPH3fZ2e0P812 -O /opt/MuseTalk/models/face-parse-bisent/79999_iter.pth && python -c \"from urllib.request import urlretrieve; urlretrieve('https://download.pytorch.org/models/resnet18-5c106cde.pth','/opt/MuseTalk/models/face-parse-bisent/resnet18-5c106cde.pth')\"",
    )
    .workdir("/opt/MuseTalk")
)


@app.function(
    image=runtime,
    gpu="T4",
    timeout=900,
    scaledown_window=120,
    max_containers=1,
    name="nova_musetalk_render_canary",
)
def render_canary(reference_png: bytes, audio_wav: bytes, expected_sha256: str) -> dict:
    if len(reference_png) > MAX_IMAGE_BYTES or len(audio_wav) > MAX_AUDIO_BYTES:
        raise ValueError("input_size_limit_exceeded")
    image_hash = hashlib.sha256(reference_png).hexdigest()
    if image_hash != expected_sha256:
        raise ValueError("approved_reference_hash_mismatch")
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    root = Path(tempfile.mkdtemp(prefix="nova-musetalk-"))
    image_path = root / "nova_reference.png"
    audio_path = root / "nova_test.wav"
    image_path.write_bytes(reference_png)
    audio_path.write_bytes(audio_wav)
    config_path = root / "input.yaml"
    result_dir = root / "results"
    second_result_dir = root / "results_cached"
    cache_path = root / "nova_identity_cache.pt"
    config_path.write_text(
        "task_0:\n"
        f"  video_path: {json.dumps(str(image_path))}\n"
        f"  audio_path: {json.dumps(str(audio_path))}\n"
        "  result_name: nova_avatar_test.mp4\n"
    )
    script_path = Path("scripts/inference.py")
    upstream = script_path.read_text()
    start_marker = "            # Preprocess input images\n"
    end_marker = "            # Smooth first and last frames\n"
    start = upstream.index(start_marker)
    end = upstream.index(end_marker, start)
    cache_block = '''            # Preprocess input images; reuse only cache for this exact Nova image.
            cache_input = os.environ.get("NOVA_IDENTITY_CACHE_INPUT", "")
            cache_output = os.environ.get("NOVA_IDENTITY_CACHE_OUTPUT", "")
            expected_hash = os.environ.get("NOVA_REFERENCE_SHA256", "")
            if cache_input and os.path.isfile(cache_input):
                identity = torch.load(cache_input, map_location="cpu")
                if identity.get("reference_sha256") != expected_hash:
                    raise ValueError("identity_cache_reference_hash_mismatch")
                coord_list = identity["coord_list"]
                frame_list = identity["frame_list"]
                input_latent_list = identity["input_latent_list"]
                print("Reusing Nova identity cache", expected_hash)
            else:
                if os.path.exists(crop_coord_save_path) and args.use_saved_coord:
                    print("Using saved coordinates")
                    with open(crop_coord_save_path, 'rb') as f:
                        coord_list = pickle.load(f)
                    frame_list = read_imgs(input_img_list)
                else:
                    print("Extracting landmarks... time-consuming operation")
                    coord_list, frame_list = get_landmark_and_bbox(input_img_list, bbox_shift)
                    with open(crop_coord_save_path, 'wb') as f:
                        pickle.dump(coord_list, f)
                input_latent_list = []
                for bbox, frame in zip(coord_list, frame_list):
                    if bbox == coord_placeholder:
                        continue
                    x1, y1, x2, y2 = bbox
                    if args.version == "v15":
                        y2 = min(y2 + args.extra_margin, frame.shape[0])
                    crop_frame = frame[y1:y2, x1:x2]
                    crop_frame = cv2.resize(crop_frame, (256,256), interpolation=cv2.INTER_LANCZOS4)
                    latents = vae.get_latents_for_unet(crop_frame)
                    input_latent_list.append(latents)
                if cache_output:
                    torch.save({"reference_sha256": expected_hash, "musetalk_commit": "''' + MUSE_TALK_COMMIT + '''",
                                "coord_list": coord_list, "frame_list": frame_list,
                                "input_latent_list": [latent.detach().cpu() for latent in input_latent_list]}, cache_output)
'''
    script_path.write_text(upstream[:start] + cache_block + upstream[end:])
    command = [
        "python", "-m", "scripts.inference",
        "--inference_config", str(config_path),
        "--result_dir", str(result_dir),
        "--unet_model_path", "models/musetalkV15/unet.pth",
        "--unet_config", "models/musetalkV15/musetalk.json",
        "--whisper_dir", "models/whisper",
        "--version", "v15", "--gpu_id", "0", "--fps", "25",
        "--batch_size", "4", "--use_float16",
    ]
    first_env = {**os.environ, "NOVA_REFERENCE_SHA256": image_hash,
                 "NOVA_IDENTITY_CACHE_OUTPUT": str(cache_path)}
    proc = subprocess.run(command, cwd="/opt/MuseTalk", env=first_env, capture_output=True, text=True, timeout=780)
    if proc.returncode != 0:
        return {
            "provider": "Modal", "status": "RENDER_FAILED",
            "gpu_type": "T4", "reference_sha256": image_hash,
            "started_at": started_at, "runtime_seconds": round(time.monotonic() - started, 3),
            "error": (proc.stderr or proc.stdout)[-2000:],
        }
    video = result_dir / "v15" / "nova_avatar_test.mp4"
    if not video.is_file():
        raise RuntimeError("musetalk_completed_without_expected_video_artifact")
    if not cache_path.is_file():
        raise RuntimeError("musetalk_did_not_persist_identity_cache")
    cached_command = list(command)
    cached_command[cached_command.index(str(result_dir))] = str(second_result_dir)
    cached_env = {**os.environ, "NOVA_REFERENCE_SHA256": image_hash,
                  "NOVA_IDENTITY_CACHE_INPUT": str(cache_path)}
    reuse_started = time.monotonic()
    reuse_proc = subprocess.run(cached_command, cwd="/opt/MuseTalk", env=cached_env,
                                capture_output=True, text=True, timeout=780)
    if reuse_proc.returncode != 0 or "Reusing Nova identity cache" not in reuse_proc.stdout:
        raise RuntimeError("identity_cache_reuse_failed:" + (reuse_proc.stderr or reuse_proc.stdout)[-1600:])
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, timeout=15, check=True,
    )
    media = json.loads(probe.stdout)
    return {
        "provider": "Modal", "status": "SUCCESS", "app": APP_NAME,
        "function": "nova_musetalk_render_canary", "gpu_type": "T4",
        "reference_sha256": image_hash,
        "video_bytes": video.read_bytes(),
        "identity_cache_bytes": cache_path.read_bytes(),
        "identity_cache_reused": True,
        "cache_reuse_render_seconds": round(time.monotonic() - reuse_started, 3),
        "media_probe": media,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "musetalk_commit": MUSE_TALK_COMMIT,
    }


@app.function(
    image=runtime,
    gpu="T4",
    timeout=900,
    scaledown_window=120,
    max_containers=1,
    name="nova_live_avatar",
)
def render_cached(reference_png: bytes, audio_wav: bytes, identity_cache: bytes,
                  expected_sha256: str, request_id: str) -> dict:
    """Render one short turn using the prevalidated Nova identity cache."""
    if len(reference_png) > MAX_IMAGE_BYTES or len(audio_wav) > MAX_AUDIO_BYTES or len(identity_cache) > MAX_CACHE_BYTES:
        raise ValueError("input_size_limit_exceeded")
    image_hash = hashlib.sha256(reference_png).hexdigest()
    if image_hash != expected_sha256:
        raise ValueError("approved_reference_hash_mismatch")
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    root = Path(tempfile.mkdtemp(prefix="nova-live-avatar-"))
    image_path = root / "nova_reference.png"
    audio_path = root / "nova_turn.wav"
    cache_path = root / "nova_identity_cache.pt"
    image_path.write_bytes(reference_png)
    audio_path.write_bytes(audio_wav)
    cache_path.write_bytes(identity_cache)
    config_path = root / "input.yaml"
    result_dir = root / "results"
    result_dir.mkdir()
    # Keep the filename already proven by the original MuseTalk canary. Each
    # invocation has an isolated result directory, so a stable basename is safe.
    output_name = "nova_avatar_test.mp4"
    config_path.write_text(
        "task_0:\n" + f"  video_path: {json.dumps(str(image_path))}\n"
        + f"  audio_path: {json.dumps(str(audio_path))}\n"
        + f"  result_name: {output_name}\n")
    script_path = Path("scripts/inference.py")
    upstream = script_path.read_text()
    start_marker = "            # Preprocess input images\n"
    end_marker = "            # Smooth first and last frames\n"
    cache_block = '''            # Reuse only the cache for this approved Nova image.
            cache_input = os.environ.get("NOVA_IDENTITY_CACHE_INPUT", "")
            expected_hash = os.environ.get("NOVA_REFERENCE_SHA256", "")
            if not cache_input or not os.path.isfile(cache_input):
                raise ValueError("nova_identity_cache_required")
            identity = torch.load(cache_input, map_location="cpu")
            if identity.get("reference_sha256") != expected_hash:
                raise ValueError("identity_cache_reference_hash_mismatch")
            coord_list = identity["coord_list"]
            frame_list = identity["frame_list"]
            if not frame_list:
                raise ValueError("identity_cache_missing_source_frame")
            # The upstream post-blend loop uses the last `frame` from its
            # preprocessing loop to clamp the face crop to source dimensions.
            frame = frame_list[-1]
            input_latent_list = [latent.to("cuda:0") for latent in identity["input_latent_list"]]
            print("Reusing Nova identity cache", expected_hash)
'''
    if start_marker in upstream:
        start = upstream.index(start_marker)
        end = upstream.index(end_marker, start)
        script_path.write_text(upstream[:start] + cache_block + upstream[end:])
    elif "NOVA_IDENTITY_CACHE_INPUT" not in upstream:
        raise RuntimeError("musetalk_inference_cache_adapter_state_unrecognized")
    command = ["python", "-m", "scripts.inference", "--inference_config", str(config_path),
               "--result_dir", str(result_dir), "--unet_model_path", "models/musetalkV15/unet.pth",
               "--unet_config", "models/musetalkV15/musetalk.json", "--whisper_dir", "models/whisper",
               "--version", "v15", "--gpu_id", "0", "--fps", "25", "--batch_size", "4", "--use_float16"]
    env = {**os.environ, "NOVA_REFERENCE_SHA256": image_hash,
           "NOVA_IDENTITY_CACHE_INPUT": str(cache_path)}
    proc = subprocess.run(command, cwd="/opt/MuseTalk", env=env,
                          capture_output=True, text=True, timeout=780)
    if proc.returncode != 0:
        return {"provider": "Modal", "status": "RENDER_FAILED", "gpu_type": "T4",
                "reference_sha256": image_hash, "request_id": request_id,
                "started_at": started_at, "runtime_seconds": round(time.monotonic() - started, 3),
                "error": (proc.stderr or proc.stdout)[-2000:]}
    videos = sorted(result_dir.rglob("*.mp4"))
    if len(videos) != 1 or not videos[0].is_file():
        raise RuntimeError(f"musetalk_video_artifact_count_invalid:{len(videos)}; "
                           f"stdout={(proc.stdout or '')[-1200:]}; stderr={(proc.stderr or '')[-1200:]}")
    video = videos[0]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                           capture_output=True, text=True, timeout=15, check=True)
    return {"provider": "Modal", "status": "SUCCESS", "app": APP_NAME,
            "function": "nova_live_avatar", "gpu_type": "T4", "request_id": request_id,
            "reference_sha256": image_hash, "identity_cache_reused": "Reusing Nova identity cache" in proc.stdout,
            "video_bytes": video.read_bytes(), "media_probe": json.loads(probe.stdout),
            "started_at": started_at, "completed_at": datetime.now(timezone.utc).isoformat(),
            "runtime_seconds": round(time.monotonic() - started, 3), "musetalk_commit": MUSE_TALK_COMMIT}


@app.function(
    image=runtime,
    cpu=1.0,
    memory=2048,
    timeout=180,
    min_containers=0,
    max_containers=1,
    scaledown_window=30,
    name="nova_musetalk_runtime_inventory",
)
def runtime_inventory() -> dict:
    """Read dependency and model digests from the built runtime; no inference."""
    import hashlib as _hashlib
    from pathlib import Path as _Path

    packages = sorted(
        f"{dist.metadata['Name']}=={dist.version}"
        for dist in importlib.metadata.distributions()
        if dist.metadata.get("Name")
    )
    model_root = _Path("/opt/MuseTalk/models")
    checkpoints = []
    for file_path in sorted(p for p in model_root.rglob("*") if p.is_file()):
        digest = _hashlib.sha256()
        with file_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        checkpoints.append({
            "path": str(file_path.relative_to(model_root)),
            "size_bytes": file_path.stat().st_size,
            "sha256": digest.hexdigest(),
        })
    os_packages = subprocess.run(
        ["dpkg-query", "-W", "-f=${binary:Package}=${Version}\\n"],
        capture_output=True, text=True, check=True, timeout=20,
    ).stdout.splitlines()
    return {
        "provider": "Modal",
        "status": "SUCCESS",
        "musetalk_commit": MUSE_TALK_COMMIT,
        "python_packages": packages,
        "checkpoint_files": checkpoints,
        "checkpoint_count": len(checkpoints),
        "os_packages": sorted(os_packages),
    }


if __name__ == "__main__":
    import base64
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    with modal.enable_output():
        with app.run():
            if args.inventory_only:
                result = runtime_inventory.remote()
            else:
                image_bytes = (repo / "assets/nova/avatar/nova_reference.png").read_bytes()
                audio_bytes = (repo / "artifacts/nova/avatar-canary/nova-test-tts.wav").read_bytes()
                digest = hashlib.sha256(image_bytes).hexdigest()
                result = render_canary.remote(image_bytes, audio_bytes, digest)
    if args.inventory_only:
        inventory_path = repo / "artifacts/nova/avatar-canary/modal-runtime-inventory.json"
        inventory_path.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": result.get("status"),
                          "package_count": len(result.get("python_packages", [])),
                          "checkpoint_count": result.get("checkpoint_count")}, indent=2))
        raise SystemExit(0 if result.get("status") == "SUCCESS" else 1)
    if result.get("status") == "SUCCESS":
        artifact = repo / "artifacts/nova/avatar-canary/nova-avatar-test.mp4"
        artifact.write_bytes(result.pop("video_bytes"))
        result["artifact_path"] = str(artifact)
        result["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        cache_data = result.pop("identity_cache_bytes")
        cache_file = repo / "artifacts/nova/avatar-canary/nova-identity-cache.pt"
        cache_file.write_bytes(cache_data)
        result["identity_cache_path"] = str(cache_file)
        result["identity_cache_sha256"] = hashlib.sha256(cache_data).hexdigest()
        result["identity_cache_key"] = digest
    else:
        result.pop("video_bytes", None)
    result_path = repo / "artifacts/nova/avatar-canary/modal-render-result.json"
    result_path.write_text(json.dumps(result, indent=2, default=lambda value: base64.b64encode(value).decode() if isinstance(value, bytes) else str(value)))
    print(json.dumps({key: value for key, value in result.items() if key != "video_bytes"}, indent=2))
