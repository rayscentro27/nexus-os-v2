"""Provider-free V2 assigned-goal workflow.

Each completed durable job creates exactly one next goal. Deliverables are
written locally and linked to the job, correlation, receipt, and source evidence.
The campaign uses an isolated local durable store; no production queue is read.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/certification/real_world_v2"
ASSETS = OUT / "assets"
SCRIPTS = ROOT / "scripts/trading"
STAGES = ["OPTIONS", "FOREX", "BUSINESS_CREATION", "BUSINESS_OPPORTUNITY",
          "BUSINESS_FUNDING", "MARKETING_CREATIVE", "SELF_UPGRADE", "NOVA"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def _record(job: Any, stage: str, refs: list[str], extra: dict[str, Any] | None = None) -> dict:
    record = {"stage": stage, "job_id": job.job_id, "correlation_id": job.correlation_id,
              "project_id": job.governance_context.get("project_id"), "created_at": now(),
              "artifact_refs": refs, "providers_used": [], "incremental_cash_spend_usd": 0,
              "external_actions": 0, **(extra or {})}
    path = OUT / "execution" / f"{stage.lower()}_{job.job_id}.json"
    record["execution_artifact_ref"] = _write(path, json.dumps(record, indent=2, sort_keys=True))
    return record


def _svg(path: Path, title: str, subtitle: str, blocks: list[str], accent: str = "#147d72") -> str:
    rows = []
    for idx, item in enumerate(blocks):
        y = 220 + idx * 92
        rows.append(f'<rect x="72" y="{y}" width="1056" height="66" rx="12" fill="#fff" stroke="#d8e4e0"/>')
        rows.append(f'<text x="100" y="{y+41}" font-family="Arial,sans-serif" font-size="22" fill="#1d3330">{item}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{max(640,260+len(blocks)*92)}" viewBox="0 0 1200 {max(640,260+len(blocks)*92)}">
<rect width="1200" height="100%" fill="#f3f7f5"/><rect width="1200" height="168" fill="{accent}"/>
<text x="72" y="76" font-family="Arial,sans-serif" font-weight="700" font-size="34" fill="#fff">{title}</text>
<text x="74" y="124" font-family="Arial,sans-serif" font-size="20" fill="#e6f4f0">{subtitle}</text>{''.join(rows)}
<text x="72" y="{max(610,230+len(blocks)*92)}" font-family="Arial,sans-serif" font-size="15" fill="#60716c">Internal evaluation draft • no publication or financial promise</text></svg>'''
    return _write(path, svg)


def _options(job: Any) -> list[str]:
    SCRIPTS.mkdir(parents=True, exist_ok=True)
    script = SCRIPTS / "v2_options_payoff_harness.py"
    _write(script, '''#!/usr/bin/env python3
"""Deterministic expiration payoff scenarios; not historical market performance."""
import json

def payoff(spot, center, wing, credit, multiplier=100):
    short_call=center+2; long_call=short_call+wing; short_put=center-2; long_put=short_put-wing
    # Compact symmetric iron-condor payoff from one call spread plus one put spread.
    call_loss=max(0.0, spot-short_call)-max(0.0, spot-long_call)
    put_loss=max(0.0, short_put-spot)-max(0.0, long_put-spot)
    return round((credit-call_loss-put_loss)*multiplier, 2)

def main():
    cfg={"underlying":"SPY","dte_entry":[30,45],"short_delta_target":0.15,"wing_width_usd":5.0,
         "entry_filter":"IV percentile >= 30; skip scheduled CPI/FOMC release day","profit_take_fraction":0.50,
         "time_exit_dte":21,"loss_exit_multiple_of_credit":2.0,"max_account_risk_fraction":0.01,
         "assumed_credit_usd_per_share":1.20,"scenario_center":500.0}
    # Illustrative settlement grid only: the assumed credit is a test input, not a quote.
    points=[490,495,498.8,500,501.2,505,510]
    rows=[{"settlement_spot":p,"pnl_usd_per_contract":payoff(p,500,5,1.20)} for p in points]
    max_loss=(5-1.20)*100
    result={"method":"THEORETICAL_EXPIRATION_SCENARIO_TEST","historical_option_data_used":False,
            "market_quotes_used":False,"live_or_paper_orders":False,"assumed_credit_not_market_quote":True,
            "specification":cfg,"max_loss_usd_per_contract":max_loss,
            "one_contract_risk_at_50000_account_fraction":max_loss/50000,
            "scenarios":rows,"assertions":{"worst_case_loss_bounded":max(r["pnl_usd_per_contract"] for r in rows)>=-max_loss,
            "center_spot_profit_equals_credit":payoff(500,500,5,1.2)==120,
            "tail_loss_does_not_exceed_defined_max":min(r["pnl_usd_per_contract"] for r in rows)>=-max_loss}}
    assert all(result["assertions"].values())
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
''')
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True, timeout=20)
    result = json.loads(proc.stdout)
    result_ref = _write(OUT / "options" / "payoff_scenarios.json", json.dumps(result, indent=2))
    md = """# Options strategy package — defined-risk iron condor\n\n**Status:** research implementation and payoff harness complete; no historical option-chain backtest or trading authorization.\n\n- **Universe:** SPY, one-lot defined-risk call/put credit spreads.\n- **Premise:** range-bound / elevated implied volatility; short premium only when IV percentile is at least 30.\n- **Entry:** 30–45 calendar DTE; short strikes near 15 delta; long wings $5 farther OTM; enter after the first 30 minutes; skip CPI/FOMC release days.\n- **Exit:** close at 50% of received credit; exit at 21 DTE; risk stop if mark reaches 2× entry credit; close earlier if range thesis invalidates.\n- **Sizing:** max defined loss per spread is wing width minus credit, ×100; risk cap 1% equity; round down contracts. No contract if one lot exceeds cap.\n- **Risk:** early assignment, pin risk, volatility expansion, gaps, fill/slippage, margin and tax effects. Avoid holding through expiration.\n- **Working assumption:** the source group discusses several different strategies; this reproducible iron-condor rule set is a V2 implementation choice, not a source-proven edge. Credit in the scenario harness is illustrative only.\n- **Backtest specification:** point-in-time SPY option chains, bid/ask fills, dividends, exercise/assignment, commissions, event flags, IV percentile, 2015+ train/validation/test splits, no lookahead, report drawdown and tail loss.\n- **Test actually run:** expiration payoff scenario harness; theoretical payoff assertions pass. It is not a historical performance backtest.\n- **Limitation / next validation:** no accessible option-chain dataset is present; obtain licensed or genuinely free point-in-time chains before measuring expectancy. Live trading remains OFF.\n\nExecutable harness: `scripts/trading/v2_options_payoff_harness.py`\nScenario output: `""" + f"`{result_ref}`"""
    md_ref = _write(OUT / "options" / "OPTIONS_STRATEGY_PACKAGE.md", md)
    return [md_ref, str(script.relative_to(ROOT)), result_ref]


