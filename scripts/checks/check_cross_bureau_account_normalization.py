#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"credit"))
from cross_bureau_credit_comparison import normalize_cross_bureau_accounts
a=lambda b,n,bal:{"bureau":b,"furnisherName":"Example Bank","accountNumberMasked":n,"itemType":"revolving","dateOpened":"2020-01-01","reportedBalance":bal,"confidence":"high"}
groups=normalize_cross_bureau_accounts([a("Experian","****1234","100"),a("Equifax","XX1234","120"),a("TransUnion","****9999","100")])
assert len(groups)==2 and len(groups[0]["bureauRecords"])==2, "must merge supported matches but not similar-name unrelated suffixes"
assert all("Not available"==g["maskedAccountReference"] or len(g["maskedAccountReference"])<=12 for g in groups)
print("PASS: conservative canonical account normalization")
