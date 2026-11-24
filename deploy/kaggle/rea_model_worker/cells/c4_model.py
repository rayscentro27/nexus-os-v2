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
