"""Supabase-backed, deterministic feeder and Ray/Nova opportunity intake.

Questionnaire execution consumes structured NotebookLM output when supplied and
otherwise creates explicit, material research questions. It never guesses
facts or selects the downstream owner from model output.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, ssl, sys, urllib.error, urllib.parse, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
BATCH='2026-10-07_FEEDER_CERTIFICATION_BATCH'
ROUTES={
 'BUSINESS_OPPORTUNITY_FEEDER':('BUSINESS_OPPORTUNITIES','ATLAS'),
 'BUSINESS_FUNDING_FEEDER':('BUSINESS_FUNDING','CLYDE'),
 'BUSINESS_CREATION_BANKABILITY_FEEDER':('BUSINESS_CREATION','BUSINESS_CREATION'),
 'FOREX_INDICATOR_STRATEGY_FEEDER':('TRADING','MERCURY_FOREX_INDICATOR_LAB'),
 'OPTIONS_STRATEGY_FEEDER':('TRADING','MERCURY_OPTIONS_LAB'),
 'RAY_NOVA_OPPORTUNITY_INTAKE':('RESEARCH','RAY'),
}
STATES={'WAITING_FOR_SOURCE','NEW','DETECTED','READY_FOR_QUESTIONNAIRE','QUESTIONNAIRE_RUNNING','QUESTIONNAIRE_COMPLETE','RESEARCH_REQUIRED','RESEARCH_IN_PROGRESS','READY_FOR_HANDOFF','HANDED_OFF','BLOCKED','FAILED_RETRYABLE'}
DEPARTMENTS={
 'BUSINESS_OPPORTUNITY_FEEDER':'BUSINESS_OPPORTUNITIES','BUSINESS_FUNDING_FEEDER':'BUSINESS_FUNDING',
 'BUSINESS_CREATION_BANKABILITY_FEEDER':'BUSINESS_CREATION','FOREX_INDICATOR_STRATEGY_FEEDER':'MERCURY_FOREX_INDICATOR_LAB',
 'OPTIONS_STRATEGY_FEEDER':'MERCURY_OPTIONS_LAB'}

# Full structured field contracts. Source evidence is never promoted to verified
# solely by questionnaire parsing. Existing BI prompts are extended here with
# the complete fields required by the approved workflow specifications.
PROMPTS={
'BUSINESS_OPPORTUNITY_FEEDER':'''PURPOSE: Evaluate a newly added source as a potential business opportunity. Answer all supported questions, use YES/NO gates, label claims SOURCE_CLAIM/CROSS_SUPPORTED/VERIFIED/CONTRADICTED/RESEARCH_REQUIRED. Never invent numbers or approve/reject a project.
A CLASSIFICATION: IS_THIS_A_BUSINESS_OPPORTUNITY=YES/NO; if NO classify MARKETING_TACTIC/SOFTWARE_TOOL/AFFILIATE_OPPORTUNITY/BUSINESS_COMPONENT/EDUCATIONAL_CONTENT/DUPLICATE/OTHER. BUSINESS_MODEL, PRIMARY_PRODUCT_OR_SERVICE, TARGET_CUSTOMER, CUSTOMER_PROBLEM, VALUE_PROPOSITION, PRIMARY_REVENUE_MODEL.
B DEMAND: CUSTOMER_DEMAND_EVIDENCE_PRESENT, INDEPENDENT_DEMAND_SUPPORT, CUSTOMER_COMPLAINTS_OR_UNMET_NEEDS_IDENTIFIED=YES/NO; EVIDENCE; exact research question for every NO.
C ECONOMICS: PRICING_PRESENT, REVENUE_CLAIMS_PRESENT, MARGIN_CLAIMS_PRESENT, UNIT_ECONOMICS_PRESENT, BREAK_EVEN_INFORMATION_PRESENT=YES/NO; SOURCE_PRICING, SOURCE_REVENUE_CLAIMS, SOURCE_MARGIN_CLAIMS, INDEPENDENTLY_SUPPORTED, FINANCIAL_GAPS.
D MARKETING: TARGET_CUSTOMER_DEFINED, PRIMARY_TRAFFIC_CHANNELS_DEFINED, MARKETING_HOOK_DEFINED, CUSTOMER_ACQUISITION_METHOD_DEFINED, CONVERSION_METHOD_DEFINED=YES/NO; CHANNELS=SEO/YOUTUBE/SHORT_FORM/PAID_ADS/EMAIL/OUTBOUND/AFFILIATE/MARKETPLACE/PARTNERSHIP/OTHER; MARKETING_EVIDENCE_PRESENT.
E COMPETITION: COMPETITORS_IDENTIFIED, CURRENT_COMPETITOR_DATA_PRESENT=YES/NO; per competitor NAME, PRICE, POSITIONING, TARGET_CUSTOMER, OFFER, STRENGTH, WEAKNESS, OBSERVABLE_GAP; COMPETITOR_RESEARCH_REQUIRED.
F ENTRY TIERS: CAN_BUSINESS_BE_STARTED_AT_MULTIPLE_COST_LEVELS=YES/NO; if YES, LEAN_BOOTSTRAP, MODERATE, ACCELERATED each REQUIRED_CAPITAL, TOOLS, LABOR, TIME_TO_LAUNCH, PROS, CONS. Unsupported costs remain blank/research required.
G AFFILIATE/WHITE LABEL: CAN_CUSTOMER_NEED_BE_SOLVED_WITH_EXISTING_PRODUCT, AFFILIATE_OPTION_IDENTIFIED, WHITE_LABEL_OPTION_IDENTIFIED, REFERRAL_OPTION_IDENTIFIED, PARTNER_OPTION_IDENTIFIED=YES/NO; OPTIONS.
H OPERATIONS: FULFILLMENT_DEFINED, SUPPLIERS_DEFINED, SOFTWARE_DEFINED, STAFFING_DEFINED, AUTOMATION_DEFINED, CUSTOMER_SUPPORT_DEFINED, TIME_REQUIREMENT_DEFINED=YES/NO.
I RISKS: MARKET_RISK, PLATFORM_RISK, CAPITAL_RISK, SUPPLIER_RISK, REGULATORY_RISK, CUSTOMER_ACQUISITION_RISK, MARGIN_RISK, FULFILLMENT_RISK, COMPETITION_RISK.
J NEXUS FIT: CAN_NEXUS_REUSE_EXISTING_CAPABILITY; HAS_NEXUS_TRIED_SIMILAR_MODEL; PRIOR_PROJECTS; AFFILIATE_OR_PARTNER_RESOURCE_AVAILABLE; REUSABLE_MARKETING_ASSET_AVAILABLE; ONE_POTENTIAL_NEXUS_IMPROVEMENT; WHY.
K REUSABLE COMPONENTS: CUSTOMER_PROBLEM, AUDIENCE, OFFER, PRICING_MODEL, MONETIZATION_MODEL, TRAFFIC_METHOD, CONTENT_METHOD, FULFILLMENT_MODEL, SUPPLIER_MODEL, AUTOMATION_MODEL, AFFILIATE_OPTION, SCALING_METHOD.
L COMPLETENESS YES/NO: BUSINESS_MODEL_DEFINED, CUSTOMER_DEFINED, PROBLEM_DEFINED, DEMAND_EVIDENCE_PRESENT, REVENUE_MODEL_DEFINED, COMPETITOR_REVIEW_COMPLETE, BASIC_COST_STRUCTURE_PRESENT, MARKETING_PATH_PRESENT, RISKS_IDENTIFIED, AFFILIATE_OPTIONS_CHECKED. Exact research question for every NO.
M INITIAL RECOMMENDATION only: PROMOTE_TO_DEDICATED_OPPORTUNITY_NOTEBOOK/ADDITIONAL_RESEARCH_REQUIRED/ATTACH_TO_EXISTING_OPPORTUNITY/SAVE_AS_REUSABLE_COMPONENT/NOT_A_BUSINESS_OPPORTUNITY; RECOMMENDATION, ACTION, NEXT_OWNER.''',
'BUSINESS_FUNDING_FEEDER':'''PURPOSE: Evaluate funding techniques, lenders, grants, credit products, banking strategies, and capital opportunities. Original claims remain SOURCE_CLAIM, not lender policy. No approval guarantee.
A PRODUCT: SPECIFIC_LENDER_IDENTIFIED, LENDER, SPECIFIC_PRODUCT_IDENTIFIED, PRODUCT, PRODUCT_TYPE=BUSINESS_LINE_OF_CREDIT/TERM_LOAN/BUSINESS_CREDIT_CARD/SBA/EQUIPMENT/VENDOR_CREDIT/GRANT/BANK_RELATIONSHIP/OTHER, CLAIMED_LIMIT, CLAIMED_MINIMUM, SECURED_OR_UNSECURED, DOCUMENTATION_CLAIM.
B CREDIT: PERSONAL_CREDIT_REQUIRED, CLAIMED_MINIMUM_SCORE, BUREAUS, HARD_PULL_CLAIM, BUSINESS_CREDIT_REQUIRED, LENDER_VERIFIED.
C BUSINESS: ENTITY_REQUIRED, TIME_IN_BUSINESS, REVENUE_REQUIREMENT, BANK_ACCOUNT_REQUIRED, BANK_RELATIONSHIP_REQUIRED, ACCOUNT_AGE_REQUIREMENT, DEPOSIT_REQUIREMENT, AVERAGE_BALANCE_REQUIREMENT, STATE_RESTRICTION, INDUSTRY_RESTRICTIONS, NAICS_RESTRICTIONS, DUNS_REQUIRED, BUSINESS_PLAN_REQUIRED.
D DOCUMENTATION: TAX_RETURNS, BANK_STATEMENTS, FINANCIAL_STATEMENTS, PROOF_OF_REVENUE, EIN, FORMATION_DOCS, ID, PERSONAL_GUARANTEE, COLLATERAL, UCC.
E PRICING: APR_OR_RATE, FEES, TERM, PAYMENT_STRUCTURE, DRAW_FEES, ANNUAL_FEES, PREPAYMENT, OTHER_COSTS.
F APPLICATION: ONLINE_APPLICATION, BRANCH, RELATIONSHIP_MANAGER, PHONE, REFERRAL, OTHER.
G GEOGRAPHY: STATES, NATIONAL, LOCAL_ONLY.
H For every claim: CLAIM, SOURCE_CLAIM, LENDER_VERIFIED, CROSS_SUPPORTED, CONTRADICTED, RESEARCH_REQUIRED, SOURCE.
I IMPROVABLE REQUIREMENTS: for each requirement BINARY, IMPROVABLE, TIME_BASED, RELATIONSHIP_BASED, CREDIT_BASED, FINANCIAL, BUSINESS_AGE_BASED, CAN_CONDITION_CHANGE, ACTION, VERIFICATION_MILESTONE. Never guarantee future approval.
J ALTERNATIVES: ARE_PRODUCTS_WITH_DIFFERENT_REQUIREMENTS_LIKELY_RELEVANT, WHAT_REQUIREMENT_DIFFERENCE_TO_SEARCH (lower score/no relationship/shorter age/lower revenue/different state/no PG/other).
K COMPLETENESS YES/NO: PRODUCT_EXISTS_VERIFIED, CURRENT_REQUIREMENTS_VERIFIED, CREDIT_REQUIREMENTS_VERIFIED, BUSINESS_REQUIREMENTS_VERIFIED, DOCUMENTATION_VERIFIED, PRICING_VERIFIED, APPLICATION_PATH_VERIFIED, GEOGRAPHY_VERIFIED. Exact question for each NO.
L RECOMMENDATION only: PROMOTE_TO_FUNDING_PRODUCT_BANK/ADDITIONAL_VERIFICATION_REQUIRED/ATTACH_TO_EXISTING_PRODUCT/SAVE_AS_FUNDING_TECHNIQUE/STALE_OR_DISCONTINUED; NEXT_ACTION, NEXT_OWNER.''',
'BUSINESS_CREATION_BANKABILITY_FEEDER':'''PURPOSE: Determine whether a NEW_BUSINESS or EXISTING_BUSINESS is established, operationally credible, and funding-positioned. BUSINESS_EXISTS=YES/NO; WORKFLOW_TYPE=NEW_BUSINESS_CREATION/EXISTING_BUSINESS_AUDIT.
A ENTITY: LEGAL_NAME, ENTITY_TYPE, STATE, FORMATION_DATE, GOOD_STANDING, EIN_PRESENT, REGISTERED_AGENT, BUSINESS_ADDRESS, ADDRESS_TYPE, LICENSES_REQUIRED, LICENSES_PRESENT.
B IDENTITY: DOMAIN_PRESENT, DOMAIN, WEBSITE_PRESENT, PROFESSIONAL_EMAIL_PRESENT, BUSINESS_PHONE_PRESENT, GOOGLE_BUSINESS_PROFILE_PRESENT, BUSINESS_LISTINGS_CONSISTENT.
C BANKING: BUSINESS_BANK_ACCOUNT_PRESENT, BANK_NAME, ACCOUNT_TYPE, ACCOUNT_OPEN_DATE, ACCOUNT_AGE, CURRENT_BALANCE, AVERAGE_BALANCE_30, AVERAGE_BALANCE_90, MONTHLY_DEPOSITS, DEPOSIT_CONSISTENCY, PRIMARY_OPERATING_ACCOUNT.
D ACTIVITY: PRIMARY_PRODUCT_OR_SERVICE, PRIMARY_CUSTOMER, PRIMARY_REVENUE_ACTIVITY, WHAT_CUSTOMERS_PAY_FOR, HOW_SERVICE_IS_DELIVERED.
E NAICS: CURRENT_NAICS, CURRENT_NAICS_ACCURATE; determine actual primary activity; for every truthful candidate NAICS, DESCRIPTION, PRIMARY_ACTIVITY_MATCH, REVENUE_ACTIVITY_MATCH, OPERATING_MODEL_MATCH, FUNDING_RISK_IMPLICATION, LICENSING_IMPLICATION, OTHER_COMPLIANCE_CONCERNS; RECOMMENDED_NAICS, WHY, FUNDING_IMPLICATION. Accuracy first; never recommend false classification.
F IDENTITY/CREDIT FILE: DUNS_PRESENT, BUSINESS_CREDIT_FILE_PRESENT, BUSINESS_BUREAUS_PRESENT.
G BUSINESS CREDIT: TRADELINES, VENDOR_ACCOUNTS, REVOLVING_BUSINESS_ACCOUNTS, REPORTING_ACCOUNTS, PAYMENT_HISTORY, BUSINESS_CREDIT_BUILDING_REQUIRED.
H PLAN: BUSINESS_PLAN_PRESENT; if yes CURRENT, STALE, CONSISTENT_WITH_ACTUAL_BUSINESS; if no BUSINESS_PLAN_REQUIRED.
I OPERATIONS: TIME_IN_BUSINESS, MONTHLY_REVENUE, ANNUAL_REVENUE, EMPLOYEES, CONTRACTORS, PRODUCTS, SERVICES, OPERATING_HISTORY.
J PERSONAL CREDIT: PERSONAL_CREDIT_AVAILABLE; if appropriate SCORE_OR_RANGE, RELEVANT_BUREAUS, UTILIZATION, MAJOR_DEROGATORY_FACTORS, INQUIRIES, AGE_OF_CREDIT, PERSONAL_CREDIT_AFFECTS_BUSINESS_FUNDING. PERSONAL_CREDIT_REPAIR_WORKFLOW=NOT_YET_GOVERNED. Do not execute repair.
K classify ENTITY, GOOD_STANDING, EIN, ADDRESS, DOMAIN, WEBSITE, EMAIL, PHONE, BANK_ACCOUNT, BANK_AGE, BANK_BALANCE, DEPOSIT_HISTORY, NAICS, DUNS, GOOGLE_BUSINESS, BUSINESS_PLAN, LICENSES, BUSINESS_CREDIT, PERSONAL_CREDIT_READINESS as COMPLETE/MISSING/NEEDS_CORRECTION/NOT_APPLICABLE.
L ordered actions: ACTION, OWNER, COMPLETION_CRITERIA. M HANDOFF: BUSINESS_CREATION_COMPLETE_ENOUGH_FOR_FUNDING_REVIEW; if NO NEXT_ACTION; if YES NEXT_OWNER=CLYDE.''',
'FOREX_INDICATOR_STRATEGY_FEEDER':'''PURPOSE: Extract a Forex/indicator strategy from a public source. Creator assertions are SOURCE_CLAIM. No profitability inference, live execution, or strategy decision.
A IDENTITY: STRATEGY_NAME, STRATEGY_FAMILY, SOURCE_CREATOR, MARKET, SYMBOLS, ASSET_CLASS, TIMEFRAMES, SESSION, SOURCE_VERSION.
B SIGNAL: INDICATORS, FUNCTION_CLASS, PARAMETERS, INPUT_SOURCE, LONG_ENTRY_RULES, SHORT_ENTRY_RULES, CONFIRMATION, FILTERS, REPAINTING_OR_LOOKAHEAD_CLAIMS.
C TRADE MANAGEMENT: ENTRY_TIMING, STOP_METHOD, STOP_RULE, TAKE_PROFIT_METHOD, EXIT_RULE, TRAILING, BREAK_EVEN, PARTIAL_EXIT, POSITION_SIZING, RISK_PER_TRADE, MAX_CONCURRENT_TRADES.
D TEST CLAIMS: SOURCE_DATE_RANGE, SIGNAL_COUNT, TRADE_COUNT, WIN_RATE, PROFIT_FACTOR, EXPECTANCY, NET_RETURN, MAX_DRAWDOWN, COSTS, SLIPPAGE, DATA_SOURCE; classify every metric SOURCE_CLAIM/CROSS_SUPPORTED/VERIFIED/CONTRADICTED/RESEARCH_REQUIRED.
E IMPLEMENTATION: SOURCE_CODE_AVAILABLE, PINE_VERSION, DEPENDENCIES, ENGINE, BAR_ASSUMPTIONS, FILL_MODEL, COMMISSION_MODEL, DATA_QUALITY, ENGINE_PARITY_REQUIRED.
F COMPLETENESS: RULES_REPRODUCIBLE, DATA_SOURCE_VERIFIED, BASELINE_REPRODUCED, COST_MODEL_PRESENT, SAMPLE_ADEQUATE, OUT_OF_SAMPLE_PRESENT, PARITY_PASS. Exact gap question for each NO.
G RECOMMENDATION: PROMOTE_TO_TRADING_BASELINE/ADDITIONAL_RESEARCH_REQUIRED/IMPLEMENTATION_PARITY_INVESTIGATION/REFERENCE_ONLY; action and next owner TRADING or RESEARCH/SYSTEMS by deterministic dependency.''',
'OPTIONS_STRATEGY_FEEDER':'''PURPOSE: Extract options strategies from transcript/article/code. Creator assertions start SOURCE_CLAIM. Do not treat creator claims as verified facts or recommend live orders.
A IDENTITY: STRATEGY_NAME, STRATEGY_FAMILY=WHEEL/CASH_SECURED_PUT/COVERED_CALL/VERTICAL/IRON_CONDOR/BUTTERFLY/CALENDAR/DIAGONAL/STRADDLE/STRANGLE/RATIO_SPREAD/BACKSPREAD/CUSTOM_MULTI_LEG/OTHER, MARKET_OUTLOOK, VOLATILITY_OUTLOOK.
B UNDERLYING: UNDERLYING_SELECTION_RULES, EXAMPLE_TICKER, ASSET_CLASS, FUNDAMENTAL_REQUIREMENTS, TREND_REQUIREMENTS, VOLATILITY_REQUIREMENTS, LIQUIDITY_REQUIREMENTS.
C Each leg: BUY_OR_SELL, CALL_OR_PUT, QUANTITY, STRIKE_SELECTION_RULE, DELTA_RULE, DTE_RULE, EXPIRATION_RELATIONSHIP.
D ECONOMICS: DEBIT_OR_CREDIT, MAX_LOSS, THEORETICAL_MAX_PROFIT, BREAK_EVEN, CAPITAL_REQUIRED, BUYING_POWER_REQUIRED.
E GREEKS/VOL: DELTA, GAMMA, THETA, VEGA, IV_REQUIREMENT, IV_RANK_OR_PERCENTILE, VOLATILITY_ASSUMPTION.
F LIQUIDITY: BID_ASK_SPREAD, OPEN_INTEREST, OPTION_VOLUME, UNDERLYING_VOLUME.
G MANAGEMENT: ENTRY_RULES, PROFIT_TAKE_RULE, STOP_RULE, TIME_EXIT, ROLL_RULE, ASSIGNMENT_RULE, EXERCISE_RULE, EXPIRATION_RULE.
H PORTFOLIO: RISK_PER_TRADE, MAX_POSITION_ALLOCATION, CASH_RESERVE_RULE, MAX_CONCURRENT_POSITIONS.
I RISKS: ASSIGNMENT, EARLY_EXERCISE, PIN, EXPIRATION, LIQUIDITY, SLIPPAGE, EVENT, EARNINGS, VOLATILITY, GAP.
J Each material assertion classified SOURCE_CLAIM/CROSS_SUPPORTED/VERIFIED/CONTRADICTED/RESEARCH_REQUIRED with source.
K exact practice questions: DTE, delta, strike spacing, underlying, IV regime, management, profit target, assignment, capital lockup, money management, portfolio allocation.''',
'RAY_NOVA_OPPORTUNITY_INTAKE':'''FIRST-PASS OPPORTUNITY CRITERIA v1. Analyze Ray-originated business ideas without requiring external source. Persist SOURCE=RAY_NOVA, IDEA_SUMMARY, BUSINESS_MODEL, TARGET_CUSTOMER, CUSTOMER_PROBLEM, PRODUCT_OR_SERVICE, VALUE_PROPOSITION, REVENUE_MODEL, WHY_THIS_MIGHT_WORK, OBVIOUS_STRENGTHS, OBVIOUS_WEAKNESSES, DEMAND_SIGNAL, NEXUS_CAPABILITY_FIT, COST_FREE_OR_LOW_COST_PATH, LIKELY_STARTUP_COMPLEXITY, AFFILIATE_POTENTIAL, WHITE_LABEL_POTENTIAL, PARTNER_POTENTIAL, FUNDING_REQUIRED_LIKELY, MAJOR_UNKNOWN, MAJOR_RISK, RESEARCH_GAPS. Conversational response: WHAT_LOOKS_STRONG, WHAT_LOOKS_WEAK, WHAT_NEXUS_ALREADY_HAS, LOW_COST_PATH, WHAT_WE_STILL_NEED_TO_KNOW, MAJOR_RISK, RECOMMENDATION. Recommendation only DISCUSS_FURTHER/SEND_TO_RESEARCH/SAVE_FOR_LATER. Ray owns the final choice. Never approve/reject/shelve a business.'''
}

def now(): return datetime.now(timezone.utc).isoformat()
def _load_env():
    sys.path.insert(0,str(ROOT/'scripts/ops'))
    from nexus_runtime_env import load_runtime_env
    load_runtime_env()
def _request(path,method='GET',body=None,prefer='return=minimal'):
    # Durable workers already provide their job ID. Legacy one-shot feeder
    # invocations receive a process-scoped context so the same egress guard
    # still aggregates bounded reads/writes instead of silently running
    # outside the job budget. These commands are short-lived entry points.
    os.environ.setdefault('NEXUS_DURABLE_JOB_ID',f"feeder-process-{os.getpid()}")
    _load_env();base=(os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL') or '').rstrip('/');key=os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not base or not key: raise RuntimeError('SUPABASE_NOT_CONFIGURED')
    try:
        from nexus_agent_platform.supabase_egress_guard import record_request, safe_mode_enabled, preflight_request
        retries=0 if safe_mode_enabled() else max(0,min(1,int(os.getenv('NEXUS_SUPABASE_MAX_RETRIES','1'))))
    except Exception:
        from nexus_agent_platform.supabase_egress_guard import record_request, preflight_request
        retries=0
    safe_write=(method.upper() in {'GET','HEAD','OPTIONS','PATCH'} or (method.upper()=='POST' and 'on_conflict=' in path))
    attempt=0
    while True:
        preflight_request(method,path)
        req=urllib.request.Request(base+'/rest/v1/'+path,data=None if body is None else json.dumps(body).encode(),method=method,headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json','Prefer':prefer})
        try:
            try: import certifi;ctx=ssl.create_default_context(cafile=certifi.where())
            except ImportError:ctx=ssl.create_default_context()
            with urllib.request.urlopen(req,timeout=20,context=ctx) as r:
                raw=r.read();result=json.loads(raw or b'[]')
                record_request(method,path,r.status,len(raw),rows=len(result) if isinstance(result,list) else 0,retries=attempt,trace=False)
                return result
        except urllib.error.HTTPError as e:
            error_body=e.read()
            record_request(method,path,e.code,len(error_body),retries=attempt,trace=False)
            if safe_write and attempt < retries and e.code in {408,429,500,502,503,504,522}:
                attempt+=1;__import__('time').sleep(min(2**attempt,2));continue
            raise RuntimeError(f'SUPABASE_HTTP_{e.code}:{error_body.decode(errors="replace")[:240]}') from e
        except (urllib.error.URLError,TimeoutError,ssl.SSLError) as e:
            record_request(method,path,0,0,retries=attempt,trace=False)
            if safe_write and attempt < retries:
                attempt+=1;__import__('time').sleep(min(2**attempt,2));continue
            raise RuntimeError(f'SUPABASE_TRANSPORT_ERROR:{type(e).__name__}') from e
def _hash(value): return hashlib.sha256(str(value).encode()).hexdigest()
def _stable(prefix,value): return prefix+'_'+hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()[:20]

def _create_durable_event_job(department,job_type,payload_ref,event_id,source_id=None):
    """Persist the next transition from the event that just completed."""
    from nexus_agent_platform.durable_jobs import default_store
    correlation=os.environ.get('NEXUS_JOB_CORRELATION_ID') or _stable('corr',source_id or event_id)
    parent=os.environ.get('NEXUS_DURABLE_JOB_ID') or None
    store=default_store()
    key='workflow:'+_stable('evt',event_id)+':'+job_type
    return store.enqueue(department,job_type,payload_ref=payload_ref,parent_job_id=parent,
                         correlation_id=correlation,idempotency_key=key)
def initialize():
    rows=[]
    for typ,prompt in PROMPTS.items():
        rows.append({'template_id':typ.lower()+'_v1','feeder_type':typ,'version':'v1','prompt_body':prompt,'active':True,'notebook_type':typ,'notebook_owner':'RESEARCH','notebook_manager':'RESEARCH','updated_at':now()})
    for row in rows:_request('nexus_feeder_templates?on_conflict=feeder_type','POST',row,'resolution=merge-duplicates,return=minimal')
    slots=[]
    for typ in list(ROUTES)[:5]:
        for i in range(1,4):slots.append({'batch_slot_id':_stable('slot',(BATCH,typ,i)),'batch_name':BATCH,'feeder_type':typ,'slot_number':i,'status':'WAITING_FOR_SOURCE'})
    for row in slots:_request('nexus_feeder_batch_slots?on_conflict=batch_slot_id','POST',row,'resolution=merge-duplicates,return=minimal')
    components=['FEEDER_INTAKE_WORKER','FEEDER_QUESTIONNAIRE_WORKER','RESEARCH_GAP_WORKER','HANDOFF_WORKER','BUSINESS_OPPORTUNITY_FEEDER','BUSINESS_FUNDING_FEEDER','BUSINESS_CREATION_FEEDER','FOREX_FEEDER','OPTIONS_FEEDER','RAY_NOVA_OPPORTUNITY_INTAKE','SUPABASE_FEEDER_TABLES','SUPABASE_HANDOFF_TABLES','SUPABASE_BANK_TABLES','NOTEBOOK_TEMPLATE_REGISTRY','FEEDER_BATCH_RUNTIME','NOVA_INTAKE_RUNTIME','NOVA_RESEARCH_HANDOFF_RUNTIME']
    for c in components:_request('nexus_feeder_system_registry?on_conflict=component_id','POST',{'component_id':c,'component_group':'NOVA' if c.startswith('NOVA') or 'RAY_NOVA' in c else 'FEEDER','enabled':True,'status':'IDLE_HEALTHY','next_workflow':'PROCESS_ON_CANONICAL_KERNEL_WAKE'},'resolution=merge-duplicates,return=minimal')
    templates=_request('nexus_feeder_templates?select=template_id,feeder_type,version,prompt_body,active&active=eq.true')
    fetched_slots=_request('nexus_feeder_batch_slots?select=batch_slot_id,status&batch_name=eq.'+urllib.parse.quote(BATCH,safe=''))
    return {'templates':len(templates),'template_types':sorted(x['feeder_type'] for x in templates),'slot_count':len(fetched_slots),'component_count':len(_request('nexus_feeder_system_registry?select=component_id'))}

def detect_source(source_id):
    rows=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&select=source_id,feeder_type,source_url,content_hash,source_title,notebook_reference,ingestion_status')
    if not rows:raise ValueError('SOURCE_NOT_FOUND')
    row=rows[0];typ=row['feeder_type']
    prior=_request('nexus_feeder_sources?source_id=neq.'+urllib.parse.quote(source_id,safe='')+'&feeder_type=eq.'+typ+'&select=source_id,source_url,content_hash,source_title,notebook_reference,ingestion_status')
    duplicates=[p for p in prior if p.get('ingestion_status')!='BLOCKED' and (
        (row.get('source_url') and p.get('source_url')==row.get('source_url')) or
        (row.get('content_hash') and p.get('content_hash')==row.get('content_hash')) or
        (row.get('source_title') and p.get('source_title')==row.get('source_title') and (not row.get('notebook_reference') or p.get('notebook_reference')==row.get('notebook_reference'))))]
    if duplicates:
        update={'ingestion_status':'BLOCKED','block_reason':'DUPLICATE_SOURCE','updated_at':now()}
    elif typ not in ROUTES:
        update={'ingestion_status':'BLOCKED','block_reason':'UNSUPPORTED_FEEDER_TYPE','updated_at':now()}
    else:update={'ingestion_status':'READY_FOR_QUESTIONNAIRE','route_department':ROUTES[typ][0],'next_owner':'FEEDER_QUESTIONNAIRE_WORKER','updated_at':now()}
    _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe=''),'PATCH',update)
    return update

def _gaps(typ,output):
    declared=output.get('RESEARCH_GAPS') or output.get('research_gaps') or []
    if isinstance(declared,str):declared=[declared]
    questions=[]
    for gap in declared:
        q=gap.get('question') if isinstance(gap,dict) else str(gap)
        if q and q not in questions:questions.append(q)
    # Each type has hard minimum completeness fields. Missing evidence becomes
    # a question, never a fabricated answer.
    required={
      'BUSINESS_OPPORTUNITY_FEEDER':['BUSINESS_MODEL','TARGET_CUSTOMER','CUSTOMER_PROBLEM','REVENUE_MODEL','DEMAND_EVIDENCE','COMPETITORS','BASIC_COST_STRUCTURE','RISKS'],
      'BUSINESS_FUNDING_FEEDER':['LENDER','PRODUCT','CURRENT_REQUIREMENTS','CREDIT_REQUIREMENTS','PRICING','APPLICATION_PATH','GEOGRAPHY'],
      'BUSINESS_CREATION_BANKABILITY_FEEDER':['BUSINESS_EXISTS','ENTITY_TYPE','PRIMARY_ACTIVITY','NAICS','BANK_ACCOUNT','KNOWN_GAPS'],
      'FOREX_INDICATOR_STRATEGY_FEEDER':['STRATEGY_FAMILY','ENTRY_RULES','EXIT_RULES','MARKET','TIMEFRAME','DATA_SOURCE','COST_MODEL'],
      'OPTIONS_STRATEGY_FEEDER':['STRATEGY_FAMILY','UNDERLYING_SELECTION_RULES','LEGS','MAX_LOSS','BREAK_EVEN','DTE','LIQUIDITY','MANAGEMENT_RULES'],
      'RAY_NOVA_OPPORTUNITY_INTAKE':['BUSINESS_MODEL','TARGET_CUSTOMER','CUSTOMER_PROBLEM','REVENUE_MODEL','DEMAND_SIGNAL','MAJOR_RISK']}
    for field in required[typ]:
        value=output.get(field) or output.get(field.lower())
        if value is None or value=='' or value is False:
            q=f'What evidence establishes {field.replace("_"," ").lower()} for this opportunity/source?'
            if q not in questions:questions.append(q)
    return questions

def _analyze_unstructured_source(row,template):
    """Run the configured Nexus model on transcript-only intake.

    Evidence labels remain conservative: model-generated factual assertions are
    source claims unless a separate verification packet supplies proof.
    Routing is still selected below from ROUTES, never from model output.
    """
    _load_env()
    from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter
    model=os.getenv('RESEARCH_AI_MODEL') or os.getenv('OPENROUTER_MODEL') or 'openai/gpt-4o-mini'
    payload={
        'source_title':row.get('source_title'),'source_url':row.get('source_url'),
        'source_creator':row.get('source_creator'),'source_date':row.get('source_date'),
        'transcript_or_extract':row.get('transcript_or_extract'),
        'notebook_output':row.get('notebook_output') or row.get('structured_input') or {},
    }
    messages=[
        {'role':'system','content':'You are a bounded Nexus feeder analyst. Answer the fixed questionnaire from the supplied evidence only. Return one JSON object, no markdown. Do not invent missing facts or numbers. Claims from the source are SOURCE_CLAIM, not VERIFIED. Leave unsupported fields null and add exact questions to RESEARCH_GAPS. Do not approve/reject/shelve, do not choose routing or a next owner.'},
        {'role':'user','content':str(template[0]['prompt_body'])+'\n\nSOURCE_PACKET_JSON:\n'+json.dumps(payload,ensure_ascii=False)[:50000]},
    ]
    result=asyncio.run(LlmGatewayAdapter('nexus_feeder_questionnaire').completion(
        model=model,messages=messages,temperature=0.1,max_tokens=6000,timeout=60))
    if result.get('error') or not result.get('content'):
        raise RuntimeError('FEEDER_ANALYSIS_PROVIDER_'+str(result.get('error') or 'EMPTY_RESPONSE'))
    content=str(result['content']).strip()
    content=re.sub(r'^```(?:json)?\s*|\s*```$','',content,flags=re.I)
    try:output=json.loads(content)
    except (ValueError,TypeError) as exc:raise RuntimeError('FEEDER_OUTPUT_REPAIR:MODEL_JSON_INVALID') from exc
    if not isinstance(output,dict):raise RuntimeError('FEEDER_OUTPUT_REPAIR:MODEL_OUTPUT_NOT_OBJECT')
    output['SOURCE_CLAIMS']=[{**(x if isinstance(x,dict) else {'claim':str(x)}),'evidence_level':'SOURCE_CLAIM'} for x in output.get('SOURCE_CLAIMS',[])]
    output['VERIFIED_FIELDS']=[]
    output['_analysis_metadata']={'provider_model':result.get('model',model),'source_basis':'TRANSCRIPT_AND_SUPPLIED_STRUCTURED_INPUT','verification':'NOT_PERFORMED'}
    return output

def run_questionnaire(source_id,row=None,template=None):
    if row is None:
        rows=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&select=source_id,feeder_type,source_type,source_title,source_url,source_creator,source_date,notebook_reference,notebook_output,structured_input,case_id,ray_opportunity_id')
        if not rows:raise ValueError('SOURCE_NOT_FOUND')
        row=rows[0]
    typ=row['feeder_type']
    if template is None:template=_request('nexus_feeder_templates?feeder_type=eq.'+typ+'&active=eq.true&select=version,prompt_body&limit=1')
    elif isinstance(template,dict):template=[template]
    if not template:raise RuntimeError('ACTIVE_TEMPLATE_MISSING')
    output=row.get('notebook_output') or row.get('structured_input') or {}
    if not isinstance(output,dict):
        _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe=''),'PATCH',{'ingestion_status':'BLOCKED','block_reason':'FEEDER_OUTPUT_REPAIR','updated_at':now()})
        raise ValueError('FEEDER_OUTPUT_REPAIR')
    supplied_fields=sum(v not in (None,'',[],{}) for v in output.values())
    if row.get('source_type')!='CERTIFICATION_FIXTURE' and supplied_fields<12:
        transcript=None
        try:
            from nexus_agent_platform.transcript_artifacts import load_transcript
            transcript=load_transcript(source_id,source_type=row.get('source_type') or 'YOUTUBE')
        except (OSError, ValueError, IOError):
            transcript=None
        if transcript is None:
            # Explicit, source-scoped compatibility path for legacy rows only.
            legacy=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&select=transcript_or_extract&limit=1')
            transcript=(legacy[0].get('transcript_or_extract') if legacy else None)
        if transcript:
            analysis_row={**row,'transcript_or_extract':transcript}
            output=_analyze_unstructured_source(analysis_row,template)
    claims=output.get('SOURCE_CLAIMS') or output.get('source_claims') or []
    claims=[{**(c if isinstance(c,dict) else {'claim':str(c)}),'evidence_level':'SOURCE_CLAIM'} for c in claims]
    verified=output.get('VERIFIED_FIELDS') or []
    contradictions=output.get('CONTRADICTIONS') or []
    gaps=_gaps(typ,output)
    runid=_stable('fq',(source_id,template[0]['version']))
    route=ROUTES[typ][0]
    action='RESEARCH_GAP_CLOSURE' if gaps else 'FORMAL_DEPARTMENT_HANDOFF'
    owner='RESEARCH' if gaps else route
    run={'run_id':runid,'source_id':source_id,'feeder_type':typ,'questionnaire_version':template[0]['version'],'started_at':now(),'completed_at':now(),'status':'QUESTIONNAIRE_COMPLETE','structured_fields':output,'source_claims':claims,'verified_fields':verified,'contradictions':contradictions,'research_gaps':gaps,'exact_research_questions':gaps,'recommended_next_action':action,'next_owner':owner}
    _request('nexus_feeder_questionnaire_runs?on_conflict=run_id','POST',run,'resolution=merge-duplicates,return=minimal')
    gap_rows=[]
    for q in gaps:
        qid=_stable('fqgap',(source_id,q));gap_rows.append({'question_id':qid,'source_id':source_id,'question':q,'why_it_matters':'Required feeder evidence is absent or unresolved.','return_to':route,'status':'IN_PROGRESS' if typ!='RAY_NOVA_OPPORTUNITY_INTAKE' else 'OPEN','research_request_id':qid if typ!='RAY_NOVA_OPPORTUNITY_INTAKE' else None})
    if gap_rows:_request('nexus_feeder_research_gaps?on_conflict=question_id','POST',gap_rows,'resolution=merge-duplicates,return=minimal')
    if typ!='RAY_NOVA_OPPORTUNITY_INTAKE':
        for gap in gap_rows:_enqueue_gap(row,gap['question_id'],gap['question'],route)
    status='RESEARCH_REQUIRED' if gaps else 'READY_FOR_HANDOFF'
    _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe=''),'PATCH',{'ingestion_status':status,'next_owner':owner,'route_department':route,'updated_at':now()})
    if gaps and typ!='RAY_NOVA_OPPORTUNITY_INTAKE':
        create_research_handoff(source_id,gaps,src=row,run=run)
        for gap in gap_rows:
            _create_durable_event_job('RESEARCH','RESEARCH_GAP_VERIFY',gap['question_id'],f"gap:{gap['question_id']}",source_id)
    if not gaps and typ!='RAY_NOVA_OPPORTUNITY_INTAKE':create_handoff(source_id,src=row,run=run)
    return {'run_id':runid,'source_id':source_id,'status':status,'gaps':gaps,'route_department':route,'next_owner':owner,'prompt_version':template[0]['version']}

def _enqueue_gap(source,qid,question,return_to):
    from nexus_agent_platform.research_work_queue import ResearchWorkQueue
    sys.path.insert(0,str(ROOT/'scripts/research'))
    from notebook_source_expansion import recommend_method
    notebook=source.get('notebook_reference')
    method=recommend_method(question,notebook_reference=notebook)
    return ResearchWorkQueue().enqueue(work_id=qid,work_class='ASSIGNED',request_type='FEEDER_GAP_CLOSURE',title=f"{source.get('source_title') or source['feeder_type']} gap closure",search_context=source.get('source_title') or source['feeder_type'],objective=f'Answer exactly: {question}',question=question,research_question=question,exact_research_question=question,research_instructions='Answer only this unresolved material question. Do not repeat full source analysis.',source_type=source['source_type'],source_url=source.get('source_url'),source_id=source['source_id'],notebook_reference=notebook,notebook_id=notebook,recommended_research_method=method,department_target='RESEARCH',requested_by='FEEDER_QUESTIONNAIRE_WORKER',priority=20,return_target=return_to,parent_request_id=source['source_id'],expected_output='Evidence-backed answer packet and source references',evidence_gaps=[question],dedup_key=qid)

def create_research_handoff(source_id,gaps,src=None,run=None):
    if src is None:src=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&select=source_id,feeder_type,source_type,source_title,source_url,source_creator,source_date,notebook_reference,notebook_type,notebook_owner,notebook_manager,case_id,ray_opportunity_id')[0]
    if run is None:run=_request('nexus_feeder_questionnaire_runs?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&order=started_at.desc&limit=1')[0]
    hid=_stable('fho',(source_id,'RESEARCH'))
    # Handoff only compact source metadata. Transcript/source text already lives
    # on the source record and must not be copied into another JSONB payload.
    source_ref={key:src.get(key) for key in ('source_id','feeder_type','source_type','source_title','source_url','source_creator','source_date','notebook_reference','notebook_type','notebook_owner','notebook_manager','case_id')}
    row={'handoff_id':hid,'source_id':source_id,'case_id':src.get('case_id') or _stable('case',source_id),'from_department':src['feeder_type'],'to_department':'RESEARCH','summary':f"Resolve {len(gaps)} exact material research gaps for {src['source_title']}",'structured_data':{'source':source_ref,'questionnaire':run['structured_fields'],'source_claims':run['source_claims'],'exact_research_gaps':gaps,'return_to':ROUTES[src['feeder_type']][0]},'what_was_completed':['Source detected','Fixed questionnaire completed','Unresolved material questions isolated'],'what_remains':gaps,'recommendation':'RESEARCH_GAP_CLOSURE','action':'Answer only the enumerated research questions and return directly to the originating feeder workflow','expected_output':'Evidence-backed answers with source references','status':'CREATED'}
    _request('nexus_feeder_handoffs?on_conflict=handoff_id','POST',row,'resolution=merge-duplicates,return=minimal')
    return row

def create_handoff(source_id, *, force=False,src=None,run=None,gaps=None):
    if src is None:
        srcs=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&select=source_id,feeder_type,source_type,source_title,source_url,source_creator,source_date,notebook_reference,notebook_type,notebook_owner,notebook_manager,case_id,ray_opportunity_id')
        if not srcs:raise ValueError('SOURCE_NOT_FOUND')
        src=srcs[0]
    if run is None:
        runs=_request('nexus_feeder_questionnaire_runs?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&order=started_at.desc&limit=1')
        if not runs:raise ValueError('QUESTIONNAIRE_NOT_COMPLETE')
        run=runs[0]
    if gaps is None:gaps=_request('nexus_feeder_research_gaps?source_id=eq.'+urllib.parse.quote(source_id,safe='')+'&status=neq.COMPLETED&select=question_id')
    if gaps and not force:raise ValueError('MATERIAL_RESEARCH_GAPS_OPEN')
    route=('BUSINESS_OPPORTUNITIES' if src['feeder_type']=='RAY_NOVA_OPPORTUNITY_INTAKE' and force else ROUTES[src['feeder_type']][0])
    packet=run['structured_fields'];case=src.get('case_id') or _stable('case',source_id);hid=_stable('fho',(source_id,route))
    source_ref={key:src.get(key) for key in ('source_id','feeder_type','source_type','source_title','source_url','source_creator','source_date','notebook_reference','notebook_type','notebook_owner','notebook_manager','case_id')}
    row={'handoff_id':hid,'source_id':source_id,'opportunity_id':src.get('ray_opportunity_id'),'case_id':case,'from_department':'RESEARCH' if src['feeder_type']!='RAY_NOVA_OPPORTUNITY_INTAKE' or force else 'NOVA','to_department':route,'summary':src['source_title'],'structured_data':{'source':source_ref,'questionnaire':packet,'source_claims':run['source_claims']},'what_was_completed':['Source detection','Fixed feeder questionnaire','Structured output persisted'],'what_remains':[g['question'] for g in gaps],'recommendation':run['recommended_next_action'] or 'DEPARTMENT_REVIEW','action':'Continue from persisted feeder packet','expected_output':f'{route} accepts and continues the existing case','status':'CREATED'}
    _request('nexus_feeder_handoffs?on_conflict=handoff_id','POST',row,'resolution=merge-duplicates,return=minimal')
    notebook_owner={'BUSINESS_OPPORTUNITY_FEEDER':'ATLAS','BUSINESS_FUNDING_FEEDER':'CLYDE','BUSINESS_CREATION_BANKABILITY_FEEDER':'BUSINESS_CREATION','FOREX_INDICATOR_STRATEGY_FEEDER':'MERCURY','OPTIONS_STRATEGY_FEEDER':'MERCURY','RAY_NOVA_OPPORTUNITY_INTAKE':'RESEARCH'}[src['feeder_type']]
    _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source_id,safe=''),'PATCH',{'ingestion_status':'HANDED_OFF','next_owner':route,'route_department':route,'notebook_owner':notebook_owner,'notebook_manager':'RESEARCH','case_id':case,'updated_at':now()})
    _create_durable_event_job('SYSTEMS','FORMAL_HANDOFF',hid,f"handoff:{hid}",source_id)
    return row

def continue_research_gap(question_id):
    """Apply one completed Research receipt to its feeder gap; do not scan peers."""
    from nexus_agent_platform.research_work_queue import ResearchWorkQueue
    qid=str(question_id)
    queue=ResearchWorkQueue(); item=next((x for x in queue.load().get('items',[]) if str(x.get('work_id'))==qid),None)
    if not item or item.get('status') not in {'COMPLETE','COMPLETED'}: return {'status':'WAITING','question_id':qid}
    result=item.get('last_result') if isinstance(item.get('last_result'),dict) else {}
    if result.get('evidence_state')=='RESEARCH_REQUIRED' or result.get('gap_state') not in {None,'COMPLETED'}: return {'status':'RESEARCH_REQUIRED','question_id':qid}
    rows=_request('nexus_feeder_research_gaps?question_id=eq.'+urllib.parse.quote(qid,safe='')+'&select=question_id,source_id,status&limit=1')
    if not rows: return {'status':'UNKNOWN_GAP','question_id':qid}
    gap=rows[0]; sid=str(gap['source_id'])
    answer={'result':result,'artifact_id':item.get('artifact_id'),'result_id':item.get('result_id'),'evidence_refs':item.get('evidence_refs',[]),'completed_at':item.get('completed_at')}
    _request('nexus_feeder_research_gaps?question_id=eq.'+urllib.parse.quote(qid,safe=''),'PATCH',{'status':'COMPLETED','answer_packet':answer,'updated_at':now()})
    remaining=_request('nexus_feeder_research_gaps?source_id=eq.'+urllib.parse.quote(sid,safe='')+'&status=neq.COMPLETED&select=question_id&limit=1')
    if remaining: return {'status':'GAP_CLOSED','question_id':qid,'source_id':sid,'next_job_count':0}
    _create_durable_event_job('FEEDER','FEEDER_RESEARCH_CONTINUATION',sid,f"research-closed:{sid}",sid)
    return {'status':'SOURCE_GAPS_CLOSED','question_id':qid,'source_id':sid,'next_job_count':1}

def continue_source(source_id):
    sid=str(source_id)
    sources=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(sid,safe='')+'&select=source_id,feeder_type,source_type,source_title,source_url,source_creator,source_date,notebook_reference,notebook_type,notebook_owner,notebook_manager,case_id,ray_opportunity_id&limit=1')
    if not sources: raise ValueError('SOURCE_NOT_FOUND')
    open_gaps=_request('nexus_feeder_research_gaps?source_id=eq.'+urllib.parse.quote(sid,safe='')+'&status=neq.COMPLETED&select=question_id&limit=1')
    if open_gaps:return {'status':'WAITING_FOR_RESEARCH_GAPS','source_id':sid}
    runs=_request('nexus_feeder_questionnaire_runs?source_id=eq.'+urllib.parse.quote(sid,safe='')+'&select=source_id,structured_fields,source_claims,recommended_next_action,started_at&order=started_at.desc&limit=1')
    if not runs: raise ValueError('QUESTIONNAIRE_NOT_COMPLETE')
    handoff=create_handoff(sid,src=sources[0],run=runs[0],gaps=[])
    return {'status':'FORMAL_HANDOFF_CREATED','source_id':sid,'handoff_id':handoff['handoff_id']}

def handoff_once(handoff_id):
    rows=_request('nexus_feeder_handoffs?handoff_id=eq.'+urllib.parse.quote(str(handoff_id),safe='')+'&select=handoff_id,to_department,status,source_id,case_id&limit=1')
    if not rows: raise ValueError('HANDOFF_NOT_FOUND')
    handoff=rows[0]
    from nexus_agent_platform.durable_jobs import default_store
    parent=os.environ.get('NEXUS_DURABLE_JOB_ID') or None
    correlation=os.environ.get('NEXUS_JOB_CORRELATION_ID') or _stable('corr',handoff['handoff_id'])
    next_job=default_store().enqueue(handoff['to_department'],'HANDOFF_DELIVERY',
        payload_ref='nexus_feeder_handoffs:'+handoff['handoff_id'],parent_job_id=parent,
        correlation_id=correlation,idempotency_key='workflow:'+_stable('handoff-delivery',handoff['handoff_id']))
    return {'status':'FORMAL_HANDOFF_PERSISTED','handoff_id':handoff['handoff_id'],'to_department':handoff['to_department'],'workflow_status':handoff['status'],'next_job_id':next_job.job_id}

def handoff_delivery_once(handoff_ref):
    """Deliver one persisted handoff receipt to its owning department queue."""
    if ':' not in str(handoff_ref): raise ValueError('INVALID_HANDOFF_REFERENCE')
    table,handoff_id=str(handoff_ref).split(':',1)
    if table not in {'nexus_feeder_handoffs','pulse_handoffs'}: raise ValueError('UNSUPPORTED_HANDOFF_TABLE')
    rows=_request(table+'?handoff_id=eq.'+urllib.parse.quote(handoff_id,safe='')+'&select=handoff_id,to_department,status&limit=1')
    if not rows: raise ValueError('HANDOFF_NOT_FOUND')
    row=rows[0]
    if row.get('status') not in {'CREATED','ACCEPTED','COMPLETED','DELIVERED'}: raise ValueError('HANDOFF_NOT_DELIVERABLE')
    return {'status':'HANDOFF_DELIVERED','handoff_id':handoff_id,'to_department':row.get('to_department'),'workflow_status':row.get('status')}

def _nova_analysis(idea, name='GoClear Business Funding'):
    text=str(idea).strip();words=set(re.findall(r'[a-zA-Z]+',text.lower()))
    # Conservative extraction: factual text is stored as Ray-provided hypothesis;
    # no prices/legal claims are synthesized.
    has_funding=bool(words & {'funding','capital','loan','credit','bankability'})
    gaps=['What exact service scope will GoClear provide?','Which customer segment and geography are in scope?','What verified customer demand supports the offer?','What fee or commission model is legally and operationally permissible?','Which lender/affiliate relationships are actually authorized?']
    fields={'OPPORTUNITY_NAME':name,'SOURCE':'RAY_NOVA','IDEA_SUMMARY':text,'BUSINESS_MODEL':'Funding readiness / business funding service hypothesis' if has_funding else None,'TARGET_CUSTOMER':'Business owners seeking capital (Ray-provided framing)' if has_funding else None,'CUSTOMER_PROBLEM':'Credit, bankability, or funding preparation (hypothesis)' if has_funding else None,'PRODUCT_OR_SERVICE':'Funding readiness services (hypothesis)' if has_funding else None,'VALUE_PROPOSITION':None,'REVENUE_MODEL':'Possible fee / commission model; unverified and not priced' if has_funding else None,'WHY_THIS_MIGHT_WORK':'Potentially aligns with existing Clyde funding analysis and client portal capabilities; validate before claims.','OBVIOUS_STRENGTHS':['Possible reuse of Clyde funding capability','Possible client portal workflow reuse'],'OBVIOUS_WEAKNESSES':['Customer demand, delivery scope, compliance and pricing are not yet verified'],'DEMAND_SIGNAL':'RESEARCH_REQUIRED','NEXUS_CAPABILITY_FIT':['Clyde funding capability','client portal capabilities; validate current scope'],'COST_FREE_OR_LOW_COST_PATH':'Interview and workflow-prototype validation before paid launch; no spend authorized.','LIKELY_STARTUP_COMPLEXITY':'MEDIUM; requires verification','AFFILIATE_POTENTIAL':'Possible; relationship availability unverified','WHITE_LABEL_POTENTIAL':'Research required','PARTNER_POTENTIAL':'Lender/affiliate relationships are hypotheses only','FUNDING_REQUIRED_LIKELY':'NO for initial validation; later amount unknown','MAJOR_UNKNOWN':gaps,'MAJOR_RISK':'Legal/compliance, lender representation, customer acquisition, and unverified economics','RESEARCH_GAPS':gaps,'NOVA_INITIAL_RECOMMENDATION':'SEND_TO_RESEARCH'}
    response={'WHAT_LOOKS_STRONG':['Potential fit with Clyde funding and existing portal capabilities'],'WHAT_LOOKS_WEAK':['Demand, exact service, permissible compensation and partner access are unverified'],'WHAT_NEXUS_ALREADY_HAS':['Clyde funding analysis and client portal capabilities; confirm scope in research'],'LOW_COST_PATH':'Start with no-spend customer/problem validation and a service workflow prototype.','WHAT_WE_STILL_NEED_TO_KNOW':gaps,'MAJOR_RISK':'Avoid implying guaranteed approvals or unverified lender relationships.','RECOMMENDATION':'SEND_TO_RESEARCH'}
    return fields,response

def create_nova_idea(idea, opportunity_name='GoClear Business Funding', *, source='RAY_CONVERSATION', opportunity_id=None):
    opportunity_id=opportunity_id or _stable('novaopp',(source,opportunity_name,idea))
    source_id=_stable('feedsrc',(opportunity_id,'RAY_NOVA_OPPORTUNITY_INTAKE'))
    fields,response=_nova_analysis(idea,opportunity_name)
    row={'source_id':source_id,'feeder_type':'RAY_NOVA_OPPORTUNITY_INTAKE','source_type':source,'source_title':opportunity_name,'transcript_or_extract':idea,'structured_input':fields,'notebook_output':fields,'content_hash':_hash(idea),'ingestion_status':'NEW','next_owner':'NOVA','route_department':'RESEARCH','ray_opportunity_id':opportunity_id,'case_id':_stable('case',opportunity_id)}
    _request('nexus_feeder_sources?on_conflict=source_id','POST',row,'resolution=merge-duplicates,return=minimal')
    opp={'opportunity_id':opportunity_id,'source_id':source_id,'opportunity_name':opportunity_name,'idea_summary':idea,'structured_analysis':fields,'conversational_response':response,'status':'RAY_INTAKE_REVIEW'}
    _request('nexus_ray_nova_opportunities?on_conflict=opportunity_id','POST',opp,'resolution=merge-duplicates,return=minimal')
    _create_durable_event_job('FEEDER','RAY_NOVA_OPPORTUNITY_INTAKE',source_id,f"nova-intake:{opportunity_id}",source_id)
    return {'opportunity_id':opportunity_id,'source_id':source_id,'status':'RAY_INTAKE_REVIEW','structured_analysis':fields,'conversational_response':response}

def ray_action(opportunity_id,action):
    if action not in {'DISCUSS_FURTHER','SEND_TO_RESEARCH','SAVE_FOR_LATER'}:raise ValueError('RAY_ACTION_NOT_ALLOWED')
    rows=_request('nexus_ray_nova_opportunities?opportunity_id=eq.'+urllib.parse.quote(opportunity_id,safe='')+'&select=opportunity_id,source_id,idea_summary,structured_analysis,status')
    if not rows:raise ValueError('OPPORTUNITY_NOT_FOUND')
    o=rows[0];status={'DISCUSS_FURTHER':'DISCUSSING','SEND_TO_RESEARCH':'SENT_TO_RESEARCH','SAVE_FOR_LATER':'SAVED_BY_RAY'}[action]
    _request('nexus_ray_nova_opportunities?opportunity_id=eq.'+urllib.parse.quote(opportunity_id,safe=''),'PATCH',{'ray_action':action,'status':status,'updated_at':now()})
    if action=='DISCUSS_FURTHER':return {'opportunity_id':opportunity_id,'status':status,'duplicate_created':False}
    if action=='SAVE_FOR_LATER':return {'opportunity_id':opportunity_id,'status':status,'preserved':True}
    source=o['source_id'];analysis=o['structured_analysis'];gaprows=_request('nexus_feeder_research_gaps?source_id=eq.'+urllib.parse.quote(source,safe='')+'&select=question_id,question,return_to,status&limit=100')
    src=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(source,safe='')+'&select=source_id,feeder_type,source_type,source_title,source_url,source_creator,source_date,notebook_reference,notebook_type,notebook_owner,notebook_manager,case_id,ray_opportunity_id')[0]
    for gap in gaprows:
        _enqueue_gap(src,gap['question_id'],gap['question'],'BUSINESS_OPPORTUNITY_WORKFLOW')
        _request('nexus_feeder_research_gaps?question_id=eq.'+urllib.parse.quote(gap['question_id'],safe=''),'PATCH',{'status':'IN_PROGRESS','research_request_id':gap['question_id'],'updated_at':now()})
        _create_durable_event_job('RESEARCH','RESEARCH_GAP_VERIFY',gap['question_id'],f"ray-gap:{gap['question_id']}",source)
    res=create_research_handoff(source,[g['question'] for g in gaprows])
    # Handoff packet is a continuation package, not a new full-source intake.
    enriched={**res,'structured_data':{'opportunity_id':opportunity_id,'SOURCE':'RAY_NOVA','IDEA_SUMMARY':o['idea_summary'],'NOVA_INITIAL_ANALYSIS':analysis,'KNOWN_FACTS':[],'RAY_ASSUMPTIONS':[o['idea_summary']],'KNOWN_CUSTOMER':analysis.get('TARGET_CUSTOMER'),'KNOWN_PROBLEM':analysis.get('CUSTOMER_PROBLEM'),'KNOWN_OFFER':analysis.get('PRODUCT_OR_SERVICE'),'KNOWN_REVENUE_MODEL':analysis.get('REVENUE_MODEL'),'QUESTIONS_ALREADY_ANSWERED':['Initial opportunity framing captured by Nova'],'EXACT_RESEARCH_GAPS':analysis.get('RESEARCH_GAPS'),'RESEARCH_OBJECTIVE':'Verify GoClear business funding readiness service demand, scope, unit economics, permissible compensation, and partner access.','RETURN_TO':'BUSINESS_OPPORTUNITY_WORKFLOW','NEXT_OWNER':'RESEARCH'}}
    _request('nexus_feeder_handoffs?handoff_id=eq.'+res['handoff_id'],'PATCH',{'structured_data':enriched['structured_data'],'summary':'Ray/Nova GoClear Business Funding opportunity research continuation','recommendation':'Continue from Nova intake; do not restart source analysis.'})
    return {'opportunity_id':opportunity_id,'status':status,'handoff':enriched}

def sync_research_returns():
    """Close feeder gap tasks from the existing Research queue's persisted receipts."""
    from nexus_agent_platform.research_work_queue import ResearchWorkQueue
    queue=ResearchWorkQueue();items=queue.load().get('items',[]);byid={str(x.get('work_id')):x for x in items}
    recovered=[]
    # Safely requeue only the known empty-URL failure caused by the former
    # source-less feeder-gap route. The current Research router resolves these
    # questions through bounded public search; no evidence is marked complete.
    for item in items:
        error=str((item.get('last_result') or {}).get('error') or '')
        if item.get('request_type')=='FEEDER_GAP_CLOSURE' and item.get('status')=='FAILED_FINAL' and "unknown url type: ''" in error:
            queue.settle(str(item['work_id']),'WAITING',result={'recovery':'EMPTY_URL_RESEARCH_ROUTE_FIXED','prior_error':error},next_eligible_at=now())
            recovered.append(str(item['work_id']))
            item['status']='WAITING'
    gaps=_request('nexus_feeder_research_gaps?status=in.(OPEN,IN_PROGRESS)&select=question_id,source_id,status&limit=200')
    completed=[]
    for gap in gaps:
        item=byid.get(gap['question_id'])
        if not item or item.get('status') not in {'COMPLETE','COMPLETED'}:continue
        prior_result=item.get('last_result') if isinstance(item.get('last_result'),dict) else {}
        if prior_result.get('evidence_state')=='RESEARCH_REQUIRED' or prior_result.get('gap_state') not in {None,'COMPLETED'}:
            # A completed research attempt is not the same as a closed evidence
            # gap. Keep the feeder open when the NotebookLM answer reports an
            # unsupported or irrelevant source set.
            continue
        answer={'result':item.get('last_result'),'artifact_id':item.get('artifact_id'),'result_id':item.get('result_id'),'evidence_refs':item.get('evidence_refs',[]),'completed_at':item.get('completed_at')}
        _request('nexus_feeder_research_gaps?question_id=eq.'+urllib.parse.quote(gap['question_id'],safe=''),'PATCH',{'status':'COMPLETED','answer_packet':answer,'updated_at':now()})
        completed.append(gap['question_id'])
    if completed:
        source_ids=sorted({g['source_id'] for g in gaps if g['question_id'] in completed})
        encoded_ids=','.join(f'"{urllib.parse.quote(sid,safe="")}"' for sid in source_ids)
        remaining_rows=_request('nexus_feeder_research_gaps?source_id=in.('+encoded_ids+')&status=neq.COMPLETED&select=source_id,question_id&limit=500')
        remaining_by_source={str(row.get('source_id')) for row in remaining_rows}
        source_fields='source_id,feeder_type,source_type,source_title,source_url,source_creator,source_date,notebook_reference,notebook_type,notebook_owner,notebook_manager,case_id,ray_opportunity_id'
        source_rows=_request('nexus_feeder_sources?source_id=in.('+encoded_ids+')&select='+source_fields+'&limit=100')
        source_by_id={str(row.get('source_id')):row for row in source_rows}
        run_fields='source_id,structured_fields,source_claims,recommended_next_action,started_at'
        run_rows=_request('nexus_feeder_questionnaire_runs?source_id=in.('+encoded_ids+')&select='+run_fields+'&order=started_at.desc&limit=200')
        run_by_source={}
        for run_row in run_rows:run_by_source.setdefault(str(run_row.get('source_id')),run_row)
        for sid in source_ids:
            if sid in remaining_by_source:continue
            src=source_by_id.get(sid)
            if not src:continue
            route=ROUTES[src['feeder_type']][0]
            _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(sid,safe=''),'PATCH',{'ingestion_status':'READY_FOR_HANDOFF','next_owner':route,'updated_at':now()})
            if src['feeder_type']=='RAY_NOVA_OPPORTUNITY_INTAKE':
                answers=_request('nexus_feeder_research_gaps?source_id=eq.'+urllib.parse.quote(sid,safe='')+'&select=answer_packet')
                passed=any((a.get('answer_packet') or {}).get('result',{}).get('promotion_gate_passed') is True for a in answers)
                if passed:
                    h=create_handoff(sid,force=True,src=src,run=run_by_source.get(sid),gaps=[]);opp_id=src.get('ray_opportunity_id')
                    if opp_id:_request('nexus_ray_nova_opportunities?opportunity_id=eq.'+urllib.parse.quote(opp_id,safe=''),'PATCH',{'status':'IN_ATLAS_WORKFLOW','atlas_opportunity_id':opp_id,'updated_at':now()})
                else:
                    _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(sid,safe=''),'PATCH',{'ingestion_status':'RESEARCH_REQUIRED','next_owner':'RESEARCH','updated_at':now()})
                    rid=_stable('fho',(sid,'RESEARCH'))
                    _request('nexus_feeder_handoffs?handoff_id=eq.'+rid,'PATCH',{'status':'COMPLETED','what_remains':['Research returned; promotion gate evidence has not been certified.'],'updated_at':now()})
            else:create_handoff(sid,src=src,run=run_by_source.get(sid),gaps=[])
    return {'completed_gap_count':len(completed),'question_ids':completed,'recovered_empty_url_task_count':len(recovered),'recovered_question_ids':recovered}

