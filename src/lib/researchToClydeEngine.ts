import type { BureauDiscrepancy, CanonicalAccount } from './crossBureauCreditComparison'
import type { CreditStrategyDefinition } from './creditStrategyCatalog'

export const RESEARCH_TO_CLYDE_RULESET='research-to-clyde-v1'
export type EvidenceLevel='authoritative'|'strong'|'moderate'|'limited'|'anecdotal'|'unsupported'|'contradicted'
export type ReadinessStatus='ready_to_review'|'almost_ready'|'action_needed'|'insufficient_information'
export const ALPHA_RESEARCH_BOUNDARY={clientTables:false,clientPii:false,clientActions:false,mailing:false,outputs:'sanitized discovery artifacts only'} as const
export const NEXUS_RESEARCH_BOUNDARY={classifyClaims:true,scoreEvidence:true,approveStrategies:true,versionStrategies:true} as const

const blocked=[/guaranteed\s+(deletion|removal|score|funding|approval)/i,/automatic\s+(damages|deletion)/i,/\bmust delete\b/i,/original signed (physical )?contract (is )?always required/i,/remove everything in four days/i,/dispute (every|everything)/i]
export function validateStrategyDraft(text:string){const hits=blocked.filter(x=>x.test(text)).map(x=>x.source);return {safe:hits.length===0,blockedPatterns:hits,clientReviewRequired:true,mailAllowed:false,disclaimer:'Draft preview only. Client review and authorization are required. Nexus does not guarantee correction, removal, score change, or funding approval.'}}
export function generateSafeStrategyDraft(input:{strategyId:string;strategyVersion:number;templateVersion:string;outputType:string;accountReference:string;detectedFacts:string[];clientConfirmedFacts?:string[]}){
 const suffix=String(input.accountReference||'').replace(/[^a-z0-9]/gi,'').slice(-4);const masked=suffix?`****${suffix}`:'Not available'
 const text=[`${input.outputType.replaceAll('_',' ')} — draft preview`, `Strategy: ${input.strategyId} version ${input.strategyVersion}`,`Account reference: ${masked}`,'Nexus-detected facts:',...input.detectedFacts.map(x=>`- ${x}`),...(input.clientConfirmedFacts?.length?['Client-confirmed facts:',...input.clientConfirmedFacts.map(x=>`- ${x}`)]:[]),'Please review the structured comparison and supporting records. Choose only an option that accurately reflects your circumstances.','Draft preview only. Client review and authorization are required. Nexus does not guarantee correction, removal, score change, or funding approval.'].join('\n')
 const validation=validateStrategyDraft(text);return {text,status:validation.safe?'draft_ready':'blocked',validation,accountReference:masked,strategyVersion:input.strategyVersion,templateVersion:input.templateVersion,clientReviewRequired:true,clientAuthorized:false,mailCreated:false,provenance:{structuredFactsOnly:true,clientConfirmedFactsOnly:true}}
}

export function classifyResearchClaim(text:string):{claimType:string;evidenceLevel:EvidenceLevel;riskScore:number;promotional:boolean;guarantee:boolean;universal:boolean;legalConclusion:boolean;clientSafe:boolean;approvalState:'needs_review'|'rejected'}{
 const promotional=/(four days|87%|hack|secret method)/i.test(text),guarantee=/(guarantee|automatic deletion|must delete|automatic damages)/i.test(text),universal=/(every negative|everything|always required|universal)/i.test(text),legalConclusion=/(violated the law|entitled to damages|must delete)/i.test(text);const rejected=promotional||guarantee||universal||legalConclusion
 return {claimType:promotional?'promotional_claim':legalConclusion?'legal_claim':'practitioner_method',evidenceLevel:rejected?'unsupported':'anecdotal',riskScore:rejected?95:45,promotional,guarantee,universal,legalConclusion,clientSafe:false,approvalState:rejected?'rejected':'needs_review'}
}

