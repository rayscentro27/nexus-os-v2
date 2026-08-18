import json

from nexus_agent_platform.pilot.run_end_to_end_pilot import run


def test_phase9_pilot_records_measurable_partial_result():
    report = run()
    assert report["opportunity"]["id"] == "unclecode_crawl4ai"
    assert report["opportunity"]["status"] == "PILOT_PROPOSED"
    assert report["creative"]["territory_count"] == 3
    assert report["real_worker_status"] == "BLOCKED"
    assert report["worker_used"] == "local_python"
    assert report["verification_status"] == "PASS"
    assert report["tokens"] == {
        "input": 0,
        "output": 0,
        "provider_cost_usd": 0.0,
        "t1_calls": 0,
        "t2_calls": 0,
        "t3_calls": 0,
        "zero_token_operations": 9,
        "local_compute_executions": 1,
    }
    ledger = report["ledger"]
    assert ledger["task_id"] == report["creative"]["build_spec"]["task_id"]
    assert ledger["retry_count"] <= 1
    assert "src/client-v2/" in ledger["verification"].get("protected_paths", []) or report["protected_paths"] == "PASS"
    json.loads((__import__("pathlib").Path("reports/hermes_modernization/end_to_end_pilot.json")).read_text())
