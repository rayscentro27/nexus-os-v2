"""Directive lifecycle -> Nova proactive event contract."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import directive_notifications as DN  # noqa: E402


def _row(events):
    return {"job_id": "job_x", "directive": {"directive_id": "job_x", "events": events}}


def _ev(kind, at="2026-11-16T05:00:00+00:00", **kw):
    return {"kind": kind, "at": at, "directive_id": "job_x", "project_id": "proj_dir_x", "department": "MARKETING",
            "status": "COMPLETE", "summary": f"{kind} happened", "next": "do next", **kw}


def test_every_kind_maps_with_required_ids_and_classification():
    evs = DN.events_from_rows([_row([_ev(k) for k in DN.DIRECTIVE_EVENT_KINDS])])
    assert [e["kind"] for e in evs] == list(DN.DIRECTIVE_EVENT_KINDS)
    for e in evs:
        for token in ("PROJECT_ID=proj_dir_x", "DIRECTIVE_ID=job_x", "DEPARTMENT=MARKETING", "STATUS=COMPLETE"):
            assert token in e["summary"]
        assert e["next"].startswith("NEXT_ACTION=") and DN.classify(e["kind"]) in {"CRITICAL", "MATERIAL"}
    assert DN.classify("APPROVAL_REQUIRED") == "CRITICAL" and DN.classify("WORK_COMPLETED") == "MATERIAL"


def test_pre_activation_events_never_sent():
    assert DN.events_from_rows([_row([_ev("WORK_COMPLETED", at="2026-11-16T03:59:59+00:00")])]) == []


def test_sources_unique_per_event_for_dedupe():
    evs = DN.events_from_rows([_row([_ev("WORK_STARTED"), _ev("WORK_STARTED", at="2026-11-16T05:01:00+00:00")])])
    assert len({e["source"] for e in evs}) == 2


def test_query_reads_only_directive_projection():
    q = DN.query()
    assert "job_type=eq.DEPARTMENT_DIRECTIVE" in q and "directive:governance_context->directive" in q and "limit=20" in q


def test_new_kinds_carry_event_id_business_and_related_ids():
    for kind in ("CREATIVE_CREATED", "CAMPAIGN_CREATED", "COMMERCE_OFFER_CREATED", "REA_WORK_STARTED", "REA_WORK_COMPLETED", "REA_WORK_FAILED"):
        assert kind in DN.DIRECTIVE_EVENT_KINDS and DN.classify(kind)
    assert DN.classify("REA_WORK_FAILED") == "CRITICAL"
    evs = DN.events_from_rows([_row([_ev("REA_WORK_STARTED", event_id="evt_abc", business_id="vnt_x", rea_job_id="job_rea"),
                                     _ev("CAMPAIGN_CREATED", event_id="evt_def", campaign_id="camp_1")])])
    assert "EVENT_ID=evt_abc" in evs[0]["summary"] and "BUSINESS_ID=vnt_x" in evs[0]["summary"] and "REA_JOB_ID=job_rea" in evs[0]["summary"]
    assert "CAMPAIGN_ID=camp_1" in evs[1]["summary"]
    assert evs[0]["source"] == "department_directive:evt_abc" != evs[1]["source"]     # dedupe key = EVENT_ID
