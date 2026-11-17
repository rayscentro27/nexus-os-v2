# ===================== CELL 1 — CONFIGURATION =====================
# Nexus REA model worker (KAGGLE_HUGGING_FACE_REA_MODEL_WORKER_R1). MODEL COMPUTE ONLY.
# Model choice comes from the approved catalog (model_catalog.json, embedded). Change only this block:
MODEL_MODE = "manual"                 # manual (MODEL_KEY) | auto (deterministic rules over MODEL_PROFILE + JOB_METADATA)
MODEL_KEY = "qwen3-30b-a3b"           # catalog key; default = certified Qwen/Qwen3-30B-A3B
FALLBACK_MODEL_KEY = "qwen3-14b"      # approved fallback when the primary does not fit or fails to load
MODEL_PROFILE = "general_rea"         # general_rea | code_analysis | deep_reasoning | long_context | fast_tool_loop | coding | security_analysis
JOB_METADATA = {"required_context": None, "tool_count": 30}
# Secrets are never written here: they come from Kaggle Add-ons -> Secrets by NAME only.

MAX_CONTEXT = None           # None = selected model operating_context (32768 for qwen3-30b-a3b, measured)
MAX_NEW_TOKENS = 4096
TEMPERATURE = 0.2
TOOL_MODE = "native"         # native | structured_json  (strict JSON protocol fallback)
THINKING = False             # Qwen3 thinking mode off for tool loops (latency)
PORT = 8080                  # authenticated proxy (the only thing a tunnel may expose)
BACKEND_PORT = 8081          # llama-server, loopback only, separate internal key
REQUEST_TIMEOUT_SECONDS = 300
MAX_BODY_BYTES = 3_000_000

TUNNEL = "named"             # quick (ephemeral trycloudflare URL, no account) | named (CLOUDFLARE_TUNNEL_TOKEN) | none
SERVE_MINUTES = 150          # 0 = certify then exit; >0 keeps the endpoint up (bounded) for live REA sessions
RUN_SELF_TEST = True

# Secret NAMES (values live in Kaggle Secrets only)
SECRET_CLIENT_KEY = "NEXUS_REA_MODEL_API_KEY"   # bearer token Contabo will use; if absent an EPHEMERAL key is generated
SECRET_HF_TOKEN = "HF_TOKEN"                    # only needed for gated models
SECRET_TUNNEL_TOKEN = "CLOUDFLARE_TUNNEL_TOKEN" # only for TUNNEL="named"

# Pinned runtime (llama.cpp build proven on this Kaggle account's 2xT4, Sept 2026)
LLAMA_CPP_TAG = "b11002"
LLAMA_CPP_COMMIT = "83078fec0db82d6b5a00d9599062c38c39145755"
CLOUDFLARED_VERSION = "2026.10.7"
CLOUDFLARED_SHA256 = "1f99fb518b83dec2ba8d870a7cc991d82a77e6196295a3d2754ba17ab9f91872"
PIP_PACKAGES = ["fastapi==0.115.12", "uvicorn==0.34.2", "httpx==0.28.1"]

import json, os, time
from pathlib import Path
WORK = Path("/tmp/nexus-rea")                    # scratch (NOT /kaggle/working: that is uploaded as output)
OUT = Path(os.environ.get("NEXUS_REA_OUT", "/kaggle/working"))                    # only the secret-free report + redacted logs go here
WORK.mkdir(parents=True, exist_ok=True)
REPORT = {"schema_version": "nexus.kaggle-rea-model-worker.v1", "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "config": {"MODEL_MODE": MODEL_MODE, "MODEL_KEY": MODEL_KEY, "FALLBACK_MODEL_KEY": FALLBACK_MODEL_KEY, "MODEL_PROFILE": MODEL_PROFILE, "MAX_CONTEXT": MAX_CONTEXT,
                     "MAX_NEW_TOKENS": MAX_NEW_TOKENS, "TEMPERATURE": TEMPERATURE, "TOOL_MODE": TOOL_MODE, "PORT": PORT,
                     "TUNNEL": TUNNEL, "SERVE_MINUTES": SERVE_MINUTES, "LLAMA_CPP_TAG": LLAMA_CPP_TAG}}

def save_report():
    (OUT / "rea_model_worker_report.json").write_text(json.dumps(REPORT, indent=2, sort_keys=True, default=str))

def kv(key, value):
    print(f"{key}={value}", flush=True)
    REPORT.setdefault("fields", {})[key] = value
    save_report()

def get_secret(name):
    """Kaggle secret by name, then environment. Never printed."""
    try:
        from kaggle_secrets import UserSecretsClient
        value = UserSecretsClient().get_secret(name)
        if value:
            return value, "KAGGLE_SECRETS"
    except Exception:
        pass
    value = os.environ.get(name)
    return (value, "ENVIRONMENT") if value else (None, None)

kv("CONFIG_LOADED", "YES")


# ===================== CELL 2 — ENVIRONMENT AUDIT =====================
import platform, shutil, subprocess, sys
kv("KAGGLE_RUNTIME", os.environ.get("KAGGLE_KERNEL_RUN_TYPE", "UNKNOWN"))
kv("PYTHON_VERSION", platform.python_version())
GPUS = []
try:
    q = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=30)
    for line in q.stdout.strip().splitlines():
        name, total, free = [x.strip() for x in line.split(",")]
        GPUS.append({"name": name, "total_mb": int(total), "free_mb": int(free)})
except Exception:
    pass
GPU_TOTAL_MB = sum(g["total_mb"] for g in GPUS)
GPU_FREE_MB = sum(g["free_mb"] for g in GPUS)
kv("GPU_AVAILABLE", "YES" if GPUS else "NO")
kv("GPU_NAME", ",".join(g["name"] for g in GPUS) or "NONE")
kv("GPU_COUNT", len(GPUS))
kv("GPU_MEMORY_TOTAL", f"{GPU_TOTAL_MB} MiB")
kv("CPU_COUNT", os.cpu_count())
try:
    mem = {l.split(":")[0]: int(l.split()[1]) for l in Path("/proc/meminfo").read_text().splitlines()}
    kv("RAM_TOTAL", f"{round(mem['MemTotal'] / 1048576, 1)} GiB")
except OSError:
    kv("RAM_TOTAL", "UNKNOWN")
DISKS = {p: shutil.disk_usage(p).free // (1024 ** 3) for p in ("/tmp", "/kaggle/working") if Path(p).exists()}
kv("DISK_FREE", json.dumps({k: f"{v} GiB" for k, v in DISKS.items()}))
try:
    smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=30).stdout
    kv("CUDA_VERSION", (smi.split("CUDA Version:")[1].split()[0]) if "CUDA Version:" in smi else "UNKNOWN")
except Exception:
    kv("CUDA_VERSION", "UNKNOWN")
try:
    import torch
    kv("TORCH_VERSION", torch.__version__)
except Exception:
    kv("TORCH_VERSION", "NOT_INSTALLED")
BLOCKER = None
if not GPUS:
    BLOCKER = "NO_GPU_AVAILABLE"
    kv("KAGGLE_MODEL_READY", "NO")
    kv("MODEL_BLOCKER", BLOCKER)      # never silently fall back to CPU for a large model
# Secrets preflight (before the ~25 min build): a live serve run needs both secrets visible to THIS version.
# Versions pushed through the Kaggle API do not inherit UI secret attachments; run from the UI with secrets toggled on.
if BLOCKER is None and SERVE_MINUTES > 0 and TUNNEL == "named":
    missing = [n for n in (SECRET_CLIENT_KEY, SECRET_TUNNEL_TOKEN) if not get_secret(n)[0]]
    if missing:
        BLOCKER = "SECRETS_NOT_VISIBLE_TO_THIS_VERSION"
        kv("KAGGLE_MODEL_READY", "NO")
        kv("MODEL_BLOCKER", f"{BLOCKER}: {','.join(missing)} (run from the Kaggle UI with Add-ons -> Secrets enabled)")
    else:
        kv("SECRETS_PREFLIGHT", "PASS (names only)")


# ===================== CELL 3 — DEPENDENCY SETUP =====================
# Minimum inference stack: llama.cpp llama-server (CUDA, GGUF) + fastapi/uvicorn/httpx proxy.
# huggingface_hub is preinstalled in the Kaggle image. No transformers/vLLM/bitsandbytes needed for GGUF.
LLAMA_SERVER = WORK / "llama.cpp" / "build" / "bin" / "llama-server"
if BLOCKER is None:
    t0 = time.time()
    missing = []
    for spec in PIP_PACKAGES:
        mod = spec.split("==")[0]
        try:
            __import__(mod)
        except ImportError:
            missing.append(spec)
    if missing:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)
    import fastapi, uvicorn, httpx, huggingface_hub
    pkgs = {"fastapi": fastapi.__version__, "uvicorn": uvicorn.__version__, "httpx": httpx.__version__,
            "huggingface_hub": huggingface_hub.__version__}
    if not LLAMA_SERVER.exists():
        src = WORK / "llama.cpp"
        subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", LLAMA_CPP_TAG,
                        "https://github.com/ggml-org/llama.cpp.git", str(src)], check=True)
        head = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head != LLAMA_CPP_COMMIT:
            raise RuntimeError(f"LLAMA_CPP_COMMIT_MISMATCH {head}")
        # Flags proven on Kaggle T4 (sm_75); NO_VMM avoids the CUDA VMM failure seen with prebuilt binaries.
        subprocess.run(["cmake", "-S", str(src), "-B", str(src / "build"), "-DCMAKE_BUILD_TYPE=Release", "-DGGML_CUDA=ON",
                        "-DGGML_CUDA_NO_VMM=ON", "-DGGML_NATIVE=OFF", "-DCMAKE_CUDA_ARCHITECTURES=75-real",
                        "-DLLAMA_BUILD_TESTS=OFF", "-DLLAMA_BUILD_EXAMPLES=OFF", "-DLLAMA_BUILD_SERVER=ON", "-DLLAMA_CURL=OFF"],
                       check=True, stdout=subprocess.DEVNULL)
        build = subprocess.run(["cmake", "--build", str(src / "build"), "--target", "llama-server", "-j", str(os.cpu_count() or 4)],
                               capture_output=True, text=True)
        (OUT / "llama_build_tail.log").write_text(build.stdout[-8000:] + build.stderr[-8000:])
        if build.returncode != 0:
            raise RuntimeError("LLAMA_SERVER_BUILD_FAILED")
    pkgs["llama.cpp"] = f"{LLAMA_CPP_TAG} ({LLAMA_CPP_COMMIT[:12]})"
    kv("PACKAGES_INSTALLED", json.dumps(pkgs))
    kv("PACKAGE_INSTALL_STATUS", "PASS")
    kv("DEPENDENCY_SETUP_SECONDS", round(time.time() - t0, 1))


