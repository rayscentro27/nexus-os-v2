import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts/ops/nexus_safe_git.py"
SPEC = importlib.util.spec_from_file_location("nexus_safe_git", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def test_broad_add_is_blocked():
    assert guard.check_git_argv(["add", "."])[0] is False
    assert guard.check_git_argv(["add", "-A"])[0] is False
    assert guard.check_git_argv(["add", "-u"])[0] is False


def test_destructive_operations_are_blocked_without_owner_approval():
    for args in (["clean", "-fdx"], ["reset", "--hard"], ["restore", "."]):
        assert guard.check_git_argv(list(args))[0] is False


def test_explicit_scoped_add_is_allowed():
    assert guard.check_git_argv(["add", "scripts/ops/nexus_safe_git.py"])[0] is True


def test_runtime_and_research_data_are_blocked_from_commits():
    errors = guard.validate_paths(["data/runtime/state.json", "data/research/findings.jsonl"])
    assert any("RUNTIME" in error for error in errors)
    assert any("RESEARCH_DATA" in error for error in errors)


def test_cross_subsystem_commit_is_blocked():
    errors = guard.validate_paths(["scripts/ops/tool.py", "scripts/nova/worker.py"])
    assert any("cross-subsystem" in error for error in errors)


def test_dotenv_template_is_configuration_but_local_env_is_secret():
    assert guard.classify(".env.example") == "CONFIGURATION"
    assert guard.classify(".env.local") == "SECRET_LOCAL"


def test_repository_governor_assets_share_one_commit_scope():
    paths = [
        "configs/nexus_repository_policy.yaml",
        "scripts/ops/nexus_safe_git.py",
        ".githooks/pre-commit",
        "docs/agents/NEXUS_REPOSITORY_GOVERNOR_CONTRACT.md",
        "docs/architecture/NEXUS_RUNTIME_PATH_SEPARATION_R1.md",
        "tests/ops/test_nexus_safe_git.py",
    ]
    assert {guard.subsystem(path) for path in paths} == {"REPOSITORY_GOVERNOR"}