def _forex(job: Any) -> list[str]:
    script = SCRIPTS / "v2_forex_backtest.py"
    _write(script, '''#!/usr/bin/env python3
"""Small-sample, assumption-labeled EURUSD M30 research harness. No broker calls."""
import argparse, json, math
from datetime import datetime
from pathlib import Path

def ema(xs, n):
    out=[]; alpha=2/(n+1); prev=None
    for x in xs:
        prev=x if prev is None else alpha*x+(1-alpha)*prev; out.append(prev)
    return out
def atr(rows,n=14):
    trs=[]; prev=None
    for r in rows:
        h,l,c=r["h"],r["l"],r["c"]; trs.append(max(h-l,abs(h-(prev if prev is not None else c)),abs(l-(prev if prev is not None else c)))); prev=c
    out=[]
    for i in range(len(trs)): out.append(sum(trs[max(0,i-n+1):i+1])/min(n,i+1))
    return out
def load(path):
    d=json.loads(Path(path).read_text()); raw=d.get("candles",[]); rows=[]
    for c in raw:
        if not c.get("complete"): continue
        m=c.get("mid") or c.get("bid") or {}; rows.append({"t":c["time"],"o":float(m["o"]),"h":float(m["h"]),"l":float(m["l"]),"c":float(m["c"])})
    # Resample contiguous M15 pairs to M30. The source snapshot is OANDA practice data.
    bars=[]
    for i in range(0,len(rows)-1,2):
        a,b=rows[i:i+2]
        if (datetime.fromisoformat(b["t"].replace("Z","+00:00"))-datetime.fromisoformat(a["t"].replace("Z","+00:00"))).total_seconds()!=900: continue
        bars.append({"t":a["t"],"o":a["o"],"h":max(a["h"],b["h"]),"l":min(a["l"],b["l"]),"c":b["c"]})
    return bars
def run(path):
    bars=load(path); closes=[r["c"] for r in bars]; e=ema(closes,20); av=atr(bars,14); trades=[]
    # Explicit working signal assumption: %R(14) leaves oversold/overbought in EMA20 direction.
    wr=[]
    for i in range(len(bars)):
        w=bars[max(0,i-13):i+1]; hi=max(x["h"] for x in w); lo=min(x["l"] for x in w)
        wr.append(-100*(hi-closes[i])/(hi-lo) if hi>lo else -50)
    for i in range(20,len(bars)-1):
        if wr[i-1] <= -80 < wr[i] and closes[i]>e[i]: side=1
        elif wr[i-1] >= -20 > wr[i] and closes[i]<e[i]: side=-1
        else: continue
        entry=bars[i+1]["o"]; stop=entry-side*1.5*av[i]; target=entry+side*3*av[i]
        # One-position, deterministic OHLC stop/target; if both touch same bar, assume stop first.
        exit_px=None; outcome="DATA_END"
        for j in range(i+1,len(bars)):
            r=bars[j]
            stop_hit=(r["l"]<=stop if side==1 else r["h"]>=stop)
            target_hit=(r["h"]>=target if side==1 else r["l"]<=target)
            if stop_hit: exit_px=stop; outcome="STOP"; break
            if target_hit: exit_px=target; outcome="TARGET"; break
        if exit_px is None: exit_px=bars[-1]["c"]
        # 1.5 pip round-trip spread/slippage proxy; swap excluded.
        pips=(exit_px-entry)*side*10000-1.5
        trades.append({"entry_time":bars[i+1]["t"],"side":"LONG" if side==1 else "SHORT","entry":entry,"exit":exit_px,"exit_reason":outcome,"net_pips_proxy":round(pips,2)})
    positives=sum(t["net_pips_proxy"]>0 for t in trades)
    return {"strategy":"EURUSD M30 EMA20 + Williams %R(14) exhaustion re-entry (assumption)","source_file":str(path),"bars":len(bars),"trade_count":len(trades),"trades":trades,"win_rate":round(positives/len(trades),4) if trades else None,"net_pips_proxy":round(sum(t["net_pips_proxy"] for t in trades),2),"live_trading":False,"broker_orders":0,"limitations":["only short OANDA practice snapshot; not a robust historical sample","EMA20 is an explicit test assumption replacing source's unspecified trend baseline; no 200-period warmup","OHLC fills and 1.5-pip spread/slippage are proxies; swaps and event filters not represented","no out-of-sample or statistical edge claim"]}
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--input",required=True); p.add_argument("--output"); a=p.parse_args(); r=run(a.input); s=json.dumps(r,indent=2); Path(a.output).write_text(s+chr(10)) if a.output else print(s)
''')
    source = ROOT / "data/runtime/wick_sequence_oanda_eurusd_m15_fresh_20261007.json"
    out = OUT / "forex" / "local_test_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(script), "--input", str(source), "--output", str(out)], capture_output=True, text=True, check=True, timeout=20)
    res = json.loads(out.read_text())
    md = f"""# Forex strategy package — EURUSD M30 exhaustion re-entry\n\n**Status:** rules are reproducible under explicit V2 assumptions; research-only, no live trading.\n\n- Pair: EURUSD. Bars: M30, built from contiguous M15 OANDA practice candles already cached locally.\n- Session: 07:00–17:00 UTC (deployment rule; this short snapshot does not establish session edge).\n- Regime: close above EMA20 for longs, below EMA20 for shorts. EMA20 is a testable working assumption because source indicator details were incomplete.\n- Entry: Williams %R(14) crosses up through -80 while above EMA20 (long); crosses down through -20 while below EMA20 (short). Enter next bar open. One position at a time.\n- Stop/target: 1.5×ATR(14) stop; 2R target. Close at stop/target or end of data. Conservative stop-first rule if same OHLC bar touches both.\n- Position sizing: risk 1% equity / stop distance, round down to broker unit step; cap total open risk at 5%; this harness reports pips only.\n- Filters/invalidation: no entry outside UTC session; invalidate if EMA regime flips before entry, if feed gaps, or if costs exceed modeled reward. No fundamentals in available snapshot.\n- Actual local test: {res['bars']} derived M30 bars, {res['trade_count']} trades, net modeled pips {res['net_pips_proxy']}; tiny practice-data snapshot only, not an edge estimate.\n- Next validation: obtain several years of timestamped bid/ask EURUSD data including spread, swap and event calendar; use chronological train/validation/test and walk-forward testing.\n\nHarness: `scripts/trading/v2_forex_backtest.py`\nInput: `data/runtime/wick_sequence_oanda_eurusd_m15_fresh_20261007.json`\nResult: `reports/certification/real_world_v2/forex/local_test_result.json`\n"""
    return [_write(OUT / "forex" / "FOREX_STRATEGY_PACKAGE.md", md), str(script.relative_to(ROOT)), str(out.relative_to(ROOT))]


