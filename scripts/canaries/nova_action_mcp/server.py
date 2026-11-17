#!/usr/bin/env python3
"""Isolated five-tool stdio MCP canary for testing Nova write actions.

The server has no network client, shell interface, production path access, or
caller-controlled filesystem paths. Its only mutable state is the dedicated
canary sandbox supplied through NOVA_ACTION_CANARY_SANDBOX.
"""
from __future__ import annotations

import json
import os
import re
import socket
import socketserver
import sys
import threading
import time
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVER_NAME = "nova-action-canary"
VERSION = "1.0.0"
SANDBOX = Path(os.environ.get("NOVA_ACTION_CANARY_SANDBOX", "")).resolve()
MAX_NAME_CHARS = 120
MAX_CONTENT_CHARS = 20_000
MAX_WRITES_PER_HOUR = 60
NOTE_ID_RE = re.compile(r"^note_[0-9a-f]{32}$")
LOCK = threading.RLock()

if not os.environ.get("NOVA_ACTION_CANARY_SANDBOX") or not SANDBOX.is_absolute():
    raise SystemExit("NOVA_ACTION_CANARY_SANDBOX must be set to the isolated sandbox")

NOTES = SANDBOX / "notes"
DELETED = SANDBOX / "deleted"
AUDIT = SANDBOX / "receipts.jsonl"
for _path in (NOTES, DELETED):
    _path.mkdir(parents=True, exist_ok=True, mode=0o700)

WRITE_POLICY = (
    "WRITE_ALLOWED=YES; COST=ZERO; EXTERNAL_EFFECT=NO; PRODUCTION_EFFECT=NO; "
    "SANDBOX_ONLY=YES; REVERSIBLE=YES. Bounded to 60 write operations per rolling hour."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_note(note_id: str) -> dict[str, Any]:
    if not isinstance(note_id, str) or not NOTE_ID_RE.fullmatch(note_id):
        raise ValueError("INVALID_NOTE_ID")
    path = NOTES / f"{note_id}.json"
    if not path.is_file() or path.is_symlink():
        raise ValueError("NOTE_NOT_FOUND")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("note_id") != note_id:
        raise ValueError("NOTE_ID_MISMATCH")
    return value


def _audit(action: str, note_id: str, receipt_id: str) -> None:
    now = time.time()
    cutoff = now - 3600
    recent = 0
    lines = []
    if AUDIT.exists():
        lines = AUDIT.read_text(encoding="utf-8").splitlines()[-500:]
        for line in lines:
            try:
                row = json.loads(line)
                if float(row.get("timestamp_epoch", 0)) >= cutoff:
                    recent += 1
            except (ValueError, TypeError):
                continue
    if recent >= MAX_WRITES_PER_HOUR:
        raise ValueError("CANARY_ROLLING_WRITE_RATE_LIMIT")
    row = {"action": action, "note_id": note_id, "receipt_id": receipt_id,
           "created_at": _now(), "timestamp_epoch": now,
           "write_allowed": True, "cost": 0, "external_effect": False,
           "production_effect": False, "sandbox_only": True}
    temporary = AUDIT.with_name(f".{AUDIT.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write("\n".join([*lines, json.dumps(row, sort_keys=True)]) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, AUDIT)


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def canary_status() -> dict[str, Any]:
    count = sum(1 for path in NOTES.glob("note_*.json") if path.is_file() and not path.is_symlink())
    return {"SERVER_NAME": SERVER_NAME, "VERSION": VERSION,
            "SANDBOX_PATH": str(SANDBOX), "CURRENT_NOTE_COUNT": count}


def canary_create_note(name: str, content: str) -> dict[str, Any]:
    if not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME_CHARS:
        raise ValueError("INVALID_NAME")
    if not isinstance(content, str) or len(content) > MAX_CONTENT_CHARS:
        raise ValueError("INVALID_CONTENT")
    with LOCK:
        note_id = "note_" + uuid.uuid4().hex
        created = _now()
        receipt = "receipt_" + uuid.uuid4().hex
        note_path = NOTES / f"{note_id}.json"
        _atomic_write(note_path, {"note_id": note_id, "name": name.strip(),
                      "content": content, "created_at": created, "updated_at": created})
        try:
            _audit("CREATE", note_id, receipt)
        except Exception:
            note_path.unlink(missing_ok=True)
            raise
        return {"NOTE_ID": note_id, "NAME": name.strip(), "CREATED_AT": created, "RECEIPT_ID": receipt}


def canary_read_note(note_id: str) -> dict[str, Any]:
    with LOCK:
        note = _load_note(note_id)
        return {"NOTE_ID": note["note_id"], "NAME": note["name"], "CONTENT": note["content"],
                "CREATED_AT": note["created_at"], "UPDATED_AT": note["updated_at"]}


def canary_update_note(note_id: str, content: str) -> dict[str, Any]:
    if not isinstance(content, str) or len(content) > MAX_CONTENT_CHARS:
        raise ValueError("INVALID_CONTENT")
    with LOCK:
        note = _load_note(note_id)
        updated = _now()
        receipt = "receipt_" + uuid.uuid4().hex
        previous = dict(note)
        note["content"] = content
        note["updated_at"] = updated
        note_path = NOTES / f"{note_id}.json"
        _atomic_write(note_path, note)
        try:
            _audit("UPDATE", note_id, receipt)
        except Exception:
            _atomic_write(note_path, previous)
            raise
        return {"NOTE_ID": note_id, "UPDATED_AT": updated, "RECEIPT_ID": receipt}


def canary_delete_note(note_id: str) -> dict[str, Any]:
    with LOCK:
        _load_note(note_id)
        receipt = "receipt_" + uuid.uuid4().hex
        source = NOTES / f"{note_id}.json"
        tombstone = DELETED / f"{note_id}.json"
        os.replace(source, tombstone)
        try:
            _audit("DELETE", note_id, receipt)
        except Exception:
            os.replace(tombstone, source)
            raise
        return {"NOTE_ID": note_id, "DELETED": "YES", "RECEIPT_ID": receipt}


TOOLS = [
    {"name": "canary_status", "description": "Read-only status for the isolated nova-action-canary server.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
    {"name": "canary_create_note", "description": "Create a note only in the isolated canary sandbox. " + WRITE_POLICY,
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string", "maxLength": MAX_NAME_CHARS},
                    "content": {"type": "string", "maxLength": MAX_CONTENT_CHARS}},
                    "required": ["name", "content"], "additionalProperties": False},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}},
    {"name": "canary_read_note", "description": "Read a note from the isolated canary sandbox.",
     "inputSchema": {"type": "object", "properties": {"NOTE_ID": {"type": "string"}},
                    "required": ["NOTE_ID"], "additionalProperties": False},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
    {"name": "canary_update_note", "description": "Update a note only in the isolated canary sandbox. " + WRITE_POLICY,
     "inputSchema": {"type": "object", "properties": {"NOTE_ID": {"type": "string"},
                    "content": {"type": "string", "maxLength": MAX_CONTENT_CHARS}},
                    "required": ["NOTE_ID", "content"], "additionalProperties": False},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}},
    {"name": "canary_delete_note", "description": "Soft-delete (tombstone) a note in the isolated canary sandbox; reversible by restoring its sandbox file. " + WRITE_POLICY,
     "inputSchema": {"type": "object", "properties": {"NOTE_ID": {"type": "string"}},
                    "required": ["NOTE_ID"], "additionalProperties": False},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}},
]