def queue_open_gaps():
    gaps=_request('nexus_feeder_research_gaps?status=eq.OPEN&select=question_id,source_id,question,return_to,research_request_id&limit=200')
    source_ids=sorted({str(g.get('source_id')) for g in gaps if g.get('source_id')})
    if not source_ids:return 0
    encoded_ids=','.join(f'"{urllib.parse.quote(sid,safe="")}"' for sid in source_ids)
    fields='source_id,feeder_type,source_type,source_title,source_url,notebook_reference,ray_opportunity_id'
    source_rows=_request('nexus_feeder_sources?source_id=in.('+encoded_ids+')&select='+fields+'&limit=200')
    source_by_id={str(row.get('source_id')):row for row in source_rows}
    queued=0
    for gap in gaps:
        if gap.get('research_request_id'):continue
        src=source_by_id.get(str(gap.get('source_id')))
        if not src:continue
        if src['feeder_type']=='RAY_NOVA_OPPORTUNITY_INTAKE':
            opps=_request('nexus_ray_nova_opportunities?opportunity_id=eq.'+urllib.parse.quote(src.get('ray_opportunity_id') or '',safe='')+'&select=status')
            if not opps or opps[0]['status']!='SENT_TO_RESEARCH':continue
        _enqueue_gap(src,gap['question_id'],gap['question'],gap['return_to'])
        _request('nexus_feeder_research_gaps?question_id=eq.'+urllib.parse.quote(gap['question_id'],safe=''),'PATCH',{'status':'IN_PROGRESS','research_request_id':gap['question_id'],'updated_at':now()})
        queued+=1
    return queued