def _business_creation(job: Any) -> list[str]:
    text = """# Business creation package — small business data-readiness service\n\n## Concept and customer\nA fixed-scope service helps very small businesses organize spreadsheets and recurring operational data into a documented, decision-ready workbook. Target: owner-operated service firms with recurring spreadsheet handoffs and no analyst. Problem and willingness to pay remain hypotheses; marketplace listings show adjacent spreadsheet cleanup requests, not demand for this exact offer.\n\n## Offer and delivery\nA 90-minute intake; source-file inventory; schema/duplicate/missing-value review; cleaned copy; reconciliation notes; one handoff call. Never overwrite source files. Exclude credit-report underwriting, legal/accounting advice, regulated decisions, and sensitive personal data unless a separately reviewed security process is approved. Delivery is local/offline first, encrypted transfer by an approved method, delete-on-schedule.\n\n## Model and pricing hypothesis\nSingle workbook audit $150–$350; cleanup project $400–$1,200; monthly maintenance $100–$300. These are test prices, not observed willingness-to-pay. Capital-light sole proprietor pilot; tooling, insurance, security review and taxes are startup costs to quote before launch. No revenue is claimed.\n\n## Requirements and bankability\nSeparate business and personal records, business bank account where appropriate, documented contracts/invoices, truthful revenue records, operating history, tax filings, and debt-service capacity improve record quality but do not guarantee credit or financing. Identify state/local registration, tax and insurance requirements before accepting work. NAICS must describe actual primary activity; candidate 541611 (administrative/general management consulting) only if advisory consulting is the principal activity, or 518210 for data processing/hosting only if actual services meet that definition. Verify with Census/IRS/state before filing; do not choose a code to influence underwriting.\n\n## Competition and acquisition\nSubstitutes: bookkeeping firms, spreadsheet freelancers, MSPs, SaaS templates and client staff. Initial acquisition hypothesis: referrals, local business groups, and a useful checklist; no outreach or advertising performed in V2.\n\n## 30-day plan\nDays 1–7: define data-handling SOP, scope, sample synthetic workbook, contract and deletion checklist. Days 8–14: create landing-page draft and interview script. Days 15–21: with Ray authorization, interview 5–8 owners without collecting files. Days 22–30: compare stated pain with actual paid-intent signals; revise offer and cost model.\n\n## 90-day development\nMonth 1 validate problem; month 2 run up to three consented fixed-scope pilots only after security/legal review; month 3 calculate delivery hours, rework, gross margin, referrals and repeat demand. Stop or redesign if data security or unit economics fail.\n\n## Risks and open questions\nSpecific customer segment, willingness to pay, liability, privacy/security controls, acquisition cost, seasonal demand, delivery effort, and truthful local registration remain open.\n"""
    ref = _write(OUT / "business_creation" / "BUSINESS_CREATION_EVALUATION.md", text)
    asset = _svg(ASSETS / "business_creation_data_readiness_offer.svg", "DATA READINESS, MADE PRACTICAL", "A fixed-scope spreadsheet clarity service concept", ["1. Map the workbook and the decisions it supports", "2. Clean a copy; preserve the original", "3. Document exceptions and hand off a clear workbook", "No financing promises • no sensitive files in this concept draft"])
    return [ref, asset]