SELECTOR_SOURCE = '"""Deterministic model selection for the Nexus REA Kaggle worker: manual | auto | fallback. Pure functions."""\nfrom __future__ import annotations\n\nLOADABLE = {"CERTIFIED", "APPROVED", "APPROVED_FALLBACK"}\nPROFILES = ("general_rea", "code_analysis", "deep_reasoning", "long_context", "fast_tool_loop", "coding", "security_analysis")\nJSON_RANK = {"high": 3, "medium": 2, "low": 1}\n\nAUTO_RULES_TEXT = {\n    "general_rea": "highest reasoning+code; CERTIFIED preferred; then speed",\n    "fast_tool_loop": "highest speed; then JSON reliability",\n    "code_analysis": "highest code strength",\n    "coding": "highest code strength",\n    "deep_reasoning": "highest reasoning strength that fits",\n    "security_analysis": "highest reasoning+code (authorized defensive analysis)",\n    "long_context": "largest trained context that fits the requested context",\n}\n\n\ndef _rank(profile: str, m: dict) -> tuple:\n    certified = m["STATUS"] == "CERTIFIED"\n    if profile == "fast_tool_loop":\n        return (m["EXPECTED_SPEED"], JSON_RANK[m["JSON_RELIABILITY"]], certified)\n    if profile in ("code_analysis", "coding"):\n        return (m["CODE_STRENGTH"], certified, m["EXPECTED_SPEED"])\n    if profile == "deep_reasoning":\n        return (m["REASONING_STRENGTH"], certified, m["EXPECTED_SPEED"])\n    if profile == "long_context":\n        return (m["CONTEXT_LIMIT"], certified, m["EXPECTED_SPEED"])\n    return (certified, m["REASONING_STRENGTH"] + m["CODE_STRENGTH"], m["EXPECTED_SPEED"])\n\n\ndef fit(model: dict, gpus_free_mb: list[int], requested_context: int | None, cal: dict) -> dict:\n    """Memory/context fit check calibrated on the measured Qwen3-30B-A3B run (est 25498 vs 25550 MiB @32K)."""\n    ctx = int(requested_context or model["operating_context"])\n    weights = model["file_gb"] * 1024 * cal["weights_overhead_factor"]\n    kv = model["kv_bytes_per_token"] * ctx / 1048576\n    compute = max(cal["min_compute_mb"], cal["compute_bytes_per_token"] * ctx / 1048576)\n    need = weights + kv + compute + cal["per_extra_gpu_overhead_mb"] * max(0, len(gpus_free_mb) - 1)\n    free = sum(gpus_free_mb)\n    reasons = []\n    if not gpus_free_mb:\n        reasons.append("NO_GPU")\n    if ctx > model["CONTEXT_LIMIT"]:\n        reasons.append(f"CONTEXT_EXCEEDS_TRAINED:{ctx}>{model[\'CONTEXT_LIMIT\']}")\n    if need > free * cal["headroom_factor"]:\n        reasons.append(f"GPU_MEMORY:{round(need)}MiB>{round(free * cal[\'headroom_factor\'])}MiB")\n    if model["STATUS"] not in LOADABLE:\n        reasons.append("STATUS_NOT_LOADABLE:" + model["STATUS"])\n    return {"model": model["key"], "context": ctx, "estimated_mb": round(need), "estimated_kv_mb": round(kv),\n            "free_mb": free, "headroom_mb": round(free - need), "fits": not reasons, "reasons": reasons}\n\n\ndef _eligible(m: dict, job: dict) -> bool:\n    if job.get("tool_count", 1) and JSON_RANK[m["JSON_RELIABILITY"]] < 2:\n        return False                          # tool loops need acceptable structured-output reliability\n    return True\n\n\ndef select(catalog: dict, *, mode: str, gpus_free_mb: list[int], model_key: str | None = None,\n           fallback_key: str | None = None, profile: str = "general_rea", job: dict | None = None) -> dict:\n    """Return {status, selected, fallback, context, fit, considered}. Never raises for a bad choice."""\n    job = dict(job or {})\n    models = {m["key"]: m for m in catalog["models"]}\n    cal = catalog["calibration"]\n    req_ctx = job.get("required_context")\n    fallback_key = fallback_key or catalog["default_fallback"]\n    considered = []\n\n    def check(key):\n        m = models.get(key)\n        if not m:\n            considered.append({"model": key, "fits": False, "reasons": ["NOT_IN_CATALOG"]})\n            return None\n        f = fit(m, gpus_free_mb, req_ctx, cal)\n        if not _eligible(m, job):\n            f["fits"] = False\n            f["reasons"].append("JSON_RELIABILITY_INSUFFICIENT")\n        considered.append(f)\n        return f if f["fits"] else None\n\n    if mode == "manual":\n        primary = model_key or catalog["default_model"]\n        ok = check(primary)\n        if ok:\n            return {"status": "SELECTED", "selected": primary, "fallback": fallback_key, "context": ok["context"],\n                    "fit": ok, "considered": considered}\n        fb = check(fallback_key) if fallback_key != primary else None\n        if fb:\n            return {"status": "REJECTED_DOES_NOT_FIT_USING_FALLBACK", "selected": fallback_key, "fallback": None,\n                    "context": fb["context"], "fit": fb, "considered": considered}\n        return {"status": "NO_MODEL_FITS", "selected": None, "fallback": None, "context": None, "fit": None, "considered": considered}\n    if mode != "auto":\n        return {"status": "INVALID_MODE", "selected": None, "fallback": None, "context": None, "fit": None, "considered": []}\n    if profile not in PROFILES:\n        profile = "general_rea"\n    candidates = [m for m in catalog["models"] if profile in m["TASK_PROFILES"]] or list(catalog["models"])\n    candidates.sort(key=lambda m: _rank(profile, m), reverse=True)\n    for m in candidates:\n        ok = check(m["key"])\n        if ok:\n            fb = fallback_key if fallback_key != m["key"] else catalog["default_model"]\n            return {"status": "SELECTED", "selected": m["key"], "fallback": fb, "context": ok["context"], "fit": ok,\n                    "profile": profile, "rule": AUTO_RULES_TEXT[profile], "considered": considered}\n    return {"status": "NO_MODEL_FITS", "selected": None, "fallback": None, "context": None, "fit": None,\n            "profile": profile, "considered": considered}\n'
CATALOG_JSON = '{\n  "schema_version": "nexus.rea-model-catalog.v1",\n  "calibration": {\n    "hardware": "Kaggle 2x Tesla T4 (2 x 15360 MiB)",\n    "measured": "Qwen3-30B-A3B Q4_K_M @ ctx 32768: estimate 25498 MiB vs measured 25550 MiB; ctx 65536 OOM (compute buffer ~4.6 GB on device 0, flash-attn off)",\n    "compute_bytes_per_token": 72000,\n    "weights_overhead_factor": 1.03,\n    "per_extra_gpu_overhead_mb": 600,\n    "min_compute_mb": 1400,\n    "headroom_factor": 0.95\n  },\n  "default_model": "qwen3-30b-a3b",\n  "default_fallback": "qwen3-14b",\n  "models": [\n    {"key": "qwen3-30b-a3b", "MODEL_ID": "Qwen/Qwen3-30B-A3B-GGUF", "file": "Qwen3-30B-A3B-Q4_K_M.gguf",\n     "sha256": "0d003f6662faee786ed5da3e31b29c978de5ae5d275c8794c606a7f3c01aa8f5", "MODEL_FAMILY": "qwen",\n     "TASK_PROFILES": ["general_rea", "fast_tool_loop", "code_analysis", "security_analysis", "deep_reasoning", "coding"],\n     "PARAMETER_SIZE": "30.5B", "ACTIVE_PARAMETER_SIZE": "3.3B", "LICENSE": "apache-2.0", "CONTEXT_LIMIT": 40960,\n     "operating_context": 32768, "file_gb": 18.56, "kv_bytes_per_token": 98304, "GPU_MEMORY_REQUIREMENT": "~25.5 GB @32K (measured)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"], "TOOL_CALL_SUPPORT": "native", "JSON_RELIABILITY": "high",\n     "CODE_STRENGTH": 4, "REASONING_STRENGTH": 4, "EXPECTED_SPEED": 5, "STATUS": "CERTIFIED"},\n    {"key": "qwen3-14b", "MODEL_ID": "Qwen/Qwen3-14B-GGUF", "file": "Qwen3-14B-Q4_K_M.gguf",\n     "sha256": "500a8806e85ee9c83f3ae08420295592451379b4f8cf2d0f41c15dffeb6b81f0", "MODEL_FAMILY": "qwen",\n     "TASK_PROFILES": ["general_rea", "code_analysis", "security_analysis", "coding"],\n     "PARAMETER_SIZE": "14.8B", "ACTIVE_PARAMETER_SIZE": null, "LICENSE": "apache-2.0", "CONTEXT_LIMIT": 40960,\n     "operating_context": 32768, "file_gb": 9.0, "kv_bytes_per_token": 163840, "GPU_MEMORY_REQUIREMENT": "~17 GB @32K (estimate)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"], "TOOL_CALL_SUPPORT": "native", "JSON_RELIABILITY": "high",\n     "CODE_STRENGTH": 3, "REASONING_STRENGTH": 3, "EXPECTED_SPEED": 3, "STATUS": "APPROVED_FALLBACK"},\n    {"key": "qwen3-8b", "MODEL_ID": "Qwen/Qwen3-8B-GGUF", "file": "Qwen3-8B-Q4_K_M.gguf",\n     "sha256": "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785", "MODEL_FAMILY": "qwen",\n     "TASK_PROFILES": ["fast_tool_loop", "general_rea"],\n     "PARAMETER_SIZE": "8.2B", "ACTIVE_PARAMETER_SIZE": null, "LICENSE": "apache-2.0", "CONTEXT_LIMIT": 40960,\n     "operating_context": 32768, "file_gb": 5.03, "kv_bytes_per_token": 147456, "GPU_MEMORY_REQUIREMENT": "~12 GB @32K (estimate)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"], "TOOL_CALL_SUPPORT": "native", "JSON_RELIABILITY": "medium",\n     "CODE_STRENGTH": 2, "REASONING_STRENGTH": 2, "EXPECTED_SPEED": 4, "STATUS": "APPROVED"},\n    {"key": "llama-3.1-8b-instruct", "MODEL_ID": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "file": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",\n     "sha256": "7b064f5842bf9532c91456deda288a1b672397a54fa729aa665952863033557c", "MODEL_FAMILY": "llama",\n     "TASK_PROFILES": ["long_context", "fast_tool_loop"],\n     "PARAMETER_SIZE": "8.0B", "ACTIVE_PARAMETER_SIZE": null, "LICENSE": "llama3.1", "CONTEXT_LIMIT": 131072,\n     "operating_context": 65536, "file_gb": 4.92, "kv_bytes_per_token": 131072, "GPU_MEMORY_REQUIREMENT": "~19 GB @64K (estimate)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"], "TOOL_CALL_SUPPORT": "native", "JSON_RELIABILITY": "medium",\n     "CODE_STRENGTH": 2, "REASONING_STRENGTH": 2, "EXPECTED_SPEED": 4, "STATUS": "APPROVED"},\n    {"key": "llama-3.3-70b-instruct", "MODEL_ID": "bartowski/Llama-3.3-70B-Instruct-GGUF", "file": "Llama-3.3-70B-Instruct-Q4_K_M.gguf",\n     "sha256": "32df3baccb556f9840059b2528b2dee4d3d516b24afdfb9d0c56ff5f63e3a664", "MODEL_FAMILY": "llama",\n     "TASK_PROFILES": ["deep_reasoning", "general_rea"],\n     "PARAMETER_SIZE": "70.6B", "ACTIVE_PARAMETER_SIZE": null, "LICENSE": "llama3.3", "CONTEXT_LIMIT": 131072,\n     "operating_context": 32768, "file_gb": 42.52, "kv_bytes_per_token": 327680, "GPU_MEMORY_REQUIREMENT": ">55 GB (does not fit 2xT4)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M"], "TOOL_CALL_SUPPORT": "native", "JSON_RELIABILITY": "high",\n     "CODE_STRENGTH": 4, "REASONING_STRENGTH": 5, "EXPECTED_SPEED": 1, "STATUS": "CATALOG_ONLY_REQUIRES_LARGER_GPU"},\n    {"key": "deepseek-r1-distill-qwen-14b", "MODEL_ID": "bartowski/DeepSeek-R1-Distill-Qwen-14B-GGUF", "file": "DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf",\n     "sha256": "0b319bd0572f2730bfe11cc751defe82045fad5085b4e60591ac2cd2d9633181", "MODEL_FAMILY": "deepseek",\n     "TASK_PROFILES": ["deep_reasoning"],\n     "PARAMETER_SIZE": "14.8B", "ACTIVE_PARAMETER_SIZE": null, "LICENSE": "mit", "CONTEXT_LIMIT": 32768,\n     "operating_context": 32768, "file_gb": 8.99, "kv_bytes_per_token": 196608, "GPU_MEMORY_REQUIREMENT": "~18 GB @32K (estimate)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"], "TOOL_CALL_SUPPORT": "structured_json_only", "JSON_RELIABILITY": "medium",\n     "CODE_STRENGTH": 3, "REASONING_STRENGTH": 4, "EXPECTED_SPEED": 2, "STATUS": "APPROVED"},\n    {"key": "devstral-small-2507", "MODEL_ID": "mistralai/Devstral-Small-2507_gguf", "file": "Devstral-Small-2507-Q4_K_M.gguf",\n     "sha256": "1bcc2b1b7b7ea3168ba2dbe782432c464f2240598bd193930122c41b117c1796", "MODEL_FAMILY": "mistral",\n     "TASK_PROFILES": ["coding", "code_analysis"],\n     "PARAMETER_SIZE": "23.6B", "ACTIVE_PARAMETER_SIZE": null, "LICENSE": "apache-2.0", "CONTEXT_LIMIT": 131072,\n     "operating_context": 32768, "file_gb": 14.33, "kv_bytes_per_token": 163840, "GPU_MEMORY_REQUIREMENT": "~23 GB @32K (estimate)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M", "Q5_K_M", "Q8_0"], "TOOL_CALL_SUPPORT": "native", "JSON_RELIABILITY": "high",\n     "CODE_STRENGTH": 5, "REASONING_STRENGTH": 3, "EXPECTED_SPEED": 2, "STATUS": "APPROVED"},\n    {"key": "mistral-small-3.2-24b-instruct", "MODEL_ID": "bartowski/mistralai_Mistral-Small-3.2-24B-Instruct-2506-GGUF",\n     "file": "mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf",\n     "sha256": "80f5bda68f156f12650ca03a0a2dbfae06a215ac41caa773b8631a479f82415e", "MODEL_FAMILY": "mistral",\n     "TASK_PROFILES": ["general_rea", "security_analysis", "long_context"],\n     "PARAMETER_SIZE": "24.0B", "ACTIVE_PARAMETER_SIZE": null, "LICENSE": "apache-2.0", "CONTEXT_LIMIT": 131072,\n     "operating_context": 32768, "file_gb": 14.33, "kv_bytes_per_token": 163840, "GPU_MEMORY_REQUIREMENT": "~23 GB @32K (estimate)",\n     "QUANTIZATION_OPTIONS": ["Q4_K_M", "Q5_K_M", "Q8_0"], "TOOL_CALL_SUPPORT": "native", "JSON_RELIABILITY": "high",\n     "CODE_STRENGTH": 3, "REASONING_STRENGTH": 3, "EXPECTED_SPEED": 2, "STATUS": "APPROVED"}\n  ]\n}\n'
# ===================== CELL 4 — MODEL SELECTION, FIT CHECK AND LOAD =====================
# Selection is deterministic (model_selector.py) over the approved catalog (model_catalog.json), both embedded.
# Sequence: selected model -> bounded retry (half context on OOM) -> approved fallback -> PAUSED with reason.
# A model failure never crashes the session: the REA step pauses and the Nexus job stays recoverable.
import hashlib, secrets, signal, urllib.request
(WORK / "model_selector.py").write_text(SELECTOR_SOURCE)
(WORK / "model_catalog.json").write_text(CATALOG_JSON)
sys.path.insert(0, str(WORK))
import model_selector as ms
CATALOG = json.loads(CATALOG_JSON)
MODELS = {m["key"]: m for m in CATALOG["models"]}
BACKEND = None
MODEL_PATH = None
BACKEND_KEY_FILE = WORK / ".backend.key"
LLAMA_LOG = WORK / "llama-server.log"
STATE_FILE = WORK / "model_state.json"
STATE = {"status": "STARTING"}