def claim_handoff(handoff_id, owner):
    rows=_request('nexus_feeder_handoffs?handoff_id=eq.'+urllib.parse.quote(handoff_id,safe='')+'&select=handoff_id,to_department,status,summary,case_id,source_id,created_at')
    if not rows:raise ValueError('HANDOFF_NOT_FOUND')
    row=rows[0]
    if owner.upper()!=row['to_department'].upper():raise ValueError('HANDOFF_OWNER_MISMATCH')
    if row['status'] not in {'CREATED','CLAIMED'}:raise ValueError('HANDOFF_NOT_CLAIMABLE')
    _request('nexus_feeder_handoffs?handoff_id=eq.'+urllib.parse.quote(handoff_id,safe=''),'PATCH',{'status':'CLAIMED','claimed_by':owner.upper(),'updated_at':now()})
    return {'handoff_id':handoff_id,'status':'CLAIMED','claimed_by':owner.upper()}

def process_once(*, fixture_only=False, feeder_type=None, source_id=None):
    from nexus_agent_platform.supabase_egress_guard import cached_static, safe_mode_enabled
    if not source_id:
        return {'status':'BLOCKED','processed':[],'count':0,'reason':'DURABLE_SOURCE_ID_REQUIRED'}
    settings=cached_static('settings:feeder_runtime',lambda:_request('nexus_feeder_runtime_settings?settings_id=eq.NEXUS_FEEDER_RUNTIME&select=settings_id,external_feeders_enabled,ray_nova_intake_enabled,max_sources_per_wake'),ttl_seconds=60)
    if not settings:raise RuntimeError('FEEDER_RUNTIME_SETTINGS_MISSING')
    cfg=settings[0]
    if cfg.get('external_feeders_enabled') is not True and cfg.get('ray_nova_intake_enabled') is not True:return {'status':'IDLE_HEALTHY','processed':[],'count':0,'reason':'ALL_INTAKES_DISABLED'}
    # Next-stage discovery is event-created by the feeder completion path.
    # A worker handles exactly its referenced source and never scans workflow
    # tables for additional work.
    research_return={'completed_gap_count':0}
    gaps_queued=0
    limit=max(1,min(10,int(cfg.get('max_sources_per_wake',4))))
    if feeder_type: limit=1
    if safe_mode_enabled(): limit=1
    select='source_id,feeder_type,source_type,source_title,source_url,source_creator,source_date,notebook_reference,notebook_type,notebook_owner,notebook_manager,notebook_output,structured_input,content_hash,ingestion_status,case_id,ray_opportunity_id'
    filter_path=('source_id=eq.'+urllib.parse.quote(str(source_id),safe='')+'&' if source_id else '')
    allrows=_request('nexus_feeder_sources?'+filter_path+'ingestion_status=in.(NEW,DETECTED,READY_FOR_QUESTIONNAIRE,FAILED_RETRYABLE)&select='+select+'&order=created_at.asc&limit='+str(1 if source_id else limit))
    allrows=[r for r in allrows if (r['feeder_type']=='RAY_NOVA_OPPORTUNITY_INTAKE' and cfg.get('ray_nova_intake_enabled') is True) or (r['feeder_type']!='RAY_NOVA_OPPORTUNITY_INTAKE' and cfg.get('external_feeders_enabled') is True)]
    if feeder_type:
        if feeder_type not in ROUTES: raise ValueError('UNKNOWN_FEEDER_TYPE')
        allrows=[r for r in allrows if r.get('feeder_type')==feeder_type]
    if fixture_only:allrows=[r for r in allrows if r.get('source_type')=='CERTIFICATION_FIXTURE']
    template_rows=cached_static('template:active_feeder',lambda:_request('nexus_feeder_templates?active=eq.true&select=feeder_type,version,prompt_body'),ttl_seconds=300)
    template_by_type={x['feeder_type']:x for x in template_rows}
    processed=[]
    for row in allrows:
        try:
            if row.get('ingestion_status')=='FAILED_RETRYABLE':
                _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(row['source_id'],safe=''),'PATCH',{'ingestion_status':'READY_FOR_QUESTIONNAIRE','updated_at':now()})
                row['ingestion_status']='READY_FOR_QUESTIONNAIRE'
            detected=detect_source(row['source_id'])
            if detected['ingestion_status']=='BLOCKED':processed.append({'source_id':row['source_id'],'status':'BLOCKED','reason':detected.get('block_reason')});continue
            claimed=_request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(row['source_id'],safe='')+'&ingestion_status=eq.READY_FOR_QUESTIONNAIRE&select=source_id','PATCH',{'ingestion_status':'QUESTIONNAIRE_RUNNING','next_owner':'FEEDER_QUESTIONNAIRE_WORKER','updated_at':now()},'return=representation')
            if not claimed:processed.append({'source_id':row['source_id'],'status':'ALREADY_CLAIMED'});continue
            result=run_questionnaire(row['source_id'],row=row,template=template_by_type.get(row['feeder_type']));processed.append(result)
        except Exception as e:
            repair=str(e).startswith('FEEDER_OUTPUT_REPAIR')
            status='BLOCKED' if repair else 'FAILED_RETRYABLE'
            processed.append({'source_id':row['source_id'],'status':status,'error':str(e)[:300]})
            _request('nexus_feeder_sources?source_id=eq.'+urllib.parse.quote(row['source_id'],safe=''),'PATCH',{'ingestion_status':status,'block_reason':'FEEDER_OUTPUT_REPAIR' if repair else None,'next_owner':'FEEDER_OUTPUT_REPAIR' if repair else 'FEEDER_QUESTIONNAIRE_WORKER','updated_at':now()})
    _update_health(processed)
    return {'status':'PASS' if processed or research_return['completed_gap_count'] or gaps_queued else 'IDLE_HEALTHY','processed':processed,'count':len(processed),'research_return':research_return,'research_gaps_enqueued':gaps_queued}

