#!/usr/bin/env python3
from pathlib import Path
import sys
text=(Path(__file__).resolve().parents[2]/'src/components/CreditSpecialistWorkbench.jsx').read_text()
terms=['Nexus performs the first-pass','Funding-impact items','Utilization actions','GoClear exceptions','Confirm Recommendation','Edit','Reject','Request Client Evidence','Prepare Draft Letter','recommendationDecisions[item.id]']
for t in terms: print(('PASS' if t in text else 'FAIL')+': '+t)
sys.exit(0 if all(t in text for t in terms) else 1)
