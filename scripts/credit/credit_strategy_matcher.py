#!/usr/bin/env python3
"""Match objective discrepancies only to reusable approved strategy definitions."""
from typing import Any
CATALOG={"cross_bureau_balance_review":("cross_bureau_balance_review",1,"Cross-Bureau Balance Review",["balance_review_draft","evidence_checklist"]),"cross_bureau_date_review":("cross_bureau_date_review",1,"Cross-Bureau Date Review",["date_accuracy_review_draft"]),"cross_bureau_status_review":("cross_bureau_status_review",1,"Cross-Bureau Status Review",["status_review_draft"]),"incorrect_payment_status_review":("incorrect_payment_status_review",1,"Incorrect Payment Status Review",["payment_status_review_draft"]),"incorrect_limit_review":("incorrect_limit_review",1,"Incorrect Limit/High-Limit Review",["limit_review_draft"]),"account_ownership_review":("account_ownership_review",1,"Account Ownership Review",[]),"purchased_debt_documentation":("purchased_debt_documentation",1,"Purchased Debt Documentation Review",["ownership_documentation_request"]),"bureau_omission_review":("bureau_omission_review",1,"Bureau Omission Review",[]),"duplicate_account_review":("duplicate_account_review",1,"Duplicate Account Review",["duplicate_review_draft"]),"unauthorized_inquiry":("unauthorized_inquiry_review",1,"Unauthorized Inquiry Review",["inquiry_review_draft"])}
def match_credit_strategies(comparison:dict[str,Any],approved_versions:list[dict[str,Any]]|None=None)->list[dict[str,Any]]:
    approved={(x["strategy_id"],int(x["version"])) for x in (approved_versions or []) if x.get("approval_state")=="approved"}
    out=[]; accounts={a["canonicalAccountId"]:a for a in comparison.get("canonicalAccounts",[])}
    for d in comparison.get("discrepancies",[]):
        strategies=[CATALOG[x] for x in d.get("possibleStrategyCategories",[]) if x in CATALOG and (approved_versions is None or (CATALOG[x][0],CATALOG[x][1]) in approved)]
        if d.get("confidence")=="low" or d.get("specialistExceptionRequired"):continue
        if not strategies:continue
        primary=strategies[0]; account=accounts.get(d["canonicalAccountId"],{})
        out.append({"recommendationId":f"rec_{d['discrepancyId']}_{primary[0]}","canonicalAccountId":d["canonicalAccountId"],"discrepancyId":d["discrepancyId"],"strategyId":primary[0],"strategyVersion":primary[1],"primaryStrategy":primary[2],"alternativeStrategies":[x[2] for x in strategies[1:]],"clientConfirmationQuestions":[],"requiredEvidence":["Relevant report pages and supporting records"],"availableTools":primary[3],"confidence":d["confidence"],"specialistException":bool(d.get("specialistExceptionRequired") or account.get("matchConfidence")=="low"),"rationale":"Objective report discrepancy matched to an approved reusable strategy; no client comparison question is required.","discrepancy":d})
    return out