def _call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "canary_status":
        if args: raise ValueError("NO_ARGUMENTS_ALLOWED")
        return canary_status()
    if name == "canary_create_note": return canary_create_note(args.get("name"), args.get("content"))
    if name == "canary_read_note": return canary_read_note(args.get("NOTE_ID"))
    if name == "canary_update_note": return canary_update_note(args.get("NOTE_ID"), args.get("content"))
    if name == "canary_delete_note": return canary_delete_note(args.get("NOTE_ID"))
    raise ValueError("UNKNOWN_TOOL")


def _encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")


def _handle(raw: str) -> dict[str, Any] | None:
    request = json.loads(raw)
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized":
        return None
    try:
        if method == "ping":
            result = {}
        elif method == "initialize":
            params = request.get("params") or {}
            result = {"protocolVersion": params.get("protocolVersion", "2024-11-05"),
                      "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": SERVER_NAME, "version": VERSION}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = request.get("params") or {}
            try:
                value = _call(params.get("name", ""), params.get("arguments") or {})
                result = {"content": [{"type": "text", "text": json.dumps(value, sort_keys=True)}],
                          "isError": False}
            except Exception as exc:
                result = {"content": [{"type": "text", "text": str(exc)[:240]}], "isError": True}
        else:
            if request_id is None:
                return None
            return {"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": -32601, "message": "Method not found"}}
        return {"jsonrpc": "2.0", "id": request_id, "result": result} if request_id is not None else None
    except Exception as exc:
        return ({"jsonrpc": "2.0", "id": request_id,
                 "error": {"code": -32603, "message": str(exc)[:240]}}
                if request_id is not None else None)


class _UnixHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        while raw := self.rfile.readline():
            try:
                response = _handle(raw.decode("utf-8"))
            except Exception as exc:
                response = {"jsonrpc": "2.0", "id": None,
                            "error": {"code": -32700, "message": str(exc)[:240]}}
            if response is not None:
                self.wfile.write(_encode(response))
                self.wfile.flush()


class _UnixServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


def _serve_unix(socket_path: Path) -> None:
    resolved = socket_path.resolve(strict=False)
    if resolved.parent != SANDBOX.resolve():
        raise SystemExit("Unix socket must be directly inside the isolated sandbox")
    if socket_path.exists() or socket_path.is_symlink():
        if not socket_path.is_socket():
            raise SystemExit("Refusing to replace non-socket canary path")
        socket_path.unlink()
    old_umask = os.umask(0o177)
    try:
        with _UnixServer(str(socket_path), _UnixHandler) as server:
            os.chmod(socket_path, 0o600)
            server.serve_forever(poll_interval=0.5)
    finally:
        os.umask(old_umask)
        try:
            socket_path.unlink()
        except FileNotFoundError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unix-socket")
    args = parser.parse_args()
    if args.unix_socket:
        _serve_unix(Path(args.unix_socket))
        return
    for raw in sys.stdin:
        try:
            response = _handle(raw)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": str(exc)[:240]}}
        if response is not None:
            sys.stdout.buffer.write(_encode(response))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
