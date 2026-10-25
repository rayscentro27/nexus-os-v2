"""Authenticated Streamable HTTP adapter for the canonical Nexus MCP.

This is a transport adapter over ``services.nexus_mcp.server.mcp``. It does
not add tools, state, authority, or filesystem access. The listener is
loopback-only by default and is intended to be reached through a private
reverse tunnel by an explicitly configured Hermes worker.
"""

from __future__ import annotations

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .server import mcp


class BearerBoundaryMiddleware(BaseHTTPMiddleware):
    """Fail closed unless the exact runtime-injected bridge token is present."""

    async def dispatch(self, request: Request, call_next):
        expected = os.getenv("NEXUS_MCP_BRIDGE_TOKEN", "")
        supplied = request.headers.get("authorization", "")
        if not expected or not supplied.startswith("Bearer ") or not hmac.compare_digest(
            supplied[7:].strip(), expected
        ):
            return JSONResponse({"error": "unauthorized", "authority": "Nexus"}, status_code=401)
        return await call_next(request)


app = mcp.streamable_http_app()
app.add_middleware(BearerBoundaryMiddleware)


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("NEXUS_MCP_BRIDGE_HOST", "127.0.0.1"),
        port=int(os.getenv("NEXUS_MCP_BRIDGE_PORT", "18765")),
        log_level="warning",
    )


if __name__ == "__main__":
    main()
