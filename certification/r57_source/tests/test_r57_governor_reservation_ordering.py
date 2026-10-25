from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "supabase/migrations/20261025150000_nexus_governor_reservation_ordering_fix.sql"
PREDECESSOR = ROOT / "certification/r57_source/predecessor/20261022120000_fix_resource_governor_jsonb_threshold.sql"


def _psql(sql: str) -> str:
    command = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-Atq", "-c", sql]
    return subprocess.run(command, check=True, capture_output=True, text=True, env=os.environ).stdout.strip()


def _reset(limit: int = 2) -> None:
    _psql("TRUNCATE public.nexus_resource_incidents, public.nexus_resource_reservations, public.nexus_resource_policies")
    _psql(
        "INSERT INTO public.nexus_resource_policies(provider,service,job_type,budget_period,"
        "autonomous_usage_allowed,autonomous_spend_allowed,hard_limits,concurrency_limit,state,approval_required) "
        f"VALUES('SUPABASE','*','*','DAILY',true,true,'{{}}'::jsonb,{limit},'NORMAL',false)"
    )


def _seed(job: str, *, status: str = "ACTIVE", expires: str = "1 hour") -> None:
    _psql(
        "INSERT INTO public.nexus_resource_reservations"
        "(reservation_id,idempotency_key,provider,service,job_type,budget_period,job_id,estimate,status,expires_at) "
        f"VALUES('r_{job}','idem_{job}','SUPABASE','durable_worker','RESEARCH_GAP_VERIFY','DAILY',"
        f"'{job}','{{}}'::jsonb,'{status}',now()+interval '{expires}')"
    )


def _reserve(job: str, *, service: str = "durable_worker", job_type: str = "RESEARCH_GAP_VERIFY", estimate: dict | None = None) -> dict:
    estimate_sql = json.dumps(estimate or {}).replace("'", "''")
    raw = _psql(
        "SELECT public.nexus_reserve_resource_budget_v2("
        f"'SUPABASE','{service}','{job_type}','DAILY','{job}','{estimate_sql}'::jsonb,'r57-test')::text"
    )
    return json.loads(raw)


def _count(where: str = "status='ACTIVE'") -> int:
    return int(_psql(f"SELECT count(*) FROM public.nexus_resource_reservations WHERE provider='SUPABASE' AND {where}"))


def test_migration_reconciles_expired_rows_before_fresh_count_and_preserves_policy():
    old = PREDECESSOR.read_text()
    new = MIGRATION.read_text().removeprefix("-- R57: reconcile expired reservations before making provider-wide concurrency decisions.\n")
    old_lock = "  perform pg_advisory_xact_lock(hashtext('nexus-governor:'||upper(p_provider)||':'||p_service||':'||p_job_type||':'||p_budget_period));"
    new_lock = "  -- Serialize all reservation scopes for this provider because concurrency is provider-wide.\n  perform pg_advisory_xact_lock(hashtext('nexus-governor-concurrency'),hashtext(upper(p_provider)));"
    assert old_lock in old
    old = old.replace(old_lock, new_lock, 1)
    old_order = "  select count(*) into active_count from public.nexus_resource_reservations where provider=pol.provider and status='ACTIVE';\n  update public.nexus_resource_reservations set status='RELEASED',reconciled_at=now() where provider=pol.provider and status='ACTIVE' and expires_at<=now();"
    new_order = "  -- Expire stale rows before counting; the count drives the concurrency decision.\n  update public.nexus_resource_reservations set status='RELEASED',reconciled_at=now() where provider=pol.provider and status='ACTIVE' and expires_at<=now();\n  select count(*) into active_count from public.nexus_resource_reservations where provider=pol.provider and status='ACTIVE' and expires_at>now();"
    assert old_order in old
    assert old.replace(old_order, new_order, 1) == new
    assert hashlib.sha256(PREDECESSOR.read_bytes()).hexdigest() == os.environ["R57_PREDECESSOR_SHA256"]


def test_zero_active_grants():
    _reset()
    assert _reserve("zero")["allowed"] is True
    assert _count() == 1


