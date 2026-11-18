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
