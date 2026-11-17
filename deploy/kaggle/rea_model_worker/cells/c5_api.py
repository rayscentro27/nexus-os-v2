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
