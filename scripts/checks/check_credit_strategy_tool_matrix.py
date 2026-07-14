#!/usr/bin/env python3
from pathlib import Path
t=(Path(__file__).resolve().parents[2]/"src/lib/creditStrategyToolMatrix.ts").read_text()
assert "high_utilization:{tools:['utilization_plan'],draftAllowed:false" in t
assert "business_profile_gap:{tools:['business_setup_checklist'],draftAllowed:false" in t
assert "clientAuthorizationRequired:true" in t and "docuPostAutomatic:false" in t
print("PASS: strategy-specific tools retain draft and mailing gates")