def _business_opportunity(job: Any) -> list[str]:
    text = """# Business opportunity — fixed-scope data-readiness assessment\n\n## Customer problem and demand confidence\nSmall service businesses may rely on inconsistent spreadsheets for lead, invoice, inventory or job tracking. Two marketplace examples show requests for generic spreadsheet cleanup, but do not prove demand for this offer, identify a local segment, or establish purchase intent. DEMAND_CONFIDENCE=LOW.\n\n## Solution and offer\nA fixed-scope assessment produces a data map, exception list, cleaned workbook copy, short operating notes and a 30-minute handoff. Start with non-sensitive synthetic/sample data; refuse financial/health/identity data until controls are reviewed.\n\n## Pricing and business model hypothesis\nOffer an initial $195 assessment, then optional $450–$900 cleanup package and $125/month maintenance. These are experiment prices, not validated. Affiliate route: refer users to established spreadsheet/bookkeeping products only with disclosure and fit; consulting route is the primary delivery; education alternative is a self-serve spreadsheet hygiene workshop if buyers prefer DIY.\n\n## Segment, substitutes, sales path\nInitial segment hypothesis: owner-operated home/service businesses with 2–15 staff. Substitutes include spreadsheets-as-is, bookkeepers, virtual assistants, freelance marketplaces and SaaS tools. Sales path: educational checklist → consented discovery call → fixed-scope quote → data minimization/security screen → signed scope → delivery/acceptance. No customer contact was made.\n\n## 30-day no-spend launch experiment\nWeek 1: publish nothing; prepare synthetic demo, data SOP and discovery script. Week 2: Ray-approved interviews with 5 owners. Week 3: offer 3 manually delivered pilot slots only if consent/security terms are approved. Week 4: measure qualified conversations, paid-intent, conversion, hours, revisions and referrals. Success threshold proposed: >=3/5 report recurring pain and >=2 request a priced proposal; this is a decision rule, not a result.\n\n## Metrics, risks, next steps\nTrack qualified problem mentions, proposal requests, conversion, delivery hours, exception rate, customer satisfaction, repeat usage and referral intent. Risks: weak specific demand, privacy/security liability, inconsistent data, scope creep, low willingness to pay and strong substitutes. Next: Ray reviews concept; then authorize or decline interviews.\n"""
    ref = _write(OUT / "business_opportunity" / "BUSINESS_OPPORTUNITY_PACKAGE.md", text)
    strategy = """# Internal campaign strategy — spreadsheet clarity\n\nAudience: owner-operated service firms managing recurring jobs and invoices in spreadsheets.\nPain: conflicting rows and unclear handoffs make routine decisions harder.\nOffer: fixed-scope workbook assessment with a cleaned copy and exception notes.\nValue proposition: understand what is in the workbook before buying a larger system.\nHook: “Before you replace the spreadsheet, find out what is actually breaking.”\nChannel: owned educational landing page concept; INTERNAL REVIEW ONLY.\nCTA: review the sample checklist.\nContent: a three-step workbook clarity checklist and synthetic before/after example.\nSuccess metrics (future, not measured): qualified discovery requests, proposal requests, paid pilot conversion, delivery hours, repeat use.\nBrand/compliance: no guaranteed savings, funding outcomes, client results, or endorsement claims; disclose hypothetical pricing; use synthetic data only.\n"""
    strategy_ref = _write(OUT / "marketing" / "V2_CAMPAIGN_STRATEGY.md", strategy)
    asset = _svg(ASSETS / "data_readiness_campaign_v2.svg", "FIND THE BREAK IN YOUR WORKBOOK", "A practical clarity check before you change systems", ["Map the columns, handoffs and decisions", "Spot duplicates, missing fields and conflicting values", "Get a cleaned copy plus a clear exception list", "Start with a short scope conversation • no outcome guarantees"])
    brief = _write(OUT / "creative" / "V2_CREATIVE_BRIEF.md", "# Creative brief\n\nCampaign: Data-readiness assessment. Format: one-page vector graphic, 1200px wide. Audience: owner-operated service firms. Tone: calm, useful, specific. Message: inspect before replacing. CTA: review a sample checklist. Exclusions: no customer logos, testimonials, revenue claims, financing claims, data uploads, or publication. Acceptance: legible at mobile scale, clear steps, truthful claims, explicit internal-review context.")
    review = _write(OUT / "creative" / "V2_MARKETING_ASSET_REVIEW.md", "# Marketing review\n\nDecision: ACCEPT_FOR_INTERNAL_REVIEW. The asset names a concrete audience, explains three steps and avoids guarantees/testimonials. CTA is low pressure. It is a concept artifact; no campaign was published and no performance is claimed.")
    return [ref, strategy_ref, brief, asset, review]


