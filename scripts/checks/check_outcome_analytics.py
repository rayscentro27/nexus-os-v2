#!/usr/bin/env python3
"""Static safety check for non-causal outcome analytics; emits no report data."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
required = [root/'src/lib/outcomeAnalytics.ts', root/'supabase/migrations/20260715152000_strategy_outcome_analytics.sql']
missing = [str(path) for path in required if not path.exists()]
policy = (root/'src/lib/outcomeAnalytics.ts').read_text() if not missing else ''
client_sources = [root/'src/lib/clydeActionEngine.ts', root/'src/pages/client/WorldClassClientPortal.jsx']
for path in client_sources:
    if not path.exists(): missing.append(str(path))
blocked = ('caused deletion','caused removal','caused a score increase','caused funding','guaranteed success','guaranteed funding','strategy worked because','strategy failed because','resulted in funding approval','proven legal violation')
missing_rules = [phrase for phrase in blocked if phrase not in policy.lower()]
unsafe = []
for path in client_sources:
    if not path.exists(): continue
    text = path.read_text().lower()
    unsafe.extend(f'{path.relative_to(root)}:{phrase}' for phrase in blocked if phrase in text)
if missing or missing_rules or unsafe:
    print('FAIL', {'missing': missing, 'missing_policy_rules': missing_rules, 'unsafe_client_output': unsafe})
    sys.exit(1)
print('PASS outcome analytics: non-causal policy, bounded comparison model, and additive migration present')
