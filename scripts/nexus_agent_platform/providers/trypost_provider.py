"""TryPost adapter for the existing Nexus social-provider contract.

This adapter deliberately separates service reachability from social-account
authorization.  The current TryPost deployment is a localhost-only Labs
canary; no social credentials are configured.  Operations whose live TryPost
schema/auth has not been certified return an explicit unsupported result rather
than fabricating provider capability.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping


UNSUPPORTED = "UNSUPPORTED_NOT_PROVEN"


@dataclass(frozen=True)
class TryPostConfig:
    base_url: str = "http://127.0.0.1:18000"
    mcp_route: str = "/mcp/trypost"
    timeout_seconds: float = 5.0
    credential_ref: str = "credential.trypost.social.lab"
    allow_external_mutations: bool = False


class TryPostProvider:
    """Provider adapter with safe service probes and governed operation gates."""

    provider = "TRYPOST"

    def __init__(self, config: TryPostConfig | None = None, opener=None, token_provider: Callable[[], str | None] | None = None) -> None:
        self.config = config or TryPostConfig()
        self._opener = opener or urllib.request.urlopen
        self._token_provider = token_provider

    def _receipt(self, operation: str, result: str, **details: Any) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "operation": operation,
            "request_id": f"trypost_{int(time.time() * 1000)}",
            "timestamp": time.time(),
            "result": result,
            "details": details,
            "secret_values_included": False,
        }

    def _read(self, path: str) -> tuple[int, bytes]:
        request = urllib.request.Request(self.config.base_url.rstrip("/") + path, method="GET", headers=self._headers())
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                return int(response.status), response.read(4096)
        except urllib.error.HTTPError as exc:
            return int(exc.code), exc.read(4096)

    def _headers(self) -> dict[str, str]:
        token = self._token_provider() if self._token_provider else None
        return {
            "Accept": "application/json",
            "User-Agent": "Nexus-TryPost-Adapter/1.0",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        }

    def _auth_required(self, operation: str) -> dict[str, Any] | None:
        if self._token_provider is None or not self._token_provider():
            return self._receipt(operation, "AUTH_REQUIRED_NOT_CONFIGURED", credential_ref=self.config.credential_ref)
        return None

    def _json_request(self, operation: str, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + path,
            method=method,
            headers={**self._headers(), "Content-Type": "application/json"},
            data=json.dumps(dict(payload or {})).encode() if method != "GET" else None,
        )
        try:
            with self._opener(request, timeout=self.config.timeout_seconds) as response:
                status = int(response.status)
                raw = response.read(65536)
                body: Any = json.loads(raw.decode()) if raw else None
                result = "PASS_REAL" if 200 <= status < 300 else self._status_result(status)
                return self._receipt(operation, result, http_status=status, response=self._sanitize_response(body))
        except urllib.error.HTTPError as exc:
            category = self._status_result(exc.code)
            return self._receipt(operation, category, http_status=int(exc.code))
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            return self._receipt(operation, "SERVICE_DOWN", error_class=type(exc).__name__)

    @staticmethod
    def _status_result(status: int) -> str:
        if status in {401, 403}:
            return "AUTH_REQUIRED"
        if status == 404:
            return "CHANNEL_NOT_CONNECTED_OR_NOT_FOUND"
        if status == 422:
            return "INVALID_PAYLOAD"
        if status == 429:
            return "RATE_LIMITED"
        return "API_FAILURE"

    @classmethod
    def _sanitize_response(cls, value: Any) -> Any:
        """Remove credential-shaped fields before a response enters a receipt."""
        blocked = ("token", "secret", "password", "cookie", "authorization", "private_key", "api_key")
        if isinstance(value, dict):
            return {
                key: cls._sanitize_response(item)
                for key, item in value.items()
                if not any(part in str(key).lower() for part in blocked)
            }
        if isinstance(value, list):
            return [cls._sanitize_response(item) for item in value]
        return value

    def probe(self) -> dict[str, Any]:
        try:
            status, _ = self._read("/")
            mcp_status, _ = self._read(self.config.mcp_route)
            oauth_status, _ = self._read("/.well-known/oauth-authorization-server")
            # urllib may follow the app's login redirect through a forwarded
            # localhost host and receive an auth response.  That still proves
            # the service path is reachable; the MCP and OAuth endpoints are
            # the authoritative route checks.
            result = "PASS_REAL" if status in {200, 302, 401} and mcp_status in {401, 405} and oauth_status == 200 else "DEGRADED"
            return self._receipt(
                "health",
                result,
                app_http=status,
                mcp_http=mcp_status,
                oauth_discovery_http=oauth_status,
                auth_state="AUTH_REQUIRED_NOT_CONFIGURED" if mcp_status in {401, 403} else "PROTECTED_ROUTE_PRESENT_UNAUTHENTICATED",
            )
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            return self._receipt("health", "SERVICE_DOWN", error_class=type(exc).__name__)

    def account_health(self, account: Mapping[str, Any]) -> dict[str, Any]:
        if required := self._auth_required("account_health"):
            return required
        result = self._json_request("account_health", "GET", "/api/social-accounts")
        result["details"]["requested_channel"] = account.get("platform")
        return result

    def probe_account(self) -> dict[str, Any]:
        if required := self._auth_required("probe_account"):
            return required
        return self._json_request("probe_account", "GET", "/api/social-accounts")

    def workspace(self) -> dict[str, Any]:
        if required := self._auth_required("workspace"):
            return required
        return self._json_request("workspace", "GET", "/api/workspace")

    def _mutation_gate(self, operation: str) -> dict[str, Any] | None:
        if not self.config.allow_external_mutations:
            return self._receipt(operation, "EXTERNAL_ACTION_GATED", reason="mutations disabled pending social-auth and Upgrade Control approval")
        return self._auth_required(operation)

    def create_draft(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if required := self._auth_required("create_draft"):
            return required
        return self._json_request("create_draft", "POST", "/api/posts", payload)

    def schedule_post(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if required := self._mutation_gate("schedule_post"):
            return required
        post_id = payload.get("post_id")
        if not post_id:
            return self._receipt("schedule_post", "INVALID_PAYLOAD", reason="post_id is required")
        body = {key: value for key, value in payload.items() if key != "post_id"}
        body["status"] = "scheduled"
        return self._json_request("schedule_post", "PUT", f"/api/posts/{post_id}", body)

    def list_scheduled(self, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if required := self._auth_required("list_scheduled"):
            return required
        return self._json_request("list_scheduled", "GET", "/api/posts?status=scheduled")

    def publish_post(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if gated := self._mutation_gate("publish_post"):
            return gated
        post_id = payload.get("post_id")
        if not post_id:
            return self._receipt("publish_post", "INVALID_PAYLOAD", reason="post_id is required")
        body = {key: value for key, value in payload.items() if key != "post_id"}
        body["status"] = "publishing"
        return self._json_request("publish_post", "PUT", f"/api/posts/{post_id}", body)

    def get_publish_status(self, post_id: str) -> dict[str, Any]:
        if required := self._auth_required("get_publish_status"):
            return required
        if not post_id:
            return self._receipt("get_publish_status", "INVALID_PAYLOAD", reason="post_id is required")
        return self._json_request("get_publish_status", "GET", f"/api/posts/{post_id}")


def service_canary(base_url: str = "http://127.0.0.1:18000") -> dict[str, Any]:
    """Return a sanitized service-only canary suitable for Supervisor/Nova."""
    result = TryPostProvider(TryPostConfig(base_url=base_url)).probe()
    return {"provider": "TRYPOST", "service_canary": result, "secret_values_included": False}
