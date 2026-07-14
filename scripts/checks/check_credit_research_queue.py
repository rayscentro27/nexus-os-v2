#!/usr/bin/env python3
from pathlib import Path
t=(Path(__file__).resolve().parents[2]/"scripts/research/process_credit_strategy_research_queue.py").read_text()
assert "--once" in t and "--max-items" in t and "min(a.max_items,10)" in t and '"needs_verification"' in t and '"approved"' not in t
print("PASS: bounded research queue never auto-approves")
