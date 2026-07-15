#!/usr/bin/env python3
"""Failing deterministic contract check for parser-shaped synthetic fixtures."""
import sys, subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]; out=root/'/tmp' if False else Path('/tmp/nexus-auth-fixture-check')
if sys.prefix == sys.base_prefix and (root/'.venv-credit/bin/python').exists():
    raise SystemExit(subprocess.call([str(root/'.venv-credit/bin/python'),__file__]))
subprocess.run([sys.executable,str(root/'scripts/testers/generate_authenticated_credit_fixtures.py'),'--persona','a','--out',str(out)],check=True,capture_output=True)
sys.path.insert(0,str(root/'scripts/credit'))
from parse_uploaded_credit_report import extract_text_pypdf, parse_text
from canonical_credit_matching import build_canonical_model, detect_discrepancies
pdf=out/'synthetic_persona_a_initial.pdf'; text,mode,warnings=extract_text_pypdf(pdf); result=parse_text(text,pdf.name,mode,warnings)
assert len(result['accounts'])==5, len(result['accounts']); assert {a['bureau'] for a in result['accounts']}=={'experian','equifax','transunion'}
model=build_canonical_model(result['accounts']); sizes=sorted(len(a['tradeline_indices']) for a in model['canonical_accounts']); assert sizes==[1,1,3],sizes
types={x['discrepancy_type'] for x in detect_discrepancies(model)}; assert {'balance_mismatch','account_status_mismatch'}<=types,types
print('PASS parser fixture contract: 5 records, 3-bureau group sizes [1,1,3], balance/status discrepancies')
