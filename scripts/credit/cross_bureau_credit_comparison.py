#!/usr/bin/env python3
"""Deterministic, PII-minimizing three-bureau account comparison."""
from __future__ import annotations
import hashlib, re
from typing import Any

BUREAUS=("experian","equifax","transunion")
def _bureau(v:Any)->str:
    x=re.sub(r"[^a-z]","",str(v or "").lower())
    return next((b for b in BUREAUS if b in x),"other")
def _name(v:Any)->str:return re.sub(r"[^a-z0-9]","",re.sub(r"\b(inc|llc|corp|corporation|company|co)\b","",str(v or "").lower()))
def _mask(v:Any)->str:return re.sub(r"[^a-zA-Z0-9]","",str(v or ""))[-4:].lower()
def _money(v:Any):
    if v in (None,""):return None
    try:return float(re.sub(r"[^0-9.-]","",str(v)))
    except ValueError:return None
def _id(prefix:str,value:str)->str:return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()[:16]}"
def _record(a:dict[str,Any])->dict[str,Any]:
    return {"bureau":_bureau(a.get("bureau")),"balance":_money(a.get("reportedBalance") or a.get("balance")),"creditLimit":_money(a.get("creditLimit")),"highLimit":_money(a.get("highLimit") or a.get("originalBalance")),"pastDue":_money(a.get("pastDue") or a.get("pastDueAmount")),"dateOpened":a.get("dateOpened"),"lastReportedDate":a.get("dateReported") or a.get("lastReportedDate"),"accountStatus":a.get("status"),"paymentStatus":a.get("paymentStatus"),"accountNumberMasked":a.get("accountNumberMasked"),"ownership":a.get("ownership") or a.get("responsibility"),"remarks":a.get("notes"),"rawFieldConfidence":a.get("confidence") or "low"}
def normalize_cross_bureau_accounts(accounts:list[dict[str,Any]],parser_result_id:str="",document_id:str="")->list[dict[str,Any]]:
    groups=[]
    for index,a in enumerate(accounts):
        furnisher=a.get("furnisherName") or a.get("accountName") or "Unknown furnisher"; n=_name(furnisher); suffix=_mask(a.get("accountNumberMasked")); opened=a.get("dateOpened"); typ=a.get("itemType") or "other"
        found=None
        for g in groups:
            existing_suffix=_mask(g["maskedAccountReference"]); same_name=_name(g["furnisher"])==n and len(n)>=4; same_suffix=bool(suffix and existing_suffix==suffix); same_type=g["accountType"]==typ; same_date=bool(opened and any(r.get("dateOpened")==opened for r in g["bureauRecords"]))
            if suffix and existing_suffix and not same_suffix:continue
            if (same_suffix and (same_name or same_type)) or (same_name and same_type and same_date):found=g;break
        if found:found["bureauRecords"].append(_record(a));found["matchReasons"].append("masked suffix plus supporting field" if suffix else "furnisher, type, and opened date");found["matchConfidence"]="high" if suffix else "medium"
        else:groups.append({"canonicalAccountId":_id("acct",f"{n or 'unknown'}_{suffix or index}"),"furnisher":furnisher,"originalCreditor":a.get("originalCreditor"),"maskedAccountReference":a.get("accountNumberMasked") or "Not available","accountType":typ,"bureauRecords":[_record(a)],"matchConfidence":"low","matchReasons":["single record; not merged by name alone"],"unmatchedWarnings":[],"sourceParserResultId":parser_result_id,"sourceDocumentId":document_id})
    for g in groups:
        missing=[b for b in BUREAUS if b not in {r["bureau"] for r in g["bureauRecords"]}]
        if missing:g["unmatchedWarnings"].append(f"Missing {', '.join(missing)} record; omission is not a confirmed error.")
    return groups