def _update_health(processed):
    sources=_request('nexus_feeder_sources?select=source_id,feeder_type,ingestion_status,created_at,updated_at&limit=100')
    handoffs=_request('nexus_feeder_handoffs?select=source_id,status,created_at&limit=100')
    gaps_all=_request('nexus_feeder_research_gaps?select=question_id,status,created_at&limit=100')
    templates_all=_request('nexus_feeder_templates?active=eq.true&select=template_id&limit=20')
    slots_all=_request('nexus_feeder_batch_slots?batch_name=eq.'+urllib.parse.quote(BATCH,safe='')+'&select=batch_slot_id,status,feeder_type&limit=100')
    route_registry_rows=[]
    for typ in ROUTES:
        matching=[r for r in sources if r['feeder_type']==typ]; statuses=[r['ingestion_status'] for r in matching]
        queued=[r for r in matching if r['ingestion_status'] in {'NEW','DETECTED','READY_FOR_QUESTIONNAIRE','QUESTIONNAIRE_RUNNING','RESEARCH_REQUIRED','RESEARCH_IN_PROGRESS'}]
        source_ids={r['source_id'] for r in matching}
        hs=[h for h in handoffs if h.get('source_id') in source_ids and h['status'] in {'CREATED','CLAIMED','IN_PROGRESS'}]
        comp='NOVA_INTAKE_RUNTIME' if typ=='RAY_NOVA_OPPORTUNITY_INTAKE' else typ
        age=max([(datetime.now(timezone.utc)-datetime.fromisoformat(r['created_at'].replace('Z','+00:00'))).total_seconds() for r in queued],default=0)
        stale_handoff=max([(datetime.now(timezone.utc)-datetime.fromisoformat(h['created_at'].replace('Z','+00:00'))).total_seconds() for h in hs if h['status']=='CREATED'],default=0)
        registry_status='HANDOFF_STALLED' if stale_handoff>3600 else 'QUEUE_BACKLOG' if age>3600 else 'IDLE_HEALTHY' if not queued else 'PASS'
        wf={'HANDOFF_STALLED':'HANDOFF_RECOVERY','QUEUE_BACKLOG':'FEEDER_QUEUE_RECOVERY','IDLE_HEALTHY':'WAIT_FOR_NEXT_CANONICAL_WAKE','PASS':'CONTINUE_FEEDER_WORKFLOW'}[registry_status]
        body={'component_id':comp,'component_group':'NOVA' if typ=='RAY_NOVA_OPPORTUNITY_INTAKE' else 'FEEDER','enabled':True,'status':registry_status,'next_workflow':wf,'last_activity':max([r['updated_at'] for r in matching],default=None),'oldest_queued_age_seconds':int(age),'queued_count':len(queued),'processing_count':statuses.count('QUESTIONNAIRE_RUNNING'),'research_required_count':statuses.count('RESEARCH_REQUIRED'),'handed_off_count':statuses.count('HANDED_OFF'),'blocked_count':statuses.count('BLOCKED'),'failed_count':statuses.count('FAILED_RETRYABLE'),'unclaimed_handoff_count':len(hs),'evidence':{'worker_run_count':len(processed),'last_worker_results':[{'source_id':x.get('source_id'),'status':x.get('status')} for x in processed[:10]],'source_count':len(matching)}}
        route_registry_rows.append(body)
    common={'last_activity':now(),'next_workflow':'CONTINUE_CANONICAL_FEEDER_RUNTIME','status':'PASS','enabled':True,'component_group':'FEEDER'}
    nova_rows=_request('nexus_ray_nova_opportunities?select=status&limit=100')
    evidence={'processed_count':len(processed),'research_gaps':len(gaps_all),'research_gaps_open':sum(g['status'] in {'OPEN','IN_PROGRESS'} for g in gaps_all),'research_gaps_completed':sum(g['status']=='COMPLETED' for g in gaps_all),'handoffs':len(handoffs),'handoffs_completed':sum(h['status']=='COMPLETED' for h in handoffs),'handoffs_unclaimed':sum(h['status']=='CREATED' for h in handoffs),'templates':len(templates_all),'slots':len(slots_all),'slots_waiting':sum(s['status']=='WAITING_FOR_SOURCE' for s in slots_all),'slots_filled':sum(s['status']!='WAITING_FOR_SOURCE' for s in slots_all),'nova_status_counts':{state:sum(x['status']==state for x in nova_rows) for state in ['RAY_INTAKE_REVIEW','DISCUSSING','SENT_TO_RESEARCH','SAVED_BY_RAY','IN_ATLAS_WORKFLOW']},'last_worker_results':[{'source_id':x.get('source_id'),'status':x.get('status')} for x in processed[:10]]}
    components=['FEEDER_INTAKE_WORKER','FEEDER_QUESTIONNAIRE_WORKER','RESEARCH_GAP_WORKER','HANDOFF_WORKER','SUPABASE_FEEDER_TABLES','SUPABASE_HANDOFF_TABLES','SUPABASE_BANK_TABLES','NOTEBOOK_TEMPLATE_REGISTRY','FEEDER_BATCH_RUNTIME','NOVA_RESEARCH_HANDOFF_RUNTIME','RAY_NOVA_OPPORTUNITY_INTAKE']
    registry_rows=[{**common,'component_id':component,'evidence':evidence} for component in components]
    _request('nexus_feeder_system_registry?on_conflict=component_id','POST',route_registry_rows,'resolution=merge-duplicates,return=minimal')
    _request('nexus_feeder_system_registry?on_conflict=component_id','POST',registry_rows,'resolution=merge-duplicates,return=minimal')
    worker={'worker_id':'canonical-feeder-intake-worker','worker_type':'FEEDER_INTAKE_AND_QUESTIONNAIRE','status':'PASS' if processed else 'IDLE_HEALTHY','last_heartbeat':now(),'receipt':{'processed_count':len(processed),'processed':[{'source_id':x.get('source_id'),'status':x.get('status')} for x in processed[:10]]}}
    _request('nexus_feeder_runtime_heartbeats?on_conflict=worker_id','POST',worker,'resolution=merge-duplicates,return=minimal')
    report=_health_from_rows(sources,gaps_all,handoffs,slots_all,templates_all,
        _request('nexus_ray_nova_opportunities?select=status'))
    out=ROOT/'reports/runtime/feeder_opportunity_intake_status_latest.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({**report,'last_cycle':worker},indent=2)+'\n')

