import type { SupabaseClient } from '@supabase/supabase-js'

export const FEEDER_TYPES = [
  'BUSINESS_OPPORTUNITY_FEEDER','BUSINESS_FUNDING_FEEDER','BUSINESS_CREATION_BANKABILITY_FEEDER',
  'FOREX_INDICATOR_STRATEGY_FEEDER','OPTIONS_STRATEGY_FEEDER','RAY_NOVA_OPPORTUNITY_INTAKE',
] as const

export type NovaRecommendation = 'DISCUSS_FURTHER'|'SEND_TO_RESEARCH'|'SAVE_FOR_LATER'

export function analyzeNovaOpportunity(idea:string, name='GoClear Business Funding') {
  const text=idea.trim()
  const funding=/funding|capital|loan|credit|bankability/i.test(text)
  const gaps=[
    'What exact service scope will be offered?',
    'Which customer segment and geography are in scope?',
    'What verified customer demand supports the offer?',
    'What fee or commission model is legally and operationally permissible?',
    'Which lender or affiliate relationships are actually authorized?',
  ]
  const analysis={
    OPPORTUNITY_NAME:name,SOURCE:'RAY_NOVA',IDEA_SUMMARY:text,
    BUSINESS_MODEL:funding?'Business funding / funding readiness service hypothesis':null,
    TARGET_CUSTOMER:funding?'Business owners seeking capital; hypothesis pending validation':null,
    CUSTOMER_PROBLEM:funding?'Credit, bankability, or funding preparation; hypothesis pending validation':null,
    PRODUCT_OR_SERVICE:funding?'Funding readiness service hypothesis':null,
    VALUE_PROPOSITION:null,
    REVENUE_MODEL:funding?'Possible fee or commission model; unverified and not priced':null,
    WHY_THIS_MIGHT_WORK:'Potential fit with Clyde funding capabilities and client portal capabilities; confirm current scope.',
    OBVIOUS_STRENGTHS:['Potential reuse of Clyde funding analysis','Potential client portal workflow reuse'],
    OBVIOUS_WEAKNESSES:['Demand, delivery scope, permitted compensation, and partner access need verification'],
    DEMAND_SIGNAL:'RESEARCH_REQUIRED',NEXUS_CAPABILITY_FIT:['Clyde funding capabilities','Client portal capabilities; scope to verify'],
    COST_FREE_OR_LOW_COST_PATH:'No-spend customer/problem validation and workflow prototype; no launch spend authorized.',
    LIKELY_STARTUP_COMPLEXITY:'MEDIUM; scope requires verification',
    AFFILIATE_POTENTIAL:'Possible; relationships unverified',WHITE_LABEL_POTENTIAL:'Research required',PARTNER_POTENTIAL:'Possible; access unverified',
    FUNDING_REQUIRED_LIKELY:'NO for initial validation; later requirements unknown',
    MAJOR_UNKNOWN:gaps,MAJOR_RISK:'Legal/compliance, lender representation, customer acquisition, and unverified economics.',
    RESEARCH_GAPS:gaps,NOVA_INITIAL_RECOMMENDATION:'SEND_TO_RESEARCH' as NovaRecommendation,
  }
  const conversational={
    WHAT_LOOKS_STRONG:['Potential fit with Clyde funding analysis and the client portal.'],
    WHAT_LOOKS_WEAK:['Demand, exact service scope, permissible compensation, and partner access are unverified.'],
    WHAT_NEXUS_ALREADY_HAS:['Clyde funding capabilities and client portal capabilities; Research should confirm current scope.'],
    LOW_COST_PATH:'Start with no-spend customer/problem validation and a service workflow prototype.',
    WHAT_WE_STILL_NEED_TO_KNOW:gaps,
    MAJOR_RISK:'Avoid implying guaranteed approvals or unverified lender relationships.',
    RECOMMENDATION:'SEND_TO_RESEARCH' as NovaRecommendation,
  }
  return {analysis,conversational}
}

async function deterministicId(prefix:string,value:string) {
  const bytes=new TextEncoder().encode(value)
  const digest=await crypto.subtle.digest('SHA-256',bytes)
  return `${prefix}_${Array.from(new Uint8Array(digest)).slice(0,10).map(x=>x.toString(16).padStart(2,'0')).join('')}`
}