def write_state(**fields):
    STATE.update(fields, updated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(STATE))
    os.replace(tmp, STATE_FILE)
    REPORT["model_state"] = dict(STATE); save_report()


def gpu_free_mb():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


def gpu_used_mb():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


def start_backend(model_path, ctx):
    if not BACKEND_KEY_FILE.exists():       # reuse on restart: the running proxy holds this key
        BACKEND_KEY_FILE.write_text(secrets.token_urlsafe(32)); os.chmod(BACKEND_KEY_FILE, 0o600)
    args = [str(LLAMA_SERVER), "--model", str(model_path), "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
            "--ctx-size", str(ctx), "--parallel", "1", "--n-gpu-layers", "999", "--split-mode", "layer",
            "--jinja", "--no-webui", "--flash-attn", "off", "--api-key-file", str(BACKEND_KEY_FILE)]
    if len(GPUS) > 1:
        args += ["--tensor-split", ",".join("1" for _ in GPUS)]
    proc = subprocess.Popen(args, stdout=open(LLAMA_LOG, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    hdr = {"Authorization": "Bearer " + BACKEND_KEY_FILE.read_text().strip()}
    for _ in range(600):                       # bounded: at most ~20 minutes
        if proc.poll() is not None:
            raise RuntimeError("LLAMA_SERVER_EXITED: " + LLAMA_LOG.read_text()[-1500:])
        try:
            with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{BACKEND_PORT}/health", headers=hdr), timeout=3) as r:
                if r.status == 200:
                    return proc
        except Exception:
            pass
        time.sleep(2)
    proc.kill()
    raise RuntimeError("LLAMA_SERVER_LOAD_TIMEOUT")


def stop_backend():
    global BACKEND
    if BACKEND and BACKEND.poll() is None:
        os.killpg(BACKEND.pid, signal.SIGTERM)
        try:
            BACKEND.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(BACKEND.pid, signal.SIGKILL)
    BACKEND = None


def ensure_model_file(m):
    """Download once into scratch (never /kaggle/working) and verify the catalog sha256."""
    from huggingface_hub import hf_hub_download
    token, _ = get_secret(SECRET_HF_TOKEN)
    if shutil.disk_usage("/tmp").free / 1e9 < m["file_gb"] + 2:
        raise RuntimeError("DISK_TOO_SMALL")
    path = Path(hf_hub_download(m["MODEL_ID"], m["file"], local_dir=str(WORK / "models"), token=token or None))
    del token
    marker = path.with_suffix(".sha256-verified")
    if not marker.exists():
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(64 << 20), b""):
                h.update(block)
        if h.hexdigest() != m["sha256"]:
            path.unlink(missing_ok=True)
            raise RuntimeError("MODEL_HASH_MISMATCH")
        marker.write_text(m["sha256"])
    return path


def load_one(key, ctx):
    """Load one catalog model at ctx; one bounded retry at half context on OOM."""
    global BACKEND, MODEL_PATH
    m = MODELS[key]
    t0 = time.time()
    path = ensure_model_file(m)
    download_s = round(time.time() - t0, 1)
    t0 = time.time()
    try:
        BACKEND = start_backend(path, ctx)
    except RuntimeError as exc:
        if "out of memory" not in str(exc) or ctx <= 8192:
            raise
        ctx //= 2
        BACKEND = start_backend(path, ctx)
    MODEL_PATH = path
    return {"context": ctx, "download_seconds": download_s, "load_seconds": round(time.time() - t0, 1)}


def select_and_load(mode, model_key=None, fallback_key=None, profile="general_rea", job=None, requested_context=None):
    job = dict(job or {})
    if requested_context:
        job["required_context"] = requested_context
    current = STATE.get("model_key")
    write_state(status="SWITCHING", requested={"mode": mode, "model_key": model_key, "profile": profile})
    stop_backend()
    sel = ms.select(CATALOG, mode=mode, gpus_free_mb=gpu_free_mb(), model_key=model_key,
                    fallback_key=fallback_key, profile=profile, job=job)
    order = [k for k in (sel.get("selected"), sel.get("fallback")) if k]
    failures = []
    for key in dict.fromkeys(order):
        f = ms.fit(MODELS[key], gpu_free_mb(), job.get("required_context"), CATALOG["calibration"])
        if not f["fits"]:
            failures.append({"model": key, "stage": "FIT", "reasons": f["reasons"]})
            continue
        try:
            info = load_one(key, f["context"])
        except Exception as exc:
            failures.append({"model": key, "stage": "LOAD", "reason": str(exc)[:300]})
            stop_backend()
            continue
        m = MODELS[key]
        write_state(status="READY", model_key=key, model_id=m["MODEL_ID"], model_file=m["file"],
                    tool_call_support=m["TOOL_CALL_SUPPORT"], selection=sel["status"], fallback_used=key != sel.get("selected"),
                    previous_model=current, failures=failures, fit=f, gpu_memory_used_mb=gpu_used_mb(), **info)
        return dict(STATE)
    write_state(status="PAUSED", reason="NO_APPROVED_MODEL_AVAILABLE", selection=sel["status"], failures=failures,
                considered=sel.get("considered"))
    return dict(STATE)


if BLOCKER is None:
    kv("MODEL_CATALOG_COUNT", len(CATALOG["models"]))
    kv("DEFAULT_MODEL", CATALOG["default_model"])
    kv("DEFAULT_FALLBACK", CATALOG["default_fallback"])
    result = select_and_load(MODEL_MODE, MODEL_KEY, FALLBACK_MODEL_KEY, MODEL_PROFILE, JOB_METADATA, MAX_CONTEXT)
    kv("MODEL_SELECTION_STATUS", result.get("selection"))
    if result["status"] != "READY":
        BLOCKER = "MODEL_STEP_PAUSED"
        kv("MODEL_LOAD", "PAUSED: " + json.dumps(result.get("failures"))[:600])
    else:
        m = MODELS[result["model_key"]]
        MAX_CONTEXT = result["context"]
        kv("SELECTED_MODEL", f"{m['MODEL_ID']}/{m['file']}")
        kv("MODEL_PARAMETER_SIZE", f"{m['PARAMETER_SIZE']}" + (f" ({m['ACTIVE_PARAMETER_SIZE']} active)" if m["ACTIVE_PARAMETER_SIZE"] else ""))
        kv("MODEL_FIT", json.dumps(result["fit"]))
        kv("MODEL_FALLBACK_USED", result["fallback_used"])
        kv("MODEL_LOAD", "PASS")
        kv("MODEL_LOAD_TIME", f"{result['load_seconds']} s")
        kv("MAX_CONTEXT", MAX_CONTEXT)
        kv("QUANTIZATION_MODE", "GGUF_" + m["file"].rsplit("-", 1)[-1].replace(".gguf", ""))
        kv("DEVICE_MAP", f"llama.cpp layer split across {len(GPUS)} GPU(s), all layers offloaded")
        kv("GPU_MEMORY_AFTER_LOAD", f"{gpu_used_mb()} MiB used")


PROXY_SOURCE = '"""Nexus REA model worker proxy (KAGGLE_HUGGING_FACE_REA_MODEL_WORKER_R1).\n\nOpenAI-compatible front for a local llama.cpp `llama-server` (MODEL COMPUTE ONLY: no job state, no\norchestration, no MCP). Adds: bearer auth, /health without secrets, metrics, request size/time bounds,\nOOM classification, SSE for streaming clients (OpenCode), native tool-call validation and a strict JSON\ntool protocol fallback (TOOL_MODE=structured_json) with exactly one correction retry.\n\nAll configuration is environment-driven; secrets are read from files written with mode 0600 and are\nnever logged or echoed.\n"""\nfrom __future__ import annotations\n\nimport asyncio\nimport json\nimport os\nimport re\nimport subprocess\nimport time\nimport uuid\nfrom pathlib import Path\nfrom typing import Any\n\nimport httpx\nfrom fastapi import FastAPI, Request\nfrom fastapi.responses import JSONResponse, StreamingResponse\n\nBACKEND_URL = os.environ.get("REA_BACKEND_URL", "http://127.0.0.1:8081")\nBACKEND_KEY = Path(os.environ["REA_BACKEND_KEY_FILE"]).read_text().strip()\nCLIENT_KEY = Path(os.environ["REA_CLIENT_KEY_FILE"]).read_text().strip()\nMODEL_NAME = os.environ.get("REA_MODEL_NAME", "nexus-rea-model")\nTOOL_MODE = os.environ.get("REA_TOOL_MODE", "native")              # native | structured_json\nMAX_CONTEXT = int(os.environ.get("REA_MAX_CONTEXT", "32768"))\nMAX_NEW_TOKENS = int(os.environ.get("REA_MAX_NEW_TOKENS", "2048"))\nDEFAULT_TEMPERATURE = float(os.environ.get("REA_TEMPERATURE", "0.2"))\nMAX_BODY_BYTES = int(os.environ.get("REA_MAX_BODY_BYTES", "3000000"))\nMAX_MESSAGES = int(os.environ.get("REA_MAX_MESSAGES", "400"))\nREQUEST_TIMEOUT = float(os.environ.get("REA_REQUEST_TIMEOUT_SECONDS", "300"))\nTHINKING = os.environ.get("REA_THINKING", "false").lower() == "true"\nREA_PROMPT = Path(os.environ["REA_SYSTEM_PROMPT_FILE"]).read_text() if os.environ.get("REA_SYSTEM_PROMPT_FILE") else ""\nSELF_TEST = os.environ.get("REA_SELF_TEST", "false").lower() == "true"\nSTATE_FILE = Path(os.environ["REA_STATE_FILE"]) if os.environ.get("REA_STATE_FILE") else None\nREQUEST_FILE = Path(os.environ["REA_MODEL_REQUEST_FILE"]) if os.environ.get("REA_MODEL_REQUEST_FILE") else None\nCATALOG = json.loads(Path(os.environ["REA_CATALOG_FILE"]).read_text()) if os.environ.get("REA_CATALOG_FILE") else None\n\n\ndef _state() -> dict:\n    """Model state written by the notebook (model selection/switching). No state file = a single static model."""\n    if not STATE_FILE:\n        return {"status": "READY", "context": MAX_CONTEXT}\n    try:\n        return json.loads(STATE_FILE.read_text())\n    except (OSError, ValueError):\n        return {"status": "STARTING"}\n\n\ndef _context() -> int:\n    return int(_state().get("context") or MAX_CONTEXT)\n\nMETRICS = {"request_count": 0, "ok_count": 0, "total_seconds": 0.0, "last_response_seconds": None, "last_request_at": None,\n           "oom_count": 0, "model_errors": 0, "timeouts": 0, "rejected_auth": 0, "rejected_size": 0, "rejected_malformed": 0,\n           "tool_call_retries": 0, "structured_retries": 0, "prompt_tokens": 0, "completion_tokens": 0}\n\napp = FastAPI(title="nexus-rea-model-worker", docs_url=None, redoc_url=None, openapi_url=None)\n\n\nclass ApiError(Exception):\n    def __init__(self, status: int, code: str, message: str):\n        super().__init__(message)\n        self.status, self.code, self.message = status, code, message\n\n\ndef _err(status: int, code: str, message: str) -> JSONResponse:\n    return JSONResponse(status_code=status, content={"error": {"type": code, "code": code, "message": message}})\n\n\n@app.exception_handler(ApiError)\nasync def _api_error(_: Request, exc: ApiError):\n    return _err(exc.status, exc.code, exc.message)\n\n\ndef _authorized(request: Request) -> bool:\n    header = request.headers.get("authorization", "")\n    token = header[7:].strip() if header.lower().startswith("bearer ") else ""\n    # constant-time compare\n    return bool(token) and len(token) == len(CLIENT_KEY) and sum(a != b for a, b in zip(token, CLIENT_KEY)) == 0\n\n\ndef _gpu() -> list[dict]:\n    try:\n        out = subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total", "--format=csv,noheader,nounits"],\n                             capture_output=True, text=True, timeout=10).stdout\n    except Exception:\n        return []\n    rows = []\n    for line in out.strip().splitlines():\n        idx, name, used, total = [x.strip() for x in line.split(",")]\n        rows.append({"index": int(idx), "name": name, "memory_used_mb": int(used), "memory_total_mb": int(total)})\n    return rows\n\n\nasync def _backend(path: str, payload: dict | None = None, *, timeout: float = REQUEST_TIMEOUT) -> dict:\n    headers = {"Authorization": f"Bearer {BACKEND_KEY}"}\n    try:\n        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10)) as client:\n            resp = await (client.post(BACKEND_URL + path, json=payload, headers=headers) if payload is not None\n                          else client.get(BACKEND_URL + path, headers=headers))\n    except httpx.TimeoutException as exc:\n        METRICS["timeouts"] += 1\n        raise ApiError(504, "model_timeout", f"model did not answer within {int(timeout)}s") from exc\n    except httpx.HTTPError as exc:\n        METRICS["model_errors"] += 1\n        raise ApiError(503, "model_unavailable", "model backend unreachable") from exc\n    text = resp.text\n    if resp.status_code >= 400:\n        low = text.lower()\n        if "out of memory" in low or "cudamalloc" in low or "failed to allocate" in low:\n            METRICS["oom_count"] += 1\n            raise ApiError(503, "model_out_of_memory", "GPU memory exhausted for this request; reduce context or max_tokens")\n        if "context" in low and ("exceed" in low or "too long" in low or "n_ctx" in low):\n            raise ApiError(413, "context_length_exceeded", f"request exceeds model context ({MAX_CONTEXT} tokens)")\n        METRICS["model_errors"] += 1\n        raise ApiError(502, "model_error", f"backend HTTP {resp.status_code}")\n    try:\n        return resp.json()\n    except ValueError as exc:\n        METRICS["model_errors"] += 1\n        raise ApiError(502, "model_error", "backend returned invalid JSON") from exc\n\n\ndef _estimate_tokens(obj: Any) -> int:\n    return len(json.dumps(obj, ensure_ascii=False)) // 4\n\n\ndef _with_rea_prompt(messages: list[dict]) -> list[dict]:\n    if not REA_PROMPT:\n        return messages\n    msgs = [dict(m) for m in messages]\n    if msgs and msgs[0].get("role") == "system":\n        content = msgs[0].get("content")\n        content = content if isinstance(content, str) else json.dumps(content)\n        msgs[0]["content"] = REA_PROMPT.strip() + "\\n\\n" + content\n    else:\n        msgs.insert(0, {"role": "system", "content": REA_PROMPT.strip()})\n    return msgs\n\n\ndef _tool_names(tools: list[dict] | None) -> set[str]:\n    return {((t or {}).get("function") or {}).get("name") for t in (tools or []) if isinstance(t, dict)} - {None}\n\n\ndef _valid_tool_calls(calls: list[dict], names: set[str]) -> tuple[bool, str]:\n    for call in calls or []:\n        fn = call.get("function") or {}\n        if fn.get("name") not in names:\n            return False, f"unknown tool {fn.get(\'name\')!r}"\n        try:\n            args = json.loads(fn.get("arguments") or "{}")\n        except ValueError:\n            return False, f"arguments for {fn.get(\'name\')} are not valid JSON"\n        if not isinstance(args, dict):\n            return False, f"arguments for {fn.get(\'name\')} must be a JSON object"\n    return True, ""\n\n\n# ---------------------------------------------------------------- structured_json fallback protocol\n\nPROTOCOL = """You must answer with exactly ONE JSON object and nothing else, in one of two forms:\n{"type":"tool_call","tool":"<tool name>","arguments":{...}}\n{"type":"final","content":"<final answer text>"}\nUse "tool_call" only with a tool listed below and arguments matching its JSON schema.\nAvailable tools:\n"""\n\n\ndef _structured_messages(messages: list[dict], tools: list[dict]) -> list[dict]:\n    catalog = [{"name": (t.get("function") or {}).get("name"), "description": ((t.get("function") or {}).get("description") or "")[:400],\n                "parameters": (t.get("function") or {}).get("parameters")} for t in tools]\n    out = [{"role": "system", "content": PROTOCOL + json.dumps(catalog, ensure_ascii=False)}]\n    for m in messages:\n        role = m.get("role")\n        if role == "tool":\n            out.append({"role": "user", "content": f"TOOL_RESULT ({m.get(\'tool_call_id\')}):\\n{m.get(\'content\')}"})\n        elif role == "assistant" and m.get("tool_calls"):\n            fn = (m["tool_calls"][0].get("function") or {})\n            out.append({"role": "assistant", "content": json.dumps({"type": "tool_call", "tool": fn.get("name"),\n                                                                    "arguments": json.loads(fn.get("arguments") or "{}")})})\n        else:\n            content = m.get("content")\n            out.append({"role": role, "content": content if isinstance(content, str) else json.dumps(content)})\n    return out\n\n\ndef parse_structured(text: str, names: set[str]) -> tuple[dict | None, str]:\n    """Validate one protocol object. Returns (object, \'\') or (None, reason)."""\n    text = (text or "").strip()\n    text = re.sub(r"^```(?:json)?\\s*|\\s*```$", "", text)\n    try:\n        obj = json.loads(text)\n    except ValueError:\n        return None, "response is not a single JSON object"\n    if not isinstance(obj, dict) or obj.get("type") not in {"tool_call", "final"}:\n        return None, \'field "type" must be "tool_call" or "final"\'\n    if obj["type"] == "final":\n        return (obj, "") if isinstance(obj.get("content"), str) else (None, \'"final" requires string "content"\')\n    if obj.get("tool") not in names:\n        return None, f"unknown tool {obj.get(\'tool\')!r}"\n    if not isinstance(obj.get("arguments"), dict):\n        return None, \'"arguments" must be a JSON object\'\n    return obj, ""\n\n\n# ---------------------------------------------------------------- endpoints\n\n@app.get("/health")\nasync def health():\n    try:\n        backend = await _backend("/health", timeout=5)\n        status = "ok" if (backend or {}).get("status") in {"ok", None} else "loading"\n    except ApiError as exc:\n        status = "degraded:" + exc.code\n    gpus = _gpu()\n    n = METRICS["ok_count"]\n    st = _state()\n    if st.get("status") != "READY":\n        status = "model_" + str(st.get("status", "unknown")).lower()\n    return {"status": status, "model": MODEL_NAME, "served_model": st.get("model_id"), "served_model_key": st.get("model_key"),\n            "model_state": st.get("status"), "tool_mode": TOOL_MODE, "max_context": _context(),\n            "gpu": [g["name"] for g in gpus], "gpu_memory_used_mb": sum(g["memory_used_mb"] for g in gpus),\n            "gpu_memory_total_mb": sum(g["memory_total_mb"] for g in gpus), "requests_served": METRICS["request_count"],\n            "last_request_at": METRICS["last_request_at"],\n            "metrics": {**{k: v for k, v in METRICS.items() if k not in {"total_seconds"}},\n                        "avg_response_seconds": round(METRICS["total_seconds"] / n, 2) if n else None}}\n\n\n@app.get("/v1/models")\nasync def models(request: Request):\n    if not _authorized(request):\n        METRICS["rejected_auth"] += 1\n        return _err(401, "unauthorized", "missing or invalid bearer token")\n    st = _state()\n    return {"object": "list", "data": [{"id": MODEL_NAME, "object": "model", "owned_by": "nexus", "context_length": _context(),\n                                        "max_output_tokens": MAX_NEW_TOKENS, "tool_mode": TOOL_MODE,\n                                        "served_model": st.get("model_id"), "served_model_key": st.get("model_key")}]}\n\n\ndef _selection_inputs(body: dict) -> dict:\n    mode = str(body.get("mode") or "manual")\n    if mode not in {"manual", "auto"}:\n        raise ApiError(400, "invalid_model_request", "mode must be manual or auto")\n    keys = {m["key"] for m in CATALOG["models"]}\n    for field in ("model_key", "fallback_key"):\n        if body.get(field) is not None and body[field] not in keys:\n            raise ApiError(400, "invalid_model_request", f"{field} not in approved catalog")\n    profile = str(body.get("profile") or "general_rea")\n    import model_selector as ms\n    if profile not in ms.PROFILES:\n        raise ApiError(400, "invalid_model_request", "unknown profile")\n    ctx = body.get("required_context")\n    if ctx is not None and (not isinstance(ctx, int) or not 2048 <= ctx <= 262144):\n        raise ApiError(400, "invalid_model_request", "required_context must be an integer 2048..262144")\n    job = body.get("job") if isinstance(body.get("job"), dict) else {}\n    return {"mode": mode, "model_key": body.get("model_key"), "fallback_key": body.get("fallback_key"), "profile": profile,\n            "job": {k: job[k] for k in ("tool_count", "code_heavy", "binary_analysis", "security_focus",\n                                         "latency_priority", "quality_priority") if k in job}, "required_context": ctx}\n\n\n@app.get("/nexus/v1/model")\nasync def model_state(request: Request):\n    if not _authorized(request):\n        METRICS["rejected_auth"] += 1\n        return _err(401, "unauthorized", "missing or invalid bearer token")\n    st = _state()\n    return {"state": {k: st.get(k) for k in ("status", "model_key", "model_id", "context", "selection", "fallback_used",\n                                             "reason", "updated_at", "tool_call_support")},\n            "catalog": [{k: m[k] for k in ("key", "MODEL_ID", "MODEL_FAMILY", "TASK_PROFILES", "STATUS", "CONTEXT_LIMIT")}\n                        for m in (CATALOG or {}).get("models", [])]}\n\n\n@app.post("/nexus/v1/model")\nasync def request_model(request: Request):\n    """Per-assignment model selection. dry_run returns the deterministic decision without loading anything."""\n    if not _authorized(request):\n        METRICS["rejected_auth"] += 1\n        return _err(401, "unauthorized", "missing or invalid bearer token")\n    if not CATALOG or not REQUEST_FILE:\n        return _err(501, "model_switching_unavailable", "worker started without a model catalog")\n    try:\n        body = json.loads(await request.body() or b"{}")\n        assert isinstance(body, dict)\n    except (ValueError, AssertionError):\n        return _err(400, "invalid_model_request", "body must be a JSON object")\n    sel_in = _selection_inputs(body)\n    import model_selector as ms\n    # Decide as if the current model were unloaded: per-GPU total minus measured idle usage.\n    totals = [g["memory_total_mb"] - 450 for g in _gpu()]\n    if SELF_TEST and os.environ.get("REA_TEST_GPU_TOTALS"):\n        totals = [int(x) for x in os.environ["REA_TEST_GPU_TOTALS"].split(",")]\n    job = dict(sel_in["job"]); job["required_context"] = sel_in["required_context"]\n    decision = ms.select(CATALOG, mode=sel_in["mode"], gpus_free_mb=totals, model_key=sel_in["model_key"],\n                         fallback_key=sel_in["fallback_key"], profile=sel_in["profile"], job=job)\n    out = {"decision": {k: decision.get(k) for k in ("status", "selected", "fallback", "context", "profile", "rule")},\n           "considered": decision.get("considered")}\n    st = _state()\n    if body.get("dry_run"):\n        return {"dry_run": True, **out}\n    if decision["status"] == "NO_MODEL_FITS":\n        return JSONResponse(status_code=409, content={"accepted": False, **out})\n    if st.get("status") == "SWITCHING" or REQUEST_FILE.exists():\n        return _err(409, "model_switch_in_progress", "a model switch is already in progress")\n    if decision["selected"] == st.get("model_key") and decision["context"] == st.get("context") and st.get("status") == "READY":\n        return {"accepted": True, "already_loaded": True, **out}\n    tmp = REQUEST_FILE.with_suffix(".tmp")\n    tmp.write_text(json.dumps({**sel_in, "requested_at": time.time()}))\n    os.replace(tmp, REQUEST_FILE)\n    return JSONResponse(status_code=202, content={"accepted": True, "already_loaded": False, **out})\n\n\n@app.post("/v1/chat/completions")\nasync def chat(request: Request):\n    if not _authorized(request):\n        METRICS["rejected_auth"] += 1\n        return _err(401, "unauthorized", "missing or invalid bearer token")\n    raw = await request.body()\n    if len(raw) > MAX_BODY_BYTES:\n        METRICS["rejected_size"] += 1\n        return _err(413, "request_too_large", f"request body exceeds {MAX_BODY_BYTES} bytes")\n    try:\n        req = json.loads(raw)\n        messages = req["messages"]\n        assert isinstance(messages, list) and messages and all(isinstance(m, dict) and m.get("role") for m in messages)\n    except (ValueError, KeyError, AssertionError, TypeError):\n        METRICS["rejected_malformed"] += 1\n        return _err(400, "invalid_request", "body must be JSON with a non-empty messages array of {role, content}")\n    if len(messages) > MAX_MESSAGES:\n        METRICS["rejected_size"] += 1\n        return _err(413, "request_too_large", f"more than {MAX_MESSAGES} messages")\n    st = _state()\n    if st.get("status") != "READY":\n        return _err(503, "model_" + str(st.get("status", "unavailable")).lower(),\n                    "model step not ready: " + str(st.get("reason") or st.get("status")))\n    ctx_limit = _context()\n    est = _estimate_tokens(messages) + _estimate_tokens(req.get("tools") or [])\n    max_tokens = min(int(req.get("max_tokens") or req.get("max_completion_tokens") or MAX_NEW_TOKENS), MAX_NEW_TOKENS)\n    if est + max_tokens > ctx_limit:\n        METRICS["rejected_size"] += 1\n        return _err(413, "context_length_exceeded", f"estimated {est} prompt tokens + {max_tokens} output exceeds {ctx_limit}")\n    timeout = REQUEST_TIMEOUT\n    if SELF_TEST and request.headers.get("x-nexus-test-timeout"):\n        timeout = float(request.headers["x-nexus-test-timeout"])  # self-test only: exercises the timeout path\n    started = time.monotonic()\n    METRICS["request_count"] += 1\n    METRICS["last_request_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())\n    tools = req.get("tools") or []\n    names = _tool_names(tools)\n    mode = req.get("x_tool_mode") or TOOL_MODE\n    base = {"model": MODEL_NAME, "temperature": req.get("temperature", DEFAULT_TEMPERATURE), "max_tokens": max_tokens,\n            "stream": False, "chat_template_kwargs": {"enable_thinking": THINKING}}\n    if req.get("response_format"):\n        base["response_format"] = req["response_format"]\n    for key in ("top_p", "stop", "seed"):\n        if key in req:\n            base[key] = req[key]\n    try:\n        message, finish, usage = await asyncio.wait_for(_complete(base, messages, tools, names, req, mode, timeout), timeout + 15)\n    except asyncio.TimeoutError:\n        METRICS["timeouts"] += 1\n        return _err(504, "model_timeout", f"model did not answer within {int(timeout)}s")\n    elapsed = time.monotonic() - started\n    METRICS["ok_count"] += 1\n    METRICS["total_seconds"] += elapsed\n    METRICS["last_response_seconds"] = round(elapsed, 2)\n    METRICS["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)\n    METRICS["completion_tokens"] += int(usage.get("completion_tokens") or 0)\n    body = {"id": "chatcmpl-" + uuid.uuid4().hex[:24], "object": "chat.completion", "created": int(time.time()), "model": MODEL_NAME,\n            "choices": [{"index": 0, "message": message, "finish_reason": finish}], "usage": usage,\n            "nexus": {"elapsed_seconds": round(elapsed, 2), "tool_mode": mode, "estimated_prompt_tokens": est}}\n    if req.get("stream"):\n        return StreamingResponse(_sse(body), media_type="text/event-stream")\n    return body\n\n\nasync def _complete(base: dict, messages: list[dict], tools: list[dict], names: set[str], req: dict, mode: str, timeout: float):\n    if mode == "structured_json" and tools:\n        msgs = _structured_messages(_with_rea_prompt(messages), tools)\n        payload = {**base, "messages": msgs, "response_format": {"type": "json_object"}}\n        for attempt in range(2):\n            out = await _backend("/v1/chat/completions", payload, timeout=timeout)\n            text = ((out.get("choices") or [{}])[0].get("message") or {}).get("content") or ""\n            obj, why = parse_structured(text, names)\n            if obj:\n                usage = out.get("usage") or {}\n                if obj["type"] == "final":\n                    return {"role": "assistant", "content": obj["content"]}, "stop", usage\n                call = {"id": "call_" + uuid.uuid4().hex[:24], "type": "function",\n                        "function": {"name": obj["tool"], "arguments": json.dumps(obj["arguments"])}}\n                return {"role": "assistant", "content": None, "tool_calls": [call]}, "tool_calls", usage\n            if attempt == 0:\n                METRICS["structured_retries"] += 1\n                payload = {**payload, "messages": msgs + [{"role": "assistant", "content": text[:2000]},\n                                                          {"role": "user", "content": f"INVALID RESPONSE: {why}. Reply again with exactly one valid JSON object in the required form."}]}\n        METRICS["model_errors"] += 1\n        raise ApiError(502, "structured_output_invalid", f"model did not produce a valid protocol object after one retry ({why})")\n    payload = {**base, "messages": _with_rea_prompt(messages)}\n    if tools:\n        payload["tools"] = tools\n        if req.get("tool_choice") is not None:\n            payload["tool_choice"] = req["tool_choice"]\n    for attempt in range(2):\n        out = await _backend("/v1/chat/completions", payload, timeout=timeout)\n        choice = (out.get("choices") or [{}])[0]\n        message = dict(choice.get("message") or {})\n        message.pop("reasoning_content", None)\n        calls = message.get("tool_calls") or []\n        ok, why = _valid_tool_calls(calls, names) if calls else (True, "")\n        if ok:\n            message.setdefault("role", "assistant")\n            return message, ("tool_calls" if calls else choice.get("finish_reason") or "stop"), out.get("usage") or {}\n        if attempt == 0:\n            METRICS["tool_call_retries"] += 1\n            payload = {**payload, "messages": payload["messages"] + [\n                {"role": "user", "content": f"Your previous tool call was invalid: {why}. Call one listed tool with JSON object arguments."}]}\n    METRICS["model_errors"] += 1\n    raise ApiError(502, "tool_call_invalid", f"model produced an invalid tool call after one retry ({why})")\n\n\nasync def _sse(body: dict):\n    choice = body["choices"][0]\n    msg = choice["message"]\n    head = {k: body[k] for k in ("id", "object", "created", "model")}\n    head["object"] = "chat.completion.chunk"\n\n    def chunk(delta: dict, finish=None, usage=None):\n        data = {**head, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}\n        if usage is not None:\n            data["usage"] = usage\n        return "data: " + json.dumps(data) + "\\n\\n"\n\n    yield chunk({"role": "assistant"})\n    if msg.get("content"):\n        yield chunk({"content": msg["content"]})\n    for i, call in enumerate(msg.get("tool_calls") or []):\n        yield chunk({"tool_calls": [{"index": i, "id": call.get("id"), "type": "function",\n                                     "function": {"name": call["function"]["name"], "arguments": ""}}]})\n        yield chunk({"tool_calls": [{"index": i, "function": {"arguments": call["function"].get("arguments") or "{}"}}]})\n    yield chunk({}, choice["finish_reason"], body.get("usage") or {})\n    yield "data: [DONE]\\n\\n"\n'
REA_SYSTEM_PROMPT = 'You are the reasoning engine for a bounded software-analysis and development harness (Nexus REA).\n\nYou do not execute tools yourself. The harness executes the tool you choose and returns its result.\n\nEach request gives you some or all of: OBJECTIVE, current evidence, available tool schemas, prior tool\nresults, unresolved questions and constraints. The request is self-contained: do not assume memory of\nearlier requests beyond the messages you are given.\n\nAt every step decide exactly one of:\n1. another tool is required -> choose ONE tool, with arguments that satisfy its schema exactly; or\n2. the evidence is sufficient -> produce the final structured findings.\n\nRules:\n- Use evidence, not guesses. Every finding must point to a tool result you actually received.\n- Never claim a tool result you have not received. Never invent file contents, paths, APIs, endpoints\n  or tool names. Use only tools present in the provided schemas.\n- Distinguish OBSERVED behavior (seen in a tool result) from INFERENCE (your reasoning about it).\n- Preserve clean-room boundaries: describe behavior, interfaces and data flow in your own words. Do not\n  copy proprietary source code, decompiled bodies or long verbatim strings into findings.\n- Do not repeat a tool call with the same arguments unless the previous call failed for a transient reason.\n  If two consecutive steps add no new evidence, stop and report the limitation.\n- Prefer passive/static inspection before dynamic execution, and summaries before complete dumps.\n- Stop as soon as the objective is satisfied.\n- Never ask for, reveal or store secrets, tokens or credentials.\n'
# ===================== CELL 5 — API SERVER (authenticated OpenAI-compatible proxy) =====================
PROXY = None
CLIENT_KEY_FILE = WORK / ".client.key"
MODEL_ALIAS = "nexus-rea-model"          # stable alias: Contabo config never changes when the served model changes
MODEL_REQUEST_FILE = WORK / "model_request.json"
PROXY_LOG = WORK / "proxy.log"
(WORK / "rea_model_proxy.py").write_text(PROXY_SOURCE)               # embedded at build time
(WORK / "REA_MODEL_SYSTEM_PROMPT.md").write_text(REA_SYSTEM_PROMPT)  # embedded at build time

def start_proxy():
    env = {**os.environ, "REA_BACKEND_URL": f"http://127.0.0.1:{BACKEND_PORT}", "REA_BACKEND_KEY_FILE": str(BACKEND_KEY_FILE),
           "REA_CLIENT_KEY_FILE": str(CLIENT_KEY_FILE), "REA_MODEL_NAME": MODEL_ALIAS,
           "REA_STATE_FILE": str(STATE_FILE), "REA_MODEL_REQUEST_FILE": str(MODEL_REQUEST_FILE),
           "REA_CATALOG_FILE": str(WORK / "model_catalog.json"),
           "REA_TOOL_MODE": TOOL_MODE, "REA_MAX_CONTEXT": str(MAX_CONTEXT), "REA_MAX_NEW_TOKENS": str(MAX_NEW_TOKENS),
           "REA_TEMPERATURE": str(TEMPERATURE), "REA_MAX_BODY_BYTES": str(MAX_BODY_BYTES),
           "REA_REQUEST_TIMEOUT_SECONDS": str(REQUEST_TIMEOUT_SECONDS), "REA_THINKING": str(THINKING).lower(),
           "REA_SYSTEM_PROMPT_FILE": str(WORK / "REA_MODEL_SYSTEM_PROMPT.md"), "REA_SELF_TEST": str(RUN_SELF_TEST).lower(),
           "PYTHONPATH": str(WORK)}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "rea_model_proxy:app", "--host", "127.0.0.1", "--port", str(PORT),
                             "--log-level", "warning", "--no-access-log"], cwd=str(WORK), env=env,
                            stdout=open(PROXY_LOG, "w"), stderr=subprocess.STDOUT, start_new_session=True)
    import urllib.request
    for _ in range(60):
        if proc.poll() is not None:
            raise RuntimeError("PROXY_EXITED: " + PROXY_LOG.read_text()[-1500:])
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as r:
                if r.status == 200:
                    return proc
        except Exception:
            time.sleep(1)
    raise RuntimeError("PROXY_START_TIMEOUT")

