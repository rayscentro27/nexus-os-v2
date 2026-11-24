"""Authenticated, loopback-only HTTP transport for the immutable Google MCP.

This adapter imports the existing Google tools from the pinned MCP release.
It adds no tools and cannot select a host, port, path, or command at runtime.
"""
from __future__ import annotations

import hmac
import os
import subprocess
import sys
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

GOOGLE_SOURCE_RELEASE = Path(__file__).resolve().parents[2]  # the release (or checkout) this transport ships in
GOOGLE_SOURCE_MODULE = GOOGLE_SOURCE_RELEASE / "services/google_mcp/server.py"
GOOGLE_SOURCE_SCRIPTS = GOOGLE_SOURCE_RELEASE / "scripts"
TRANSPORT_HOST = "127.0.0.1"
TRANSPORT_PORT = 18767
TRANSPORT_TOKEN_ENV = "GOOGLE_MCP_TRANSPORT_TOKEN"
KEYCHAIN_SERVICE = "nexus/credential.nexus.google.mcp.transport.v1"
KEYCHAIN_ACCOUNT = "google_mcp_bearer"

if not GOOGLE_SOURCE_MODULE.is_file():
    raise RuntimeError("PINNED_GOOGLE_MCP_RELEASE_UNAVAILABLE")
sys.path.insert(0, str(GOOGLE_SOURCE_SCRIPTS))
sys.path.insert(0, str(GOOGLE_SOURCE_RELEASE))

from services.google_mcp import server as google_server  # noqa: E402

if not Path(google_server.__file__).resolve().is_relative_to(GOOGLE_SOURCE_RELEASE.resolve()):
    raise RuntimeError("GOOGLE_MCP_SOURCE_RELEASE_MISMATCH")

mcp = google_server.mcp


class GoogleBearerBoundaryMiddleware(BaseHTTPMiddleware):
    """Require the dedicated MCP transport token; Google OAuth stays internal."""

    async def dispatch(self, request: Request, call_next):
        expected = os.environ.get(TRANSPORT_TOKEN_ENV, "")
        supplied = request.headers.get("authorization", "")
        if not expected or not supplied.startswith("Bearer ") or not hmac.compare_digest(
            supplied[7:].strip(), expected
        ):
            return JSONResponse({"error": "unauthorized", "authority": "Google MCP transport"}, status_code=401)
        return await call_next(request)


app = mcp.streamable_http_app()
app.add_middleware(GoogleBearerBoundaryMiddleware)


def _transport_token() -> str:
    supplied = os.environ.get(TRANSPORT_TOKEN_ENV, "")
    if supplied:
        return supplied
    try:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
             "-a", KEYCHAIN_ACCOUNT, "-w"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("GOOGLE_MCP_TRANSPORT_CREDENTIAL_UNAVAILABLE") from exc
    token = result.stdout.strip()
    if result.returncode != 0 or not token:
        raise RuntimeError("GOOGLE_MCP_TRANSPORT_CREDENTIAL_UNAVAILABLE")
    return token


def main() -> None:
    import uvicorn

    os.environ[TRANSPORT_TOKEN_ENV] = _transport_token()
    uvicorn.run(app, host=TRANSPORT_HOST, port=TRANSPORT_PORT, log_level="warning")


if __name__ == "__main__":
    main()
