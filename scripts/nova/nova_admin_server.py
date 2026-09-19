"""Loopback-only bounded Admin transport for canonical Hermes Nova.

The Admin server owns HTTP validation and the browser contract. Hermes Agent
0.20.6 owns Nova execution, sessions, tool routing, and model orchestration.
The former local graph is intentionally disabled; it is not a rollback runtime.
"""
from __future__ import annotations
import argparse, json, os, re, ssl, threading, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from nexus_agent_platform.bridge.oracle_hermes_cli import run_oracle_hermes

ALLOWED_ORIGIN = "https://goclearonline.cc"
MAX_BODY_BYTES = 32 * 1024
MAX_MESSAGE_CHARS = 4000
MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 14000
ADMIN_CHAT_ID = 0  # Browser memory is deliberately separate from Telegram.
SENSITIVE_CLIENT_INPUT = re.compile(r"(?:\b\d{3}-\d{2}-\d{4}\b|\b(?:ssn|social security|bank account|routing number|date of birth|credit report)\b|\b[^\s@]+@[^\s@]+\.[^\s@]+\b)", re.I)
BEARER_RE = re.compile(r"^Bearer\s+\S+$", re.I)

def _runtime_env():
    values = {}
    path = os.path.expanduser(os.environ.get("NEXUS_RUNTIME_ENV_PATH", "~/.config/nexus/runtime.env"))
    try:
        with open(path, encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip().removeprefix("export ")] = value.strip().strip("'\"")
    except OSError:
        pass
    return values

def _env_value(*names):
    runtime = _runtime_env()
    for name in names:
        value = os.environ.get(name) or runtime.get(name)
        if value:
            return value
    return ""

def _require_admin(headers):
    authorization = headers.get("Authorization", "")
    if not BEARER_RE.fullmatch(authorization):
        return False
    base = _env_value("SUPABASE_URL", "VITE_SUPABASE_URL").rstrip("/")
    anon = _env_value("SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY")
    if not base or not anon:
        return False
    request_headers = {"apikey": anon, "authorization": authorization}
    def get(path):
        try:
            request = urllib.request.Request(f"{base}{path}", headers=request_headers)
            with urllib.request.urlopen(request, timeout=8) as response:
                return response.getcode(), json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            return 0, None
    user_status, user = get("/auth/v1/user")
    if user_status != 200 or not isinstance(user, dict) or not user.get("id"):
        return False
    user_id = urllib.parse.quote(str(user["id"]), safe="")
    admin_status, admins = get(f"/rest/v1/admin_users?id=eq.{user_id}&active=neq.false&select=role&limit=1")
    role = admins[0].get("role") if admin_status == 200 and isinstance(admins, list) and admins else None
    if not role:
        membership_status, memberships = get(f"/rest/v1/tenant_memberships?user_id=eq.{user_id}&role=in.(super_admin,admin,operator)&select=role&limit=1")
        role = memberships[0].get("role") if membership_status == 200 and isinstance(memberships, list) and memberships else None
    return bool(role)

def _supabase_request(method, path, payload=None):
    base = _env_value("SUPABASE_URL", "VITE_SUPABASE_URL").rstrip("/")
    service_key = _env_value("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not service_key:
        return 0, None
    headers = {"apikey": service_key, "authorization": f"Bearer {service_key}", "content-type": "application/json"}
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    try:
        request = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=10, context=context) as response:
            raw = response.read().decode("utf-8")
            return response.getcode(), json.loads(raw) if raw else None
    except (OSError, ValueError, urllib.error.URLError):
        return 0, None

def _remote_command_worker():
    """Consume new Admin user messages and return replies through existing tables."""
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    while True:
        try:
            status, rows = _supabase_request("GET", f"/rest/v1/admin_ai_messages?role=eq.user&created_at=gte.{urllib.parse.quote(started_at, safe='')}&select=id,conversation_id,user_id,content,created_at&order=created_at.asc&limit=20")
            pending = None
            for row in rows if status == 200 and isinstance(rows, list) else []:
                conversation_id = urllib.parse.quote(str(row.get("conversation_id", "")), safe="")
                c_status, conversations = _supabase_request("GET", f"/rest/v1/admin_ai_conversations?id=eq.{conversation_id}&agent=eq.nova&select=id&limit=1")
                if c_status != 200 or not conversations:
                    continue
                a_status, assistants = _supabase_request("GET", f"/rest/v1/admin_ai_messages?conversation_id=eq.{conversation_id}&role=eq.assistant&created_at=gt.{urllib.parse.quote(str(row.get('created_at')), safe='')}&select=id&limit=1")
                if a_status == 200 and not assistants:
                    pending = row
                    break
            if not pending:
                time.sleep(2)
                continue
            try:
                result = invoke_nova(str(pending.get("content", "")), str(pending.get("conversation_id", "")), [])
                completed = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                _supabase_request("POST", "/rest/v1/admin_ai_messages", {"conversation_id": pending.get("conversation_id"), "user_id": pending.get("user_id"), "role": "assistant", "content": result.get("text", "")})
                _supabase_request("PATCH", f"/rest/v1/admin_ai_conversations?id=eq.{urllib.parse.quote(str(pending.get('conversation_id')), safe='')}", {"updated_at": completed})
            except Exception as exc:
                # Persist an auditable bounded failure in the existing Admin
                # conversation rather than silently dropping the request.
                _supabase_request("POST", "/rest/v1/admin_ai_messages", {"conversation_id": pending.get("conversation_id"), "user_id": pending.get("user_id"), "role": "error", "content": f"Nova unavailable: {type(exc).__name__}"})
        except Exception:
            time.sleep(2)

