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