if BLOCKER is None:
    client_key, source = get_secret(SECRET_CLIENT_KEY)
    if client_key:
        key_mode = "KAGGLE_SECRET:" + SECRET_CLIENT_KEY
    else:
        client_key, key_mode = secrets.token_urlsafe(32), "EPHEMERAL_RUN_KEY (self-test only; Contabo cannot use it)"
    CLIENT_KEY_FILE.write_text(client_key); os.chmod(CLIENT_KEY_FILE, 0o600)
    CLIENT_KEY = client_key
    del client_key
    PROXY = start_proxy()
    MODEL_NAME = MODEL_ALIAS
    kv("API_SERVER", f"PASS (uvicorn proxy 127.0.0.1:{PORT} -> llama-server 127.0.0.1:{BACKEND_PORT})")
    kv("API_AUTH", "BEARER_TOKEN_REQUIRED (/v1/*); /health unauthenticated, no secrets")
    kv("SECRET_STORAGE", key_mode)
    kv("MODEL_NAME", MODEL_NAME)


# ===================== CELL 6 — TEMPORARY ENDPOINT (tunnel) =====================
import re, socket, urllib.request, urllib3.util.connection as _uc
_uc.allowed_gai_family = lambda: socket.AF_INET   # no IPv6 route on Kaggle
TUNNEL_PROC = None
PUBLIC_BASE = None
NAMED_TUNNEL_HOSTNAME = "https://kaggle-model.goclearonline.cc"   # existing route -> 127.0.0.1:8080 (named mode only)
if BLOCKER is None and TUNNEL != "none":
    cf = WORK / "cloudflared"
    if not cf.exists():
        subprocess.run(["wget", "-q", "-O", str(cf),
                        f"https://github.com/cloudflare/cloudflared/releases/download/{CLOUDFLARED_VERSION}/cloudflared-linux-amd64"], check=True)
        if hashlib.sha256(cf.read_bytes()).hexdigest() != CLOUDFLARED_SHA256:
            raise RuntimeError("CLOUDFLARED_HASH_MISMATCH")
        os.chmod(cf, 0o755)
    tlog = WORK / "cloudflared.log"
    if TUNNEL == "named":
        token, _ = get_secret(SECRET_TUNNEL_TOKEN)
        if not token:
            raise RuntimeError(f"{SECRET_TUNNEL_TOKEN} secret not attached")
        tf = WORK / ".tunnel.token"; tf.write_text(token); os.chmod(tf, 0o600); del token
        TUNNEL_PROC = subprocess.Popen([str(cf), "tunnel", "--no-autoupdate", "run", "--token-file", str(tf)],
                                       stdout=open(tlog, "w"), stderr=subprocess.STDOUT, start_new_session=True)
        PUBLIC_BASE = NAMED_TUNNEL_HOSTNAME
    else:
        TUNNEL_PROC = subprocess.Popen([str(cf), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{PORT}"],
                                       stdout=open(tlog, "w"), stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(60):
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", tlog.read_text())
            if m:
                PUBLIC_BASE = m.group(0)
                break
            time.sleep(1)
    reachable = False
    for _ in range(45):                       # DNS/edge propagation, bounded
        try:
            with urllib.request.urlopen(PUBLIC_BASE + "/health", timeout=10) as r:
                reachable = r.status == 200
        except Exception:
            pass
        if reachable:
            break
        time.sleep(2)
    kv("MODEL_ENDPOINT", (PUBLIC_BASE or "NONE") + "/v1")
    kv("ENDPOINT_TYPE", "EPHEMERAL")
    kv("ENDPOINT_PERSISTENCE", "NO")
    kv("PUBLIC_EXPOSURE", f"{'cloudflare quick tunnel' if TUNNEL == 'quick' else 'cloudflare named tunnel'} -> authenticated proxy only; "
       f"llama-server stays on loopback; reachable={'YES' if reachable else 'NO'}")


# ===================== CELL 7 — HEALTH + OPENAI COMPATIBILITY TESTS =====================
import requests, socket, urllib3.util.connection as _uc
_uc.allowed_gai_family = lambda: socket.AF_INET      # Kaggle kernels have no IPv6 route (run 3: Errno 101 on an AAAA record)
LOCAL = f"http://127.0.0.1:{PORT}"

def retry(fn, attempts=3, wait=5):
    """Bounded retry for transient network errors only; HTTP status codes are returned, never retried."""
    for i in range(attempts):
        try:
            return fn()
        except requests.ConnectionError:
            if i == attempts - 1:
                raise
            time.sleep(wait)
AUTH = {"Authorization": "Bearer " + CLIENT_KEY} if BLOCKER is None else {}
TESTS = {}

def chat(messages, base=LOCAL, **extra):
    hdrs = {**AUTH, **extra.pop("headers", {})}
    body = {"model": MODEL_NAME, "messages": messages, "temperature": 0, **extra}
    return retry(lambda: requests.post(base + "/v1/chat/completions", headers=hdrs, json=body, timeout=400))

def record(name, ok, detail=""):
    TESTS[name] = {"pass": bool(ok), "detail": str(detail)[:300]}
    print(f"TEST {name} = {'PASS' if ok else 'FAIL'} {str(detail)[:160]}", flush=True)
    REPORT["tests"] = TESTS; save_report()

if BLOCKER is None:
    for label, base in (("local", LOCAL), ("public", PUBLIC_BASE)):
        if not base:
            continue
        h = retry(lambda: requests.get(base + "/health", timeout=30))
        body = h.text
        record(f"{label}_health", h.status_code == 200 and h.json()["status"] == "ok" and CLIENT_KEY not in body, h.json().get("status"))
        r0 = retry(lambda: requests.get(base + "/v1/models", timeout=30))
        r1 = retry(lambda: requests.get(base + "/v1/models", headers=AUTH, timeout=30))
        record(f"{label}_models_auth", r0.status_code == 401 and r1.status_code == 200 and r1.json()["data"][0]["id"] == MODEL_NAME,
               f"without_key={r0.status_code} with_key={r1.status_code}")
    t = time.time(); r = chat([{"role": "user", "content": "Reply with exactly: NEXUS_REA_OK"}], base=PUBLIC_BASE or LOCAL, max_tokens=32)
    c = r.json()["choices"][0]["message"].get("content") or "" if r.status_code == 200 else r.text
    shape = r.status_code == 200 and r.json().get("object") == "chat.completion" and r.json()["choices"][0]["finish_reason"] == "stop"
    record("simple_chat", shape and "NEXUS_REA_OK" in c, f"{round(time.time()-t,1)}s {c!r}")
    r = chat([{"role": "user", "content": "Remember the code 4817. Reply only OK."}, {"role": "assistant", "content": "OK"},
              {"role": "user", "content": "What code did I ask you to remember? Reply with the number only."}], max_tokens=16)
    c = (r.json()["choices"][0]["message"].get("content") or "") if r.status_code == 200 else r.text
    record("multiturn", "4817" in c, repr(c))
    r = chat([{"role": "user", "content": 'Return a JSON object with keys "status" (string "ok") and "count" (number 3).'}],
             response_format={"type": "json_object"}, max_tokens=64)
    try:
        obj = json.loads(r.json()["choices"][0]["message"]["content"]); ok = obj.get("status") == "ok" and obj.get("count") == 3
    except Exception as e:
        obj, ok = str(e), False
    record("json_mode", ok, obj)
    TOOL = [{"type": "function", "function": {"name": "get_system_status", "description": "Return the status of a named system.",
             "parameters": {"type": "object", "properties": {"system_name": {"type": "string"}}, "required": ["system_name"]}}}]
    for mode in ("native", "structured_json"):
        r = chat([{"role": "user", "content": "Check the status of Nexus."}], tools=TOOL, tool_choice="auto", max_tokens=256, x_tool_mode=mode)
        try:
            call = r.json()["choices"][0]["message"]["tool_calls"][0]["function"]
            ok = call["name"] == "get_system_status" and json.loads(call["arguments"]).get("system_name", "").lower() == "nexus"
        except Exception as e:
            call, ok = r.text[:200], False
        record(f"tool_call_{mode}", ok, call)
    r = requests.post(LOCAL + "/v1/chat/completions", headers=AUTH, stream=True, timeout=400,
                      json={"model": MODEL_NAME, "stream": True, "temperature": 0, "tools": TOOL, "max_tokens": 256,
                            "messages": [{"role": "user", "content": "Check the status of Nexus."}]})
    lines = [l for l in r.iter_lines(decode_unicode=True) if l]
    record("streaming_sse", lines[-1] == "data: [DONE]" and any("tool_calls" in l for l in lines), f"{len(lines)} events")
    kv("OPENAI_CHAT_COMPAT", "PASS" if TESTS["simple_chat"]["pass"] and TESTS["streaming_sse"]["pass"] else "FAIL")
    kv("MULTITURN", "PASS" if TESTS["multiturn"]["pass"] else "FAIL")
    kv("JSON_MODE", "PASS" if TESTS["json_mode"]["pass"] else "FAIL")
    kv("TOOL_CALL_TEST", "PASS" if TESTS["tool_call_native"]["pass"] else "FAIL")
    kv("NATIVE_TOOL_CALLING", "YES" if TESTS["tool_call_native"]["pass"] else "NO")
    kv("STRUCTURED_FALLBACK", "PASS" if TESTS["tool_call_structured_json"]["pass"] else "FAIL")
    kv("TOOL_CALL_MODE", f"{TOOL_MODE} (structured_json available per request via x_tool_mode or TOOL_MODE)")
    kv("HEALTH_ENDPOINT", "PASS" if TESTS.get("public_health", TESTS.get("local_health"))["pass"] else "FAIL")
    # Model selection (validation only; no second large model is downloaded)
    MU = LOCAL + "/nexus/v1/model"
    r = retry(lambda: requests.post(MU, headers=AUTH, timeout=30, json={"mode": "manual", "model_key": "llama-3.3-70b-instruct", "dry_run": True}))
    d = r.json().get("decision", {})
    record("manual_selection_rejects_oversize_uses_fallback", d.get("status") == "REJECTED_DOES_NOT_FIT_USING_FALLBACK" and d.get("selected") == "qwen3-14b", d)
    r = retry(lambda: requests.post(MU, headers=AUTH, timeout=30, json={"mode": "manual", "model_key": "not-approved"}))
    record("manual_selection_rejects_unapproved", r.status_code == 400, r.status_code)
    r = retry(lambda: requests.post(MU, headers=AUTH, timeout=30, json={"mode": "auto", "profile": "code_analysis", "dry_run": True}))
    record("auto_selection_code_analysis", r.json().get("decision", {}).get("selected") == "devstral-small-2507", r.json().get("decision"))
    r = retry(lambda: requests.post(MU, headers=AUTH, timeout=30, json={"mode": "manual", "model_key": STATE.get("model_key")}))
    record("manual_selection_current_model_already_loaded", r.status_code == 200 and r.json().get("already_loaded") is True, r.text[:200])
    kv("MANUAL_MODEL_SELECTION", "PASS" if TESTS["manual_selection_rejects_oversize_uses_fallback"]["pass"] and TESTS["manual_selection_rejects_unapproved"]["pass"] and TESTS["manual_selection_current_model_already_loaded"]["pass"] else "FAIL")
    kv("AUTO_MODEL_SELECTION", "PASS" if TESTS["auto_selection_code_analysis"]["pass"] else "FAIL")


# ===================== CELL 8 — REA REASONING SIMULATION + FAILURE TESTS =====================
# Model-only simulation: mock tools executed here (NOT the live REA MCP).
MOCK_REPO = {
    "README.md": "Demo web app. Login flow: POST /login. Sessions are cookie based.",
    "src/routes/login.ts": ("import { verifyPassword } from '../auth/password';\nimport { createSession } from '../auth/session';\n"
                            "router.post('/login', async (req, res) => {\n  const user = await users.findByEmail(req.body.email);\n"
                            "  if (!user || !(await verifyPassword(req.body.password, user.hash))) return res.status(401).end();\n"
                            "  const token = createSession(user.id);\n  res.cookie('sid', token, { httpOnly: true });\n  res.json({ ok: true });\n});"),
    "src/auth/session.ts": ("export function createSession(userId) { const token = randomBytes(32).toString('hex');\n"
                            "  store.set(token, { userId, exp: Date.now() + 3600e3 }); return token; }\n"
                            "export function requireSession(req, res, next) { const s = store.get(req.cookies.sid);\n"
                            "  if (!s || s.exp < Date.now()) return res.status(401).end(); req.userId = s.userId; next(); }"),
    "src/auth/password.ts": "export async function verifyPassword(plain, hash) { return argon2.verify(hash, plain); }",
    "src/middleware/auth.ts": "import { requireSession } from '../auth/session';\nexport default requireSession;",
}
MOCK_ROUTES = [{"method": "POST", "path": "/login", "handler": "src/routes/login.ts"},
               {"method": "GET", "path": "/me", "handler": "src/routes/me.ts", "middleware": "src/middleware/auth.ts"}]
SIM_TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read one repository file by exact path.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "search_repo", "description": "Search repository file contents for a literal string.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "inspect_api", "description": "List HTTP routes, optionally filtered by path prefix.",
     "parameters": {"type": "object", "properties": {"prefix": {"type": "string"}}, "required": []}}},
]