class NovaAdminLimiter:
    def __init__(self, requests_per_minute=12):
        self.requests_per_minute, self.history, self.active, self.lock = requests_per_minute, defaultdict(deque), 0, threading.Lock()
    def acquire(self, session):
        now = time.monotonic()
        with self.lock:
            history = self.history[session]
            while history and now - history[0] >= 60: history.popleft()
            if len(history) >= self.requests_per_minute or self.active >= 1: return False
            history.append(now); self.active += 1; return True
    def release(self):
        with self.lock: self.active = max(0, self.active - 1)

def _hermes_context(message, recent_history, conversation_id=""):
    """Build bounded Nexus pre-context for Hermes without becoming an agent.

    Hermes remains the execution owner. These projections are read-only
    evidence supplied by the Mac control plane so the profile can answer from
    current Nexus state rather than a stale generic brief.
    """
    try:
        from nexus_agent_platform.nova_company_context import build_company_context, context_for_prompt
        from nexus_agent_platform.nova_knowledge_retrieval import (
            classify_question_layers, format_knowledge_for_prompt, retrieve_knowledge,
        )
        context = context_for_prompt(build_company_context())
        layers = classify_question_layers(message, recent_history)
        retrieval = format_knowledge_for_prompt(retrieve_knowledge(message, layers))
    except Exception as exc:
        context = json.dumps({"status": "UNAVAILABLE", "reason": type(exc).__name__})
        retrieval = ""
    history = []
    for item in (recent_history or [])[-8:]:
        if isinstance(item, dict) and item.get("role") in {"user", "assistant"}:
            content = str(item.get("content", "")).strip()[:1800]
            if content:
                history.append({"role": item["role"], "content": content})
    try:
        from nexus_agent_platform.nova_capability_truth import capability_truth_for_prompt
        runtime_capability = capability_truth_for_prompt()
    except Exception as exc:
        runtime_capability = f"Google capability truth unavailable: {type(exc).__name__}; do not claim Google access."
    capability = (
        "CURRENT HERMES NOVA RUNTIME CAPABILITY TRUTH (authoritative):\n"
        "- Hermes Agent: 0.20.6 on Oracle, profile nova_nexus.\n"
        "- Nexus MCP: active through the configured nexus_mcp_remote profile toolset; "
        "read-only Nexus checks are available to this Hermes turn.\n"
        + runtime_capability + "\n"
        "- Never infer active access from repository documentation or historical Hermes reports.\n"
        f"- ADMIN_CONVERSATION_ID for delegation correlation: {str(conversation_id)[:120]}\n"
        "DEPARTMENT DELEGATION CONTRACT (authoritative):\n"
        "- If the user explicitly says Ask Systems Engineering, call nexus_delegate_specialist with specialist SYSTEM.\n"
        "- If the user explicitly says Ask Research, call nexus_delegate_specialist with specialist RESEARCH.\n"
        "- If the user explicitly says Ask Alpha, call nexus_delegate_specialist with specialist ALPHA.\n"
        "- Do not substitute a generic business-state read or historical report for an explicit delegation.\n"
        "- A delegated result is valid only with its delegation_receipt, freshness, status, and evidence references.\n"
        "- If the receipt is BLOCKED or unavailable, say so; do not present a historical artifact as fresh execution.\n"
    )
    return (
        "[NEXUS HERMES ADMIN CONTEXT]\n"
        "Use this bounded read-only context as evidence. Current governed/runtime facts outrank repository/history; "
        "exact entity records outrank generic summaries; historical documents explain architecture but do not override live state. "
        "Conversation history supports continuity but never overrides verified current state. Do not claim a tool action or result "
        "unless it occurred in this Hermes turn.\n"
        + capability
        + "CURRENT NEXUS CONTEXT:\n" + context[:12000]
        + ("\nRELEVANT KNOWLEDGE:\n" + retrieval[:12000] if retrieval else "")
        + ("\nRECENT ADMIN CONVERSATION:\n" + json.dumps(history, ensure_ascii=False) if history else "")
    )