def health_report():
    # Systems and the feeder worker maintain this Supabase-backed snapshot from
    # their readbacks. One small indexed read avoids re-scanning every payload
    # table for each morning report/dashboard refresh.
    rows=_request('nexus_feeder_system_registry?select=component_id,enabled,status,next_workflow,last_activity,oldest_queued_age_seconds,queued_count,processing_count,research_required_count,handed_off_count,blocked_count,failed_count,unclaimed_handoff_count,evidence&limit=100')
    byid={r['component_id']:r for r in rows}
    route_rows={typ:byid.get('NOVA_INTAKE_RUNTIME' if typ=='RAY_NOVA_OPPORTUNITY_INTAKE' else typ,{}) for typ in ROUTES}
    counts={typ:{'sources':r.get('source_count',(r.get('evidence') or {}).get('source_count',0)),'queued':r.get('queued_count',0),'research_required':r.get('research_required_count',0),'handed_off':r.get('handed_off_count',0),'blocked':r.get('blocked_count',0),'failed':r.get('failed_count',0)} for typ,r in route_rows.items()}
    snapshot=next((r.get('evidence') or {} for r in rows if r.get('component_id')=='FEEDER_INTAKE_WORKER'),{})
    if not snapshot and rows:snapshot=(rows[0].get('evidence') or {})
    nowdt=datetime.now(timezone.utc)
    ages=[]
    for r in rows:
        stamp=r.get('last_activity')
        if stamp:
            try:ages.append((nowdt-datetime.fromisoformat(stamp.replace('Z','+00:00'))).total_seconds())
            except ValueError:pass
    stale=max(ages,default=10**9)
    states={str(r.get('status') or 'NOT_CONFIGURED') for r in rows}
    if not rows:overall,nextwf='NOT_CONFIGURED','SUPABASE_RUNTIME_RECOVERY'
    elif 'HANDOFF_STALLED' in states:overall,nextwf='HANDOFF_STALLED','HANDOFF_RECOVERY'
    elif 'QUEUE_BACKLOG' in states:overall,nextwf='QUEUE_BACKLOG','FEEDER_QUEUE_RECOVERY'
    elif 'RESEARCH_STALLED' in states:overall,nextwf='RESEARCH_STALLED','RESEARCH_WORKFLOW_RECOVERY'
    elif stale>1800:overall,nextwf='STALE','SUPABASE_RUNTIME_RECOVERY'
    elif not any(x['queued'] or x['research_required'] for x in counts.values()) and not snapshot.get('handoffs_unclaimed'):overall,nextwf='IDLE_HEALTHY','WAIT_FOR_NEXT_CANONICAL_WAKE'
    else:overall,nextwf='PASS','CONTINUE_FEEDER_WORKFLOW'
    return {'status':overall,'generated_at':now(),'source_counts':counts,'research_gaps':{'open':snapshot.get('research_gaps_open',0),'completed':snapshot.get('research_gaps_completed',0),'oldest_age_seconds':None},'handoffs':{'completed':snapshot.get('handoffs_completed',0),'unclaimed':snapshot.get('handoffs_unclaimed',0),'oldest_unclaimed_age_seconds':None},'batch':{'name':BATCH,'total_slots':snapshot.get('slots',0),'waiting_for_source':snapshot.get('slots_waiting',0),'real_sources_added':snapshot.get('slots_filled',0)},'nova':snapshot.get('nova_status_counts',{}),'templates':snapshot.get('templates',0),'systems_next_workflow':nextwf,'oldest_queued_age_seconds':max((r.get('oldest_queued_age_seconds',0) or 0 for r in route_rows.values()),default=0),'monitor_snapshot_age_seconds':int(stale)}

