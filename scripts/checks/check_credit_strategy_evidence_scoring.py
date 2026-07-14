#!/usr/bin/env python3
from pathlib import Path
t=(Path(__file__).resolve().parents[2]/"src/lib/creditStrategyEvidenceScoring.ts").read_text()
for x in ("officialAuthoritySupport","statutorySupport","practitionerEvidence","deceptiveWordingRisk","conditional_review","reject"):assert x in t
assert "views" not in t.lower() and "testimonials" not in t.lower()
print("PASS: evidence and deceptive-wording scoring")