def test_two_valid_active_reservations_enforce_limit():
    _reset()
    _seed("valid_a")
    _seed("valid_b")
    result = _reserve("third")
    assert result["allowed"] is False
    assert result["code"] == "CONCURRENCY_LIMIT"
    assert _count() == 2


def test_two_expired_reservations_are_released_before_count():
    _reset()
    _seed("expired_a", expires="-1 second")
    _seed("expired_b", expires="-1 second")
    result = _reserve("after_expiry")
    assert result["allowed"] is True
    assert _count() == 1
    assert _count("status='RELEASED'") == 2


def test_mixed_valid_and_expired_rows_leave_one_slot():
    _reset()
    _seed("mixed_valid")
    _seed("mixed_expired", expires="-1 second")
    assert _reserve("mixed_new")["allowed"] is True
    assert _count() == 2
    assert _count("status='RELEASED'") == 1


def test_idempotent_replay_does_not_consume_another_slot():
    _reset()
    first = _reserve("same_job")
    second = _reserve("same_job")
    assert first["allowed"] and second["allowed"]
    assert first["reservation_id"] == second["reservation_id"]
    assert second["idempotent_replay"] is True
    assert _count() == 1


def test_reconciliation_is_idempotent_for_previously_released_row():
    _reset()
    _seed("already_released", status="RELEASED", expires="-1 second")
    before = _psql("SELECT coalesce(reconciled_at::text,'') FROM public.nexus_resource_reservations WHERE job_id='already_released'")
    assert _reserve("new_after_release")["allowed"] is True
    after = _psql("SELECT coalesce(reconciled_at::text,'') FROM public.nexus_resource_reservations WHERE job_id='already_released'")
    assert before == after


def test_provider_wide_lock_prevents_concurrent_overbooking_across_scopes():
    _reset()
    for i in range(8):
        _psql(
            "INSERT INTO public.nexus_resource_policies(provider,service,job_type,budget_period,"
            "autonomous_usage_allowed,autonomous_spend_allowed,hard_limits,concurrency_limit,state,approval_required) "
            f"VALUES('SUPABASE','scope_{i}','type_{i}','DAILY',true,true,'{{}}'::jsonb,2,'NORMAL',false)"
        )
    _psql("CREATE OR REPLACE FUNCTION public.r57_test_delay_insert() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_sleep(0.2); RETURN NEW; END $$")
    _psql("CREATE TRIGGER r57_test_delay BEFORE INSERT ON public.nexus_resource_reservations FOR EACH ROW EXECUTE FUNCTION public.r57_test_delay_insert()")
    barrier = threading.Barrier(8)
    def call(i: int) -> dict:
        barrier.wait(timeout=10)
        return _reserve(f"race_{i}", service=f"scope_{i}", job_type=f"type_{i}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(call, range(8)))
    assert sum(bool(result["allowed"]) for result in results) == 2
    assert _count() == 2
    _psql("DROP TRIGGER r57_test_delay ON public.nexus_resource_reservations")


def test_policy_limits_and_guardrails_are_not_changed_by_migration():
    sql = MIGRATION.read_text()
    assert "concurrency_limit=2" not in sql
    assert "UPDATE PUBLIC.NEXUS_RESOURCE_POLICIES SET CONCURRENCY_LIMIT" not in sql.upper()
    assert "max_response_bytes" in sql
    assert "max_requests" in sql
    assert "max_estimated_cost" in sql
    assert "pol.hard_limits->'rate'" in sql
    assert "pol.hard_limits->'usage'" in sql


@pytest.mark.parametrize(("dimension", "cap", "amount"), [
    ("requests", "max_requests", 2),
    ("bytes", "max_response_bytes", 2048),
    ("cost", "max_estimated_cost", 2),
])
def test_per_job_request_byte_and_cost_limits_remain_enforced(dimension, cap, amount):
    _reset()
    result = _reserve(f"limit_{dimension}", estimate={
        dimension: amount, "job_budget": {cap: amount - 1}
    })
    assert result["allowed"] is False
    assert result["code"] == "JOB_BUDGET_LIMIT"
    assert _count() == 0
