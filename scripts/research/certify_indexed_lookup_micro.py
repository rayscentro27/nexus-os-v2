"""Plain-Python contract certification for bounded Research case lookup.

Uses the production lookup functions with stubbed exact-state dependencies. It
never opens the production Research ledger or invokes pytest/provider code.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from research import research_case_engine as engine


ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "data/migrations/research_state_v2/hot_state_seed.json"
INDEX_PATH = ROOT / "data/migrations/research_state_v2/authoritative_production_case_index.json"
MANIFEST_PATH = ROOT / "data/migrations/research_state_v2/selective_preservation_manifest.json"


class _Remote:
    def __init__(self, status: int, rows: list[dict[str, Any]]):
        self.status = status
        self.rows = rows

    def configured(self) -> bool:
        return True

    def rest(self, method: str, path: str):
        assert method == "GET" and "memory_id" in path, "lookup must be exact-ID indexed"
        return self.status, self.rows


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> dict[str, str]:
    results: dict[str, str] = {}
    original_supabase = engine.research_memory.supabase
    original_hydrate = engine.research_memory.hydrate_memory
    original_read_records = engine.persistence.read_records
    original_collection_path = engine.persistence.collection_path
    original_emit = engine._emit_current_state_lookup_unavailable
    try:
        # A full-ledger persistence read is a hard failure for both control reads.
        def fail_full_read(*_args, **_kwargs):
            raise AssertionError("LEGACY_FULL_READ_ATTEMPTED")

        engine.persistence.read_records = fail_full_read
        expected = {"memory_id": "micro-case-1", "case_id": "micro-case-1", "status": "PROMISING"}
        engine.research_memory.supabase = _Remote(200, [expected])
        _check(engine.get_case_control("micro-case-1") == expected, "exact control lookup mismatch")
        results["CASE_CONTROL_EXACT_LOOKUP"] = "PASS"

        emitted: list[dict[str, Any]] = []
        engine.research_memory.supabase = None
        engine._emit_current_state_lookup_unavailable = lambda cid: emitted.append(
            {"case_id": cid, "event_id": "micro-event-1",
             "error_code": "CURRENT_STATE_LOOKUP_UNAVAILABLE"}) or emitted[-1]
        try:
            engine.get_case_control("micro-unavailable")
        except engine.CurrentStateLookupUnavailable:
            explicit = True
        else:
            explicit = False
        _check(len(emitted) == 1 and emitted[0]["error_code"] == "CURRENT_STATE_LOOKUP_UNAVAILABLE",
               "unavailable control lookup did not emit the expected event")
        _check(explicit, "unavailable control lookup did not fail explicitly")
        results["CASE_CONTROL_UNAVAILABLE_EVENT"] = "PASS"
        results["CASE_CONTROL_EXPLICIT_FAILURE"] = "PASS"
        results["CASE_CONTROL_LEGACY_SCAN"] = "NO"

        # Any implicit local/archival lookup path fails immediately.
        def fail_local_path(*_args, **_kwargs):
            raise AssertionError("IMPLICIT_ARCHIVE_SCAN")

        engine.persistence.collection_path = fail_local_path
        engine.research_memory.hydrate_memory = lambda cid: {
            "memory_id": cid, "case_id": cid, "status": "PROMISING"}
        _check(engine.get_case("micro-case-2")["case_id"] == "micro-case-2", "exact get_case lookup mismatch")
        results["GET_CASE_NORMAL_USES_EXACT_LOOKUP"] = "YES"

        engine.research_memory.hydrate_memory = lambda _cid: None
        engine._emit_current_state_lookup_unavailable = lambda cid: {
            "case_id": cid, "error_code": "CURRENT_STATE_LOOKUP_UNAVAILABLE"}
        try:
            engine.get_case("micro-unavailable-case")
        except engine.CurrentStateLookupUnavailable:
            pass
        else:
            raise AssertionError("normal get_case did not fail explicitly")
        results["GET_CASE_IMPLICIT_TAIL_FALLBACK"] = "NO"

        # Exercise only a disposable local fixture behind the explicit recovery flag.
        with tempfile.TemporaryDirectory(prefix="nexus_lookup_micro_") as temporary:
            fixture = Path(temporary) / "research_runtime_states.jsonl"
            fixture_row = {"memory_kind": "RESEARCH_CASE", "case_id": "micro-recovery",
                           "recorded_at": "2026-10-22T00:00:00Z"}
            fixture.write_text(json.dumps(fixture_row) + "\n", encoding="utf-8")
            engine.persistence.collection_path = lambda *_args, **_kwargs: fixture
            _check(engine.get_case("micro-recovery", allow_bounded_local_recovery=True) == fixture_row,
                   "explicit bounded recovery fixture lookup failed")
        results["GET_CASE_EXPLICIT_RECOVERY_FLAG_REQUIRED"] = "YES"
        results["LEGACY_FULL_READ_ATTEMPTED"] = "NO"
        results["IMPLICIT_ARCHIVE_SCAN"] = "NO"
        results["ARCHIVE_ACCESS_REQUIRES_EXPLICIT_RECOVERY_OR_AUDIT"] = "YES"

        # Certification isolation is verified from configuration/launcher only.
        cert = json.loads((ROOT / "config/certification_research_namespace.v1.json").read_text())
        launcher = (ROOT / cert["launcher"]).read_text()
        cert_root = Path(cert["state_root"]).resolve()
        _check(cert["production_writes_allowed"] is False and
               cert["production_archive_writes_allowed"] is False, "certification writes not disabled")
        _check(str(cert_root) == str((Path.home() / ".nexus/state/certification/research").resolve()),
               "unexpected certification state root")
        _check("CERTIFICATION_AND_PRODUCTION_STATE_ROOTS_OVERLAP" in launcher and
               'NEXUS_RESEARCH_STATE_ROOT="$CERTIFICATION_ROOT"' in launcher,
               "certification launcher isolation guard missing")
        results["CERTIFICATION_NAMESPACE_ISOLATED"] = "YES"

        # Validate only small seed/index/manifest artifacts.
        seed = json.loads(SEED_PATH.read_text())
        index = json.loads(INDEX_PATH.read_text())
        manifest = json.loads(MANIFEST_PATH.read_text())
        seed_cases = {case.get("case_id"): case for case in seed.get("cases", [])}
        required = {row["CASE_ID"] for row in index.get("cases", [])
                    if row.get("CLASSIFICATION") in {"ACTIVE_REAL", "BLOCKED_REAL", "DORMANT_RESUMABLE_REAL"}}
        _check(required <= set(seed_cases), "active/resumable indexed case missing from seed")
        p5 = seed_cases.get("rcase_f6c19e2c0afe9c44ea", {})
        _check(p5.get("objective_id") == "nova_research_16a764a4c75b65d81e46" and
               p5.get("project_id") == "nova_research_work_16a764a4c75b65d81e46" and
               p5.get("job_id") == "job_d27d3093c0e248a3a1481a5a45730475" and
               p5.get("case_status") == "PROMISING" and p5.get("current_turn") == 7,
               "Phase 5 seed lineage/state mismatch")
        recovery = seed.get("recovery", {})
        _check(recovery.get("incident", {}).get("event_id") == "sys_host_io_degraded_20261022_r50_001" and
               recovery.get("recovery_job", {}).get("recovery_job_id") == "sysjob_5a4c011f291d6388eae93d8c",
               "host recovery state missing from seed")
        disposable = {row.get("CASE_ID") for row in manifest.get("EXCLUDED_FROM_STATE_V2_IMPORT", [])}
        _check(len(disposable) == 5 and not (disposable & set(seed_cases)),
               "disposable certification state leaked into hot seed")
        _check(index.get("classification_counts", {}).get("UNKNOWN_REQUIRES_REVIEW") == 0,
               "unknown cases remain")
        results["HOT_STATE_SEED_CONTRACT"] = "PASS"
        return results
    finally:
        engine.research_memory.supabase = original_supabase
        engine.research_memory.hydrate_memory = original_hydrate
        engine.persistence.read_records = original_read_records
        engine.persistence.collection_path = original_collection_path
        engine._emit_current_state_lookup_unavailable = original_emit


if __name__ == "__main__":
    outcome = run()
    for key, value in outcome.items():
        print(f"{key}={value}")
    print("MICRO_CERTIFICATION=PASS")
