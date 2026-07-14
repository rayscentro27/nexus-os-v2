#!/usr/bin/env python3
"""Deterministic three-bureau normalization and conservative account matching."""
from __future__ import annotations
import hashlib,re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any
ENGINE_VERSION="canonical-match-1.0.0";THRESHOLD_VERSION="canonical-threshold-1";RULESET_VERSION="discrepancy-1"
ALIASES={"b of a":"bank of america","bank of amer":"bank of america","bank of america na":"bank of america"}
def normalize_bureau(v:Any)->str:
    x=re.sub(r"[^a-z]","",str(v or "").lower());return "experian" if "experian" in x else "equifax" if "equifax" in x else "transunion" if "transunion" in x else "other"
def normalize_creditor(v:Any)->str:
    x=re.sub(r"[^a-z0-9 ]"," ",str(v or "").lower());x=re.sub(r"\b(incorporated|inc|llc|ltd|corporation|corp|company|co|n a|na)\b"," ",x);x=" ".join(x.split());return ALIASES.get(x,x)
def normalize_account_type(v:Any)->str:
    x=str(v or "").lower().replace("-"," ").replace("_"," ");return "revolving" if any(k in x for k in ("credit card","revolving","charge card")) else "collection" if "collection" in x else "installment" if any(k in x for k in ("installment","auto","loan","mortgage")) else "other" if not x.strip() else " ".join(x.split())
def normalize_money(v:Any):
    if v in (None,""):return None
    try:return float(re.sub(r"[^0-9.-]","",str(v)))
    except ValueError:return None
def normalize_date(v:Any):
    if not v:return None
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%m/%Y","%b %Y","%B %Y"):
        try:return datetime.strptime(str(v).strip(),fmt).date().isoformat()
        except ValueError:pass
    return None
def normalize_status(v:Any)->str:
    x=" ".join(str(v or "").lower().replace("_"," ").split());return "charge_off" if "charge" in x and "off" in x else "collection" if "collection" in x else "closed" if "closed" in x else "open" if "open" in x else "paid" if "paid" in x else x or "unknown"
def masked_reference(v:Any)->str:
    s=str(v or "").strip();suffix=account_suffix(s);return f"****{suffix}" if suffix else "Not available"
def account_suffix(v:Any)->str:return re.sub(r"[^a-zA-Z0-9]","",str(v or ""))[-4:].upper()
def _value(a:dict[str,Any],*keys):return next((a[k] for k in keys if a.get(k) not in (None,"")),None)
def normalize_tradeline(a:dict[str,Any],index:int)->dict[str,Any]:
    creditor=_value(a,"furnisherName","accountName","creditorName");original=_value(a,"originalCreditor");ref=_value(a,"accountNumberMasked","account_reference_masked")
    return {"source_index":index,"bureau":normalize_bureau(a.get("bureau")),"creditor_name_original":creditor,"creditor_name_normalized":normalize_creditor(creditor),"original_creditor_original":original,"original_creditor_normalized":normalize_creditor(original),"account_type_original":_value(a,"itemType","accountType"),"account_type_normalized":normalize_account_type(_value(a,"itemType","accountType")),"account_reference_masked":masked_reference(ref),"account_suffix":account_suffix(ref),"account_status_original":a.get("status"),"account_status_normalized":normalize_status(a.get("status")),"payment_status_original":a.get("paymentStatus"),"payment_status_normalized":normalize_status(a.get("paymentStatus")),"balance":normalize_money(_value(a,"reportedBalance","balance")),"credit_limit":normalize_money(a.get("creditLimit")),"high_balance":normalize_money(_value(a,"highLimit","highBalance","originalBalance")),"past_due":normalize_money(_value(a,"pastDue","pastDueAmount")),"date_opened":normalize_date(a.get("dateOpened")),"date_closed":normalize_date(a.get("dateClosed")),"last_reported_date":normalize_date(_value(a,"dateReported","lastReportedDate")),"ownership_original":_value(a,"ownership","responsibility"),"ownership_normalized":normalize_status(_value(a,"ownership","responsibility")),"remarks":a.get("notes"),"comments":a.get("comments"),"payment_history":a.get("paymentHistory") if isinstance(a.get("paymentHistory"),list) else [],"source_reference":a.get("sourceReference"),"parser_confidence":a.get("confidence") if a.get("confidence") in ("low","medium","high") else "low","raw_normalized_extraction_reference":f"accounts[{index}]"}