def invoke_nova(message, conversation_id="admin-browser", recent_history=None):
    """Invoke the one canonical Hermes runtime; reject legacy graph mode."""
    if SENSITIVE_CLIENT_INPUT.search(message):
        raise ValueError("client-sensitive-input-not-available-in-nova-browser")
    runtime = os.environ.get("NEXUS_ADMIN_NOVA_RUNTIME", "hermes").strip().lower()
    if runtime != "hermes":
        raise RuntimeError("legacy_direct_nova_disabled")
    result = run_oracle_hermes(
        message,
        str(conversation_id),
        timeout_seconds=180.0,
        pre_context=_hermes_context(message, recent_history, conversation_id),
    )
    if result.status != "SUCCEEDED" or not result.response:
        raise RuntimeError(result.error or "hermes-nova-unavailable")
    return {
        "schema_version": "nexus.nova-response.v1",
        "text": result.response,
        "provider": result.provider,
        "model": result.model,
        "executor": "hermes_agent_0.20.6",
        "runtime": "hermes",
        "runtime_host": result.runtime_host,
        "profile": result.profile,
        "toolset": result.toolset,
        "latency_ms": result.latency_ms,
        "execution_authority": "NONE",
        "conversation_scope": "admin_browser",
        "memory_scope": "nova_admin_channel",
        "session_id": str(conversation_id),
        "hermes_session_id": result.hermes_session_id,
    }

class NovaAdminHandler(BaseHTTPRequestHandler):
    server_version = "NexusNovaAdminLocal/1"
    def _cors(self):
        if self.headers.get("Origin") == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN); self.send_header("Access-Control-Allow-Credentials", "true"); self.send_header("Vary", "Origin")
    def _send(self, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self._cors(); self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self):
        if self.headers.get("Origin") != ALLOWED_ORIGIN: self._send(403, {"error": "origin-not-allowed"}); return
        self.send_response(204); self._cors(); self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS"); self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Nexus-Nova-Session"); self.send_header("Access-Control-Max-Age", "300"); self.end_headers()
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self._send(404, {"error": "not-found"}); return
        self._send(200, {"service": "nova-admin", "status": "healthy", "chat_route": "/v1/nova/chat"})
    def do_POST(self):
        if self.path != "/v1/nova/chat": self._send(404, {"error": "not-found"}); return
        if self.headers.get("Origin") != ALLOWED_ORIGIN: self._send(403, {"error": "origin-not-allowed"}); return
        if not _require_admin(self.headers): self._send(401, {"error": "admin_authentication_required"}); return
        try: length = int(self.headers.get("Content-Length", "0"))
        except ValueError: self._send(400, {"error": "invalid-content-length"}); return
        if length <= 0 or length > MAX_BODY_BYTES: self._send(413, {"error": "request-size-bounded"}); return
        session = self.headers.get("X-Nexus-Nova-Session", "admin-browser")[:120]
        if not self.server.limiter.acquire(session): self._send(429, {"error": "nova-rate-limited-or-busy"}); return
        try:
            try: payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError): self._send(400, {"error": "invalid-json"}); return
            message = payload.get("message") if isinstance(payload, dict) else None
            if not isinstance(message, str) or not message.strip() or len(message) > MAX_MESSAGE_CHARS: self._send(400, {"error": "message-bounded"}); return
            conversation_id = payload.get("conversation_id")
            if not isinstance(conversation_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,120}", conversation_id): self._send(400, {"error": "conversation-id-bounded"}); return
            supplied_history = payload.get("recent_history", [])
            if not isinstance(supplied_history, list) or len(supplied_history) > MAX_HISTORY_MESSAGES: self._send(400, {"error": "history-bounded"}); return
            recent_history = []
            history_chars = 0
            for item in supplied_history:
                if not isinstance(item, dict) or item.get("role") not in ("user", "assistant") or not isinstance(item.get("content"), str): self._send(400, {"error": "history-contract-invalid"}); return
                content = item["content"].strip()[:2400]
                history_chars += len(content)
                if content: recent_history.append({"role": item["role"], "content": content})
            if history_chars > MAX_HISTORY_CHARS: self._send(413, {"error": "history-size-bounded"}); return
            self._send(200, invoke_nova(message.strip(), conversation_id, recent_history))
        except ValueError as exc: self._send(400, {"error": str(exc)})
        except Exception: self._send(503, {"error": "nova-unavailable"})
        finally: self.server.limiter.release()
    def log_message(self, *_args): return

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8790); args = parser.parse_args()
    if args.host != "127.0.0.1": raise SystemExit("Nova Admin server must remain bound to 127.0.0.1")
    server = ThreadingHTTPServer((args.host, args.port), NovaAdminHandler); server.limiter = NovaAdminLimiter()
    threading.Thread(target=_remote_command_worker, name="admin-nova-remote-queue", daemon=True).start()
    server.serve_forever(); return 0

if __name__ == "__main__": raise SystemExit(main())
