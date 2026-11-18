import { supabase } from './supabaseClient'
import { BI_BANK_TYPES, BI_NOTEBOOK_TYPES, BUSINESS_INTELLIGENCE_PROMPTS, allFundingClaimsRemainUnverified, canPromoteBusinessOpportunity, validateBusinessSourceInput, validateDepartmentHandoff, type BusinessSourceInput, type DepartmentHandoff } from './businessIntelligenceWorkflows'
import type { SupabaseClient } from '@supabase/supabase-js'

type BIClient = SupabaseClient | null
const requireClient = (client: BIClient) => { if (!client) throw new Error('Supabase is not configured'); return client }

export async function initializeBusinessIntelligence(client: BIClient = supabase) {
  const db = requireClient(client)
  const notebooks = BI_NOTEBOOK_TYPES.map(type => ({notebook_type:type,owner_department:'RESEARCH',manager_department:'RESEARCH',master_prompt_version:'v1',master_prompt:BUSINESS_INTELLIGENCE_PROMPTS[type],status:'ACTIVE'}))
  const banks = BI_BANK_TYPES.map(bank_type => ({bank_type,item_count:0,stale_items:0,metadata:{initialized_by:'business_intelligence_workflows_v1'}}))
  const [n,b] = await Promise.all([
    db.from('business_intelligence_notebooks').upsert(notebooks,{onConflict:'notebook_type',ignoreDuplicates:true}),
    db.from('business_intelligence_banks').upsert(banks,{onConflict:'bank_type',ignoreDuplicates:true}),
  ])
  if(n.error) throw n.error
  if(b.error) throw b.error
  const [nr,br] = await Promise.all([
    db.from('business_intelligence_notebooks').select('*').in('notebook_type',[...BI_NOTEBOOK_TYPES]),
    db.from('business_intelligence_banks').select('*').in('bank_type',[...BI_BANK_TYPES]),
  ])
  if(nr.error) throw nr.error
  if(br.error) throw br.error
  return {notebooks:nr.data||[],banks:br.data||[]}
}

export async function persistBusinessIntelligenceRecord(input:{record_type:string;record_key:string;case_id?:string;lane?:'CLIENT_GOCLEAR'|'NEXUS_INTERNAL';status:string;evidence_level:string;payload:Record<string,unknown>;source_references?:unknown[];next_action:string;next_owner:string},client:BIClient=supabase) {
  const db=requireClient(client)
  const {data,error}=await db.from('business_intelligence_records').upsert({...input,source_references:input.source_references||[],updated_at:new Date().toISOString()},{onConflict:'record_type,record_key'}).select('*').single()
  if(error) throw error
  return data
}

export async function persistBusinessIntelligenceRecords(inputs:Array<{record_type:string;record_key:string;case_id?:string;lane?:'CLIENT_GOCLEAR'|'NEXUS_INTERNAL';status:string;evidence_level:string;payload:Record<string,unknown>;source_references?:unknown[];next_action:string;next_owner:string}>,client:BIClient=supabase) {
  const db=requireClient(client)
  if(!inputs.length) return []
  const {data,error}=await db.from('business_intelligence_records').upsert(inputs.map(input=>({...input,source_references:input.source_references||[],updated_at:new Date().toISOString()})),{onConflict:'record_type,record_key'}).select('*')
  if(error) throw error
  return data||[]
}

export async function persistBusinessHandoff(packet: DepartmentHandoff, client:BIClient=supabase) {
  const missing = validateDepartmentHandoff(packet)
  if (missing.length) throw new Error(`Handoff is incomplete: ${missing.join(', ')}`)
  const db=requireClient(client)
  const { data, error } = await db.from('business_intelligence_handoffs').insert({
    case_id:packet.case_id, handoff_type:packet.handoff_type, from_department:packet.from_department,
    next_owner:packet.next_owner, packet:{SUMMARY:packet.summary,SUPPORTING_DATA:packet.supporting_data,WHAT_WAS_COMPLETED:packet.what_was_completed,WHAT_REMAINS:packet.what_remains,RECOMMENDATION:packet.recommendation,ACTION:packet.action,NEXT_OWNER:packet.next_owner,EXPECTED_OUTPUT:packet.expected_output}
  }).select('*').single()
  if (error) throw error
  return data
}

