import importlib

from hermes import hermes_web_search


def test_search_receipt_uses_authoritative_writable_repo_root(tmp_path, monkeypatch):
    module = hermes_web_search
    try:
        with monkeypatch.context() as scoped:
            scoped.setenv("NEXUS_REPO_ROOT", str(tmp_path))
            importlib.reload(module)
            receipt = module._save_receipt("bounded fixture", "none", [], "not_configured")
            expected = tmp_path / "reports/hermes/web_search" / f"{receipt['receipt_id']}.json"
            assert expected.is_file()
            assert module.RECEIPT_DIR == str(tmp_path / "reports/hermes/web_search")
    finally:
        importlib.reload(module)
