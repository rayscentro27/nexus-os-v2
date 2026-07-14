#!/usr/bin/env python3
from pathlib import Path
import sys
text=(Path(__file__).resolve().parents[2]/'src/lib/businessFundingReadiness.ts').read_text()
terms=['evaluateBusinessFundingReadiness','completenessScore','tier1Status','tier2Status','missingRequirements','recommendedActions','upload_document','/client/documents','businessBankAccountStatus']
for t in terms: print(('PASS' if t in text else 'FAIL')+': '+t)
sys.exit(0 if all(t in text for t in terms) and 'affiliate' not in text.lower() else 1)
