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
