"""Fail-closed target check for local UI certification helpers."""
import os
from urllib.parse import urlsplit


def require_local_browser_target(value: str) -> None:
    if (os.environ.get("NEXUS_E2E_APPROVED") != "1"
            or not os.environ.get("NEXUS_DURABLE_JOB_ID")
            or not os.environ.get("NEXUS_CORRELATION_ID")
            or not os.environ.get("NEXUS_APPROVAL_ID")):
        raise RuntimeError("E2E_DISABLED_REQUIRES_APPROVED_DURABLE_JOB")
    parsed = urlsplit(str(value or ""))
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("BROWSER_EXTERNAL_TARGET_DENIED")
