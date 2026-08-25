from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_product_evolution import netlify_adapter as adapter  # noqa: E402


def test_adapter_uses_lockfile_install_before_build_and_fixed_deploy():
    source = (ROOT / "scripts/nexus_product_evolution/netlify_adapter.py").read_text(encoding="utf-8")
    assert '["npm", "ci"]' in source
    assert source.index('["npm", "ci"]') < source.index('["npm", "run", "build"]')
    assert '"--prod", "--no-build"' in source
    assert "shell=True" not in source


def test_build_environment_is_secret_free_and_candidate_bound():
    env = adapter._build_environment("a" * 40)
    assert env["VITE_BUILD_COMMIT"] == "a" * 40
    assert env["VITE_NEXUS_VOICE_ENDPOINT"].startswith("https://")
    assert not any(key.endswith(("TOKEN", "SECRET", "PASSWORD", "API_KEY")) for key in env)


def test_netlify_token_is_limited_to_netlify_environment(monkeypatch):
    monkeypatch.setenv("NETLIFY_AUTH_TOKEN", "test-token")
    build = adapter._build_environment("a" * 40)
    netlify = adapter._netlify_environment()
    assert "NETLIFY_AUTH_TOKEN" not in build
    assert netlify["NETLIFY_AUTH_TOKEN"] == "test-token"
    assert "SUPABASE_SERVICE_ROLE_KEY" not in netlify
    assert "OPENAI_API_KEY" not in netlify
    assert "STRIPE_SECRET_KEY" not in netlify


def test_fixed_tool_path_supports_minimal_launchd_path(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert str(adapter.NODE_BIN) in adapter._build_environment("a" * 40)["PATH"]
    assert adapter._netlify_environment()["PATH"].split(":")[0] == str(adapter.NODE_BIN)


def test_stale_worktree_cleanup_is_qualified(monkeypatch, tmp_path):
    stale = tmp_path / "nexus-release-stale"
    stale.mkdir()
    output = f"worktree {stale}\nHEAD {'a' * 40}\ndetached\n"
    calls = []
    monkeypatch.setattr(adapter.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(adapter.subprocess, "run", lambda args, **kwargs: (calls.append(args) or type("R", (), {"returncode": 0, "stdout": output, "stderr": ""})()))
    adapter._cleanup_stale_adapter_worktrees()
    assert any(args[:3] == ["git", "worktree", "list"] for args in calls)
    assert any(args[:3] == ["git", "worktree", "remove"] for args in calls)


def test_auth_unavailable_blocks_without_deploy(monkeypatch):
    calls = []
    monkeypatch.setattr(adapter, "exact_sha_netlify_status", lambda: {"available": False})
    monkeypatch.setattr(adapter.subprocess, "run", lambda *args, **kwargs: calls.append(args[0]))
    result = adapter.deploy_exact_sha("a" * 40, adapter.TARGET)
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "NETLIFY_AUTH_UNAVAILABLE"
    assert calls == []


def test_safe_tail_redacts_credentials():
    text = adapter._safe_tail("NETLIFY_AUTH_TOKEN=secret-value\nAuthorization: Bearer abc123")
    assert "secret-value" not in text
    assert "abc123" not in text