def run_mock(name, args):
    if name == "read_file":
        return MOCK_REPO.get(args.get("path"), "ERROR: FILE_NOT_FOUND")
    if name == "search_repo":
        q = str(args.get("query") or "")
        hits = [f"{p}: {line.strip()}" for p, text in MOCK_REPO.items() for line in text.splitlines() if q and q.lower() in line.lower()]
        return "\n".join(hits[:20]) or "NO_MATCHES"
    if name == "inspect_api":
        return json.dumps([r for r in MOCK_ROUTES if r["path"].startswith(args.get("prefix") or "")])
    return "ERROR: UNKNOWN_TOOL"

def rea_simulation(mode, max_steps=8):
    names = {t["function"]["name"]: t["function"]["parameters"].get("required", []) for t in SIM_TOOLS}
    msgs = [{"role": "system", "content": "REA harness session. Return final findings as a short JSON object with keys "
                                          "NEXT_FILE, REASON, OBSERVED, INFERRED once evidence is sufficient."},
            {"role": "user", "content": "OBJECTIVE: Determine which file should be inspected next to understand the authentication workflow.\n"
                                        "EVIDENCE: route listing shows POST /login is handled by src/routes/login.ts.\n"
                                        "UNRESOLVED: how is the logged-in state created and checked?"}]
    steps, calls, observed_text, final = [], [], "", None
    for _ in range(max_steps):
        r = chat(msgs, tools=SIM_TOOLS, tool_choice="auto", max_tokens=1024, x_tool_mode=mode)
        if r.status_code != 200:
            steps.append({"error": r.status_code, "body": r.text[:200]}); break
        msg = r.json()["choices"][0]["message"]
        tcs = msg.get("tool_calls") or []
        if not tcs:
            final = msg.get("content") or ""; break
        tc = tcs[0]; fn = tc["function"]; args = json.loads(fn["arguments"] or "{}")
        valid = fn["name"] in names and all(k in args for k in names.get(fn["name"], []))
        result = run_mock(fn["name"], args)
        observed_text += "\n" + result
        calls.append((fn["name"], json.dumps(args, sort_keys=True)))
        steps.append({"tool": fn["name"], "args": args, "valid": valid, "result_chars": len(result)})
        msgs += [{"role": "assistant", "content": None, "tool_calls": [tc]},
                 {"role": "tool", "tool_call_id": tc.get("id") or "call", "content": result}]
    auth_files = {"src/auth/session.ts", "src/auth/password.ts", "src/middleware/auth.ts"}
    named = {p for p in MOCK_REPO if final and p in final}
    module = lambda p: p.removeprefix("src/").rsplit(".", 1)[0]          # "auth/session" (as imported in login.ts)
    seen = lambda p: p in observed_text or module(p) in observed_text
    checks = {
        "chose_a_tool": len(calls) >= 1,
        "all_tool_calls_valid": all(s.get("valid") for s in steps if "tool" in s) and not any("error" in s for s in steps),
        "used_tool_results": bool(final) and bool(named) and all(seen(p) for p in named),
        "final_names_auth_file_from_evidence": any(seen(p) for p in named & auth_files),
        "no_repeated_identical_call": len(calls) == len(set(calls)),
        "terminated_within_bound": final is not None,
    }
    return {"mode": mode, "pass": all(checks.values()), "checks": checks, "steps": steps, "final": (final or "")[:800]}

