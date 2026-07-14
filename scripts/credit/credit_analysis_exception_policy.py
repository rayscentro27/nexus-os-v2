#!/usr/bin/env python3
"""Exception-only routing policy; negative tradelines are normal input, not exceptions."""
from typing import Any
def evaluate_credit_analysis_exception(data:dict[str,Any])->dict[str,Any]:
    def hit(code,reason,action,confidence="high"):return {"exception_required":True,"exception_code":code,"reason":reason,"confidence":confidence,"recommended_next_action":action}
    if data.get("admin_requested"):return hit("admin_requested_review","An authorized admin explicitly requested review.","Open the GoClear exception record.")
    if data.get("identity_theft_asserted"):return hit("identity_theft_indicator","Identity theft was asserted and requires a protected specialist workflow.","Route to identity-theft support; do not infer facts.")
    if data.get("complaint_or_legal_threat"):return hit("client_complaint_or_legal_threat","Complaint or legal-threat language requires specialist handling.","Pause automation and route to GoClear.")
    if data.get("integrity_mismatch"):return hit("system_integrity_failure","Saved counts or relationships do not match verified output.","Stop client actions and inspect integrity.")
    if data.get("extraction_success") is False:return hit("unreadable_report","The report could not be extracted reliably.","Request a readable report or retry extraction.")
    if data.get("generation_failed"):return hit("generation_failure","Canonical generation failed after parsing.","Retry safely, then escalate if attempts are exhausted.")
    if int(data.get("ambiguous_match_count") or 0)>0:return hit("ambiguous_account_match",f"{data['ambiguous_match_count']} account match candidate(s) are below the merge threshold.","Review only ambiguous candidates.","medium")
    if data.get("parser_confidence")=="low":return hit("parser_low_confidence","Parser confidence is below the automatic-processing threshold.","Review extraction quality.","medium")
    if data.get("unsupported_override"):return hit("unsupported_manual_override","A manual override is unsupported by current rules.","Require an authorized documented decision.")
    if int(data.get("account_count") or 0)==0:return hit("missing_source_structure","No usable tradeline structure was found.","Confirm format or request another report.","medium")
    return {"exception_required":False,"exception_code":"none","reason":"Normal report processing completed without a defined exception.","confidence":"high","recommended_next_action":"Continue automated readiness processing."}
