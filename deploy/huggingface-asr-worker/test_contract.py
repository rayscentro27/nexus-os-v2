from pathlib import Path


ROOT = Path(__file__).parent


def test_worker_artifacts_exist():
    assert (ROOT / "app.py").is_file()
    assert (ROOT / "Dockerfile").is_file()
    assert (ROOT / "requirements.txt").is_file()


def test_no_secret_literals():
    source = (ROOT / "app.py").read_text()
    assert "SUPABASE_SERVICE_ROLE_KEY" not in source
    assert "NEXUS_WORKER_TOKEN=" not in source