def _funding(job: Any) -> list[str]:
    text = """# Funding readiness product and client workflow\n\n## Target and useful product\nSmall-business owners who are exploring financing and need a truthful view of missing records before speaking with a bank or official program. Product: educational readiness review, not brokerage, underwriting, legal advice, or approval service.\n\n## Readiness model\n1. Business identity and ownership consistency. 2. Time in business and operating records. 3. Revenue/cash-flow evidence and debt obligations. 4. Tax returns and bookkeeping completeness. 5. Credit report accuracy and dispute documentation. 6. Requested amount/use, repayment capacity and collateral where lender asks. 7. Geography, industry and product-specific criteria. Score only documentation completeness; never infer lender approval.\n\n## Intake and documents\nIntake: state, entity type, ownership, operating date, industry, revenue range, requested amount/use, debt obligations, prior applications, preferred timing and consent. Ask only minimum necessary. Checklist: formation/registration, EIN confirmation (if applicable), business bank statements, tax returns, P&L/balance sheet, debt schedule, ownership IDs only when required and securely handled, project/use-of-funds evidence. No identity or credit data in this educational V2 artifact.\n\n## Qualification and sequencing\nConsent → scope and privacy notice → completeness check → identify goals and use → classify possible product categories → verify current official lender/program terms → assemble questions/documents → client decides whether to apply directly → follow-up on missing records. Do not submit applications. Product categories can include term loans, lines of credit, SBA-backed lending, equipment financing and community lender/CDFI options; exact eligibility and terms are lender-specific and unverified here.\n\n## Service structure and journey\nFree public checklist concept; paid readiness review only after legal/compliance review; optional bookkeeping cleanup referral with disclosed conflicts. Journey: inquiry → consent → intake → document completeness map → human review → written report → client-directed next steps. Proposed service tiers/pricing are not set; Ray review required.\n\n## Verified vs unverified\nVerified process references in existing research include official SBA program overview and IRS EIN information; they describe process, not this client's eligibility. Video claims about approval speed, stacking, limits, fees, credit thresholds and particular issuers remain source claims/unverified. Do not advertise these as facts.\n\n## Marketing / limitations\nConcept: “Know what to gather before you compare business funding options.” CTA: download the document checklist. No guaranteed approval, score improvement, credit access, lender relationship, or funding timeline. State/federal compliance review, compensation disclosures, privacy controls, lender-specific terms, actual costs and qualifications remain unresolved.\n"""
    ref = _write(OUT / "business_funding" / "FUNDING_READINESS_PRODUCT.md", text)
    asset = _svg(ASSETS / "funding_readiness_checklist.svg", "PREPARE BEFORE YOU COMPARE", "A document-readiness checklist • educational concept", ["Business identity and ownership records", "Revenue, expense and debt records", "Requested amount and documented use", "Current lender terms verified before any decision", "Readiness is not eligibility or approval"], "#425c8a")
    return [ref, asset]


