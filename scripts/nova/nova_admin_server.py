"""Loopback-only bounded adapter for the canonical Nova graph."""
from __future__ import annotations
import argparse, hashlib, json, os, re, threading, time, uuid
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from nexus_agent_platform.adapters.state_adapter import AgentState
from nexus_agent_platform.agents.nova import get_nova_graph

ALLOWED_ORIGIN = "https://goclearonline.cc"
MAX_BODY_BYTES = 32 * 1024
MAX_MESSAGE_CHARS = 4000
MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 14000
ADMIN_CHAT_ID = 0  # Browser memory is deliberately separate from Telegram.
SENSITIVE_CLIENT_INPUT = re.compile(r"(?:\b\d{3}-\d{2}-\d{4}\b|\b(?:ssn|social security|bank account|routing number|date of birth|credit report)\b|\b[^\s@]+@[^\s@]+\.[^\s@]+\b)", re.I)

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

def _conversation_chat_id(conversation_id):
    """Return a stable non-identifying runtime key for this Admin thread."""
    digest = hashlib.sha256(str(conversation_id).encode("utf-8")).hexdigest()[:15]
    return int(digest, 16)


def invoke_nova(message, conversation_id="admin-browser", recent_history=None):
    if SENSITIVE_CLIENT_INPUT.search(message): raise ValueError("client-sensitive-input-not-available-in-nova-browser")
    recent_history = recent_history if isinstance(recent_history, list) else []
    runtime_chat_id = _conversation_chat_id(conversation_id)
    result = get_nova_graph().invoke(AgentState(agent_id="hermes_nova", mission_id=f"nova_admin_{uuid.uuid4().hex}", thread_id=str(conversation_id), user_message=message, metadata={"chat_id": runtime_chat_id, "conversation_id": str(conversation_id), "conversation_history": recent_history, "channel": "admin_browser", "execution_authority": "NONE"}))
    state = result if isinstance(result, AgentState) else AgentState.from_dict(result)
    metadata = state.metadata or {}
    return {"schema_version": "nexus.nova-response.v1", "text": state.assistant_response, "provider": metadata.get("model_provider", "openrouter"), "model": metadata.get("model_used") or os.environ.get("HERMES_NOVA_MODEL", "unknown"), "role": "strategic_adviser", "execution_authority": "NONE", "conversation_scope": "admin_browser", "memory_scope": "nova_admin_channel", "session_id": str(conversation_id)}

class NovaAdminHandler(BaseHTTPRequestHandler):
    server_version = "NexusNovaAdminLocal/1"
    def _cors(self):
        if self.headers.get("Origin") == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN); self.send_header("Access-Control-Allow-Credentials", "true"); self.send_header("Vary", "Origin")
    def _send(self, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self._cors(); self.end_headers(); self.wfile.write(body)
    def do_OPTIONS(self):
        if self.headers.get("Origin") != ALLOWED_ORIGIN: self._send(403, {"error": "origin-not-allowed"}); return
        self.send_response(204); self._cors(); self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS"); self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Nexus-Nova-Session"); self.send_header("Access-Control-Max-Age", "300"); self.end_headers()
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self._send(404, {"error": "not-found"}); return
        self._send(200, {"service": "nova-admin", "status": "healthy", "chat_route": "/v1/nova/chat"})
    def do_POST(self):
        if self.path != "/v1/nova/chat": self._send(404, {"error": "not-found"}); return
        if self.headers.get("Origin") != ALLOWED_ORIGIN: self._send(403, {"error": "origin-not-allowed"}); return
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
    # Build the canonical graph before accepting HTTP traffic.  Lazy graph
    # construction in the first request can make the single-request limiter
    # appear permanently busy while optional runtime modules import.
    get_nova_graph()
    server = ThreadingHTTPServer((args.host, args.port), NovaAdminHandler); server.limiter = NovaAdminLimiter(); server.serve_forever(); return 0

if __name__ == "__main__": raise SystemExit(main())