def score_pair(a:dict[str,Any],b:dict[str,Any])->dict[str,Any]:
    scores={};positive=[];conflicts=[]
    scores["creditor_name"]=round(SequenceMatcher(None,a["creditor_name_normalized"],b["creditor_name_normalized"]).ratio(),3) if a["creditor_name_normalized"] and b["creditor_name_normalized"] else 0
    scores["masked_suffix"]=1 if a["account_suffix"] and a["account_suffix"]==b["account_suffix"] else 0
    if a["account_suffix"] and b["account_suffix"] and not scores["masked_suffix"]:conflicts.append("different masked account suffixes")
    scores["date_opened"]=1 if a["date_opened"] and a["date_opened"]==b["date_opened"] else .5 if not a["date_opened"] or not b["date_opened"] else 0
    if a["date_opened"] and b["date_opened"] and not scores["date_opened"]:conflicts.append("conflicting opened dates")
    scores["account_type"]=1 if a["account_type_normalized"]==b["account_type_normalized"] and a["account_type_normalized"]!="other" else 0
    if a["account_type_normalized"]!=b["account_type_normalized"]:conflicts.append("incompatible account types")
    scores["original_creditor"]=1 if a["original_creditor_normalized"] and a["original_creditor_normalized"]==b["original_creditor_normalized"] else 0
    if a["balance"] is not None and b["balance"] is not None:scores["balance_proximity"]=max(0,1-abs(a["balance"]-b["balance"])/max(abs(a["balance"]),abs(b["balance"]),100))
    else:scores["balance_proximity"]=.4
    scores["status_compatibility"]=1 if a["account_status_normalized"]==b["account_status_normalized"] else .4
    scores["ownership_compatibility"]=1 if a["ownership_normalized"]==b["ownership_normalized"] else .4
    if {a["ownership_normalized"],b["ownership_normalized"]}&{"authorized user"} and a["ownership_normalized"]!=b["ownership_normalized"]:conflicts.append("authorized-user ownership differs from primary ownership")
    total=sum(scores[k]*w for k,w in {"creditor_name":.18,"masked_suffix":.32,"date_opened":.16,"account_type":.14,"original_creditor":.05,"balance_proximity":.08,"status_compatibility":.04,"ownership_compatibility":.03}.items())
    if scores["masked_suffix"]:positive.append("matching masked suffix")
    if scores["creditor_name"]>=.85:positive.append("strong normalized creditor similarity")
    if scores["date_opened"]==1:positive.append("matching opened date")
    if scores["account_type"]==1:positive.append("compatible account type")
    hard_conflict=bool({"different masked account suffixes","incompatible account types","conflicting opened dates"}&set(conflicts));ownership_conflict="authorized-user ownership differs from primary ownership" in conflicts; tier="high_confidence" if total>=.78 and not hard_conflict and not ownership_conflict and (scores["masked_suffix"] or (scores["date_opened"]==1 and scores["account_type"]==1)) else "ambiguous" if total>=.52 and not hard_conflict else "rejected"
    return {"decision":tier,"total_score":round(total,4),"component_scores":scores,"positive_reasons":positive,"conflict_reasons":conflicts,"threshold_version":THRESHOLD_VERSION,"matching_engine_version":ENGINE_VERSION}
