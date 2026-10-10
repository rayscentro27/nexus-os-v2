from scripts.ops import nexus_runtime_env


def test_runtime_env_loader_filters_sensitive_values_by_caller_allowlist(tmp_path, monkeypatch):
    env_file = tmp_path / "runtime.env"
    env_file.write_text("OPENROUTER_API_KEY=sensitive-model\nNEXUS_DEPARTMENT=research\nTELEGRAM_BOT_TOKEN=sensitive-bot\n")
    loaded = nexus_runtime_env.parse_env_file(env_file, allowed_sensitive_keys={"OPENROUTER_API_KEY"})
    assert loaded == {"OPENROUTER_API_KEY": "sensitive-model", "NEXUS_DEPARTMENT": "research"}
    assert "TELEGRAM_BOT_TOKEN" not in loaded


def test_runtime_env_loader_defaults_to_no_sensitive_keys(tmp_path):
    env_file = tmp_path / "runtime.env"
    env_file.write_text("SERVICE_PASSWORD=secret\nNEXUS_DEPARTMENT=research\n")
    assert nexus_runtime_env.parse_env_file(env_file) == {"NEXUS_DEPARTMENT": "research"}


def test_runtime_env_loader_does_not_load_service_role_for_unlisted_caller(tmp_path, monkeypatch):
    env_file = tmp_path / "runtime.env"
    env_file.write_text("SUPABASE_SERVICE_ROLE_KEY=private\nNEXUS_JOB_TYPE=RESEARCH\n")
    monkeypatch.setattr(nexus_runtime_env, "CANONICAL_RUNTIME_ENV", env_file)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    loaded = nexus_runtime_env.load_runtime_env(override=True)
    assert "SUPABASE_SERVICE_ROLE_KEY" not in loaded
    assert "SUPABASE_SERVICE_ROLE_KEY" not in __import__("os").environ
