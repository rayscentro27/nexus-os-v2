#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];t=(r/"src/lib/clydeCreditStrategyEngine.ts").read_text()+(r/"src/pages/client/WorldClassClientPortal.jsx").read_text()
for x in ("bureauComparison","differenceSummary","Use Recommended Strategy","Compare Other Options","Upload Evidence","Prepare Draft","Save for Later","Request GoClear Exception Review"):assert x in t
assert "Does this balance appear correct" not in t and "guaranteed removal" not in t
print("PASS: Clyde Strategy Cards state detected differences and safe actions")
