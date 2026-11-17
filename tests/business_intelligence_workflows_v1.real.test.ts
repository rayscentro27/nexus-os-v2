import { afterAll, describe, expect, it } from 'vitest'
import { createClient } from '@supabase/supabase-js'
import { allFundingClaimsRemainUnverified, evaluateNaicsCandidates, fundingMatchState } from '../src/lib/businessIntelligenceWorkflows'
import { createFundingReadinessHandoff, ingestFundingSource, initializeBusinessIntelligence, persistBankabilityAudit, persistBusinessHandoff, persistBusinessIntelligenceRecord, persistBusinessIntelligenceRecords, queryBusinessHub, runOpportunityFeeder } from '../src/lib/businessIntelligenceStore'

const url=process.env.SUPABASE_URL||process.env.VITE_SUPABASE_URL
const key=process.env.SUPABASE_SERVICE_ROLE_KEY
const enabled=process.env.NEXUS_BI_REAL_SUPABASE==='YES'&&Boolean(url&&key)
const tracedFetch:typeof fetch=async(input,init)=>{
  const original=globalThis.fetch
  const path=typeof input==='string'?new URL(input).pathname:new URL((input as Request).url).pathname
  const method=init?.method||'GET',started=Date.now()
  console.log(`BI_SUPABASE_REQUEST ${method} ${path}`)
  const response=await original(input,{...init,signal:init?.signal||AbortSignal.timeout(30000)})
  console.log(`BI_SUPABASE_RESPONSE ${method} ${path} ${response.status} ${Date.now()-started}ms`)
  return response
}
const db=enabled?createClient(url!,key!,{auth:{persistSession:false,autoRefreshToken:false},global:{fetch:tracedFetch}}):null
const runId=`bi-cert-${new Date().toISOString().replace(/[-:.TZ]/g,'').slice(0,14)}`
const caseIds={opportunity:`${runId}-opportunity`,funding:`${runId}-funding`,creation:`${runId}-creation`}

async function handoff(case_id:string,handoff_type:string,from_department:string,next_owner:string,summary:string,completed:string[],remaining:string[],recommendation:string,action:string,expected:string,notebookId=`local-fixture:${handoff_type}`){
  return persistBusinessHandoff({case_id,handoff_type,from_department,next_owner,summary,supporting_data:{TEST_FIXTURE:true,NOTEBOOK_ID:notebookId},what_was_completed:completed,what_remains:remaining,recommendation,action,expected_output:expected},db)
}

