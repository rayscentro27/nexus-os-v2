"""Private, bounded ChatTTS GPU inference in the existing Nova Modal app.

No web endpoints are defined. All inference is invoked through authenticated
Modal function calls, and the provider guard prevents commercial/production
use. MuseTalk is not imported or rebuilt here.
"""
from __future__ import annotations

import modal

APP_NAME = "nexus-creative-gpu-worker"
GPU = "T4"
CHAT_TTS_CODE_REVISION = "77b89ee281cd479f5b1a787ada330dc975ca1f2a"
CHAT_TTS_MODEL_REVISION = "1a3c04a8b0651689bd9242fbb55b1f4b5a9aef84"
MODEL_NAME = "2Noise/ChatTTS"
MODEL_LICENSE = "CC-BY-NC-4.0"
CACHE_MOUNT = "/cache"
app = modal.App(APP_NAME)
model_cache = modal.Volume.from_name("nova-chattts-private-model-cache", create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install("git", "libsndfile1")
    .pip_install(
        "torch==2.5.1",
        "torchaudio==2.5.1",
        index_url="https://download.pytorch.org/whl/cu121",
        extra_index_url="https://pypi.org/simple",
    )
    .pip_install(
        "numpy==1.26.4",
        "numba==0.60.0",
        "transformers==4.46.3",
        "vocos==0.1.0",
        "vector-quantize-pytorch==1.18.5",
        "pybase16384==0.3.7",
        "huggingface_hub==0.26.2",
        "safetensors==0.4.5",
        "soundfile==0.12.1",
        "tqdm==4.67.1",
        f"git+https://github.com/2noise/ChatTTS.git@{CHAT_TTS_CODE_REVISION}",
    )
    .env({"HF_HOME": f"{CACHE_MOUNT}/huggingface", "TOKENIZERS_PARALLELISM": "false"})
)


@app.cls(
    image=image,
    gpu=GPU,
    timeout=1200,
    scaledown_window=600,
    max_containers=1,
    volumes={CACHE_MOUNT: model_cache},
)
class ChatTTSGPU:
    @modal.enter()
    def load_model(self) -> None:
        import os
        import time
        from huggingface_hub import snapshot_download
        import ChatTTS

        if MODEL_LICENSE != "CC-BY-NC-4.0":
            raise RuntimeError("chattts_noncommercial_license_guard_failed")
        started = time.monotonic()
        self.container_started_monotonic = started
        cache_dir = f"{CACHE_MOUNT}/huggingface/hub"
        snapshot_download(
            repo_id=MODEL_NAME,
            revision=CHAT_TTS_MODEL_REVISION,
            cache_dir=cache_dir,
            allow_patterns=["*.yaml", "*.json", "*.safetensors"],
        )
        self.chat = ChatTTS.Chat()
        self.chat_api = ChatTTS.Chat
        # ChatTTS's default whitelist drops apostrophes even when its text
        # normalization and homophone features are disabled. Preserve the
        # literal prompt punctuation for this adapter's exact-script canaries.
        import re
        self.chat.normalizer.reject_pattern = re.compile(r"[^\u4e00-\u9fffA-Za-z'，。、,\. ]")
        if not self.chat.load(
            source="huggingface",
            custom_path=cache_dir,
            compile=False,
            device="cuda",
        ):
            raise RuntimeError("chattts_model_load_failed")
        model_cache.commit()
        self.model_load_seconds = round(time.monotonic() - started, 3)
        self.model = f"{MODEL_NAME}@{CHAT_TTS_MODEL_REVISION}"
        self.device = "cuda"
        if not os.path.isdir(cache_dir):
            raise RuntimeError("chattts_model_cache_missing")

    @modal.method()
    def runtime_metrics(self) -> dict:
        import time

        return {
            "container_active_seconds": round(time.monotonic() - self.container_started_monotonic, 3),
            "model_load_seconds": self.model_load_seconds,
            "gpu_type": GPU,
            "gpu_name": __import__("torch").cuda.get_device_name(0),
        }

    @modal.method()
    def synthesize(self, text: str, speaker_seed: int, style: str = "default",
                   usage_mode: str = "PRIVATE_NON_COMMERCIAL_TEST",
                   production_requested: bool = False) -> dict:
        import io
        import random
        import time
        import uuid

        import numpy as np
        import soundfile as sf
        import torch

        if usage_mode != "PRIVATE_NON_COMMERCIAL_TEST" or production_requested:
            raise PermissionError("chattts_private_noncommercial_guard_rejected_request")
        if style not in {"default", "restrained_pause"}:
            raise ValueError("unsupported_chattts_style")
        if not text or len(text) > 1000:
            raise ValueError("text_missing_or_over_limit")
        if not isinstance(speaker_seed, int) or speaker_seed < 0 or speaker_seed > 2**31 - 1:
            raise ValueError("speaker_seed_out_of_range")
        torch.manual_seed(speaker_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(speaker_seed)
            torch.cuda.synchronize()
        np.random.seed(speaker_seed % (2**32 - 1))
        random.seed(speaker_seed)
        speaker = self.chat.sample_random_speaker()
        infer_params = self.chat_api.InferCodeParams(
            spk_emb=speaker,
            manual_seed=speaker_seed,
            temperature=0.3,
            top_P=0.7,
            top_K=20,
            show_tqdm=False,
        )
        kwargs = {"text": [text], "skip_refine_text": True, "lang": "en",
                  "params_infer_code": infer_params,
                  "do_text_normalization": False, "do_homophone_replacement": False}
        if style == "restrained_pause":
            kwargs["params_refine_text"] = self.chat_api.RefineTextParams(
                prompt="[oral_2][laugh_0][break_2]",
                manual_seed=speaker_seed,
                show_tqdm=False,
            )
            kwargs["skip_refine_text"] = False
        started = time.monotonic()
        wavs = self.chat.infer(**kwargs)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        synthesis_seconds = round(time.monotonic() - started, 3)
        if not wavs or wavs[0] is None:
            raise RuntimeError("chattts_returned_no_audio")
        audio = np.asarray(wavs[0], dtype=np.float32).squeeze()
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise RuntimeError("chattts_audio_array_invalid")
        buffer = io.BytesIO()
        sample_rate = 24000
        sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
        audio_bytes = buffer.getvalue()
        duration = float(audio.size / sample_rate)
        return {
            "status": "SUCCESS",
            "audio_wav": audio_bytes,
            "audio_format": "wav",
            "sample_rate": sample_rate,
            "duration_seconds": round(duration, 4),
            "synthesis_seconds": synthesis_seconds,
            "rtf": round(synthesis_seconds / duration, 4),
            "request_id": str(uuid.uuid4()),
            "provider": "ChatTTS",
            "usage_mode": "PRIVATE_NON_COMMERCIAL_TEST",
            "production_commercial_approved": False,
            "model": self.model,
            "model_license": MODEL_LICENSE,
            "model_load_seconds": self.model_load_seconds,
            "gpu_type": GPU,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO_CUDA",
            "cuda_available": bool(torch.cuda.is_available()),
            "speaker_seed": speaker_seed,
            "style": style,
        }
