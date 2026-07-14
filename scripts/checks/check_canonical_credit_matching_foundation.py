#!/usr/bin/env python3
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts/credit"))
from canonical_credit_matching import build_canonical_model,detect_discrepancies,normalize_creditor,normalize_money,normalize_date,masked_reference
fixtures=json.loads((ROOT/"tests/fixtures/credit/canonical_matching_scenarios.json").read_text())
for fixture in fixtures:
    original=json.loads(json.dumps(fixture["records"]));model=build_canonical_model(fixture["records"]);grouped=any(len(c["tradeline_indices"])>1 for c in model["canonical_accounts"]);ambiguous=any(p["decision"]=="ambiguous" for p in model["pair_decisions"])
    if fixture["expected"]=="group":assert grouped,fixture["name"]
    elif fixture["expected"]=="ambiguous":assert ambiguous and not grouped,fixture["name"]
    else:assert not grouped,fixture["name"]
    assert fixture["records"]==original,"source input mutated"
    assert all(t["account_reference_masked"]=="Not available" or t["account_reference_masked"].startswith("****") for t in model["tradelines"])
    assert all(p["threshold_version"] and p["matching_engine_version"] and isinstance(p["component_scores"],dict) for p in model["pair_decisions"])
assert normalize_creditor("BANK OF AMERICA, N.A.")==normalize_creditor("B OF A")=="bank of america"
assert normalize_money("$1,234.50")==1234.5 and normalize_date("01/02/2020")=="2020-01-02" and masked_reference("XX-9911")=="****9911"
omission=next(x for x in fixtures if x["name"]=="bureau_omission");assert any(d["discrepancy_type"]=="bureau_omission" for d in detect_discrepancies(build_canonical_model(omission["records"])))
print(f"PASS: {len(fixtures)} canonical matching fixtures, normalization, preservation, masking, scores, and reasons")
