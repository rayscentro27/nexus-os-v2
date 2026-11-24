"""Durable dispatcher bounded scan (2026-11-13 repair).

The Research parent watchdog and the dispatch candidate scan read scalar
projections instead of full governance_context rows, so a busy queue can no
longer exhaust the 2 MB per-run response budget. Decisions must be identical
to the full-row path, and an exhausted budget yields a bounded receipt rather
than a traceback crash loop.
"""
from __future__ import annotations

import io
import json
import shutil
from contextlib import redirect_stdout

import pytest

from nexus_agent_platform import durable_jobs as dj
from nexus_agent_platform import research_parent_workflow as rpw
from nexus_agent_platform.research_parent_workflow import create_continuation_job, new_parent


class IndexedStore(dj.DurableJobStore):
    """Local store exposing the same projection methods as SupabaseJobStore."""

    def list_research_parent_index(self, limit: int = 500):
        self.index_calls = getattr(self, "index_calls", 0) + 1
        rows = []
        for job in self.list_research_parent_jobs_raw(limit):
            ctx = job.governance_context or {}
            ps = ctx.get("research_parent_state")
            get = (lambda key: ps.get(key)) if isinstance(ps, dict) else (lambda key: None)
            text = lambda value: None if value is None else str(value)
            rows.append({"job_id": job.job_id, "state": job.state, "created_at": job.created_at,
                         "objective_id": text(get("objective_id")),
                         "ctx_objective_id": text(ctx.get("research_parent_objective_id")),
                         "continuation_sequence": text(get("continuation_sequence")),
                         "parent_status": text(get("status")),
                         "terminal_condition": text(get("terminal_condition"))})
        return rows

    def list_research_parent_jobs_raw(self, limit):
        with self._connect() as db:
            rows = db.execute("SELECT * FROM jobs WHERE department='RESEARCH' AND job_type='RESEARCH_INTAKE' "
                              "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._job(row) for row in rows]

    def get_many(self, job_ids, *, chunk: int = 20):
        self.full_fetched = getattr(self, "full_fetched", 0) + len(job_ids)
        return [job for job in (self.get(job_id) for job_id in job_ids) if job is not None]

    def list_research_parent_jobs(self, limit: int = 500):
        raise AssertionError("bounded path must not read every full parent row")


def _parent(store, objective_id, *, status="IN_PROGRESS", job_state="BLOCKED", dict_state=True):
    state = new_parent(objective_id=objective_id, original_objective=f"objective {objective_id}")
    job = create_continuation_job(store, state=state, parent_job_id=None, payload_ref=f"work:{objective_id}")
    if status != "IN_PROGRESS":
        ctx = dict(job.governance_context)
        ctx["research_parent_state"] = {**ctx["research_parent_state"], "status": status}
        store.set_governance_context(job.job_id, ctx)
    if not dict_state:
        ctx = dict(job.governance_context)
        ctx["research_parent_state"] = "not-a-dict"
        store.set_governance_context(job.job_id, ctx)
    if job_state != "READY":
        store.transition(job.job_id, job_state, error_code="TEST")
    return job


def _seed(path):
    store = dj.DurableJobStore(path)
    _parent(store, "complete", status="COMPLETE")            # skipped: latest COMPLETE
    _parent(store, "active", job_state="READY")              # skipped: child active
    _parent(store, "orphan")                                 # recovered: new child
    _parent(store, "nondict", dict_state=False)              # unprovable -> full path decides
    return store


def _snapshot(path):
    with dj.DurableJobStore(path)._connect() as db:
        rows = db.execute("SELECT idempotency_key,state,parent_job_id IS NOT NULL p FROM jobs").fetchall()
    return sorted((r[0], r[1], r[2]) for r in rows)


def test_bounded_parent_scan_matches_full_scan(tmp_path):
    full_db, bounded_db = tmp_path / "full.sqlite3", tmp_path / "bounded.sqlite3"
    _seed(full_db)
    shutil.copyfile(full_db, bounded_db)

    full = rpw.recover_orphaned_parents(dj.DurableJobStore(full_db))
    bounded_store = IndexedStore(bounded_db)
    bounded = rpw.recover_orphaned_parents(bounded_store)

    assert _snapshot(full_db) == _snapshot(bounded_db)        # identical durable mutations
    assert bounded["recovered"] == full["recovered"] == 1
    assert bounded["indexed_rows"] == 4 and bounded["scanned"] == bounded["indexed_groups"] == 4
    # Only the orphaned group and the group whose parent state cannot be proven
    # from projections are read in full; COMPLETE and active groups are not.
    assert bounded_store.full_fetched == 2 and bounded["full_rows_fetched"] == 2


def test_full_row_fetch_is_capped_and_rotates(tmp_path, monkeypatch):
    store = IndexedStore(tmp_path / "q.sqlite3")
    for n in range(6):
        _parent(store, f"orphan{n}")
    monkeypatch.setattr(rpw.time, "time", lambda: 0.0)
    jobs, info = rpw._bounded_parent_rows(store, store.list_research_parent_index(), max_full_rows=2)
    assert len(jobs) == 2 and info["groups_deferred"] == 4
    monkeypatch.setattr(rpw.time, "time", lambda: 30.0 * 3)
    later, _ = rpw._bounded_parent_rows(store, store.list_research_parent_index(), max_full_rows=2)
    assert {j.job_id for j in later} != {j.job_id for j in jobs}  # deferred groups are reached later


def test_dispatch_uses_projection_scan_and_reports_counters(tmp_path):
    class Store(IndexedStore):
        def list_ready_index(self, limit=50):
            self.index_ready = True
            return dj.DurableJobStore.list_ready(self, limit)

        def count_ready(self, limit=100):
            return len(dj.DurableJobStore.list_ready(self, limit))

        def list_ready(self, limit=20):
            raise AssertionError("dispatch must not read full ready rows")

    store = Store(tmp_path / "d.sqlite3")
    job = store.enqueue("SYSTEMS", "SYSTEMS_INTERNAL_CANARY", payload_ref="a", governance_context={"source": "CERTIFICATION"})
    store.enqueue("SYSTEMS", "SYSTEMS_INTERNAL_CANARY", payload_ref="b", governance_context={"source": "OTHER"})
    result = dj.dispatch_once(store, launch=False, worker_id="w1", allowed_job_sources={"CERTIFICATION"})
    assert store.index_ready
    assert result["scanned"] == 2 and result["claimable"] == 1 and result["started"] == 1
    assert store.get(job.job_id).state == "RUNNING"            # same durable job id, claimed once
    again = dj.dispatch_once(store, launch=False, worker_id="w2", allowed_job_sources={"CERTIFICATION"})
    assert again["started"] == 0                               # no duplicate claim


def test_budget_exhaustion_writes_bounded_receipt_not_crash(monkeypatch):
    from nexus_agent_platform import dispatcher_once
    from nexus_agent_platform.supabase_egress_guard import JobEgressBudgetExceeded

    class Exhausted:
        def recover_expired(self):
            raise JobEgressBudgetExceeded("JOB_EGRESS_BUDGET_EXCEEDED:test")

    monkeypatch.setattr(dispatcher_once, "default_store", lambda: Exhausted())
    out = io.StringIO()
    with redirect_stdout(out):
        code = dispatcher_once.main()
    receipt = json.loads(out.getvalue())
    assert code == 0
    assert receipt["status"] == "BUDGET_EXHAUSTED" and receipt["stage"] == "recover_expired"
    assert receipt["budget"] == {"max_requests": 120, "max_response_bytes": 2_000_000}