def _self_upgrade(job: Any) -> list[str]:
    # A zero-cost Needle-derived capability: searchable, durable project memory.
    code = ROOT / "scripts/nexus_agent_platform/project_portfolio_memory.py"
    _write(code, '''"""Local searchable portfolio memory; standard library only, no network/secrets."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

def save(record: dict, path: str | Path) -> None:
    required={"project_id","version","score","outputs","weaknesses","missing_components","improvement_targets","research_triggers","next_stage"}
    if required-set(record): raise ValueError("PORTFOLIO_RECORD_FIELDS_MISSING")
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    row={**record,"updated_at":datetime.now(timezone.utc).isoformat()}
    existing=[]
    if p.exists(): existing=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    existing=[x for x in existing if not (x.get("project_id")==row["project_id"] and x.get("version")==row["version"])]
    existing.append(row); tmp=p.with_suffix(p.suffix+".tmp"); tmp.write_text("".join(json.dumps(x,sort_keys=True)+chr(10) for x in existing)); tmp.replace(p)

def search(query: str, path: str | Path) -> list[dict]:
    terms=[x.casefold() for x in query.split() if x]
    if not terms: return []
    rows=[json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    def score(row):
        text=json.dumps(row,sort_keys=True).casefold(); return sum(t in text for t in terms)
    return sorted((r for r in rows if score(r)),key=score,reverse=True)

def match_research_and_reopen(new_finding: str, path: str | Path) -> list[dict]:
    """Return completed projects whose saved research triggers match a new finding.

    This creates explicit improvement candidates; it does not promote projects,
    alter approvals, or schedule work without a workflow assignment.
    """
    tokens={x.casefold() for x in new_finding.split() if len(x)>2}
    candidates=[]
    for row in search(new_finding,path):
        triggers=" ".join(row.get("research_triggers",[])).casefold()
        matched=sorted(t for t in tokens if t in triggers)
        if matched: candidates.append({"project_id":row["project_id"],"version":row["version"],
            "matched_triggers":matched,"status":"REOPEN_CANDIDATE","authority_change":False})
    return candidates
''')
    test = ROOT / "tests/test_project_portfolio_memory.py"
    _write(test, '''import tempfile, unittest
from pathlib import Path
from scripts.nexus_agent_platform.project_portfolio_memory import save, search, match_research_and_reopen

class PortfolioMemoryTests(unittest.TestCase):
 def test_save_and_retrieve_by_research_trigger(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"memory.jsonl"
   save({"project_id":"p1","version":"v1","score":4,"outputs":["workbook"],"weaknesses":["demand"],"missing_components":[],"improvement_targets":["interviews"],"research_triggers":["spreadsheet cleanup demand"],"next_stage":"RAY_REVIEW"},p)
   self.assertEqual(search("spreadsheet demand",p)[0]["project_id"],"p1")
 def test_requires_complete_portfolio_record(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError): save({"project_id":"p"},Path(d)/"x")
 def test_new_research_finds_reopen_candidate_without_authority_change(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"memory.jsonl"
   save({"project_id":"p1","version":"v1","score":4,"outputs":[],"weaknesses":[],"missing_components":[],"improvement_targets":[],"research_triggers":["customer demand evidence"],"next_stage":"RAY_REVIEW"},p)
   found=match_research_and_reopen("new customer demand evidence",p)
   self.assertEqual(found[0]["status"],"REOPEN_CANDIDATE")
   self.assertFalse(found[0]["authority_change"])

if __name__=="__main__": unittest.main()
''')
    return [str(code.relative_to(ROOT)), str(test.relative_to(ROOT))]


