"""Private F5-TTS reference-conditioned inference on the existing Nova Modal app.

No HTTP endpoints are exposed.  The guard below deliberately limits this path
to private, non-commercial testing and prevents production use.
"""
from __future__ import annotations

import modal

APP_NAME = "nexus-creative-gpu-worker"
GPU = "L4"
USAGE_MODE = "PRIVATE_NON_COMMERCIAL_TEST"
PRODUCTION_COMMERCIAL_APPROVED = False
F5_CODE_LICENSE = "MIT"
F5_MODEL_LICENSE = "CC-BY-NC-4.0"
F5_CODE_REVISION = "283252563dbf91be625e0c27926acfaac449186c"
F5_MODEL_REVISION = "84e5a410d9cead4de2f847e7c9369a6440bdfaca"
VOCODER_REVISION = "0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21"
ASR_MODEL_REVISION = "41f01f3fe87f28c78e2fbf8b568835947dd65ed9"
MODEL_ID = "SWivid/F5-TTS"
VOCODER_ID = "charactr/vocos-mel-24khz"
ASR_MODEL_ID = "openai/whisper-large-v3-turbo"
CACHE_MOUNT = "/cache"

app = modal.App(APP_NAME)
# Reuse the existing Nova GPU worker's authenticated Modal account and model
# cache volume; no public service or second Modal app is created.
model_cache = modal.Volume.from_name("nova-chattts-private-model-cache")

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04", add_python="3.11"
    )
    .apt_install("git", "ffmpeg", "libsndfile1")
    .pip_install(
        "torch==2.5.1", "torchaudio==2.5.1",
        index_url="https://download.pytorch.org/whl/cu121",
        extra_index_url="https://pypi.org/simple",
    )
    # Install the pinned upstream inference package without its optional
    # Gradio, training, dataset, and experiment-tracking dependencies.
    .pip_install(
        f"f5-tts @ git+https://github.com/SWivid/F5-TTS.git@{F5_CODE_REVISION}",
        extra_options="--no-deps",
    )
    .pip_install(
        "accelerate>=0.33.0", "cached_path", "datasets==3.2.0", "ema_pytorch>=0.5.2",
        "hydra-core>=1.3.0", "librosa", "numpy==1.26.4", "pydub",
        "pypinyin", "rjieba", "safetensors", "soundfile", "torchdiffeq",
        "tqdm>=4.65.0", "transformers==4.46.3", "tokenizers==0.20.3",
        "transformers_stream_generator",
        "unidecode", "vocos", "x_transformers>=1.31.14", "matplotlib",
        "huggingface_hub==0.26.2", "wandb==0.19.1",
    )
    .env({
        "HF_HOME": f"{CACHE_MOUNT}/huggingface",
        "HF_HUB_CACHE": f"{CACHE_MOUNT}/huggingface/hub",
        "TOKENIZERS_PARALLELISM": "false",
        "MPLBACKEND": "Agg",
    })
)


