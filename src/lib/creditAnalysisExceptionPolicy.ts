export type CreditExceptionCode='none'|'parser_low_confidence'|'unreadable_report'|'ambiguous_account_match'|'contradictory_source_data'|'missing_source_structure'|'identity_theft_indicator'|'client_complaint_or_legal_threat'|'unsupported_manual_override'|'generation_failure'|'system_integrity_failure'|'admin_requested_review'
export interface CreditExceptionEvaluation {exception_required:boolean;exception_code:CreditExceptionCode;reason:string;confidence:'high'|'medium'|'low';recommended_next_action:string}
export function evaluateCreditAnalysisException(input:{parserConfidence?:string;extractionSuccess?:boolean;accountCount?:number;ambiguousMatchCount?:number;integrityMismatch?:boolean;identityTheftAsserted?:boolean;complaintOrLegalThreat?:boolean;unsupportedOverride?:boolean;generationFailed?:boolean;adminRequested?:boolean}):CreditExceptionEvaluation{
  const hit=(code:CreditExceptionCode,reason:string,action:string,confidence:'high'|'medium'|'low'='high'):CreditExceptionEvaluation=>({exception_required:true,exception_code:code,reason,confidence,recommended_next_action:action})
  if(input.adminRequested)return hit('admin_requested_review','An authorized admin explicitly requested review.','Open the GoClear exception record.')
  if(input.identityTheftAsserted)return hit('identity_theft_indicator','Identity theft was asserted and requires a protected specialist workflow.','Route to identity-theft support; do not infer facts.')
  if(input.complaintOrLegalThreat)return hit('client_complaint_or_legal_threat','Complaint or legal-threat language requires specialist handling.','Pause automation and route to GoClear.')
  if(input.integrityMismatch)return hit('system_integrity_failure','Saved counts or relationships do not match verified processing output.','Stop client actions and inspect system integrity.')
  if(input.extractionSuccess===false)return hit('unreadable_report','The report could not be extracted reliably.','Request a readable report or retry supported extraction.')
  if(input.generationFailed)return hit('generation_failure','Canonical generation failed after parsing.','Retry safely, then escalate if attempts are exhausted.')
  if((input.ambiguousMatchCount||0)>0)return hit('ambiguous_account_match',`${input.ambiguousMatchCount} account match candidate(s) are below the automatic merge threshold.`,'Review only the ambiguous candidates.','medium')
  if(input.parserConfidence==='low')return hit('parser_low_confidence','Parser confidence is below the automatic-processing threshold.','Review extraction quality before client action.','medium')
  if(input.unsupportedOverride)return hit('unsupported_manual_override','A requested manual override is not supported by current rules.','Require an authorized documented decision.')
  if((input.accountCount||0)===0)return hit('missing_source_structure','No usable tradeline structure was found.','Confirm the document format or request another report.','medium')
  return {exception_required:false,exception_code:'none',reason:'Normal report processing completed without a defined exception.',confidence:'high',recommended_next_action:'Continue automated readiness processing.'}
}
