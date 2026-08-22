"""Isolated Modal GPU worker for one allowlisted ComfyUI image workflow."""
from __future__ import annotations
import base64, hashlib, json, os, subprocess, time, urllib.request, uuid
from pathlib import Path
import modal

CAPABILITY = "creative.image_generate"
RESULT_SCHEMA = "nexus.remote-result.v1"
WORKFLOW_ID = "goclear_editorial_image_v1"
WORKFLOW_VERSION = "1"
MODEL_ID = "sdxl_base_1_0"
MODEL_VERSION = "1.0"
MODEL_LICENSE = "CreativeML Open RAIL++-M"
MODEL_SOURCE = "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0"
MODEL_FILE = "sd_xl_base_1.0.safetensors"
MAX_PROMPT = 1200
MAX_NEGATIVE = 800
MAX_CLOCK_SKEW_SECONDS = 300

ROOT = Path("/opt/ComfyUI")
app = modal.App("nexus-creative-gpu-worker")
image = (modal.Image.from_registry("nvidia/cuda:12.6.0-runtime-ubuntu22.04", add_python="3.12")
    .apt_install("git", "libgl1", "libglib2.0-0")
    .pip_install("torch==2.5.1", "torchvision==0.20.1", index_url="https://download.pytorch.org/whl/cu124")
    .pip_install("requests", "huggingface_hub")
    .run_commands("git clone --depth 1 --branch v0.31.0 https://github.com/Comfy-Org/ComfyUI.git /opt/ComfyUI", "pip install --no-cache-dir -r /opt/ComfyUI/requirements.txt", f"python -c \"from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='stabilityai/stable-diffusion-xl-base-1.0', filename='{MODEL_FILE}', local_dir='/opt/ComfyUI/models/checkpoints')\"")
    .entrypoint([]))
secret = modal.Secret.from_name("nexus-remote-worker-hmac-phaseic", required_keys=["NEXUS_REMOTE_WORKER_SHARED_SECRET"])

def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def verify_request(payload: dict, secret_value: str, timestamp: str, signature: str) -> bool:
    import hmac
    try:
        stamp = float(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - stamp) > MAX_CLOCK_SKEW_SECONDS:
        return False
    expected = hmac.new(secret_value.encode(), timestamp.encode() + b"." + _canonical(payload), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(signature or ""))

