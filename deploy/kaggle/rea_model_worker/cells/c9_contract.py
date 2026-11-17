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