def compare_canonical_account_across_bureaus(a:dict[str,Any])->list[dict[str,Any]]:
    result=[]; fields=(("balance","balance_mismatch"),("creditLimit","credit_limit_mismatch"),("highLimit","high_limit_mismatch"),("pastDue","past_due_mismatch"),("dateOpened","date_opened_mismatch"),("lastReportedDate","last_reported_date_mismatch"),("accountStatus","account_status_mismatch"),("paymentStatus","payment_status_mismatch"),("accountNumberMasked","account_number_fragment_mismatch"),("ownership","ownership_mismatch"))
    strategy={"balance_mismatch":["cross_bureau_balance_review"],"date_opened_mismatch":["cross_bureau_date_review"],"last_reported_date_mismatch":["cross_bureau_date_review"],"account_status_mismatch":["cross_bureau_status_review"],"payment_status_mismatch":["incorrect_payment_status_review"],"credit_limit_mismatch":["incorrect_limit_review"],"high_limit_mismatch":["incorrect_limit_review"],"ownership_mismatch":["account_ownership_review","purchased_debt_documentation"]}
    for key,typ in fields:
        rows=[r for r in a["bureauRecords"] if r.get(key) not in (None,"")]; vals={str(r[key]).lower() for r in rows}
        if len(rows)>=2 and len(vals)>1:
            nums=[r[key] for r in rows if isinstance(r[key],(int,float))]; diff=max(nums)-min(nums) if len(nums)>1 else None; summary=f"{key} differs by ${diff:,.0f} across reporting bureaus." if diff is not None else f"{key} differs across reporting bureaus."
            result.append({"discrepancyId":_id("disc",a["canonicalAccountId"]+typ),"canonicalAccountId":a["canonicalAccountId"],"discrepancyType":typ,"comparedFields":[key],"bureauValues":{r["bureau"]:r[key] for r in rows},"differenceSummary":summary,"exactDifference":diff,"confidence":"high" if all(r["rawFieldConfidence"]=="high" for r in rows) else "medium","severity":"high" if typ in ("balance_mismatch","past_due_mismatch","account_status_mismatch") else "medium","fundingImpact":"Inconsistent reporting may affect Credit Profile interpretation and funding readiness.","tier1Impact":"medium","tier2Impact":"medium","possibleStrategyCategories":strategy.get(typ,["report_item_review"]),"clientConfirmationRequired":False,"specialistExceptionRequired":a["matchConfidence"]=="low","supportingParserFields":[key,"bureau"]})
    present={r["bureau"] for r in a["bureauRecords"]}; missing=[b for b in BUREAUS if b not in present]
    if len(a["bureauRecords"])>=2 and missing:result.append({"discrepancyId":_id("disc",a["canonicalAccountId"]+"omission"),"canonicalAccountId":a["canonicalAccountId"],"discrepancyType":"bureau_omission","comparedFields":["bureau"],"bureauValues":{b:"reported" for b in present},"differenceSummary":f"No matching record parsed for {', '.join(missing)}; omission is not a confirmed error.","exactDifference":None,"confidence":a["matchConfidence"],"severity":"low","fundingImpact":"Different bureau coverage may change lender-visible information.","tier1Impact":"low","tier2Impact":"low","possibleStrategyCategories":["bureau_omission_review"],"clientConfirmationRequired":False,"specialistExceptionRequired":a["matchConfidence"]=="low","supportingParserFields":["bureau"]})
    return result
def compare_credit_report(parse_result:dict[str,Any],parser_result_id:str="",document_id:str="")->dict[str,Any]:
    accounts=normalize_cross_bureau_accounts(parse_result.get("accounts") or [],parser_result_id,document_id); discrepancies=[d for a in accounts for d in compare_canonical_account_across_bureaus(a)]
    for i,a in enumerate(accounts):
        for b in accounts[i+1:]:
            ar,br=a["bureauRecords"][0],b["bureauRecords"][0]
            if _name(a["furnisher"])==_name(b["furnisher"]) and a["accountType"]==b["accountType"] and ar.get("dateOpened") and ar.get("dateOpened")==br.get("dateOpened") and ar.get("balance") is not None and ar.get("balance")==br.get("balance"):
                discrepancies.append({"discrepancyId":_id("disc",a["canonicalAccountId"]+b["canonicalAccountId"]+"duplicate"),"canonicalAccountId":a["canonicalAccountId"],"discrepancyType":"duplicate_possible","comparedFields":["furnisher","accountType","dateOpened","balance"],"bureauValues":{"first":a["maskedAccountReference"],"second":b["maskedAccountReference"]},"differenceSummary":"Two separately grouped records share furnisher, type, opened date, and balance; duplicate review may be appropriate.","exactDifference":None,"confidence":"medium","severity":"medium","fundingImpact":"Possible duplicate reporting may overstate obligations.","tier1Impact":"medium","tier2Impact":"medium","possibleStrategyCategories":["duplicate_account_review"],"clientConfirmationRequired":True,"specialistExceptionRequired":False,"supportingParserFields":["furnisherName","itemType","dateOpened","reportedBalance"]})
    inquiry_groups={}
    for q in parse_result.get("inquiries") or []:inquiry_groups.setdefault((_name(q.get("company")),q.get("date")),[]).append(q)
    for key,rows in inquiry_groups.items():
        seen={_bureau(q.get("bureau")) for q in rows}
        if len(rows)>=2 and len(seen)<3:discrepancies.append({"discrepancyId":_id("inq",str(key)),"canonicalAccountId":"inquiries","discrepancyType":"inquiry_mismatch","comparedFields":["company","date","bureau"],"bureauValues":{_bureau(q.get("bureau")):q.get("date") or "reported" for q in rows},"differenceSummary":f"{rows[0].get('company') or 'Inquiry'} reporting differs by bureau; authorization still requires client confirmation.","exactDifference":None,"confidence":"medium","severity":"low","fundingImpact":"Recent inquiry reporting may affect some funding evaluations.","tier1Impact":"medium","tier2Impact":"low","possibleStrategyCategories":["unauthorized_inquiry"],"clientConfirmationRequired":True,"specialistExceptionRequired":False,"supportingParserFields":["company","date","bureau"]})
    return {"canonicalAccounts":accounts,"discrepancies":discrepancies}
