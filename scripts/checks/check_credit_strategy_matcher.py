#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"credit"))
from credit_strategy_matcher import match_credit_strategies
d={"canonicalAccounts":[{"canonicalAccountId":"a","matchConfidence":"high"}],"discrepancies":[{"canonicalAccountId":"a","discrepancyId":"d","discrepancyType":"balance_mismatch","possibleStrategyCategories":["cross_bureau_balance_review"],"confidence":"high","specialistExceptionRequired":False}]}
m=match_credit_strategies(d);assert m and not m[0]["clientConfirmationQuestions"] and "approved reusable strategy" in m[0]["rationale"]
print("PASS: objective-first approved strategy matching")