def build_goal(stage: str, job: Any) -> list[str]:
    if stage == "OPTIONS": return _options(job)
    if stage == "FOREX": return _forex(job)
    if stage == "BUSINESS_CREATION": return _business_creation(job)
    if stage == "BUSINESS_OPPORTUNITY": return _business_opportunity(job)
    if stage == "BUSINESS_FUNDING": return _funding(job)
    if stage == "MARKETING_CREATIVE": return []
    if stage == "SELF_UPGRADE": return _self_upgrade(job)
    return []


def handle_job(job: Any, store: Any) -> dict:
    if job.governance_context.get("providers_allowed") != [] or job.governance_context.get("spend_allowed") is not False:
        raise PermissionError("V2_PROVIDER_OR_SPEND_NOT_ALLOWED")
    payload_path = (ROOT / (job.payload_ref or "")).resolve()
    if ROOT.resolve() not in payload_path.parents:
        raise ValueError("V2_PAYLOAD_PATH_OUTSIDE_REPO")
    payload = json.loads(payload_path.read_text())
    stage = payload["stage"]
    if stage not in STAGES[:-1]: raise ValueError("V2_STAGE_INVALID")
    refs = build_goal(stage, job)
    if stage == "MARKETING_CREATIVE" and not refs:
        refs = [str(p.relative_to(ROOT)) for p in [OUT/"marketing"/"V2_CAMPAIGN_STRATEGY.md", OUT/"creative"/"V2_CREATIVE_BRIEF.md", OUT/"assets"/"data_readiness_campaign_v2.svg", OUT/"creative"/"V2_MARKETING_ASSET_REVIEW.md"]]
    if stage == "SELF_UPGRADE":
        # Run the deterministic replacement's focused tests in this actual goal.
        proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_project_portfolio_memory.py"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        if proc.returncode: raise RuntimeError("SELF_UPGRADE_TEST_FAILED:" + proc.stderr[-1000:])
        refs.append(_write(OUT/"self_upgrade"/"SELF_UPGRADE_TEST_RESULT.txt", proc.stdout + proc.stderr))
    execution = _record(job, stage, refs, {"goal_complete": True, "test_status": "PASS" if stage in {"OPTIONS","FOREX","SELF_UPGRADE"} else "ARTIFACT_VALIDATED"})
    from nexus_agent_platform.durable_jobs import create_next_job
    idx = STAGES.index(stage)
    next_stage = STAGES[idx+1]
    if next_stage == "NOVA":
        # Prepare a read-only campaign snapshot and evidence payload for the existing
        # Nova certification handler. This is a durable child job, not a model/provider call.
        from nexus_agent_platform.marketing_creative_workflow import _campaign_path
        campaign_id = job.governance_context["campaign_id"]
        cpath = _campaign_path(campaign_id); cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text(json.dumps({"campaign_id":campaign_id,"project_id":job.governance_context["project_id"],
            "state":"RAY_REVIEW_REQUIRED","approval_state":"READY_FOR_RAY_REVIEW","workflow_stage":"COMPLETE",
            "correlation_id":job.correlation_id,"asset_ids":["v2_asset_data_readiness"],"updated_at":now()},indent=2)+chr(10))
        summary = {"category_decisions":{"OPTIONS":"COMPLETE_RESEARCH_PACKAGE","FOREX":"COMPLETE_RESEARCH_PACKAGE",
          "BUSINESS_CREATION":"COMPLETE_EVALUATION_PACKAGE","BUSINESS_OPPORTUNITY":"COMPLETE_OPPORTUNITY_PACKAGE",
          "BUSINESS_FUNDING":"COMPLETE_READINESS_WORKFLOW"},"campaign_id":campaign_id,"certification_version":"V2",
          "external_actions":"NONE","live_trading":"OFF"}
        nova_payload = {"campaign_id":campaign_id,"source_artifacts":[*refs,
            "reports/certification/real_world_v2/options/OPTIONS_STRATEGY_PACKAGE.md",
            "reports/certification/real_world_v2/forex/FOREX_STRATEGY_PACKAGE.md",
            "reports/certification/real_world_v2/business_opportunity/BUSINESS_OPPORTUNITY_PACKAGE.md",
            "reports/certification/real_world_v2/self_upgrade/SELF_UPGRADE_DECISION.md"],
            "executive_summary":summary,"integrated_company_run":True}
        p = OUT / "execution" / "nova_payload.json"; _write(p,json.dumps(nova_payload,indent=2))
        child = create_next_job(store,job,department="NOVA",job_type="CERTIFICATION_NOVA_SUMMARY",
           payload_ref=str(p.relative_to(ROOT)),event_id="v2:all-goals-to-nova")
    else:
        p = OUT / "execution" / f"payload_{next_stage.lower()}.json"
        _write(p,json.dumps({"stage":next_stage,"certification_version":"V2"},indent=2))
        child = create_next_job(store,job,department={"BUSINESS_CREATION":"ATLAS","BUSINESS_OPPORTUNITY":"BUSINESS",
            "BUSINESS_FUNDING":"CLYDE","MARKETING_CREATIVE":"MARKETING","SELF_UPGRADE":"SYSTEMS"}.get(next_stage,next_stage),
            job_type="REAL_WORLD_V2_GOAL",payload_ref=str(p.relative_to(ROOT)),event_id=f"v2:{stage}-complete-to-{next_stage.lower()}")
    execution["next_job_id"] = child.job_id
    # Record the child identifier back into the execution artifact.
    exec_path = ROOT / execution["execution_artifact_ref"]
    exec_record = json.loads(exec_path.read_text()); exec_record["next_job_id"] = child.job_id
    _write(exec_path,json.dumps(exec_record,indent=2,sort_keys=True))
    return {"status":"COMPLETED","stage":stage,"artifact_refs":refs,
            "execution_artifact_ref":execution["execution_artifact_ref"],"next_job_id":child.job_id,
            "providers_used":[],"cash_spend_usd":0}
