import ipaddress
import json
import time
from pathlib import Path

from scripts.nexus_agent_platform.evidence_ingestion import (
    build_job_envelope, ingest_file, ingest_url, material_hash, normalize_text, validate_public_url,
)


def fixture_converter(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def paths(tmp_path):
    root = tmp_path / "runtime"
    return root, root / "receipts", root / "intake.jsonl"


def test_markitdown_conversion_provenance_hashes_and_duplicate(tmp_path):
    root, receipts, handoff = paths(tmp_path); fixture = root / "fixtures" / "sample.txt"
    fixture.parent.mkdir(parents=True); fixture.write_text("# Hello\r\nStable evidence\n", encoding="utf-8")
    first = ingest_file(str(fixture), allowed_roots=[fixture.parent], root=root, receipt_dir=receipts, handoff=handoff, converter=fixture_converter)
    second = ingest_file(str(fixture), allowed_roots=[fixture.parent], root=root, receipt_dir=receipts, handoff=handoff, converter=fixture_converter)
    assert first["status"] == "SUCCESS"; assert second["status"] == "DUPLICATE"
    assert first["integrity"]["source_hash"] == second["integrity"]["source_hash"]
    assert first["integrity"]["material_hash"] == second["integrity"]["material_hash"]
    assert first["source"]["provenance"]["path_scope"] == "approved_local_intake"
    assert json.loads(Path(first["receipt_ref"]).read_text())["evidence_id"] == first["evidence_id"]
    handoff_event = json.loads(handoff.read_text(encoding="utf-8").splitlines()[0])
    assert handoff_event["event_type"] == "evidence_ingestion_completed"
    assert handoff_event["artifact_ref"] == first["artifact_ref"]


def test_real_material_change_gets_new_hash(tmp_path):
    root, receipts, handoff = paths(tmp_path); fixture = root / "fixtures" / "changed.md"
    fixture.parent.mkdir(parents=True); fixture.write_text("alpha", encoding="utf-8")
    first = ingest_file(str(fixture), allowed_roots=[fixture.parent], root=root, receipt_dir=receipts, handoff=handoff, converter=fixture_converter)
    fixture.write_text("beta", encoding="utf-8")
    second = ingest_file(str(fixture), allowed_roots=[fixture.parent], root=root, receipt_dir=receipts, handoff=handoff, converter=fixture_converter)
    assert first["integrity"]["material_hash"] != second["integrity"]["material_hash"]
    assert second["status"] == "SUCCESS"


def test_path_format_size_and_sensitive_path_guards(tmp_path):
    root, receipts, handoff = paths(tmp_path); fixture = root / "fixtures" / "bad.bin"; fixture.parent.mkdir(parents=True); fixture.write_bytes(b"x")
    assert ingest_file(str(fixture), allowed_roots=[fixture.parent], root=root, receipt_dir=receipts, handoff=handoff, converter=fixture_converter)["status"] == "UNSUPPORTED_FORMAT"
    secret = root / "fixtures" / ".env"; secret.write_text("TOKEN=secret", encoding="utf-8")
    assert ingest_file(str(secret), allowed_roots=[secret.parent], root=root, receipt_dir=receipts, handoff=handoff, converter=fixture_converter)["status"] == "BLOCKED_PATH"
    large = root / "fixtures" / "large.txt"; large.write_text("x", encoding="utf-8")
    assert ingest_file(str(large), allowed_roots=[large.parent], root=root, receipt_dir=receipts, handoff=handoff, max_bytes=0, converter=fixture_converter)["status"] == "SOURCE_TOO_LARGE"


def test_timeout_and_empty_result_are_safe(tmp_path):
    root, receipts, handoff = paths(tmp_path); fixture = root / "fixtures" / "slow.txt"; fixture.parent.mkdir(parents=True); fixture.write_text("x", encoding="utf-8")
    def slow(_): time.sleep(0.2); return "x"
    assert ingest_file(str(fixture), allowed_roots=[fixture.parent], root=root, receipt_dir=receipts, handoff=handoff, timeout_seconds=1, converter=slow)["status"] == "SUCCESS"
    assert ingest_file(str(fixture), allowed_roots=[fixture.parent], root=root, receipt_dir=receipts, handoff=handoff, timeout_seconds=1, converter=lambda _: "")["status"] == "CONTENT_EMPTY"


def test_url_scheme_ssrf_and_redirect_guards():
    assert validate_public_url("file:///etc/passwd")[1]
    assert validate_public_url("http://127.0.0.1")[1]
    assert validate_public_url("http://169.254.169.254/latest/meta-data")[1]
    assert validate_public_url("http://10.0.0.1")[1]
    public, reason = validate_public_url("https://example.com", resolve_host=lambda _: [ipaddress.ip_address("93.184.216.34")])
    assert public == "https://example.com" and reason is None


def test_crawl_contract_hashes_duplicates_and_private_redirect(tmp_path):
    root, receipts, handoff = paths(tmp_path)
    def crawler(url, _timeout): return {"success": True, "status_code": 200, "final_url": url, "title": "Fixture", "markdown": "# stable\ncontent", "html": "<h1>stable</h1><p>content</p>"}
    first = ingest_url("https://example.com", root=root, receipt_dir=receipts, handoff=handoff, crawler=crawler)
    second = ingest_url("https://example.com", root=root, receipt_dir=receipts, handoff=handoff, crawler=crawler)
    assert first["status"] == "SUCCESS" and second["status"] == "DUPLICATE"
    assert first["integrity"]["material_hash"] == second["integrity"]["material_hash"]
    def private_redirect(url, _timeout): return {"success": True, "final_url": "http://127.0.0.1:8080", "markdown": "bad", "html": "bad"}
    assert ingest_url("https://example.com", root=root, receipt_dir=receipts, handoff=handoff, crawler=private_redirect)["status"] == "REDIRECT_BLOCKED"


def test_crawl_response_size_is_bounded(tmp_path):
    root, receipts, handoff = paths(tmp_path)
    def oversized(url, _timeout):
        return {"success": True, "status_code": 200, "final_url": url, "markdown": "ok", "html": "x" * (8 * 1024 * 1024 + 1)}
    result = ingest_url("https://example.com", root=root, receipt_dir=receipts, handoff=handoff, crawler=oversized)
    assert result["status"] == "SOURCE_TOO_LARGE"


def test_contract_is_serializable_and_normalization_ignores_volatile_metadata():
    assert normalize_text(" a\r\n b  \n") == " a\n b"
    assert material_hash("same\n") == material_hash("same\r\n")
    envelope = build_job_envelope(adapter="markitdown", source={"source_type": "local_file", "original_reference": "fixture.txt"}, tenant_context={"tenant_id": "tenant-test", "scope": "test"})
    assert json.dumps(envelope)
    assert envelope["tenant_context"]["tenant_id"] == "tenant-test"
    assert envelope["capability"] == "evidence_ingestion"


def test_errors_are_normalized_and_receipted(tmp_path):
    root, receipts, handoff = paths(tmp_path)
    result = ingest_url("http://127.0.0.1", root=root, receipt_dir=receipts, handoff=handoff)
    assert result["status"] == "PRIVATE_NETWORK_BLOCKED"
    assert result["error"]["classification"] == "PRIVATE_NETWORK_BLOCKED"
    assert Path(result["receipt_ref"]).exists()
    assert "token" not in json.dumps(result).lower()