export async function promoteBusinessOpportunity(input: { opportunityId:string; caseId:string; sourceReferences:string[]; initialResearchPacket:Record<string,unknown>; gates:Record<string,boolean> }, client:BIClient=supabase) {
  if (!canPromoteBusinessOpportunity(input.gates)) throw new Error('Promotion gate is not satisfied; keep the case in RESEARCH_GAP_CLOSURE.')
  const db=requireClient(client)
  const notebookId = `opportunity:${input.opportunityId}`
  const {error: notebookError} = await db.from('business_intelligence_project_notebooks').upsert({notebook_id:notebookId,notebook_type:'BUSINESS_OPPORTUNITY',case_id:input.caseId,owner_department:'ATLAS / BUSINESS_OPPORTUNITIES',manager_department:'RESEARCH',source_references:input.sourceReferences,initial_research_packet:input.initialResearchPacket,status:'ACTIVE',updated_at:new Date().toISOString()},{onConflict:'notebook_id'})
  if (notebookError) throw notebookError
  const {error} = await db.from('business_intelligence_records').upsert({record_type:'OPPORTUNITY',record_key:input.opportunityId,case_id:input.caseId,status:'ATLAS_PLAN_REQUIRED',evidence_level:'CROSS_SUPPORTED',payload:{OPPORTUNITY_ID:input.opportunityId,CASE_ID:input.caseId,NOTEBOOK_ID:notebookId,INITIAL_RESEARCH_PACKET:input.initialResearchPacket,NEXT_OWNER:'BUSINESS_OPPORTUNITIES'},source_references:input.sourceReferences,next_action:'Atlas builds complete business plan and queries Business Hub',next_owner:'ATLAS / BUSINESS_OPPORTUNITIES'},{onConflict:'record_type,record_key'})
  if (error) throw error
  const {count:opportunityCount,error:countError}=await db.from('business_intelligence_records').select('id',{count:'exact',head:true}).eq('record_type','OPPORTUNITY')
  if(countError) throw countError
  const {error:bankError}=await db.from('business_intelligence_banks').update({item_count:opportunityCount||0,last_sync:new Date().toISOString(),updated_at:new Date().toISOString()}).eq('bank_type','OPPORTUNITY_BANK')
  if(bankError) throw bankError
  const {count:projectCount,error:projectCountError}=await db.from('business_intelligence_project_notebooks').select('notebook_id',{count:'exact',head:true}).eq('notebook_type','BUSINESS_OPPORTUNITY').eq('status','ACTIVE')
  if(projectCountError) throw projectCountError
  const {error:templateError}=await db.from('business_intelligence_notebooks').update({active_projects:projectCount||0,last_updated:new Date().toISOString()}).eq('notebook_type','BUSINESS_OPPORTUNITY_FEEDER')
  if(templateError) throw templateError
  return {notebookId,nextOwner:'BUSINESS_OPPORTUNITIES'}
}

