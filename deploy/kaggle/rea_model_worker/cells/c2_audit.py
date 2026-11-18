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