def _health_from_rows(sources,gaps,handoffs,slots,templates,nova):
    counts={typ:{'sources':sum(r['feeder_type']==typ for r in sources),'queued':sum(r['feeder_type']==typ and r['ingestion_status'] in {'NEW','DETECTED','READY_FOR_QUESTIONNAIRE','QUESTIONNAIRE_RUNNING','RESEARCH_REQUIRED','RESEARCH_IN_PROGRESS'} for r in sources),'research_required':sum(r['feeder_type']==typ and r['ingestion_status']=='RESEARCH_REQUIRED' for r in sources),'handed_off':sum(r['feeder_type']==typ and r['ingestion_status']=='HANDED_OFF' for r in sources),'blocked':sum(r['feeder_type']==typ and r['ingestion_status']=='BLOCKED' for r in sources),'failed':sum(r['feeder_type']==typ and r['ingestion_status']=='FAILED_RETRYABLE' for r in sources)} for typ in ROUTES}
    nowdt=datetime.now(timezone.utc);oldest=max([(nowdt-datetime.fromisoformat(r['created_at'].replace('Z','+00:00'))).total_seconds() for r in sources if r['ingestion_status'] in {'NEW','DETECTED','READY_FOR_QUESTIONNAIRE','QUESTIONNAIRE_RUNNING','RESEARCH_REQUIRED','RESEARCH_IN_PROGRESS'}],default=0)
    unclaimed=[h for h in handoffs if h['status']=='CREATED'];handoff_age=max([(nowdt-datetime.fromisoformat(h['created_at'].replace('Z','+00:00'))).total_seconds() for h in unclaimed],default=0)
    open_gap_age=max([(nowdt-datetime.fromisoformat(g['created_at'].replace('Z','+00:00'))).total_seconds() for g in gaps if g['status'] in {'OPEN','IN_PROGRESS'}],default=0)
    if handoff_age>3600:overall,nextwf='HANDOFF_STALLED','HANDOFF_RECOVERY'
    elif open_gap_age>14400:overall,nextwf='RESEARCH_STALLED','RESEARCH_WORKFLOW_RECOVERY'
    elif oldest>3600:overall,nextwf='QUEUE_BACKLOG','FEEDER_QUEUE_RECOVERY'
    elif not any(x['queued'] for x in counts.values()) and not unclaimed:overall,nextwf='IDLE_HEALTHY','WAIT_FOR_NEXT_CANONICAL_WAKE'
    else:overall,nextwf='PASS','CONTINUE_FEEDER_WORKFLOW'
    return {'status':overall,'generated_at':now(),'source_counts':counts,'research_gaps':{'open':sum(g['status'] in {'OPEN','IN_PROGRESS'} for g in gaps),'completed':sum(g['status']=='COMPLETED' for g in gaps),'oldest_age_seconds':int(open_gap_age)},'handoffs':{'completed':sum(h['status']=='COMPLETED' for h in handoffs),'unclaimed':len(unclaimed),'oldest_unclaimed_age_seconds':int(handoff_age)},'batch':{'name':BATCH,'total_slots':len(slots),'waiting_for_source':sum(s['status']=='WAITING_FOR_SOURCE' for s in slots),'real_sources_added':sum(s['status']!='WAITING_FOR_SOURCE' for s in slots)},'nova':{state:sum(x['status']==state for x in nova) for state in ['RAY_INTAKE_REVIEW','DISCUSSING','SENT_TO_RESEARCH','SAVED_BY_RAY','IN_ATLAS_WORKFLOW']},'templates':templates,'systems_next_workflow':nextwf,'oldest_queued_age_seconds':int(oldest)}