FAILURES = {}
if BLOCKER is None:
    SIM = {m: rea_simulation(m) for m in ("native", "structured_json")}
    for m, res in SIM.items():
        print("REA_SIM", m, "PASS" if res["pass"] else "FAIL", json.dumps(res["checks"]), flush=True)
    REPORT["rea_simulation"] = SIM; save_report()
    kv("REA_REASONING_LOOP_SIMULATION", "PASS" if SIM[TOOL_MODE]["pass"] else "FAIL")
    kv("REA_REASONING_LOOP_SIMULATION_OTHER_MODE",
       {m: ("PASS" if r["pass"] else "FAIL") for m, r in SIM.items() if m != TOOL_MODE})

    # --- failure handling (bounded, clear errors) ---
    r = requests.post(LOCAL + "/v1/chat/completions", headers={**AUTH, "content-type": "application/json"}, data=b"{broken", timeout=30)
    FAILURES["malformed_request"] = r.status_code == 400
    r = requests.post(LOCAL + "/v1/chat/completions", headers=AUTH, timeout=60,
                      json={"messages": [{"role": "user", "content": "x" * (MAX_BODY_BYTES + 10)}]})
    FAILURES["oversized_request"] = r.status_code == 413
    r = chat([{"role": "user", "content": "word " * MAX_CONTEXT}], max_tokens=64)
    FAILURES["context_exceeded"] = r.status_code == 413
    t = time.time()
    r = chat([{"role": "user", "content": "Write a 3000 word essay about compilers."}], max_tokens=MAX_NEW_TOKENS,
             headers={"x-nexus-test-timeout": "2"})
    FAILURES["model_timeout"] = r.status_code == 504 and time.time() - t < 60
    sys.path.insert(0, str(WORK)); os.environ.setdefault("REA_BACKEND_KEY_FILE", str(BACKEND_KEY_FILE))
    os.environ.setdefault("REA_CLIENT_KEY_FILE", str(CLIENT_KEY_FILE))
    import rea_model_proxy as _p
    bad = ["sure!", '{"type":"tool_call","tool":"rm_rf","arguments":{}}', '{"type":"final"}', '[1,2]']
    FAILURES["malformed_structured_json_rejected"] = all(_p.parse_structured(b, {"read_file"})[0] is None for b in bad)
    FAILURES["gpu_oom"] = "NOT_SAFELY_SIMULATABLE_ON_SHARED_GPU: OOM classification -> HTTP 503 model_out_of_memory is contract-tested offline"
    # endpoint restart: stop backend -> fast 503 + degraded health -> restart -> healthy
    os.killpg(BACKEND.pid, signal.SIGTERM); BACKEND.wait(timeout=60)
    t = time.time(); r = chat([{"role": "user", "content": "hi"}], max_tokens=8)
    down_ok = r.status_code == 503 and time.time() - t < 20
    degraded = requests.get(LOCAL + "/health", timeout=20).json()["status"].startswith("degraded")
    t = time.time(); BACKEND = start_backend(MODEL_PATH, MAX_CONTEXT)
    r = chat([{"role": "user", "content": "Reply with exactly: BACK"}], max_tokens=8)
    FAILURES["endpoint_restart"] = down_ok and degraded and r.status_code == 200
    FAILURES["endpoint_restart_seconds"] = round(time.time() - t, 1)
    REPORT["failure_tests"] = FAILURES; save_report()
    ok = all(v for k, v in FAILURES.items() if isinstance(v, bool))
    kv("FAILURE_HANDLING", ("PASS " if ok else "FAIL ") + json.dumps(FAILURES))


