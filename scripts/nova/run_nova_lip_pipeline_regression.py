#!/usr/bin/env python3
"""Exercise the locked Nova lip Candidate B path on the raw regression fixture."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.nova.nova_lip_color_pipeline import ROOT, apply_candidate_b, assert_lip_regression_guard

RAW_FIXTURE=ROOT/"artifacts/nova/identity-preservation/nova_lip_identity_canary_raw.mp4"
OUT=ROOT/"artifacts/nova/lip-color-correction/lip_pipeline_lock_regression.json"


def main() -> dict:
    with tempfile.TemporaryDirectory(prefix="nova-lip-b-regression-") as work:
        video=Path(work)/"nova-lip-b-regression.mp4"
        receipt=apply_candidate_b(RAW_FIXTURE,video)
        assert_lip_regression_guard(receipt)
        report={"schema_version":"nexus.nova.lip-pipeline-regression.v1",
                "created_at":datetime.now(timezone.utc).isoformat(),"status":"PASS",
                "fixture":str(RAW_FIXTURE.relative_to(ROOT)),"output_was_temporary":True,
                "receipt":receipt}
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report


if __name__=="__main__":
    print(json.dumps(main(),indent=2))
