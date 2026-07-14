#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]; text=(root/'scripts/credit/parse_uploaded_credit_report.py').read_text(); diag=(root/'scripts/credit/check_credit_worker_environment.py').read_text()
checks={'diagnostic exists':bool(diag),'certifi CA context':'certifi.where()' in text and 'ssl.create_default_context' in text,'SSL verification not disabled':'CERT_NONE' not in text and 'verify=False' not in text,'expected project ref':'iqjwgpnujbeoyaeuwehj' in diag,'no secret output':'SERVICE_ROLE_KEY})' not in diag and 'print(service' not in diag.lower()}
for n,v in checks.items(): print(('PASS' if v else 'FAIL')+': '+n)
sys.exit(0 if all(checks.values()) else 1)