export async function persistNovaOpportunity(client:SupabaseClient,idea:string,name='GoClear Business Funding',existingId?:string) {
  const opportunityId=existingId||await deterministicId('novaopp',`RAY_CONVERSATION|${name}|${idea.trim()}`)
  const sourceId=await deterministicId('feedsrc',`${opportunityId}|RAY_NOVA_OPPORTUNITY_INTAKE`)
  const {analysis,conversational}=analyzeNovaOpportunity(idea,name)
  const source={source_id:sourceId,feeder_type:'RAY_NOVA_OPPORTUNITY_INTAKE',source_type:'RAY_CONVERSATION',source_title:name,transcript_or_extract:idea.trim(),structured_input:analysis,notebook_output:analysis,content_hash:await deterministicId('sha',idea.trim()),ingestion_status:'NEW',next_owner:'NOVA',route_department:'RESEARCH',ray_opportunity_id:opportunityId,case_id:await deterministicId('case',opportunityId)}
  const sourceResult=await client.from('nexus_feeder_sources').upsert(source,{onConflict:'source_id'})
  if(sourceResult.error)throw sourceResult.error
  const existing=existingId?await client.from('nexus_ray_nova_opportunities').select('conversational_response').eq('opportunity_id',opportunityId).maybeSingle():{data:null,error:null}
  const prior=existing.data?.conversational_response||{}
  const history=Array.isArray(prior.discussion_history)?prior.discussion_history:[]
  const conversationalResponse={...conversational,discussion_history:[...history,{ray_message:idea.trim(),nova_response:conversational,at:new Date().toISOString()}]}
  const oppResult=await client.from('nexus_ray_nova_opportunities').upsert({opportunity_id:opportunityId,source_id:sourceId,opportunity_name:name,idea_summary:idea.trim(),structured_analysis:analysis,conversational_response:conversationalResponse,status:existingId?'DISCUSSING':'RAY_INTAKE_REVIEW'},{onConflict:'opportunity_id'})
  if(oppResult.error)throw oppResult.error
  return {opportunityId,sourceId,analysis,conversational:conversationalResponse,status:existingId?'DISCUSSING':'RAY_INTAKE_REVIEW'}
}

export async function persistRayOpportunityAction(client:SupabaseClient,opportunityId:string,action:NovaRecommendation) {
  const {data:opp,error}=await client.from('nexus_ray_nova_opportunities').select('*').eq('opportunity_id',opportunityId).single()
  if(error)throw error
  const status={DISCUSS_FURTHER:'DISCUSSING',SEND_TO_RESEARCH:'SENT_TO_RESEARCH',SAVE_FOR_LATER:'SAVED_BY_RAY'}[action]
  const update=await client.from('nexus_ray_nova_opportunities').update({ray_action:action,status,updated_at:new Date().toISOString()}).eq('opportunity_id',opportunityId)
  if(update.error)throw update.error
  if(action==='SEND_TO_RESEARCH') {
    const handoffId=await deterministicId('fho',`${opp.source_id}|RESEARCH`)
    const packet={opportunity_id:opportunityId,SOURCE:'RAY_NOVA',IDEA_SUMMARY:opp.idea_summary,KNOWN_FACTS:[],RAY_ASSUMPTIONS:[opp.idea_summary],NOVA_INITIAL_ANALYSIS:opp.structured_analysis,KNOWN_CUSTOMER:opp.structured_analysis.TARGET_CUSTOMER,KNOWN_PROBLEM:opp.structured_analysis.CUSTOMER_PROBLEM,KNOWN_OFFER:opp.structured_analysis.PRODUCT_OR_SERVICE,KNOWN_REVENUE_MODEL:opp.structured_analysis.REVENUE_MODEL,NEXUS_CAPABILITY_FIT:opp.structured_analysis.NEXUS_CAPABILITY_FIT,QUESTIONS_ALREADY_ANSWERED:['Nova captured the initial opportunity framing.'],EXACT_RESEARCH_GAPS:opp.structured_analysis.RESEARCH_GAPS,RESEARCH_OBJECTIVE:'Verify customer need, delivery scope, demand, unit economics, permissible compensation, and partner access. Continue from this packet; do not restart.',RETURN_TO:'BUSINESS_OPPORTUNITY_WORKFLOW',NEXT_OWNER:'RESEARCH'}
    const {data:source, error:sourceError}=await client.from('nexus_feeder_sources').select('case_id').eq('source_id',opp.source_id).single()
    if(sourceError)throw sourceError
    const handoff=await client.from('nexus_feeder_handoffs').upsert({handoff_id:handoffId,source_id:opp.source_id,opportunity_id:opportunityId,case_id:source.case_id,from_department:'NOVA',to_department:'RESEARCH',summary:'Ray/Nova opportunity research continuation',structured_data:packet,what_was_completed:['Ray described the idea','Nova created and persisted first-pass analysis'],what_remains:opp.structured_analysis.RESEARCH_GAPS,recommendation:'SEND_TO_RESEARCH',action:'Research only the listed gaps and return to the existing opportunity',expected_output:'Evidence-backed opportunity continuation packet for the Business Opportunity workflow',status:'CREATED'},{onConflict:'handoff_id'})
    if(handoff.error)throw handoff.error
  }
  return {opportunityId,status,action}
}
