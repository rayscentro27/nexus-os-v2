from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "alpha"))

import alpha_live_research as alpha


def test_research_direct_supabase_persistence_is_disabled(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "must-not-be-used")
    monkeypatch.setattr(alpha, "http_json", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network call")))
    assert alpha.supabase_headers() == {}
    assert alpha.supabase_insert("nexus_research_results", {"id": "placeholder"}) == (
        False,
        "durable_job_backend_required",
        None,
    )
