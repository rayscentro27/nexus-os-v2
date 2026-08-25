from pathlib import Path

from scripts.checks.check_frontend_build_hermeticity import scan


def test_current_frontend_has_no_forbidden_runtime_imports():
    result = scan(Path(__file__).resolve().parents[3])
    assert result["status"] == "PASS", result
    assert result["forbidden"] == []


def test_guard_rejects_forbidden_runtime_import(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "fixture.ts").write_text(
        "import state from '../data/runtime/nexus_loops/loop_state.json';\n",
        encoding="utf-8",
    )
    result = scan(tmp_path)
    assert result["status"] == "FAIL"
    assert result["forbidden"][0]["rule"] == "data/runtime/"


def test_guard_allows_safe_tracked_style_import(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "fixture.ts").write_text(
        "import snapshot from '../public/runtime/hermes-current.json';\n",
        encoding="utf-8",
    )
    result = scan(tmp_path)
    assert result["status"] == "PASS"
