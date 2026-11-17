"""Bounded GitHub Remote Capability. Reads use GitHub HTTPS APIs; no git clone."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

DB_PATH = Path.home() / ".nexus/state/github_remote/github_remote.sqlite3"
SNAPSHOT_ROOT = Path.home() / ".nexus/tmp/github_remote"
MAX_READ_BYTES = 1_000_000
MAX_TREE_ITEMS = 1000
MAX_SNAPSHOT_BYTES = 50 * 1024 * 1024
SNAPSHOT_TTL_HOURS = 24
API = "https://api.github.com"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
OWNERS = {"SYSTEMS", "RESEARCH", "BUSINESS_OPPORTUNITIES", "TRADING", "CREATIVE", "MARKETING", "SHARED"}
ROUTES = {"RESEARCH_THEN_OPPORTUNITIES", "RESEARCH_THEN_TRADING", "SYSTEMS_ONLY", "RESEARCH_ONLY", "RESEARCH_THEN_CREATIVE"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
 source_id TEXT PRIMARY KEY, repository_full_name TEXT NOT NULL UNIQUE,
 repository_url TEXT NOT NULL, default_branch TEXT, owner_engine TEXT NOT NULL,
 routing_target TEXT NOT NULL, monitor_enabled INTEGER NOT NULL DEFAULT 0,
 monitor_method TEXT NOT NULL DEFAULT 'GITHUB_API_COMMIT_SHA', monitor_frequency TEXT NOT NULL DEFAULT 'MANUAL_OR_GITHUB_ACTIONS',
 tracked_paths_json TEXT NOT NULL DEFAULT '[]', last_known_commit TEXT, last_seen_commit TEXT,
 last_checked_at TEXT, last_changed_at TEXT, last_change_summary TEXT,
 verification_required INTEGER NOT NULL DEFAULT 1, execution_mode TEXT NOT NULL DEFAULT 'READ_ONLY',
 local_install_allowed INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'ACTIVE',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS change_events (
 event_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
 previous_commit TEXT, current_commit TEXT NOT NULL, changed_paths_json TEXT NOT NULL,
 summary TEXT NOT NULL, owner_engine TEXT NOT NULL, routing_target TEXT NOT NULL,
 verification_required INTEGER NOT NULL, observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
 snapshot_id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(source_id),
 repository_full_name TEXT NOT NULL, requested_ref TEXT NOT NULL, exact_commit TEXT NOT NULL,
 archive_path TEXT NOT NULL, sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL,
 expires_at TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_source_time ON change_events(source_id, observed_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if DB_PATH.parent == Path.home() / ".nexus/state/github_remote":
        DB_PATH.parent.chmod(0o700)
    if DB_PATH.is_symlink():
        raise ValueError("registry_database_must_not_be_symlinked")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    if DB_PATH.exists():
        DB_PATH.chmod(0o600)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA user_version=1")
    return conn


def _repo(value: str) -> str:
    value = (value or "").strip().removeprefix("https://github.com/").strip("/")
    if value.endswith(".git"):
        value = value[:-4]
    if not REPO_RE.fullmatch(value) or value.count("/") != 1:
        raise ValueError("repository_must_be_owner_and_name_or_github_url")
    owner, name = value.split("/")
    if owner.startswith(("-", ".")) or name.startswith(("-", ".")) or name in {".", ".."}:
        raise ValueError("repository_must_use_canonical_owner_and_name")
    return value


def _request(url: str, *, accept: str = "application/vnd.github+json", max_bytes: int = MAX_READ_BYTES) -> tuple[bytes, dict[str, str]]:
    headers = {"Accept": accept, "User-Agent": "Nexus-GitHub-Remote/1.0", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError("github_response_exceeds_size_bound")
            return data, {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as exc:
        remaining = exc.headers.get("X-RateLimit-Remaining", "unknown") if exc.headers else "unknown"
        raise RuntimeError(f"github_http_{exc.code}; rate_limit_remaining={remaining}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"github_request_failed:{type(exc).__name__}") from None


def _json(path: str, *, max_bytes: int = MAX_READ_BYTES) -> tuple[Any, dict[str, str]]:
    raw, headers = _request(API + path, max_bytes=max_bytes)
    return json.loads(raw.decode("utf-8")), headers


def _redact_remote_text(value: str) -> str:
    value = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b", "[REDACTED_GITHUB_TOKEN]", value)
    value = re.sub(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", value)
    return value


def _secret_path(path: str) -> bool:
    name = Path(path).name.lower()
    return (name in {".env", ".npmrc", ".pypirc", "auth.json", "credentials.json", "secrets.json"}
            or name.startswith(".env.") or name.endswith((".pem", ".key", ".p12", ".pfx")))


def repo_info(repository: str) -> dict[str, Any]:
    repo = _repo(repository)
    data, headers = _json("/repos/" + urllib.parse.quote(repo, safe="/"))
    return {"status": "OK", "repository": data.get("full_name"), "url": data.get("html_url"),
            "description": _redact_remote_text(data.get("description") or ""), "default_branch": data.get("default_branch"),
            "visibility": "private" if data.get("private") else "public", "archived": data.get("archived"),
            "stars": data.get("stargazers_count"), "forks": data.get("forks_count"),
            "license": (data.get("license") or {}).get("spdx_id"), "language": data.get("language"),
            "updated_at": data.get("updated_at"), "rate_limit_remaining": headers.get("x-ratelimit-remaining")}


def current_commit(repository: str, ref: str = "") -> dict[str, Any]:
    repo = _repo(repository)
    if ref and (len(ref) > 160 or ref.startswith("-") or ".." in ref):
        raise ValueError("invalid_ref")
    info = repo_info(repo)
    branch = ref or info["default_branch"]
    data, _ = _json(f"/repos/{repo}/commits/{urllib.parse.quote(branch, safe='')}")
    return {"status": "OK", "repository": repo, "ref": branch, "commit": data["sha"],
            "message": ((data.get("commit") or {}).get("message") or "").splitlines()[0][:300],
            "committed_at": (data.get("commit") or {}).get("committer", {}).get("date")}


def read_file(repository: str, path: str, ref: str = "") -> dict[str, Any]:
    repo = _repo(repository)
    path = (path or "").strip("/")
    if not path or path.startswith("-") or ".." in Path(path).parts or len(path) > 500:
        raise ValueError("invalid_repository_path")
    if _secret_path(path):
        raise ValueError("sensitive_repository_path_read_denied")
    qs = "?ref=" + urllib.parse.quote(ref, safe="") if ref else ""
    data, _ = _json(f"/repos/{repo}/contents/{urllib.parse.quote(path, safe='/')}" + qs,
                    max_bytes=MAX_READ_BYTES * 2)
    if not isinstance(data, dict) or data.get("type") != "file":
        raise ValueError("path_is_not_a_single_file")
    import base64
    raw = base64.b64decode(data.get("content", ""), validate=False)
    if len(raw) > MAX_READ_BYTES:
        raise ValueError("file_exceeds_read_bound")
    return {"status": "OK", "repository": repo, "path": path, "sha": data.get("sha"),
            "size": len(raw), "encoding": "utf-8", "content": _redact_remote_text(raw.decode("utf-8", errors="replace"))}


def read_readme(repository: str, ref: str = "") -> dict[str, Any]:
    repo = _repo(repository)
    qs = "?ref=" + urllib.parse.quote(ref, safe="") if ref else ""
    data, _ = _json(f"/repos/{repo}/readme{qs}", max_bytes=MAX_READ_BYTES * 2)
    import base64
    raw = base64.b64decode(data.get("content", ""), validate=False)
    if len(raw) > MAX_READ_BYTES:
        raw = raw[:MAX_READ_BYTES]
    return {"status": "OK", "repository": repo, "path": data.get("path"), "sha": data.get("sha"),
            "content": _redact_remote_text(raw.decode("utf-8", errors="replace"))}


def list_files(repository: str, path: str = "", ref: str = "") -> dict[str, Any]:
    repo = _repo(repository)
    info = repo_info(repo)
    branch = ref or info["default_branch"]
    tree, _ = _json(f"/repos/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1", max_bytes=4_000_000)
    prefix = (path.strip("/") + "/") if path else ""
    rows = [{"path": item["path"], "type": item["type"], "size": item.get("size")}
            for item in tree.get("tree", []) if item.get("path", "").startswith(prefix)][:MAX_TREE_ITEMS]
    return {"status": "OK", "repository": repo, "ref": branch, "truncated": bool(tree.get("truncated")), "items": rows}


def releases(repository: str, limit: int = 10) -> dict[str, Any]:
    repo = _repo(repository)
    limit = max(1, min(int(limit), 20))
    data, _ = _json(f"/repos/{repo}/releases?per_page={limit}", max_bytes=1_000_000)
    return {"status": "OK", "repository": repo, "items": [
        {"tag": x.get("tag_name"), "name": x.get("name"), "published_at": x.get("published_at"),
         "url": x.get("html_url"), "draft": x.get("draft"), "prerelease": x.get("prerelease")}
        for x in data]}


def register_source(repository: str, owner_engine: str, routing_target: str, *, monitor_enabled: bool = False,
                    tracked_paths: list[str] | None = None, verification_required: bool = True,
                    execution_mode: str = "READ_ONLY") -> dict[str, Any]:
    repo = _repo(repository)
    owner = owner_engine.upper()
    route = routing_target.upper()
    if owner not in OWNERS or route not in ROUTES:
        raise ValueError("unsupported_owner_or_routing_target")
    if execution_mode not in {"READ_ONLY", "MONITOR_ONLY", "TEMPORARY_SNAPSHOT_EXECUTE"}:
        raise ValueError("unsupported_execution_mode")
    paths = tracked_paths or []
    if len(paths) > 100 or any(not isinstance(p, str) or p.startswith("/") or ".." in Path(p).parts for p in paths):
        raise ValueError("invalid_tracked_paths")
    info = repo_info(repo)
    now = _now()
    conn = _connect()
    try:
        existing = conn.execute("SELECT source_id FROM sources WHERE repository_full_name=?", (repo,)).fetchone()
        sid = existing["source_id"] if existing else "ghsrc_" + uuid.uuid4().hex
        conn.execute("""INSERT INTO sources(source_id,repository_full_name,repository_url,default_branch,owner_engine,
          routing_target,monitor_enabled,tracked_paths_json,last_known_commit,verification_required,execution_mode,
          local_install_allowed,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(repository_full_name) DO UPDATE SET repository_url=excluded.repository_url,
          default_branch=excluded.default_branch,owner_engine=excluded.owner_engine,routing_target=excluded.routing_target,
          monitor_enabled=excluded.monitor_enabled,tracked_paths_json=excluded.tracked_paths_json,
          verification_required=excluded.verification_required,execution_mode=excluded.execution_mode,updated_at=excluded.updated_at""",
          (sid, repo, info["url"], info["default_branch"], owner, route, int(monitor_enabled),
           json.dumps(paths), None, int(verification_required), execution_mode, 0, "ACTIVE", now, now))
        conn.commit()
        row = dict(conn.execute("SELECT * FROM sources WHERE repository_full_name=?", (repo,)).fetchone())
        return {"status": "REGISTERED", "source": _safe_source(row)}
    finally:
        conn.close()


def _safe_source(row: dict[str, Any]) -> dict[str, Any]:
    row.pop("source_id", None)
    row["tracked_paths"] = json.loads(row.pop("tracked_paths_json", "[]"))
    return row


def list_sources(owner_engine: str = "", limit: int = 100) -> dict[str, Any]:
    conn = _connect()
    try:
        sql, args = "SELECT * FROM sources", []
        if owner_engine:
            sql += " WHERE owner_engine=?"; args.append(owner_engine.upper())
        rows = conn.execute(sql + " ORDER BY updated_at DESC LIMIT ?", (*args, max(1, min(int(limit), 100)))).fetchall()
        return {"status": "OK", "count": len(rows), "items": [_safe_source(dict(r)) for r in rows]}
    finally:
        conn.close()


def check_source(repository: str) -> dict[str, Any]:
    repo = _repo(repository)
    try:
        commit = current_commit(repo)
    except Exception as exc:
        conn = _connect()
        try:
            conn.execute("UPDATE sources SET status='FAILED',last_checked_at=?,updated_at=? WHERE repository_full_name=?",
                         (_now(), _now(), repo))
            conn.commit()
        finally:
            conn.close()
        return {"status": "ERROR", "repository": repo, "reason": f"github_check_failed:{type(exc).__name__}"}
    now = _now()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM sources WHERE repository_full_name=?", (repo,)).fetchone()
        if row is None:
            return {"status": "UNREGISTERED", "repository": repo, "current_commit": commit["commit"], "observed_at": now}
        previous = row["last_known_commit"]
        changed = bool(previous and previous != commit["commit"])
        changed_paths: list[str] = []
        if changed:
            compare, _ = _json(f"/repos/{repo}/compare/{previous}...{commit['commit']}", max_bytes=2_000_000)
            tracked = json.loads(row["tracked_paths_json"])
            changed_paths = [f["filename"] for f in compare.get("files", [])
                             if not tracked or any(f["filename"] == p or f["filename"].startswith(p.rstrip("/") + "/") for p in tracked)][:100]
        conn.execute("""UPDATE sources SET last_seen_commit=?,last_checked_at=?,last_known_commit=?,
          last_changed_at=CASE WHEN ? THEN ? ELSE last_changed_at END,
          last_change_summary=CASE WHEN ? THEN ? ELSE last_change_summary END,
          updated_at=? WHERE repository_full_name=?""",
          (commit["commit"], now, commit["commit"], int(changed), now, int(changed), commit.get("message", "Repository changed"), now, repo))
        if changed and changed_paths:
            conn.execute("INSERT INTO change_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("ghevt_" + uuid.uuid4().hex, row["source_id"], previous, commit["commit"], json.dumps(changed_paths),
                 commit.get("message", "Repository changed"), row["owner_engine"], row["routing_target"],
                 row["verification_required"], now))
        conn.commit()
        return {"status": "CHANGED" if changed and changed_paths else "UNCHANGED" if previous else "BASELINE_SET",
                "repository": repo, "previous_commit": previous, "current_commit": commit["commit"],
                "changed_paths": changed_paths, "observed_at": now,
                "owner_engine": row["owner_engine"], "routing_target": row["routing_target"],
                "verification_required": bool(row["verification_required"]),
                "summary": commit.get("message", "Repository state observed"),
                "research_request_prepared": bool(changed_paths and row["routing_target"].startswith("RESEARCH")),
                "local_install_allowed": False}
    finally:
        conn.close()


def monitor_status() -> dict[str, Any]:
    conn = _connect()
    try:
        total, enabled, stale, failed = conn.execute("SELECT COUNT(*),SUM(monitor_enabled),SUM(CASE WHEN monitor_enabled=1 AND (last_checked_at IS NULL OR last_checked_at<?) THEN 1 ELSE 0 END),SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) FROM sources", ((datetime.now(timezone.utc)-timedelta(days=7)).isoformat(),)).fetchone()
        try:
            limits, _ = _json("/rate_limit", max_bytes=200_000)
            core = limits.get("resources", {}).get("core", {})
            rate_limit = {"limit": core.get("limit"), "remaining": core.get("remaining"), "reset_epoch": core.get("reset")}
            api_state = "AVAILABLE"
        except Exception as exc:
            rate_limit = {"status": "UNKNOWN"}
            api_state = f"UNAVAILABLE:{type(exc).__name__}"
        return {"status": "OK", "registered_sources": total or 0, "monitor_enabled": enabled or 0,
                "stale_sources_7d": stale or 0, "failed_sources": failed or 0,
                "monitor_method": "GitHub REST API; manual or GitHub Actions invocation",
                "github_api": api_state, "rate_limit": rate_limit,
                "mac_scheduler": False, "last_monitor_run": conn.execute("SELECT MAX(last_checked_at) FROM sources").fetchone()[0]}
    finally:
        conn.close()


def get_changes(repository: str = "", limit: int = 50) -> dict[str, Any]:
    conn = _connect()
    try:
        sql = "SELECT e.*,s.repository_full_name FROM change_events e JOIN sources s USING(source_id)"
        args: list[Any] = []
        if repository:
            sql += " WHERE s.repository_full_name=?"; args.append(_repo(repository))
        rows = conn.execute(sql + " ORDER BY observed_at DESC LIMIT ?", (*args, max(1, min(int(limit), 100)))).fetchall()
        out = []
        for r in rows:
            d = dict(r); d.pop("event_id", None); d.pop("source_id", None); d["changed_paths"] = json.loads(d.pop("changed_paths_json"))
            out.append(d)
        return {"status": "OK", "count": len(out), "items": out}
    finally:
        conn.close()


def fetch_snapshot(repository: str, ref: str) -> dict[str, Any]:
    repo = _repo(repository)
    if not ref or len(ref) > 160 or ref.startswith("-") or ".." in ref:
        raise ValueError("exact_commit_tag_or_release_required")
    commit = current_commit(repo, ref)
    temp_root = Path.home() / ".nexus/tmp"
    if temp_root.is_symlink():
        raise ValueError("nexus_temporary_root_must_not_be_symlinked")
    SNAPSHOT_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if SNAPSHOT_ROOT.is_symlink():
        raise ValueError("snapshot_directory_must_not_be_symlinked")
    SNAPSHOT_ROOT.chmod(0o700)
    snapshot_id = "ghsnap_" + uuid.uuid4().hex
    url = f"https://api.github.com/repos/{repo}/tarball/{urllib.parse.quote(commit['commit'], safe='')}"
    raw, _ = _request(url, accept="application/vnd.github+json", max_bytes=MAX_SNAPSHOT_BYTES)
    path = SNAPSHOT_ROOT / (snapshot_id + ".tar.gz")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    sha = hashlib.sha256(raw).hexdigest()
    now = datetime.now(timezone.utc)
    conn = _connect()
    try:
        source = conn.execute("SELECT source_id FROM sources WHERE repository_full_name=?", (repo,)).fetchone()
        conn.execute("INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?,?,?)", (snapshot_id, source[0] if source else None,
            repo, ref, commit["commit"], str(path), sha, len(raw), (now+timedelta(hours=SNAPSHOT_TTL_HOURS)).isoformat(), now.isoformat()))
        conn.commit()
    finally:
        conn.close()
    return {"status": "OK", "snapshot_reference": snapshot_id, "repository": repo, "requested_ref": ref,
            "exact_commit": commit["commit"], "sha256": sha, "byte_size": len(raw),
            "expires_at": (now+timedelta(hours=SNAPSHOT_TTL_HOURS)).isoformat(), "history_included": False,
            "local_install_allowed": False}


def snapshot_info(snapshot_reference: str) -> dict[str, Any]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_reference,)).fetchone()
        if not row:
            return {"status": "NOT_FOUND"}
        d = dict(row); exists = Path(d["archive_path"]).is_file()
        d.pop("snapshot_id", None); d.pop("source_id", None); d["available"] = exists
        d["snapshot_path"] = d.pop("archive_path") if exists else ""
        return {"status": "OK", "snapshot": d}
    finally:
        conn.close()


def cleanup_snapshots(snapshot_reference: str = "") -> dict[str, Any]:
    now = _now(); removed = 0
    if snapshot_reference and not re.fullmatch(r"ghsnap_[a-f0-9]{32}", snapshot_reference):
        raise ValueError("invalid_snapshot_reference")
    conn = _connect()
    try:
        if snapshot_reference:
            rows = conn.execute("SELECT snapshot_id,archive_path FROM snapshots WHERE snapshot_id=?",
                                 (snapshot_reference,)).fetchall()
        else:
            rows = conn.execute("SELECT snapshot_id,archive_path FROM snapshots WHERE expires_at<=?", (now,)).fetchall()
        for row in rows:
            path = Path(row["archive_path"])
            if path.parent == SNAPSHOT_ROOT and path.name == row["snapshot_id"] + ".tar.gz" and path.is_file():
                path.unlink(); removed += 1
                conn.execute("DELETE FROM snapshots WHERE snapshot_id=?", (row["snapshot_id"],))
            elif not path.exists():
                conn.execute("DELETE FROM snapshots WHERE snapshot_id=?", (row["snapshot_id"],))
        conn.commit()
    finally:
        conn.close()
    return {"status": "OK", "snapshots_removed": removed, "retention_hours": SNAPSHOT_TTL_HOURS}


def classify(repository: str, owner_engine: str = "SHARED", routing_target: str = "RESEARCH_ONLY") -> dict[str, Any]:
    owner_engine = owner_engine.upper()
    routing_target = routing_target.upper()
    if owner_engine not in OWNERS or routing_target not in ROUTES:
        raise ValueError("unsupported_owner_or_routing_target")
    info = repo_info(repository)
    readme = read_readme(repository).get("content", "")[:30000]
    paths = [x["path"].lower() for x in list_files(repository).get("items", [])]
    text = (str(info.get("description") or "") + "\n" + readme).lower()
    runtime_names = ("python", "node", "docker", "cuda", "gpu", "database", "api", "rust", "go", "java")
    runtime = [name for name in runtime_names if name in text or any(p.endswith(name) for p in paths)]
    signals = {
        "hosted_service": any(x in text for x in ("hosted service", "cloud platform", "sign up", "web app", "hosted api")),
        "api": any(x in text for x in ("rest api", "api documentation", "api reference", "api key")),
        "sdk": any(x in text for x in ("sdk", "software development kit")) or any("sdk" in p for p in paths),
        "mcp": "mcp" in text or any("mcp" in p for p in paths),
        "cli": "command line" in text or any(Path(p).name in {"cli.py", "cli.ts", "main.go"} for p in paths),
        "gpu": "gpu" in text or "cuda" in text,
        "persistent_state": any(x in text for x in ("persistent state", "database", "sqlite", "postgres")),
        "network": any(x in text for x in ("internet connection", "network access", "http request", "api endpoint")),
    }
    if signals["hosted_service"]:
        mode = "HOSTED_SERVICE"
    elif signals["api"]:
        mode = "API_INTEGRATION"
    elif signals["sdk"]:
        mode = "SDK_INTEGRATION"
    elif any("github/workflows/" in p for p in paths):
        mode = "MONITOR_ONLY"
    else:
        mode = "READ_ONLY"
    return {"status": "OK", "repository": info["repository"], "mode": mode,
        "reason": "Remote metadata and README review only; no code executed. A local installation is not inferred from source availability.",
        "recommended_compute_target": "GitHub-hosted service/API if supported; otherwise isolated temporary compute after review",
        "mac_mini_impact": "NONE for remote read/monitor; do not install by default",
        "credentials_required": "unknown until specific integration is selected",
        "estimated_recurring_cost": "UNKNOWN; no paid provider activated",
        "risk_flags": ["license_review_required" if not info.get("license") else "security_review_before_execution",
                       "repository_content_untrusted"], "capability_signals": signals,
        "runtime_requirements_hints": runtime,
        "license": info.get("license"), "local_install_required": False,
        "owner_engine": owner_engine, "routing_target": routing_target, "execution_policy": "REMOTE_FIRST"}


def route_change(repository: str) -> dict[str, Any]:
    repo = _repo(repository)
    changes = get_changes(repo, 1)["items"]
    if not changes:
        return {"status": "NO_UNROUTED_CHANGE", "repository": repo}
    event = changes[0]
    return {"status": "PREPARED_FOR_OWNER_ROUTING", "event": event,
            "research_request_prepared": event["routing_target"].startswith("RESEARCH"),
            "downstream_write_performed": False,
            "note": "Compact verified-source change reference only; Research must inspect and verify before downstream promotion."}


def health() -> dict[str, Any]:
    conn = _connect()
    try:
        integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        return {"status": "HEALTHY" if integrity == "ok" else "DEGRADED", "sqlite_integrity": integrity,
                "schema_version": version or 1, "source_count": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
                "snapshot_count": conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
                "source_adapter": "GitHub REST API; credentials optional and never persisted",
                "research_interface": "NOT_PROBED; route prepared change through the existing Research MCP R5 interface; no direct database writes",
                "nexus_mcp_exposure": "registered in existing Nexus MCP"}
    finally:
        conn.close()

