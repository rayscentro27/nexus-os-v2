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