export async function ingestFundingSource(input:BusinessSourceInput & {caseId:string;productId:string},client:BIClient=supabase) {
  const missing=validateBusinessSourceInput(input); if(missing.length) throw new Error(`Funding feeder input missing: ${missing.join(', ')}`)
  if(!allFundingClaimsRemainUnverified(input.SOURCE_CLAIMS)) throw new Error('Funding source feeder cannot promote source claims to lender-verified facts.')
  const db=requireClient(client)
  const sourceKey=`${input.caseId}:FIRST_CITIZENS_SOURCE`
  const [,product]=await persistBusinessIntelligenceRecords([
    {record_type:'FUNDING_SOURCE',record_key:sourceKey,case_id:input.caseId,status:'VERIFICATION_GAP_CLOSURE',evidence_level:'SOURCE_CLAIM',payload:{...input,questionnaire:{...input.NOTEBOOK_OUTPUT},verification_gaps:input.RESEARCH_GAPS.map(g=>g.question)},source_references:[input.SOURCE_URL_OR_REFERENCE],next_action:input.RESEARCH_GAPS[0]?.question||'Verify current lender requirements from authoritative sources',next_owner:'RESEARCH'},
    {record_type:'FUNDING_PRODUCT_BANK',record_key:input.productId,case_id:input.caseId,status:'ADDITIONAL_VERIFICATION_REQUIRED',evidence_level:'SOURCE_CLAIM',payload:{lender:'First Citizens Bank',product:'Business Line of Credit',product_type:'BUSINESS_LINE_OF_CREDIT',claims:input.SOURCE_CLAIMS.map(c=>({...c,evidence_level:'SOURCE_CLAIM'})),requirements_verified:false,credit_requirements_verified:false,pricing_verified:false,verification_gaps:input.RESEARCH_GAPS.map(g=>g.question)},source_references:[input.SOURCE_URL_OR_REFERENCE],next_action:'Research exact lender product and requirement questions',next_owner:'RESEARCH'},
  ],db)
  const {count,error:countError}=await db.from('business_intelligence_records').select('id',{count:'exact',head:true}).eq('record_type','FUNDING_PRODUCT_BANK')
  if(countError) throw countError
  const {error:bankError}=await db.from('business_intelligence_banks').update({item_count:count||0,last_sync:new Date().toISOString(),updated_at:new Date().toISOString()}).eq('bank_type','FUNDING_PRODUCT_BANK')
  if(bankError) throw bankError
  return {source:sourceKey,product,claimEvidenceLevel:'SOURCE_CLAIM',verificationGaps:input.RESEARCH_GAPS}
}

export async function runOpportunityFeeder(input:BusinessSourceInput & {caseId:string;opportunityId:string;gates:Record<string,boolean>},client:BIClient=supabase) {
  const missing=validateBusinessSourceInput(input); if(missing.length) throw new Error(`Opportunity feeder input missing: ${missing.join(', ')}`)
  const db=requireClient(client), sourceRef=[input.SOURCE_URL_OR_REFERENCE]
  const [source]=await persistBusinessIntelligenceRecords([
    {record_type:'OPPORTUNITY_SOURCE',record_key:`${input.caseId}:SOURCE`,case_id:input.caseId,status:'RESEARCH_GAP_CLOSURE',evidence_level:'CROSS_SUPPORTED',payload:{...input,completeness_gates:input.gates},source_references:sourceRef,next_action:input.RESEARCH_GAPS[0]?.question||'Evaluate all required promotion gates',next_owner:'RESEARCH'},
    ...input.RESEARCH_GAPS.map((gap,index)=>({record_type:'RESEARCH_GAP_TASK',record_key:`${input.caseId}:GAP:${index+1}`,case_id:input.caseId,status:'OPEN',evidence_level:'RESEARCH_REQUIRED',payload:{question:gap.question,reason:gap.reason||'Required evidence is absent'},source_references:sourceRef,next_action:gap.question,next_owner:gap.owner||'RESEARCH'})),
  ],db)
  const promotable=canPromoteBusinessOpportunity(input.gates)
  if(!promotable) return {source, promoted:false, status:'RESEARCH_GAP_CLOSURE',missingGates:Object.entries(input.gates).filter(([,value])=>!value).map(([key])=>key)}
  const promoted=await promoteBusinessOpportunity({opportunityId:input.opportunityId,caseId:input.caseId,sourceReferences:sourceRef,initialResearchPacket:{source:input,questions:input.NOTEBOOK_OUTPUT,gates:input.gates},gates:input.gates},db)
  await persistBusinessHandoff({case_id:input.caseId,handoff_type:'RESEARCH_TO_BUSINESS_OPPORTUNITIES',from_department:'RESEARCH',next_owner:'BUSINESS_OPPORTUNITIES',summary:'Complete feeder research packet passed the opportunity promotion gate.',supporting_data:{opportunity_id:input.opportunityId,NOTEBOOK_ID:promoted.notebookId,notebook_id:promoted.notebookId},what_was_completed:['Source intake','Questionnaire','Gap closure','Promotion gate'],what_remains:['Atlas business plan','Business Hub review','Finance review'],recommendation:'Promote to Atlas-owned opportunity notebook.',action:'Build the complete business plan and query BUSINESS_HUB.',expected_output:'BUSINESS_OPPORTUNITY_FINAL_HANDOFF for Ray review.'},db)
  return {...promoted,source,promoted:true,status:'ATLAS_PLAN_REQUIRED'}
}

