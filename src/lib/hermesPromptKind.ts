import { isCasualCommonQuestion, isHumanExperienceQuestion } from './hermesCommonConversation';
import { isAdvisoryFollowUpQuestion } from './hermesAdvisoryContinuity';

export type HermesPromptKind =
  | 'safety_execution' | 'provenance' | 'system_health' | 'approvals_pending'
  | 'research_engine_status' | 'client_records' | 'specialist_handoff'
  | 'specialist_agent_inventory' | 'external_current_info' | 'ray_review' | 'scheduling' | 'selection_reference' | 'casual_common'
  | 'advisory_followup' | 'explicit_new_topic' | 'unknown';

export function normalizePrompt(message: string): string {
  return message.normalize('NFKC').replace(/[’]/g, "'").replace(/\s+/g, ' ').trim();
}

export function isProvenanceQuestion(message: string): boolean {
  return /\b(?:where did (?:that|this|your|the) (?:answer|response) come from|what (?:source|sources) did you use|what did you get (?:that|this|the) (?:answer|response) from|what part of your decision[- ]making process did you use|how did you decide|why did you answer|show (?:the )?(?:full )?(?:route|trace))\b/i.test(message);
}

export function isSystemHealthQuestion(message: string): boolean {
  return /\b(?:how|what) (?:is|does) (?:the |our )?system health|\bsystem health\b|\b(?:what is|what's|how's|how is) (?:the |our )?(?:nexus |system )?health\b|\b(?:is|how) (?:nexus|system) (?:healthy|working|running|operational)\b|\b(?:what is broken|where is the problem|what is not working|what's broken|what ain't working)\b|\b(?:what is working|what's working|what is operational)\b/i.test(message);
}

export function isApprovalStatusQuestion(message: string): boolean {
  return /\b(?:do i have|are there|show|list|what|which|any|how many)\b.*\b(?:approval|approvals|ray review|review cards?)\b.*\b(?:pending|waiting|open|have|there|show|list)?\b|\b(?:pending|waiting|open)\b.*\b(?:approval|approvals|ray review|review cards?)\b/i.test(message);
}

export function isResearchStatusQuestion(message: string): boolean {
  return /\b(?:is|does|how is|check|show|what is)\b.*\b(?:research engine|youtube research|research pipeline)\b.*\b(?:working|running|configured|status|work|health)?\b|\b(?:research engine|research pipeline)\b.*\b(?:status|working|running|configured|health)\b/i.test(message);
}

export function isClientRecordQuestion(message: string): boolean {
  return /\b(?:do we have|are there|show|list|how many|any)\b.*\b(?:clients?|customers?|client records?|client profiles?)\b|\b(?:clients?|customers?)\b.*\b(?:exist|active|available|do we have)\b/i.test(message);
}

export function isSelectionReference(message: string): boolean {
  return /^(?:number|option|#)\s*\d+[.!]?$/i.test(message.trim()) || /^(?:that one|this one|the (?:first|second|third|last) one)[.!]?$/i.test(message.trim()) || /\bcreate (?:a )?(?:ray review )?card for (?:that|it)\b/i.test(message);
}

export function isSpecialistAgentInventoryQuestion(message: string): boolean {
  return /\b(?:do (?:we|i|you) have|is (?:there|the)\b.*\b(?:a |an )?|who handles?|what about)\b.*\b(?:specialist|agent)\b|\b(?:credit|funding|research|grant|trading|crm|content|sales|marketing|automation|compliance)\s+specialist\b|\bspecialist\s+(?:agent|for)\b|\bwho\s+(?:handles?|does|is responsible for|manages?)\s+(?:the\s+)?(?:credit|funding|research|grant|trading|crm|content|sales|marketing|automation|compliance)\b/i.test(message);
}

export function isExternalCurrentInfoQuestion(message: string): boolean {
  return /\b(?:what was|what is|what['']s|tell me|give me|show me)\b.*\b(?:score|scores?|results?|outcome|winner|champion|standings?|record|stats?)\b.*\b(?:last night|tonight|today|yesterday|this (?:week|weekend|season|year)|recently|latest)\b|\b(?:sports?|game|match|race|event|news|weather|stock|price|score)\b.*\b(?:last night|tonight|today|yesterday|this (?:week|weekend|season|year)|recently|latest|now|current)\b|\b(?:what happened|what['']s happening|what['']s going on)\b.*\b(?:today|tonight|last night|this (?:week|weekend))\b|\b(?:current|latest|recent|today['']s|tonight['']s)\b.*\b(?:news|events?|happenings?|stock|price|weather|forecast)\b/i.test(message);
}

export function isCasualHumanExperience(message: string): boolean {
  return isHumanExperienceQuestion(message) || isCasualCommonQuestion(message);
}

export function isActionRequest(message: string): boolean {
  return /\b(?:create|prepare|delegate|handoff|schedule|send|publish|charge|deploy|delete|execute|approve|assign|start)\b/i.test(message);
}

export function isExplicitNewTopic(message: string): boolean {
  if (/\b(?:tesla\s+)?model\s+(?:3|s|x|y)\b|\bbusiness model\b|\bpricing model\b/i.test(message)) return true;
  return /\b(?:client|approval|research engine|system health|crm|car|vehicle|trading|business opportunit|credit|funding|marketing|nexus)\b/i.test(message) && !/^(?:that|this|it|so|and|but)\b/i.test(message.trim());
}

export function detectPromptKind(raw: string): HermesPromptKind {
  const message = normalizePrompt(raw);
  if (/\b(?:publish|charge|deploy|delete|truncate|execute|place)\b.*\b(?:now|live|customer|trade|database|production)?\b|\bstart\b.*\bscheduler\b/i.test(message)) return 'safety_execution';
  if (isProvenanceQuestion(message)) return 'provenance';
  if (isSystemHealthQuestion(message)) return 'system_health';
  if (isApprovalStatusQuestion(message)) return 'approvals_pending';
  if (isResearchStatusQuestion(message)) return 'research_engine_status';
  if (isClientRecordQuestion(message)) return 'client_records';
  if (/\b(?:prepare|create|draft)\b.*\bspecialist handoff\b|^specialist handoff$/i.test(message)) return 'specialist_handoff';
  if (isSpecialistAgentInventoryQuestion(message)) return 'specialist_agent_inventory';
  if (isExternalCurrentInfoQuestion(message)) return 'external_current_info';
  if (/\b(?:create|prepare|queue|add)\b.*\b(?:ray review|review card)\b/i.test(message)) return 'ray_review';
  if (/\b(?:schedule|set up|create)\b.*\b(?:report|summary|reminder|audit)\b|\b(?:weekly|daily|recurring)\b.*\b(?:report|summary|audit)\b/i.test(message)) return 'scheduling';
  if (isCasualHumanExperience(message)) return 'casual_common';
  if (isSelectionReference(message)) return 'selection_reference';
  if (isExplicitNewTopic(message)) return 'explicit_new_topic';
  if (isAdvisoryFollowUpQuestion(message)) return 'advisory_followup';
  return 'unknown';
}