def build_canonical_model(accounts:list[dict[str,Any]])->dict[str,Any]:
    tradelines=[normalize_tradeline(a,i) for i,a in enumerate(accounts)];pairs=[]
    for i,a in enumerate(tradelines):
        for j,b in enumerate(tradelines[i+1:],i+1):
            if a["bureau"]==b["bureau"]:continue
            result=score_pair(a,b);pairs.append({"left_index":i,"right_index":j,**result})
    parent=list(range(len(tradelines)))
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for p in pairs:
        if p["decision"]=="high_confidence":parent[find(p["right_index"])]=find(p["left_index"])
    grouped={}
    for i in range(len(tradelines)):grouped.setdefault(find(i),[]).append(i)
    canonical=[]
    for indices in grouped.values():
        linked=[p for p in pairs if p["left_index"] in indices and p["right_index"] in indices and p["decision"]=="high_confidence"]
        confidence=max((p["total_score"] for p in linked),default=.35);ambiguous=any(p["decision"]=="ambiguous" and (p["left_index"] in indices or p["right_index"] in indices) for p in pairs)
        tier="high_confidence" if len(indices)>1 else "ambiguous" if ambiguous else "rejected";first=tradelines[indices[0]]
        canonical.append({"canonical_key":hashlib.sha256((str(indices)+first["creditor_name_normalized"]).encode()).hexdigest()[:20],"tradeline_indices":indices,"normalized_creditor_label":first["creditor_name_normalized"] or "unknown creditor","normalized_account_type":first["account_type_normalized"],"canonical_status":first["account_status_normalized"],"match_confidence":confidence,"match_tier":tier,"match_reasons":sorted({x for p in linked for x in p["positive_reasons"]}),"conflict_reasons":sorted({x for p in pairs if p["left_index"] in indices or p["right_index"] in indices for x in p["conflict_reasons"]}),"review_requirement":"exception_required" if ambiguous else "not_required","threshold_version":THRESHOLD_VERSION,"matching_engine_version":ENGINE_VERSION,"version":1})
    unmatched=[{"tradeline_index":i,"reason":"No safe cross-bureau match met the automatic threshold.","exception_required":any(p["decision"]=="ambiguous" and i in (p["left_index"],p["right_index"]) for p in pairs)} for i in range(len(tradelines)) if not any(i in c["tradeline_indices"] and len(c["tradeline_indices"])>1 for c in canonical)]
    return {"tradelines":tradelines,"pair_decisions":pairs,"canonical_accounts":canonical,"unmatched_tradelines":unmatched,"ambiguous_match_count":sum(p["decision"]=="ambiguous" for p in pairs),"engine_version":ENGINE_VERSION,"threshold_version":THRESHOLD_VERSION}
def detect_discrepancies(model:dict[str,Any])->list[dict[str,Any]]:
    out=[];fields=(("balance","balance_mismatch"),("credit_limit","credit_limit_mismatch"),("high_balance","high_balance_mismatch"),("past_due","past_due_mismatch"),("date_opened","date_opened_mismatch"),("last_reported_date","last_reported_date_mismatch"),("account_status_original","account_status_mismatch"),("payment_status_original","payment_status_mismatch"),("account_suffix","masked_suffix_mismatch"),("original_creditor_original","original_creditor_mismatch"),("ownership_original","ownership_mismatch"))
    for c in model["canonical_accounts"]:
        rows=[model["tradelines"][i] for i in c["tradeline_indices"]]
        for key,kind in fields:
            values={r["bureau"]:r[key] for r in rows if r.get(key) not in (None,"")}
            if len(values)>=2 and len({str(v).lower() for v in values.values()})>1:out.append({"canonical_key":c["canonical_key"],"tradeline_indices":c["tradeline_indices"],"discrepancy_type":kind,"bureau_values":values,"confidence":"high" if all(r["parser_confidence"]=="high" for r in rows) else "medium","severity":"high" if kind in ("balance_mismatch","past_due_mismatch","account_status_mismatch") else "medium","detection_rule":f"distinct non-null {key} values across safely grouped bureau tradelines","ruleset_version":RULESET_VERSION,"explanation":f"The safely grouped bureau records report different {key.replace('_',' ')} values: "+"; ".join(f"{b}: {v}" for b,v in values.items())+". This is a reporting difference for review, not a legal conclusion.","client_confirmation_required":False,"exception_review_required":False,"status":"detected"})
        present={r["bureau"] for r in rows};missing=[b for b in ("experian","equifax","transunion") if b not in present]
        if len(rows)>=2 and missing:out.append({"canonical_key":c["canonical_key"],"tradeline_indices":c["tradeline_indices"],"discrepancy_type":"bureau_omission","bureau_values":{r["bureau"]:"reported" for r in rows},"confidence":"medium","severity":"low","detection_rule":"safe canonical group absent from one or more bureaus","ruleset_version":RULESET_VERSION,"explanation":f"No matching tradeline was parsed for {', '.join(missing)}. Missing data is not a confirmed error.","client_confirmation_required":False,"exception_review_required":False,"status":"detected"})
    return out