export async function createFundingReadinessHandoff(input:{caseId:string;businessId:string;clientOrNexus:'CLIENT_GOCLEAR'|'NEXUS_INTERNAL';profile:Record<string,unknown>;gaps:string[];actions:string[];fundingGoal:string;amountNeeded:number;useOfFunds:string},client:BIClient=supabase) {
  const db=requireClient(client)
  const record=await persistBusinessIntelligenceRecord({record_type:'BUSINESS_FUNDING_READINESS',record_key:input.businessId,case_id:input.caseId,lane:input.clientOrNexus,status:'CLYDE_READINESS_REVIEW',evidence_level:'CROSS_SUPPORTED',payload:{...input.profile,known_gaps:input.gaps,readiness_actions_completed:input.actions,funding_goal:input.fundingGoal,amount_needed:input.amountNeeded,use_of_funds:input.useOfFunds,personal_credit_repair_workflow:'NOT_YET_GOVERNED'},source_references:[],next_action:'Clyde evaluates funding readiness and product matches',next_owner:'CLYDE'},db)
  const handoff=await persistBusinessHandoff({case_id:input.caseId,handoff_type:'BUSINESS_CREATION_TO_CLYDE',from_department:'BUSINESS_CREATION',next_owner:'CLYDE',summary:'Bankability audit and readiness gaps are packaged for funding review.',supporting_data:{business_id:input.businessId,NOTEBOOK_ID:input.profile.business_creation_notebook_id||'local-fixture:BUSINESS_CREATION_BANKABILITY',notebook_id:input.profile.business_creation_notebook_id||'local-fixture:BUSINESS_CREATION_BANKABILITY',record_id:record.id,known_gaps:input.gaps},what_was_completed:['Business profile audit','NAICS review','Business credit review','Ordered bankability gap plan'],what_remains:input.gaps,recommendation:'Clyde review potential matches and paths to eligibility; do not guarantee approval.',action:'Compare profile with the Funding Product Bank.',expected_output:'Clyde recommendation followed by client or Ray decision gate.'},db)
  return {record,handoff}
}

export async function persistBankabilityAudit(input:{caseId:string;businessId:string;profile:Record<string,unknown>;gaps:string[];orderedActions:string[];recommendedNaics:string;naicsReason:string;sourceReferences?:string[]},client:BIClient=supabase) {
  return persistBusinessIntelligenceRecord({record_type:'BUSINESS_BANKABILITY_AUDIT',record_key:input.businessId,case_id:input.caseId,status:'BANKABILITY_GAP_ACTION',evidence_level:'CROSS_SUPPORTED',payload:{...input.profile,known_gaps:input.gaps,ordered_actions:input.orderedActions,recommended_naics:input.recommendedNaics,naics_reason:input.naicsReason,personal_credit_repair_workflow:'NOT_YET_GOVERNED'},source_references:input.sourceReferences||[],next_action:input.orderedActions[0]||'Recheck funding readiness',next_owner:'BUSINESS_CREATION'},client)
}

export async function queryBusinessHub(input:{caseId:string;query:string;opportunityId:string},client:BIClient=supabase) {
  const db=requireClient(client)
  const {data,error}=await db.from('business_intelligence_records').select('record_key,status,evidence_level,payload,source_references').eq('record_type','BUSINESS_HUB').limit(50)
  if(error) throw error
  const matches=data||[]
  const review=await persistBusinessIntelligenceRecord({record_type:'BUSINESS_HUB_REVIEW',record_key:`${input.caseId}:ATLAS_HUB_REVIEW`,case_id:input.caseId,status:matches.length?'MATCHES_FOUND':'NO_MATCHING_RECORDS',evidence_level:'CROSS_SUPPORTED',payload:{query:input.query,opportunity_id:input.opportunityId,matches,results_count:matches.length,decision_authority:'ATLAS_RECOMMENDS_RAY_DECIDES'},source_references:[],next_action:matches.length?'Atlas incorporates relevant prior Nexus lessons.':'Atlas records that no matching Business Hub records were present at query time.',next_owner:'ATLAS / BUSINESS_OPPORTUNITIES'},db)
  return {matches,review}
}
