"""Small shadow case repository; production Supabase is never written."""
from __future__ import annotations

import json
import copy
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonCaseStore:
    """Atomic JSON persistence for isolated Research Room shadow cases."""
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, case_id: str) -> Path:
        safe = "".join(ch for ch in case_id if ch.isalnum() or ch in "-_" )
        if not safe:
            raise ValueError("INVALID_CASE_ID")
        return self.root / f"{safe}.json"

    def save(self, case: Any) -> dict[str, Any]:
        payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
        target = self._path(str(payload["case_id"]))
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return payload

    def load(self, case_id: str) -> dict[str, Any] | None:
        path = self._path(case_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


class SupabaseCaseStore:
    """Opt-in store for the dedicated shadow-only case table.

    It is disabled by default and never writes to production Research tables.
    The included proof suite uses ``JsonCaseStore`` so it has no live DB side
    effects. Deploy ``schema.sql`` before explicitly enabling this adapter.
    """
    table_name = "research_room_cases"

    def __init__(self, *, enabled: bool | None = None, session: Any = None,
                 url: str | None = None, key: str | None = None):
        enabled = (os.getenv("NEXUS_RESEARCH_ROOM_SUPABASE_SHADOW_ENABLED", "").lower() == "true") if enabled is None else enabled
        if not enabled:
            raise RuntimeError("RESEARCH_ROOM_SHADOW_SUPABASE_SCHEMA_NOT_CONFIGURED")
        if url is None or key is None:
            from scripts.ops.nexus_runtime_env import load_runtime_env
            load_runtime_env(allowed_keys={"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"})
            url = url or os.getenv("SUPABASE_URL")
            key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("RESEARCH_ROOM_SHADOW_SUPABASE_CREDENTIALS_UNAVAILABLE")
        import requests
        self.url, self.key = url.rstrip("/"), key
        self.session = session or requests.Session()
        self.session.headers.update({"apikey": key, "Authorization": f"Bearer {key}",
                                     "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=representation"})

    def save(self, case: Any) -> dict[str, Any]:
        payload = case.to_dict() if hasattr(case, "to_dict") else dict(case)
        if payload.get("metadata", {}).get("shadow_mode") is not True:
            raise ValueError("RESEARCH_ROOM_STORE_ACCEPTS_SHADOW_CASES_ONLY")
        stored_state = copy.deepcopy(payload)
        source = stored_state.get("source_report") or {}
        raw = str(source.get("text") or "")
        if len(raw) > 2400:
            source["source_content_hash"] = source.get("source_content_hash") or hashlib.sha256(raw.encode()).hexdigest()
            source["source_character_count"] = source.get("source_character_count") or len(raw)
            source["text"] = raw[:2400]
            source["raw_content_storage"] = "OMITTED_FROM_SUPABASE_SHADOW_STATE"
        for message in stored_state.get("room_messages", []):
            if message.get("kind") == "SOURCE_REPORT" and len(str(message.get("content", ""))) > 1800:
                message["content"] = str(message["content"])[:1800]
        row = {"case_id": payload["case_id"], "root_objective": payload.get("root_objective"),
               "status": payload.get("status"), "shadow_mode": True, "state": stored_state,
               "updated_at": datetime.now(timezone.utc).isoformat()}
        response = self.session.post(f"{self.url}/rest/v1/{self.table_name}?on_conflict=case_id",
            json=row, timeout=10)
        response.raise_for_status()
        return payload

    def load(self, case_id: str) -> dict[str, Any] | None:
        response = self.session.get(f"{self.url}/rest/v1/{self.table_name}",
            params={"case_id": f"eq.{case_id}", "select": "state", "limit": "1"}, timeout=10)
        response.raise_for_status()
        rows = response.json()
        return (rows[0].get("state") if rows else None)