# ===================== CELL 9 — CONNECTION CONTRACT FOR CONTABO + SERVE WINDOW =====================
if BLOCKER is None:
    h = requests.get(LOCAL + "/health", timeout=30).json()
    m = h["metrics"]
    kv("REQUEST_COUNT", m["request_count"])
    kv("AVG_RESPONSE_SECONDS", m["avg_response_seconds"])
    kv("LAST_RESPONSE_SECONDS", m["last_response_seconds"])
    kv("OOM_COUNT", m["oom_count"])
    kv("MODEL_ERRORS", m["model_errors"])
    contract = {"PROVIDER_NAME": "nexus_rea_model", "BASE_URL": (PUBLIC_BASE or LOCAL) + "/v1  (EPHEMERAL: changes every run)",
                "MODEL_NAME": MODEL_NAME, "SERVED_MODEL": STATE.get("model_id"), "API_KEY_REQUIRED": "YES", "OPENAI_COMPATIBLE": "YES (chat.completions, SSE streaming, tools)",
                "TOOL_MODE": TOOL_MODE, "CONTEXT_LENGTH": MAX_CONTEXT, "MAX_OUTPUT_TOKENS": MAX_NEW_TOKENS,
                "CONTABO_MODEL_PROVIDER_JSON": {"status": "READY", "base_url": "<BASE_URL>", "model_name": MODEL_NAME,
                    "context_length": MAX_CONTEXT, "output_limit": MAX_NEW_TOKENS, "tool_calling": True, "json_mode": True,
                    "cost_class": "FREE", "api_key_ref": "/rea/config/secrets/nexus_rea_model.key (value = Kaggle secret NEXUS_REA_MODEL_API_KEY)"}}
    REPORT["connection_contract"] = contract
    print(json.dumps(contract, indent=2))
    kv("NOTEBOOK_RESTARTABLE", "YES (every cell is idempotent; scratch in /tmp; no authoritative state on Kaggle)")
    kv("MODEL_SWITCHABLE", "YES (edit MODEL_* in Cell 1)")
    kv("PAID_EXTERNAL_SERVICES_USED", "NO")
    kv("SERVE_WINDOW_MINUTES", SERVE_MINUTES)
    end = time.time() + SERVE_MINUTES * 60
    last_snapshot = 0
    switches = REPORT.setdefault("model_switches", [])
    while time.time() < end:                    # bounded serve window; never indefinite
        if MODEL_REQUEST_FILE.exists():         # per-assignment model selection (queued by the proxy)
            try:
                req = json.loads(MODEL_REQUEST_FILE.read_text())
            except ValueError:
                req = None
            if req:
                result = select_and_load(req["mode"], req.get("model_key"), req.get("fallback_key"), req.get("profile") or "general_rea",
                                         req.get("job"), req.get("required_context"))
                switches.append({"request": req, "status": result["status"], "model_key": result.get("model_key"),
                                 "fallback_used": result.get("fallback_used"), "failures": result.get("failures")})
                save_report()
            MODEL_REQUEST_FILE.unlink(missing_ok=True)
        if time.time() - last_snapshot > 60:
            try:
                REPORT["serve_health"] = requests.get(LOCAL + "/health", timeout=20).json(); save_report()
            except Exception:
                pass
            last_snapshot = time.time()
        time.sleep(5)
# Shutdown: stop tunnel, proxy, model; remove key files. Nothing secret is left in /kaggle/working.
for proc in (globals().get("TUNNEL_PROC"), globals().get("PROXY"), globals().get("BACKEND")):
    try:
        if proc and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        pass
for f in WORK.glob(".*"):
    f.unlink(missing_ok=True)
for name in ("llama-server.log", "proxy.log", "cloudflared.log"):
    p = WORK / name
    if p.exists():
        text = p.read_text(errors="replace")[-20000:]
        text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}", r"\1[REDACTED]", text)
        (OUT / name).write_text(text)
kv("KAGGLE_HUGGING_FACE_REA_MODEL_WORKER_R1", "BLOCKED:" + BLOCKER if BLOCKER else
   ("PASS" if all(t["pass"] for t in TESTS.values()) and REPORT["fields"].get("REA_REASONING_LOOP_SIMULATION") == "PASS"
    and str(REPORT["fields"].get("FAILURE_HANDLING", "")).startswith("PASS") else "FAIL"))
REPORT["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); save_report()