export interface StrategyMatchDecision {strategy:CreditStrategyDefinition;score:number;matchReasons:string[];exclusionReasons:string[];strategyVersion:number}
export function rankApprovedStrategies(discrepancy:BureauDiscrepancy,catalog:CreditStrategyDefinition[],account?:CanonicalAccount){
 const included:StrategyMatchDecision[]=[];const excluded:Array<{strategyId:string;reasons:string[]}>=[]
 for(const strategy of catalog){const reasons:string[]=[]
  if(!['approved_for_education','approved_for_tool_use'].includes(strategy.approvalStatus))reasons.push('strategy_not_approved')
  if(discrepancy.confidence==='low')reasons.push('low_confidence_discrepancy')
  if(account?.matchConfidence==='low')reasons.push('low_confidence_canonical_match')
  if(!strategy.categories.some(c=>c===discrepancy.discrepancyType||discrepancy.possibleStrategyCategories.includes(c)))reasons.push('eligibility_not_met')
  if(reasons.length){excluded.push({strategyId:strategy.strategyId,reasons});continue}
  const tool=strategy.approvalStatus==='approved_for_tool_use';const score=Math.min(100,55+(discrepancy.confidence==='high'?20:10)+(tool?10:5)+(strategy.officialSupportSummary?5:0))
  included.push({strategy,score,matchReasons:[`objective_${discrepancy.discrepancyType}`,'approved_reusable_strategy',`evidence_${discrepancy.confidence}`],exclusionReasons:[],strategyVersion:strategy.version})
 }
 return {matches:included.sort((a,b)=>b.score-a.score),excluded,rulesetVersion:RESEARCH_TO_CLYDE_RULESET,exceptionRequired:discrepancy.confidence==='low'||account?.matchConfidence==='low'}
}

export function buildStructuredClydeGuidance(input:{account:CanonicalAccount;discrepancy:BureauDiscrepancy;match:StrategyMatchDecision}){
 const {account,discrepancy,match}=input;return {detectedFact:discrepancy.differenceSummary,source:'Nexus structured bureau comparison',accountLabel:`${account.furnisher} ${account.maskedAccountReference}`.trim(),bureaus:Object.keys(discrepancy.bureauValues),bureauValues:discrepancy.bureauValues,approvedEducationalStrategy:{id:match.strategy.strategyId,version:match.strategyVersion,title:match.strategy.name,whyItMayApply:match.matchReasons.join(', '),evidenceLevel:discrepancy.confidence},uncertainty:discrepancy.confidence==='high'?'The difference is objective; the correct value still depends on records and client facts.':'The extraction or match needs review before action.',limitations:match.strategy.limitations,clientQuestions:match.strategy.clientFactsNeeded,nextTools:match.strategy.availableTools,readiness:{status:'action_needed' as ReadinessStatus,creditProfileImpact:discrepancy.fundingImpact,tier1:discrepancy.tier1Impact,tier2:discrepancy.tier2Impact},choices:['This matches my situation','I need more information','This does not apply','I have supporting evidence','I do not have supporting evidence','Save and return later']}
}

export function evaluateResearchToClydeException(input:{approvedMatches:number;highImpact?:boolean;conflictingStrategies?:boolean;lowConfidenceDiscrepancy?:boolean;lowConfidenceMatch?:boolean;evidenceContradiction?:boolean;complaint?:boolean;identityTheft?:boolean;generationFailed?:boolean;draftBlocked?:boolean;clientRequested?:boolean}){
 const hit=(code:string,reason:string,risk='medium')=>({exceptionRequired:true,code,reason,confidence:'high',risk,recommendedAction:'Pause the affected automation and open a GoClear exception.'})
 if(input.identityTheft)return hit('identity_theft_indicator','Possible identity theft requires protected specialist handling.','high')
 if(input.complaint)return hit('client_complaint_or_legal_threat','Complaint or legal-threat language requires specialist handling.','high')
 if(input.draftBlocked)return hit('draft_safety_validator_failure','The proposed draft contains prohibited wording.','high')
 if(input.generationFailed)return hit('strategy_generation_failure','The structured strategy output failed integrity checks.','high')
 if(input.evidenceContradiction)return hit('evidence_contradicts_report','Client evidence conflicts with structured report facts.')
 if(input.conflictingStrategies)return hit('conflicting_approved_strategies','Approved strategies conflict and cannot be ranked safely.')
 if(input.lowConfidenceDiscrepancy||input.lowConfidenceMatch)return hit('low_confidence_strategy_input','The discrepancy or canonical match is below the safe automation threshold.')
 if(input.highImpact&&input.approvedMatches===0)return hit('no_approved_strategy','No approved reusable strategy covers this high-impact discrepancy.')
 if(input.clientRequested)return hit('client_requested_specialist_review','The client explicitly requested specialist review.','low')
 return {exceptionRequired:false,code:'none',reason:'Approved normal-case automation may continue.',confidence:'high',risk:'low',recommendedAction:'Present approved options to the client.'}
}
