#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];w=(r/"src/components/CreditSpecialistWorkbench.jsx").read_text();p=(r/"scripts/credit/parse_uploaded_credit_report.py").read_text()
for x in ("Low-confidence exceptions","Research awaiting approval","Client selections","exception_required","client_choice_pending"):assert x in w+p
assert '"client_visible": not match["specialistException"]' in p
print("PASS: ordinary strategies automate; exceptions route to GoClear")