def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('initialize')
    intake=sub.add_parser('intake');intake.add_argument('--feeder-type',required=True,choices=ROUTES);intake.add_argument('--source-type',required=True);intake.add_argument('--title',required=True);intake.add_argument('--url');intake.add_argument('--creator');intake.add_argument('--transcript');intake.add_argument('--notebook-reference');intake.add_argument('--notebook-type');intake.add_argument('--notebook-owner');intake.add_argument('--notebook-manager');intake.add_argument('--input-json',default='{}');intake.add_argument('--source-id')
    nova=sub.add_parser('nova');nova.add_argument('--idea',required=True);nova.add_argument('--name',default='GoClear Business Funding');nova.add_argument('--source',default='RAY_CONVERSATION');nova.add_argument('--opportunity-id')
    action=sub.add_parser('ray-action');action.add_argument('--opportunity-id',required=True);action.add_argument('--action',required=True,choices=['DISCUSS_FURTHER','SEND_TO_RESEARCH','SAVE_FOR_LATER'])
    claim=sub.add_parser('claim-handoff');claim.add_argument('--handoff-id',required=True);claim.add_argument('--owner',required=True)
    proc=sub.add_parser('process-once');proc.add_argument('--fixture-only',action='store_true');proc.add_argument('--feeder-type',choices=sorted(ROUTES));proc.add_argument('--source-id')
    cont=sub.add_parser('continue-source');cont.add_argument('--source-id',required=True)
    hand=sub.add_parser('handoff-once');hand.add_argument('--handoff-id',required=True)
    delivery=sub.add_parser('handoff-delivery-once');delivery.add_argument('--handoff-ref',required=True)
    sub.add_parser('health')
    a=p.parse_args(argv)
    if a.cmd=='initialize':out=initialize()
    elif a.cmd=='intake':
        data=json.loads(a.input_json);content=a.transcript or '';sid=a.source_id or _stable('feedsrc',(a.feeder_type,a.url,a.title,_hash(content)))
        transcript_meta=None
        if content:
            from nexus_agent_platform.transcript_artifacts import store_transcript
            transcript_meta=store_transcript(sid,content,source_url=a.url,source_type=a.source_type)
        body={'source_id':sid,'feeder_type':a.feeder_type,'source_type':a.source_type,'source_title':a.title,'source_url':a.url,'source_creator':a.creator,'notebook_reference':a.notebook_reference,'notebook_type':a.notebook_type,'notebook_owner':a.notebook_owner,'notebook_manager':a.notebook_manager,'notebook_output':data,'structured_input':data,'content_hash':_hash(content) if content else None,'ingestion_status':'NEW','next_owner':'FEEDER_INTAKE_WORKER'}
        if transcript_meta:
            body.update({'transcript_storage_class':'LOCAL_ARTIFACT','transcript_ref':transcript_meta['TRANSCRIPT_REF'],'transcript_sha256':transcript_meta['SHA256'],'transcript_char_count':transcript_meta['CHAR_COUNT'],'transcript_byte_count':transcript_meta['BYTE_COUNT'],'transcript_available':True})
        try:
            _request('nexus_feeder_sources?on_conflict=source_id','POST',body,'resolution=merge-duplicates,return=minimal')
        except RuntimeError as exc:
            # Metadata columns are additive; keep old installations usable while
            # never falling back to a full transcript write.
            if transcript_meta and any(token in str(exc).lower() for token in ('transcript_storage_class','transcript_ref','column')):
                for key in ('transcript_storage_class','transcript_ref','transcript_sha256','transcript_char_count','transcript_byte_count','transcript_available'):
                    body.pop(key,None)
                _request('nexus_feeder_sources?on_conflict=source_id','POST',body,'resolution=merge-duplicates,return=minimal')
            else: raise
        out={'source_id':sid,'status':'NEW','transcript_storage':'LOCAL_ARTIFACT' if transcript_meta else ('LEGACY_FIXTURE' if content else 'NONE')}
        if a.source_type!='CERTIFICATION_FIXTURE':
            slots=_request('nexus_feeder_batch_slots?batch_name=eq.'+urllib.parse.quote(BATCH,safe='')+'&feeder_type=eq.'+a.feeder_type+'&status=eq.WAITING_FOR_SOURCE&order=slot_number.asc&limit=1')
            if slots:_request('nexus_feeder_batch_slots?batch_slot_id=eq.'+slots[0]['batch_slot_id'],'PATCH',{'source_id':sid,'source_reference':a.url or a.title,'status':'NEW','updated_at':now()})
    elif a.cmd=='nova':out=create_nova_idea(a.idea,a.name,source=a.source,opportunity_id=a.opportunity_id)
    elif a.cmd=='ray-action':out=ray_action(a.opportunity_id,a.action)
    elif a.cmd=='claim-handoff':out=claim_handoff(a.handoff_id,a.owner)
    elif a.cmd=='process-once':out=process_once(fixture_only=a.fixture_only,feeder_type=a.feeder_type,source_id=a.source_id)
    elif a.cmd=='continue-source':out=continue_source(a.source_id)
    elif a.cmd=='handoff-once':out=handoff_once(a.handoff_id)
    elif a.cmd=='handoff-delivery-once':out=handoff_delivery_once(a.handoff_ref)
    else:out=health_report()
    print(json.dumps(out,indent=2,default=str));return 0

if __name__=='__main__':raise SystemExit(main())
