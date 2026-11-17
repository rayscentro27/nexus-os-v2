from __future__ import annotations

import base64
import json
import sqlite3

import pytest

from scripts.github_remote import github_remote as gh
from scripts.github_remote.cloud_monitor.scripts import check_sources as cloud


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.headers = headers or {"X-RateLimit-Remaining": "58"}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, size=-1): return self.payload[:size]


@pytest.fixture
def temp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(gh, "DB_PATH", tmp_path / "state.sqlite3")
    monkeypatch.setattr(gh, "SNAPSHOT_ROOT", tmp_path / "snapshots")
    return tmp_path


def test_repository_validation_and_no_arbitrary_hosts():
    assert gh._repo("https://github.com/owner/project.git") == "owner/project"
    for bad in ("https://evil.example/a/b", "owner/project/extra", "../owner/repo", "-owner/repo"):
        with pytest.raises(ValueError): gh._repo(bad)
    assert gh._secret_path("config/.env.production") is True
    redacted = gh._redact_remote_text("Authorization: Bearer abcdefghijklmnop and ghp_" + "x"*28)
    assert "[REDACTED]" in redacted and "[REDACTED_GITHUB_TOKEN]" in redacted


def test_remote_metadata_readme_commit_and_tree(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        if "/repos/owner/repo/commits/" in url: return {"sha": "a"*40, "commit": {"message": "latest", "committer": {"date": "2026-11-01"}}}, {}
        if "/readme" in url: return {"content": base64.b64encode(b"# Remote read").decode(), "path": "README.md", "sha": "blob"}, {}
        if "/git/trees/" in url: return {"tree": [{"path": "README.md", "type": "blob"}], "truncated": False}, {}
        return {"full_name": "owner/repo", "html_url": "https://github.com/owner/repo", "default_branch": "main",
                "private": False, "license": {"spdx_id": "MIT"}}, {"x-ratelimit-remaining": "58"}
    monkeypatch.setattr(gh, "_json", get)
    assert gh.repo_info("owner/repo")["license"] == "MIT"
    assert gh.read_readme("owner/repo")["content"] == "# Remote read"
    assert gh.current_commit("owner/repo")["commit"] == "a"*40
    assert gh.list_files("owner/repo")["items"][0]["path"] == "README.md"
    assert not any("git/clone" in x for x in calls)


def test_registry_idempotence_monitor_baseline_and_changes(temp_state, monkeypatch):
    monkeypatch.setattr(gh, "repo_info", lambda repo: {"repository": repo, "url": f"https://github.com/{repo}", "default_branch": "main"})
    commits = iter(["a"*40, "b"*40])
    monkeypatch.setattr(gh, "current_commit", lambda repo, ref="": {"commit": next(commits), "message": "update"})
    monkeypatch.setattr(gh, "_json", lambda path, **kw: ({"files": [{"filename": "README.md"}]}, {}))
    first = gh.register_source("owner/repo", "RESEARCH", "RESEARCH_THEN_OPPORTUNITIES", monitor_enabled=True)
    again = gh.register_source("owner/repo", "RESEARCH", "RESEARCH_THEN_OPPORTUNITIES", monitor_enabled=True)
    assert first["source"]["repository_full_name"] == again["source"]["repository_full_name"]
    assert gh.check_source("owner/repo")["status"] == "BASELINE_SET"
    changed = gh.check_source("owner/repo")
    assert changed["status"] == "CHANGED"
    assert changed["research_request_prepared"] is True
    assert gh.get_changes("owner/repo")["count"] == 1
    assert gh.health()["sqlite_integrity"] == "ok"


def test_snapshot_exact_reference_temporary_and_cleanup(temp_state, monkeypatch):
    monkeypatch.setattr(gh, "current_commit", lambda repo, ref="": {"commit": "c"*40})
    monkeypatch.setattr(gh, "_request", lambda *a, **kw: (b"bounded-tarball", {}))
    out = gh.fetch_snapshot("owner/repo", "v1.2")
    assert out["history_included"] is False
    info = gh.snapshot_info(out["snapshot_reference"])
    assert info["snapshot"]["exact_commit"] == "c"*40
    assert info["snapshot"]["available"] is True
    conn = sqlite3.connect(gh.DB_PATH)
    conn.execute("UPDATE snapshots SET expires_at='2000-01-01T00:00:00+00:00'")
    conn.commit(); conn.close()
    assert gh.cleanup_snapshots()["snapshots_removed"] == 1
    assert gh.snapshot_info(out["snapshot_reference"])["status"] == "NOT_FOUND"


def test_classifier_defaults_remote_first(monkeypatch):
    monkeypatch.setattr(gh, "repo_info", lambda repo: {"repository": repo, "description": "research tool", "license": "MIT"})
    monkeypatch.setattr(gh, "read_readme", lambda repo: {"content": "Read repository documentation."})
    monkeypatch.setattr(gh, "list_files", lambda repo: {"items": []})
    out = gh.classify("owner/repo")
    assert out["mode"] == "READ_ONLY"
    assert out["local_install_required"] is False
    assert out["execution_policy"] == "REMOTE_FIRST"


def test_invalid_source_owner_route_and_refuse_install():
    with pytest.raises(ValueError): gh.register_source("owner/repo", "OTHER", "SYSTEMS_ONLY")
    with pytest.raises(ValueError): gh.register_source("owner/repo", "SYSTEMS", "SYSTEMS_ONLY", execution_mode="LOCAL_INSTALL_REQUIRED")
    with pytest.raises(ValueError): gh.fetch_snapshot("owner/repo", "../branch")


def test_cloud_monitor_prepares_compact_events_and_preserves_no_change_output(tmp_path, monkeypatch):
    source_file = tmp_path / "sources.yaml"
    state_file = tmp_path / "state.json"
    output_file = tmp_path / "changes.json"
    source_file.write_text("sources:\n  - repository: owner/repo\n    owner_engine: RESEARCH\n    routing_target: RESEARCH_THEN_OPPORTUNITIES\n    tracked_paths: [README.md]\n")
    state_file.write_text("{}\n")
    output_file.write_text('{"events":[]}\n')
    monkeypatch.setattr(cloud, "SOURCE_FILE", source_file)
    monkeypatch.setattr(cloud, "STATE_FILE", state_file)
    monkeypatch.setattr(cloud, "OUTPUT_FILE", output_file)
    commits = iter(["a"*40, "b"*40, "b"*40])
    def fake_api(path):
        if path == "/repos/owner/repo": return {"default_branch": "main"}
        if "/commits/" in path: return {"sha": next(commits), "commit": {"message": "update"}}
        return {"files": [{"filename": "README.md"}, {"filename": "untracked.txt"}]}
    monkeypatch.setattr(cloud, "api", fake_api)
    cloud.main()
    assert json.loads(output_file.read_text())["events"] == []
    cloud.main()
    payload = json.loads(output_file.read_text())
    assert payload["events"][0]["changed_paths"] == ["README.md"]
    assert payload["events"][0]["routing_target"] == "RESEARCH_THEN_OPPORTUNITIES"
    before = output_file.read_text()
    cloud.main()
    assert output_file.read_text() == before