@app.cls(
    image=image,
    gpu=GPU,
    timeout=1800,
    scaledown_window=300,
    max_containers=1,
    volumes={CACHE_MOUNT: model_cache},
)
class F5TTSWorker:
    @modal.enter()
    def load_model(self) -> None:
        import time
        import torch
        from huggingface_hub import snapshot_download
        from f5_tts.api import F5TTS

        if F5_MODEL_LICENSE != "CC-BY-NC-4.0" or PRODUCTION_COMMERCIAL_APPROVED:
            raise RuntimeError("f5_private_noncommercial_license_guard_failed")
        self.container_started = time.monotonic()
        self.gpu_name = torch.cuda.get_device_name(0)
        started = time.monotonic()
        self.f5_dir = snapshot_download(
            repo_id=MODEL_ID, revision=F5_MODEL_REVISION,
            cache_dir=f"{CACHE_MOUNT}/huggingface/hub",
            allow_patterns=["F5TTS_v1_Base/model_1250000.safetensors",
                            "F5TTS_v1_Base/vocab.txt"],
        )
        self.vocoder_dir = snapshot_download(
            repo_id=VOCODER_ID, revision=VOCODER_REVISION,
            cache_dir=f"{CACHE_MOUNT}/huggingface/hub",
            allow_patterns=["config.yaml", "pytorch_model.bin"],
        )
        self.asr_dir = snapshot_download(
            repo_id=ASR_MODEL_ID, revision=ASR_MODEL_REVISION,
            cache_dir=f"{CACHE_MOUNT}/huggingface/hub",
        )
        self.model = F5TTS(
            model="F5TTS_v1_Base",
            ckpt_file=f"{self.f5_dir}/F5TTS_v1_Base/model_1250000.safetensors",
            vocab_file=f"{self.f5_dir}/F5TTS_v1_Base/vocab.txt",
            vocoder_local_path=self.vocoder_dir,
            device="cuda",
            hf_cache_dir=f"{CACHE_MOUNT}/huggingface",
        )
        self.model_load_seconds = round(time.monotonic() - started, 3)
        model_cache.commit()

    @modal.method()
    def transcribe_reference(
        self,
        audio_bytes: bytes,
        usage_mode: str = USAGE_MODE,
        production_requested: bool = False,
    ) -> dict:
        import hashlib
        import os
        import tempfile

        import torch
        from transformers import pipeline

        if usage_mode != USAGE_MODE or production_requested or PRODUCTION_COMMERCIAL_APPROVED:
            raise PermissionError("f5_private_noncommercial_guard_rejected_request")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            audio_path = f.name
        try:
            if not hasattr(self, "asr"):
                self.asr = pipeline(
                    "automatic-speech-recognition", model=self.asr_dir,
                    torch_dtype=torch.float16, device="cuda",
                )
            text = self.asr(
                audio_path, chunk_length_s=30, batch_size=1,
                generate_kwargs={"task": "transcribe", "language": "english"},
                return_timestamps=False,
            )["text"].strip()
            if not text:
                raise RuntimeError("f5_reference_transcription_empty")
            return {
                "transcript": text,
                "reference_sha256": hashlib.sha256(audio_bytes).hexdigest(),
                "asr_model": f"{ASR_MODEL_ID}@{ASR_MODEL_REVISION}",
                "gpu": self.gpu_name,
                "audio_bytes_received": len(audio_bytes),
            }
        finally:
            os.unlink(audio_path)

    @modal.method()
    def synthesize_reference(
        self,
        reference_audio_bytes: bytes,
        reference_text: str,
        generated_text: str,
        speed: float = 1.0,
        usage_mode: str = USAGE_MODE,
        production_requested: bool = False,
    ) -> dict:
        import hashlib
        import io
        import time
        import uuid

        import numpy as np
        import soundfile as sf
        import torch

        if usage_mode != USAGE_MODE or production_requested or PRODUCTION_COMMERCIAL_APPROVED:
            raise PermissionError("f5_private_noncommercial_guard_rejected_request")
        if not reference_audio_bytes or not reference_text.strip() or not generated_text.strip():
            raise ValueError("ref_audio_ref_text_and_gen_text_are_required")
        if not 0.9 <= speed <= 1.1:
            raise ValueError("speed_out_of_private_canary_range")
        ref_hash = hashlib.sha256(reference_audio_bytes).hexdigest()
        with __import__("tempfile").NamedTemporaryFile(suffix=".wav") as ref_file:
            ref_file.write(reference_audio_bytes)
            ref_file.flush()
            start = time.monotonic()
            wav, sample_rate, _ = self.model.infer(
                ref_file=ref_file.name,
                ref_text=reference_text,
                gen_text=generated_text,
                speed=speed,
                file_wave=None,
            )
            torch.cuda.synchronize()
            latency = time.monotonic() - start
        audio = np.asarray(wav, dtype=np.float32).squeeze()
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise RuntimeError("f5_returned_invalid_audio")
        peak = float(np.max(np.abs(audio)))
        buffer = io.BytesIO()
        sf.write(buffer, audio, int(sample_rate), format="WAV", subtype="PCM_16")
        duration = len(audio) / int(sample_rate)
        return {
            "status": "SUCCESS",
            "audio_wav": buffer.getvalue(),
            "provider": "F5-TTS",
            "model": f"F5TTS_v1_Base@SWivid/F5-TTS@{F5_MODEL_REVISION}",
            "voice": "reference-conditioned (PRIMARY reference)",
            "reference_sha256": ref_hash,
            "reference_text_sha256": hashlib.sha256(reference_text.encode()).hexdigest(),
            "generated_text_sha256": hashlib.sha256(generated_text.encode()).hexdigest(),
            "sample_rate": int(sample_rate),
            "format": "wav/pcm16",
            "duration_seconds": round(duration, 4),
            "latency_seconds": round(latency, 4),
            "rtf": round(latency / duration, 4),
            "speed": speed,
            "gpu": GPU,
            "gpu_name": self.gpu_name,
            "model_load_seconds": self.model_load_seconds,
            "container_active_seconds": round(time.monotonic() - self.container_started, 3),
            "request_id": str(uuid.uuid4()),
            "peak_amplitude": peak,
            "clipping_sample_count": int(np.count_nonzero(np.abs(audio) >= 0.999)),
            "usage_mode": USAGE_MODE,
            "production_commercial_approved": False,
        }

    @modal.method()
    def runtime_metrics(self) -> dict:
        import time

        return {
            "container_active_seconds": round(time.monotonic() - self.container_started, 3),
            "model_load_seconds": self.model_load_seconds,
            "gpu_name": self.gpu_name,
            "gpu_type": GPU,
        }
