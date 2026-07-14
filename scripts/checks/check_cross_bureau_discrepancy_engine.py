#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"credit"))
from cross_bureau_credit_comparison import normalize_cross_bureau_accounts,compare_canonical_account_across_bureaus,compare_credit_report
base={"furnisherName":"Fixture Bank","accountNumberMasked":"****4321","itemType":"revolving","confidence":"high"}
rows=[{**base,"bureau":"Experian","reportedBalance":"2450","creditLimit":"5000","dateOpened":"2020-01-01","dateReported":"2026-06-01","status":"open","paymentStatus":"current"},{**base,"bureau":"Equifax","reportedBalance":"3190","creditLimit":"4500","dateOpened":"2020-02-01","dateReported":"2026-05-01","status":"closed","paymentStatus":"late"},{**base,"bureau":"TransUnion","reportedBalance":"2450","creditLimit":"5000","dateOpened":"2020-01-01","dateReported":"2026-06-01","status":"open","paymentStatus":"current"}]
d=compare_canonical_account_across_bureaus(normalize_cross_bureau_accounts(rows)[0]);types={x["discrepancyType"] for x in d}
assert {"balance_mismatch","credit_limit_mismatch","date_opened_mismatch","last_reported_date_mismatch","account_status_mismatch","payment_status_mismatch"}<=types
assert next(x for x in d if x["discrepancyType"]=="balance_mismatch")["exactDifference"]==740
assert all(not x["clientConfirmationRequired"] for x in d)
fixture={"accounts":rows+[{**base,"bureau":"Experian","accountNumberMasked":"****9999","reportedBalance":"2450","dateOpened":"2020-01-01"},{**base,"bureau":"Equifax","furnisherName":"Omission Bank","accountNumberMasked":"****7777","reportedBalance":"90","dateOpened":"2022-01-01"},{**base,"bureau":"TransUnion","furnisherName":"Omission Bank","accountNumberMasked":"****7777","reportedBalance":"90","dateOpened":"2022-01-01"}],"inquiries":[{"bureau":"Experian","company":"Sample Lender","date":"2026-06-01","confidence":"high"},{"bureau":"Equifax","company":"Sample Lender","date":"2026-06-01","confidence":"high"}]}
all_types={x["discrepancyType"] for x in compare_credit_report(fixture)["discrepancies"]}
assert {"duplicate_possible","bureau_omission","inquiry_mismatch"}<=all_types
print("PASS: objective numeric/date/status discrepancies and exact difference")