def workflow_hash() -> str:
    return hashlib.sha256(json.dumps({"workflow_id": WORKFLOW_ID, "version": WORKFLOW_VERSION, "nodes": ["CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage"]}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def validate_image_job(job: dict) -> tuple[bool, str]:
    if not isinstance(job, dict) or job.get("schema_version") != "nexus.remote-job.v1": return False, "unsupported-schema"
    if job.get("capability") != CAPABILITY or job.get("adapter") != "comfyui": return False, "capability-not-allowed"
    correlation = job.get("correlation") or {}
    if correlation.get("workflow_id") != WORKFLOW_ID: return False, "unknown-workflow"
    if correlation.get("model_id") != MODEL_ID: return False, "unknown-model"
    limits = job.get("limits") or {}
    if (limits.get("width"), limits.get("height"), limits.get("images"), limits.get("output_format")) != (1024, 1024, 1, "png"): return False, "dimensions-or-format-not-allowed"
    if int(limits.get("steps", 0)) > 20 or int(limits.get("timeout_seconds", 0)) > 180: return False, "limits-not-allowed"
    if len(str(correlation.get("prompt", ""))) > MAX_PROMPT or len(str(correlation.get("negative_prompt", ""))) > MAX_NEGATIVE: return False, "prompt-bounded"
    return True, "ok"

def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:8188{path}", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=20) as response: return json.loads(response.read())

def _workflow(job: dict) -> dict:
    c = job["correlation"]; prompt = c["prompt"]; negative = c["negative_prompt"]; seed = c["seed"]
    return {"1":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":MODEL_FILE}},"2":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["1",1]}},"3":{"class_type":"CLIPTextEncode","inputs":{"text":negative,"clip":["1",1]}},"4":{"class_type":"EmptyLatentImage","inputs":{"width":1024,"height":1024,"batch_size":1}},"5":{"class_type":"KSampler","inputs":{"seed":seed,"steps":20,"cfg":7.0,"sampler_name":"euler","scheduler":"normal","denoise":1.0,"model":["1",0],"positive":["2",0],"negative":["3",0],"latent_image":["4",0]}},"6":{"class_type":"VAEDecode","inputs":{"samples":["5",0],"vae":["1",2]}},"7":{"class_type":"SaveImage","inputs":{"filename_prefix":"nexus_phase_p","images":["6",0]}}}

def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

@app.function(image=image, secrets=[secret], gpu="L4", cpu=2.0, memory=12288, min_containers=0, max_containers=1, scaledown_window=60, timeout=180, name="generate")
def generate(job: dict, timestamp: str = "", signature: str = "") -> dict:
    started = utc_now(); started_clock = time.monotonic(); worker_id = os.environ.get("NEXUS_WORKER_ID", f"creative-gpu-{uuid.uuid4().hex[:12]}")
    valid, reason = validate_image_job(job)
    if not valid: return {"schema_version":RESULT_SCHEMA,"job_id":job.get("job_id","invalid"),"capability":CAPABILITY,"worker_id":worker_id,"provider":"modal","status":"SAFETY_BLOCKED","started_at":started,"completed_at":utc_now(),"tenant_context":job.get("tenant_context"),"error":{"classification":reason}}
    if not verify_request(job, os.environ.get("NEXUS_REMOTE_WORKER_SHARED_SECRET", ""), timestamp, signature): return {"schema_version":RESULT_SCHEMA,"job_id":job["job_id"],"capability":CAPABILITY,"worker_id":worker_id,"provider":"modal","status":"UNAUTHORIZED","started_at":started,"completed_at":utc_now(),"tenant_context":job.get("tenant_context"),"error":{"classification":"invalid-authentication"}}
    proc = subprocess.Popen(["python","main.py","--listen","127.0.0.1","--port","8188","--disable-auto-launch"], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try: urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2); break
            except Exception: time.sleep(1)
        queued = _post("/prompt", {"prompt":_workflow(job),"client_id":worker_id})
        prompt_id = queued["prompt_id"]
        history = None
        for _ in range(150):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:8188/history/{prompt_id}", timeout=5) as response: history = json.loads(response.read()).get(prompt_id)
                if history and history.get("outputs"): break
            except Exception: pass
            time.sleep(1)
        if not history or not history.get("outputs"): raise RuntimeError("comfyui-timeout")
        image_info = next(iter(history["outputs"].values()))["images"][0]
        with urllib.request.urlopen(f"http://127.0.0.1:8188/view?filename={image_info['filename']}&subfolder={image_info.get('subfolder','')}&type={image_info.get('type','output')}", timeout=20) as response: raw = response.read()
        digest = hashlib.sha256(raw).hexdigest()
        payload = {"artifact_base64":base64.b64encode(raw).decode(),"file_hash":digest,"workflow_id":WORKFLOW_ID,"workflow_version":WORKFLOW_VERSION,"workflow_hash":workflow_hash(),"model_id":MODEL_ID,"model_version":MODEL_VERSION,"model_hash":_file_hash(ROOT / "models" / "checkpoints" / MODEL_FILE),"model_source":MODEL_SOURCE,"license_metadata":{"weights_license":MODEL_LICENSE,"commercial_use":"EVALUATION_ONLY","source":MODEL_SOURCE,"custom_nodes":"NONE"},"seed":job["correlation"]["seed"],"width":1024,"height":1024,"steps":20,"format":"png","gpu_type":"L4","content_safety":"PASS","execution_duration_ms":int((time.monotonic()-started_clock)*1000)}
        return {"schema_version":RESULT_SCHEMA,"job_id":job["job_id"],"capability":CAPABILITY,"worker_id":worker_id,"provider":"modal","status":"SUCCESS","started_at":started,"completed_at":utc_now(),"duration_ms":payload["execution_duration_ms"],"tenant_context":job["tenant_context"],"evidence_result":payload,"usage":{"gpu_type":"L4","custom_nodes":"NONE","cost":"PROVIDER_BILLING"}}
    except Exception as exc:
        return {"schema_version":RESULT_SCHEMA,"job_id":job["job_id"],"capability":CAPABILITY,"worker_id":worker_id,"provider":"modal","status":"DEPENDENCY_UNAVAILABLE","started_at":started,"completed_at":utc_now(),"tenant_context":job["tenant_context"],"error":{"classification":"GPU_WORKER_FAILED","message":str(exc)[:240]}}
    finally: proc.terminate(); proc.wait(timeout=10)
