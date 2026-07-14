#!/usr/bin/env python3
from pathlib import Path
import sys
text=(Path(__file__).resolve().parents[2]/'src/lib/tierFundingReadinessEngine.ts').read_text(); page=(Path(__file__).resolve().parents[2]/'src/pages/client/WorldClassClientPortal.jsx').read_text()
terms=['ready_to_review','almost_ready','action_needed','insufficient_information','tier1','tier2','utilizationHigh','timeInBusiness','revenue','banking','Tier 1 / Tier 2 Funding Readiness']
for t in terms: print(('PASS' if t in text+page else 'FAIL')+': '+t)
sys.exit(0 if all(t in text+page for t in terms) and 'pre-approved' not in text.lower() else 1)
