#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"credit"));from credit_analysis_exception_policy import evaluate_credit_analysis_exception as e
normal=e({"parser_confidence":"medium","extraction_success":True,"account_count":26,"ambiguous_match_count":0});assert not normal["exception_required"]
for payload,code in [({"parser_confidence":"low","account_count":2},"parser_low_confidence"),({"extraction_success":False,"account_count":0},"unreadable_report"),({"ambiguous_match_count":1,"account_count":2},"ambiguous_account_match"),({"identity_theft_asserted":True,"account_count":1},"identity_theft_indicator"),({"integrity_mismatch":True,"account_count":1},"system_integrity_failure")]:assert e(payload)["exception_code"]==code
assert not e({"parser_confidence":"high","extraction_success":True,"account_count":5,"negative_accounts":5})["exception_required"]
print("PASS: normal negative data stays automated; defined exceptions route to GoClear")