describe.skipIf(!enabled)('real Supabase workflow certification fixtures',()=>{
  afterAll(()=>{db?.auth.stopAutoRefresh()})
  it('initializes all templates/banks and certifies opportunity, funding, creation, handoffs, and admin readback',async()=>{
    const initialized=await initializeBusinessIntelligence(db)
    console.log('BI_CERT_STAGE=INITIALIZED')
    expect(initialized.notebooks).toHaveLength(3)
    expect(initialized.banks).toHaveLength(5)
    expect(initialized.notebooks.every(x=>x.owner_department==='RESEARCH'&&x.manager_department==='RESEARCH'&&x.master_prompt_version==='v1'&&Boolean(x.master_prompt))).toBe(true)
    const retired=await db!.from('business_intelligence_project_notebooks').update({status:'CERTIFICATION_FIXTURE_SUPERSEDED'}).like('case_id','bi-cert-%-opportunity').neq('case_id',caseIds.opportunity)
    expect(retired.error).toBeNull()

    // Existing real opportunity research: supported public category/competitor evidence and explicitly assumption-based economics.
    const opportunityInput={caseId:caseIds.opportunity,opportunityId:`${runId}-mobile-detailing`,SOURCE_TYPE:'LOCAL_RESEARCH_PACKET',SOURCE_TITLE:'Phoenix mobile detailing demand and economics research',SOURCE_URL_OR_REFERENCE:'reports/rebuild/WP8_3_ALPHA_RESEARCH_EVIDENCE.md; reports/rebuild/WP8_3_MOBILE_DETAILING_ECONOMICS.md; reports/rebuild/WP8_3_NOVA_OPPORTUNITY_DECISION.md',SOURCE_TRANSCRIPT:'Five public sources support an existing Phoenix-area paid category, competitor pricing, recurring plans, and operating constraints. They do not prove direct customer demand, CAC, conversion, retention, or profitability.',NOTEBOOK_OUTPUT:{business_model:'Mobile detailing, one-time and recurring plans',target_customer:['Phoenix vehicle owners','households','fleets'],customer_problem:'Convenient vehicle cleaning and recurring maintenance',value_proposition:'Mobile service at customer-selected location',revenue_model:'Per-service ticket plus recurring plans',economics:{base_ticket:165,monthly_job_assumption:66,variable_cost_assumption:45,fixed_cost_assumption:1200,marketing_cost_assumption:900,all_values_are_assumptions:true},source_evidence:'SUPPORTED_PROXY_NOT_DIRECT_DEMAND',competitor_sources:['Sunshine Detailing AZ','Revival Phoenix','Valley Shine Mobile','Washos Maricopa'],risks:['Direct demand unknown','CAC/conversion unknown','Retention unknown','Throughput and route density unvalidated']},SOURCE_CLAIMS:[{claim:'Local category and competitor pricing exist',value:'Five sources recorded',evidence_level:'CROSS_SUPPORTED' as const},{claim:'66 monthly jobs',value:66,evidence_level:'SOURCE_CLAIM' as const},{claim:'CAC payback',value:'UNPROVEN',evidence_level:'RESEARCH_REQUIRED' as const}],RESEARCH_GAPS:[{question:'What direct Phoenix customer evidence demonstrates willingness to pay for the proposed mobile service and selected segment?',reason:'Current evidence is category/competitor proxy only.',owner:'ATLAS / BUSINESS_OPPORTUNITIES'},{question:'What measured acquisition cost, conversion, retention, and route throughput result from a governed validation pilot?',reason:'These are explicitly unknown.',owner:'ATLAS / BUSINESS_OPPORTUNITIES'}],gates:{BUSINESS_MODEL_DEFINED:true,CUSTOMER_DEFINED:true,PROBLEM_DEFINED:true,REVENUE_MODEL_DEFINED:true,DEMAND_EVIDENCE_PRESENT:true,COMPETITOR_REVIEW_COMPLETE:true,BASIC_COST_STRUCTURE_PRESENT:true,RISKS_IDENTIFIED:true}}
    const opp=await runOpportunityFeeder(opportunityInput,db)
    console.log('BI_CERT_STAGE=OPPORTUNITY_PROMOTED_AND_HANDED_OFF')
    expect(opp.promoted).toBe(true)
    const savedGaps=await db!.from('business_intelligence_records').select('*').eq('case_id',caseIds.opportunity).eq('record_type','RESEARCH_GAP_TASK')
    expect(savedGaps.data).toHaveLength(2)
    expect(savedGaps.data!.every(x=>x.next_owner==='ATLAS / BUSINESS_OPPORTUNITIES')).toBe(true)
    const project=await db!.from('business_intelligence_project_notebooks').select('*').eq('case_id',caseIds.opportunity).single()
    expect(project.error).toBeNull()
    expect(project.data.owner_department).toContain('ATLAS')
    expect(project.data.manager_department).toBe('RESEARCH')
    const hub=await queryBusinessHub({caseId:caseIds.opportunity,opportunityId:opportunityInput.opportunityId,query:'Phoenix mobile detailing: similar Nexus projects, prior lessons, reusable capabilities, partners, marketing assets, and possible model improvement.'},db)
    expect(hub.review.status).toBe('NO_MATCHING_RECORDS')
    expect(hub.review.payload.results_count).toBe(0)

    await handoff(caseIds.opportunity,'BUSINESS_OPPORTUNITIES_TO_FINANCE','BUSINESS_OPPORTUNITIES','FINANCE','Finance review requested; planning values are labeled assumptions, no available budget or capital gap asserted.',['Opportunity assumptions packaged'],['Reconcile actual available business, experiment, and marketing budgets'], 'Finance determines supportable budgets and capital gap.','Read authoritative Finance state and return cost-free/lean/moderate/accelerated feasibility.','Finance review result in Supabase.',opp.notebookId)
    await handoff(caseIds.opportunity,'BUSINESS_OPPORTUNITIES_TO_BUSINESS_FUNDING_TEST_FIXTURE','BUSINESS_OPPORTUNITIES','BUSINESS_FUNDING','Conditional capital-gap routing branch exercised with an explicitly simulated governance fixture; this is not a real project capital gap.', ['Conditional routing and required packet fields exercised'],['Replace simulation with Finance-confirmed capital gap before any recommendation'], 'Test that positive capital gap routes to Clyde funding review.','Evaluate legitimate funding sources; do not apply or accept.','Clyde recommendation and Ray decision gate; simulation only.',opp.notebookId)
    await handoff(caseIds.opportunity,'ATLAS_TO_RAY','ATLAS','RAY','Atlas to Ray handoff-contract fixture; the final opportunity packet is not yet decision-ready.',['Opportunity promotion and Atlas ownership','Business Hub query with zero matching records','Ray decision boundary schema exercised'],['Complete the full business plan and marketing strategy','Obtain actual Finance budget review','Run real Funding review only if Finance confirms a capital gap','Assemble final Atlas recommendation packet'],'No business merits decision is requested from this contract fixture.','Keep the final decision gate closed until required reviews are complete.','Complete BUSINESS_OPPORTUNITY_FINAL_HANDOFF, then Ray makes the decision.',opp.notebookId)
    console.log('BI_CERT_STAGE=OPPORTUNITY_GATES')

    const sourceClaims=[
      ['CLAIMED_LIMIT','$25,000'],['CLAIMED_NO_DOC','YES'],['CLAIMED_STATED_INCOME','YES'],['CLAIMED_BUSINESS_CHECKING_AGE','90 DAYS'],['CLAIMED_CONSISTENT_DEPOSITS','YES'],['CLAIMED_MINIMUM_FICO','720'],['CLAIMED_BUREAUS','EXPERIAN + EQUIFAX'],['CLAIMED_GEOGRAPHIC_LIMIT','23 STATES'],['CLAIMED_APPLICATION_METHOD','RELATIONSHIP MANAGER'],
    ].map(([claim,value])=>({claim,value,evidence_level:'SOURCE_CLAIM' as const}))
    const fundingInput={caseId:caseIds.funding,productId:`${runId}-first-citizens-25k-bloc`,SOURCE_TYPE:'CONTROLLED_LOCAL_WORKFLOW_FIXTURE',SOURCE_TITLE:'First Citizens $25K business LOC example — unverified source claims',SOURCE_URL_OR_REFERENCE:'fixture://business-funding/first-citizens-v1; source unavailable in checkout',SOURCE_TRANSCRIPT:'No lender source or creator transcript was found. This controlled feeder fixture preserves only the claims in the workflow specification.',NOTEBOOK_OUTPUT:{lender:'First Citizens Bank',product:'Business Line of Credit',product_type:'BUSINESS_LINE_OF_CREDIT',claimed_limit:25000,claimed_no_doc:true,claimed_stated_income:true,claimed_checking_age_days:90,claimed_consistent_deposits:true,claimed_minimum_fico:720,claimed_bureaus:['EXPERIAN','EQUIFAX'],claimed_geographic_limit_states:23,claimed_application_method:'RELATIONSHIP_MANAGER',current_requirements_verified:false,credit_requirements_verified:false,pricing_verified:false},SOURCE_CLAIMS:sourceClaims,RESEARCH_GAPS:[{question:'Does a current First Citizens Bank business line of credit matching this description exist, and what is its official product name and product page?',reason:'Product existence has not been established.'},{question:'What are the current time-in-business, checking-account age, deposit, and average-balance requirements?',reason:'The 90-day relationship and deposit statements are source claims only.'},{question:'Are a 720 personal score and Experian/Equifax specifically required, and what pull type/bureaus apply?',reason:'Credit claims are unverified.'},{question:'What current rate/APR, fees, term, payment structure, and documentation are required?',reason:'Pricing and documentation are absent.'},{question:'Which states and industries are eligible, and is application through a relationship manager required?',reason:'Geography and application path are unverified.'}]}
    expect(allFundingClaimsRemainUnverified(fundingInput.SOURCE_CLAIMS)).toBe(true)
    const funding=await ingestFundingSource(fundingInput,db)
    console.log('BI_CERT_STAGE=FUNDING_SOURCE_AND_PRODUCT_PERSISTED')
    expect(funding.claimEvidenceLevel).toBe('SOURCE_CLAIM')
    const product=await db!.from('business_intelligence_records').select('*').eq('record_type','FUNDING_PRODUCT_BANK').eq('record_key',fundingInput.productId).single()
    expect(product.error).toBeNull()
    expect(product.data.evidence_level).toBe('SOURCE_CLAIM')
    expect(product.data.payload.requirements_verified).toBe(false)
    expect(product.data.payload.credit_requirements_verified).toBe(false)
    expect(product.data.payload.pricing_verified).toBe(false)
    expect(product.data.payload.claims.every((x:any)=>x.evidence_level==='SOURCE_CLAIM')).toBe(true)
    expect(product.data.lane).toBeNull()

    const scenarios=[
      {profile:'PROFILE_A',met:9,unmet:0,unverified:0,expected:'CURRENT_MATCH',warning:'Simulation against source-claim criteria only; not a real product eligibility result.'},
      {profile:'PROFILE_B',met:8,unmet:1,unverified:0,expected:'PATH_TO_ELIGIBILITY',current_gap:'90-day business checking relationship',can_improve:true,action:'Maintain qualifying business checking relationship and consistent deposits if lender requirements verify.',milestone:'Obtain official lender criteria and verify account age and deposit history.',alternative_products_search_required:true},
      {profile:'PROFILE_C',met:3,unmet:4,unverified:2,expected:'PATH_TO_ELIGIBILITY'},
      {profile:'PROFILE_B_NEAR',met:8,unmet:0,unverified:1,expected:'NEAR_MATCH'},
      {profile:'PROFILE_ALTERNATIVE',met:0,unmet:2,unverified:0,alternative:true,expected:'ALTERNATIVE_PRODUCT_MATCH'},
      {profile:'PROFILE_NOT_APPROPRIATE',met:0,unmet:2,unverified:0,expected:'NOT_APPROPRIATE'},
    ]
    await persistBusinessIntelligenceRecords(scenarios.map(scenario=>{
      const match=fundingMatchState(scenario); expect(match).toBe(scenario.expected)
      const why=scenario.profile==='PROFILE_A'?'Meets every stated source claim in a synthetic fixture only; no lender criteria have been verified.':scenario.profile==='PROFILE_B'?'One stated source claim is missed and is time-improvable if the lender confirms it.':scenario.profile==='PROFILE_B_NEAR'?'Known source claims align; one material requirement remains unverified.':scenario.profile==='PROFILE_ALTERNATIVE'?'Current profile misses the reference product; comparison is redirected to products with different requirements.':scenario.profile==='PROFILE_NOT_APPROPRIATE'?'Multiple stated requirements are missed and no evidence-supported improvement path is available for this fixture.':'Multiple material requirements are missed; readiness actions and product alternatives need research.'
      return {record_type:'FUNDING_MATCH_SCENARIO',record_key:`${fundingInput.productId}:${scenario.profile}`,case_id:caseIds.funding,lane:'CLIENT_GOCLEAR' as const,status:match,evidence_level:'SOURCE_CLAIM',payload:{...scenario,match_state:match,why_match:why,current_gaps:scenario.current_gap?[scenario.current_gap]:[],actions:scenario.action?[scenario.action]:['Verify lender criteria and gather business documentation.'],milestones:scenario.milestone?[scenario.milestone]:['Obtain lender confirmation and evidence for each criterion.'],risks:['All First Citizens inputs remain source claims; underwriting determines actual approval.'],documents_needed:['Lender-confirmed requirements','Business formation and EIN records','Current bank statements if required'],application_readiness:'NOT_READY_UNTIL_REQUIREMENTS_VERIFIED',simulation_only:true,approval_guarantee:false,alternative_products_search_required:scenario.profile==='PROFILE_B'?true:Boolean(scenario.alternative)},source_references:[fundingInput.SOURCE_URL_OR_REFERENCE],next_action:scenario.profile==='PROFILE_B'?'Verify requirement; collect milestone evidence; search alternatives.':'Clyde provides recommendation only; client decides.',next_owner:'CLYDE'}
    }),db)
    console.log('BI_CERT_STAGE=MATCH_SCENARIOS')
    const clydeRecommendation=await persistBusinessIntelligenceRecord({record_type:'CLYDE_FUNDING_RECOMMENDATION',record_key:`${fundingInput.productId}:CLYDE_RECOMMENDATION`,case_id:caseIds.funding,lane:'CLIENT_GOCLEAR',status:'CLIENT_DECISION_REQUIRED',evidence_level:'SOURCE_CLAIM',payload:{recommendation_only:true,approval_guarantee:false,current_matches:['PROFILE_A (synthetic source-claim alignment only)'],near_matches:['PROFILE_B_NEAR'],paths_to_eligibility:['PROFILE_B','PROFILE_C'],alternative_product_matches:['PROFILE_ALTERNATIVE'],not_appropriate:['PROFILE_NOT_APPROPRIATE'],recommended_sequence:['Verify product existence and official requirements','Compare client facts with verified criteria','Gather documents and improvement milestones','Client decides whether to apply'],proposed_action:'CLIENT_DECISION_REQUIRED'},source_references:[fundingInput.SOURCE_URL_OR_REFERENCE],next_action:'Client reviews verified options and makes the funding decision.',next_owner:'CLIENT'},db)
    await persistBusinessIntelligenceRecord({record_type:'FUNDING_MATCH_SCENARIO',record_key:`${fundingInput.productId}:NEXUS_INTERNAL_SIMULATION`,case_id:caseIds.opportunity,lane:'NEXUS_INTERNAL',status:'PATH_TO_ELIGIBILITY',evidence_level:'SOURCE_CLAIM',payload:{funding_case_type:'NEXUS_INTERNAL',capital_gap:2500,available_internal_budget:0,simulation_only:true,client_profile_data_used:false},source_references:[fundingInput.SOURCE_URL_OR_REFERENCE],next_action:'Replace simulated capital gap with Finance-confirmed internal budget before recommending a funding product.',next_owner:'FINANCE'},db)
    await handoff(caseIds.funding,'CLYDE_TO_CLIENT','CLYDE','CLIENT','Clyde recommendation and non-binary paths are persisted for client review.',['Claims and verification gaps preserved','Six match scenarios classified','Clyde recommendation sequence persisted'],['Verify product facts with lender','Client decision'], 'Potential matches and paths only; source claims remain unverified and no approval is guaranteed.','Client chooses whether to pursue any independently verified option.','CLIENT_DECISION_REQUIRED',`local-fixture:BUSINESS_FUNDING_FEEDER:${runId}`)
    await handoff(caseIds.funding,'CLYDE_ATLAS_TO_RAY','CLYDE / ATLAS','RAY','Nexus funding recommendation awaits Ray decision.',['Source-claim alternatives and capital gap review packet'],['Ray decision'], 'RECOMMENDATION_ONLY','Ray decides whether Nexus proceeds with a funding path.','RAY_DECISION_REQUIRED')

    const profile={TEST_FIXTURE:true,legal_name:'Copper Mesa Mobile Care LLC (fictional)',entity_type:'LLC',state:'AZ',formation_date:'2024-04-15',good_standing:true,ein_present:true,registered_agent:'Fictional agent',business_address:'100 Example Road, Phoenix, AZ 85001',address_type:'COMMERCIAL_MAILBOX_TEST',domain:'coppermesa.example.test',website:false,business_email:'ops@coppermesa.example.test',business_phone:'+1-555-010-0198',bank_name:'Example Test Bank',business_bank_account_present:true,bank_account_age_days:45,current_balance:3200,average_balance_30:2800,average_balance_90:null,monthly_deposits:4500,deposit_consistency:'2_MONTHS_ONLY',primary_activity:'Mobile automotive washing and detailing at customer locations',naics:'811192',duns_present:false,google_business:false,business_plan:true,business_credit_profile:{file_present:false,tradelines:0,reporting_accounts:0},personal_credit_readiness:{available:false,status:'NOT_PROVIDED',repair_workflow:'NOT_YET_GOVERNED'},licenses_required:'RESEARCH_REQUIRED',licenses_present:false}
    const naicsA=evaluateNaicsCandidates([{code:'811192',description:'Car washes',truthfulActivityFit:true,primaryActivityFit:true}])
    const naicsB=evaluateNaicsCandidates([{code:'561720',description:'Janitorial services including interiors of transportation equipment',truthfulActivityFit:true,primaryActivityFit:true,revenueShare:0.55},{code:'811192',description:'Car washes including automotive detailing and mobile washes',truthfulActivityFit:true,primaryActivityFit:false,revenueShare:0.45},{code:'561790',description:'Other services to buildings and dwellings',truthfulActivityFit:false,primaryActivityFit:false}],)
    expect(naicsA.recommended?.code).toBe('811192')
    expect(naicsB.defensible.map(x=>x.code)).toEqual(['561720','811192'])
    expect(naicsB.recommended?.code).toBe('561720')
    await persistBankabilityAudit({caseId:caseIds.creation,businessId:`${runId}-fictional-business`,profile:{...profile,naics_governance:{case_a:naicsA,case_b:naicsB,accuracy_first:true,false_naics_optimization_allowed:false}},gaps:['DUNS/business credit file missing','Business credit tradelines missing','Google Business presence unverified','90-day bank averages unavailable','Licensing obligations require verification','Personal credit readiness not provided'],orderedActions:['Confirm licenses and operating/address requirements with Arizona/local authorities.','Build 90-day operating deposit history before a funding comparison.','Review legitimate business credit resources and reporting terms.','Reassess only after profile evidence is updated.'],recommendedNaics:'811192',naicsReason:'Single-activity fictional profile primarily performs mobile vehicle cleaning/detailing; Census 2022 NAICS lists automotive detail shops and mobile car/truck washes under 811192.',sourceReferences:['https://www.census.gov/naics/?details=811192&input=car+wash&year=2022','https://www.census.gov/naics/resources/archives/sect56.html']},db)
    const creation=await createFundingReadinessHandoff({caseId:caseIds.creation,businessId:`${runId}-fictional-business`,clientOrNexus:'CLIENT_GOCLEAR',profile,gaps:['DUNS/business credit file missing','Business credit tradelines missing','Google Business presence unverified','90-day bank averages unavailable','Licensing obligations require verification','Personal credit readiness not provided'],actions:['Confirm local licensing','Build verifiable operating history','Research legitimate reporting trade accounts'],fundingGoal:'Equipment and working capital review',amountNeeded:10000,useOfFunds:'Fictional test fixture only; no application authorized.'},db)
    console.log('BI_CERT_STAGE=BUSINESS_CREATION_HANDOFF')
    expect(creation.record.payload.personal_credit_repair_workflow).toBe('NOT_YET_GOVERNED')

    await db!.from('business_intelligence_banks').update({last_sync:new Date().toISOString(),last_research_run:new Date().toISOString(),next_refresh:new Date(Date.now()+30*86400000).toISOString()}).in('bank_type',['BUSINESS_HUB','OPPORTUNITY_BANK','OPPORTUNITY_COMPONENT_BANK','FUNDING_PRODUCT_BANK','BUSINESS_CREDIT_PRODUCT_BANK'])
    const [handoffs,templates,banks,records,projects]=await Promise.all([
      db!.from('business_intelligence_handoffs').select('*').in('case_id',[caseIds.opportunity,caseIds.funding,caseIds.creation]),
      db!.from('business_intelligence_notebooks').select('*'),
      db!.from('business_intelligence_banks').select('*'),
      db!.from('business_intelligence_records').select('*').in('case_id',[caseIds.opportunity,caseIds.funding,caseIds.creation]),
      db!.from('business_intelligence_project_notebooks').select('*').eq('case_id',caseIds.opportunity),
    ])
    expect(handoffs.error).toBeNull(); expect(templates.error).toBeNull(); expect(banks.error).toBeNull(); expect(records.error).toBeNull(); expect(projects.error).toBeNull()
    const profileB=records.data!.find(x=>x.record_type==='FUNDING_MATCH_SCENARIO'&&x.payload.profile==='PROFILE_B')
    expect(profileB?.status).toBe('PATH_TO_ELIGIBILITY')
    expect(profileB?.payload.current_gap).toBe('90-day business checking relationship')
    expect(profileB?.payload.can_improve).toBe(true)
    expect(profileB?.payload.action).toContain('Maintain qualifying')
    expect(profileB?.payload.milestone).toContain('verify account age')
    expect(profileB?.payload.alternative_products_search_required).toBe(true)
    expect(records.data!.some(x=>x.record_type==='CLYDE_FUNDING_RECOMMENDATION'&&x.status==='CLIENT_DECISION_REQUIRED'&&x.lane==='CLIENT_GOCLEAR')).toBe(true)
    expect(records.data!.some(x=>x.record_type==='FUNDING_MATCH_SCENARIO'&&x.payload.funding_case_type==='NEXUS_INTERNAL'&&x.lane==='NEXUS_INTERNAL'&&x.payload.client_profile_data_used===false)).toBe(true)
    expect(records.data!.filter(x=>x.record_type==='FUNDING_MATCH_SCENARIO'&&x.payload.profile).every(x=>x.lane==='CLIENT_GOCLEAR')).toBe(true)
    const types=new Set(handoffs.data!.map(x=>x.handoff_type))
    for(const type of ['RESEARCH_TO_BUSINESS_OPPORTUNITIES','BUSINESS_OPPORTUNITIES_TO_FINANCE','BUSINESS_OPPORTUNITIES_TO_BUSINESS_FUNDING_TEST_FIXTURE','ATLAS_TO_RAY','BUSINESS_CREATION_TO_CLYDE','CLYDE_TO_CLIENT','CLYDE_ATLAS_TO_RAY']) expect(types.has(type)).toBe(true)
    expect(handoffs.data!.every(x=>x.status==='OPEN'&&x.packet.SUMMARY&&x.packet.SUPPORTING_DATA?.NOTEBOOK_ID&&x.packet.WHAT_WAS_COMPLETED&&x.packet.WHAT_REMAINS&&x.packet.RECOMMENDATION&&x.packet.ACTION&&x.packet.EXPECTED_OUTPUT&&x.next_owner)).toBe(true)
    expect(templates.data).toHaveLength(3); expect(banks.data).toHaveLength(5); expect(projects.data).toHaveLength(1)
    expect(banks.data!.find(x=>x.bank_type==='FUNDING_PRODUCT_BANK')?.item_count).toBeGreaterThan(0)
    expect(records.data!.some(x=>x.record_type==='BUSINESS_BANKABILITY_AUDIT')).toBe(true)
  },360000)
})
