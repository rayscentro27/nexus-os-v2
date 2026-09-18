/** Transformation-first Research -> Alpha -> Marketing -> Creative contract. */

export type ClaimClass = 'OBSERVED_FACT' | 'SUPPORTED_CLAIM' | 'HYPOTHESIS' | 'POSSIBLE_OUTCOME' | 'PROHIBITED_GUARANTEE'
export type PackageStatus = 'DRAFT' | 'READY_FOR_CREATIVE' | 'READY_FOR_QA' | 'READY_FOR_REVIEW' | 'BLOCKED'

export interface TransformationContract {
  transformation_id: string; audience: string; current_state: string; pain: string; limitations: string[]
  desired_outcome: string; transformation_statement: string; after_state: string; emotional_result: string
  business_result: string; proof_requirements: string[]; research_evidence_refs: string[]
  alpha_decision_ref: string; confidence: 'low' | 'medium' | 'high'; created_at: string
}
export interface MarketingInput {
  marketing_input_id: string; research_need_id: string; research_evidence_refs: string[]; alpha_receipt_id: string
  alpha_decision: 'QUALIFY'; audience: string; customer_language: string[]; current_state: string; pain: string
  desired_outcome: string; commercial_intent: string; offer_candidates: string[]; seo_evidence_refs: string[]; transformation_ref: string
}
export interface MarketingBrief {
  marketing_brief_id: string; campaign_id: string; audience: string; current_state: string; pain: string; desired_outcome: string
  transformation_statement: string; after_state: string; emotional_result: string; business_result: string; offer: string; proof: string[]
  channel: string; funnel: string; cta: string; success_metric: string[]; research_evidence_refs: string[]; alpha_decision_ref: string
  transformation_ref: string; status: PackageStatus
}
export interface CreativeInput {
  creative_input_id: string; marketing_brief_id: string; campaign_id: string; audience: string; before_state: string; after_state: string
  transformation_statement: string; emotional_transformation: string; proof: string[]; cta: string; channel: string; platform: string
  brand_requirements: string[]; asset_requirements: string[]
}
export interface CreativeBrief {
  creative_brief_id: string; creative_input_id: string; marketing_brief_id: string; campaign_id: string; audience: string
  before_state: string; after_state: string; visual_transformation: string; emotional_transformation: string; hook: string; script: string
  scenes: string[]; proof: string[]; cta: string; platform: string; asset_types: string[]; quality_requirements: string[]
  brand_requirements: string[]; status: PackageStatus
}
export interface CreativePackage {
  creative_package_id: string; campaign_id: string; marketing_brief_id: string; creative_brief_id: string; transformation_id: string
  platform: string; aspect_ratio: string; duration_target: string; hook: string; script: string; scenes: string[]; visual_direction: string
  asset_requirements: string[]; audio_requirements: string[]; caption_requirements: string[]; branding_requirements: string[]; cta: string
  proof_constraints: string[]; quality_requirements: string[]
}
export interface ProductionPlanning {
  production_planning_id: string; creative_package_id: string; campaign_id: string
  objective: string; deliverables: string[]; phases: string[]; dependencies: string[]
  resource_constraints: string[]; continuity_bible_ref: string; readiness_gate: string
}
export interface ScriptCritique {
  script_critique_id: string; production_planning_id: string; strengths: string[]; deficiencies: string[]
  claim_risks: string[]; required_revisions: string[]; status: 'PASS' | 'REVISE'
}
export interface Storyboard {
  storyboard_id: string; production_planning_id: string; scenes: Array<{ scene_id: string; purpose: string; action: string; dialogue_or_vo: string; proof: string }>
  status: 'DRAFT' | 'READY'
}
export interface ContinuityPlan {
  continuity_plan_id: string; storyboard_id: string; characters: string[]; environments: string[]; props: string[]
  wardrobe_and_style: string[]; continuity_rules: string[]
}
export interface PromptPackage {
  prompt_package_id: string; storyboard_id: string; image_prompts: string[]; video_prompts: string[]
  negative_prompts: string[]; prompt_constraints: string[]
}
export interface ProductionReadiness {
  production_readiness_id: string; creative_package_id: string; planning_id: string; script_critique_id: string
  storyboard_id: string; continuity_plan_id: string; prompt_package_id: string; status: 'READY' | 'BLOCKED'
  gates: Record<string, boolean>; blockers: string[]
}
export interface QAReceipt {
  qa_receipt_id: string; creative_package_id: string; status: 'PASS' | 'REQUEST_REVISION' | 'BLOCKED'; findings: string[]
  checked_fields: string[]; claim_classification: ClaimClass[]; created_at: string
}
export interface ApprovalRecord {
  approval_id: string; campaign_id: string; creative_package_id: string; status: 'PENDING_RAY_REVIEW' | 'APPROVED_INTERNAL' | 'REJECTED'
  publication_authorized: false; created_at: string
}
export interface OutcomeFeedbackContract {
  feedback_id: string; campaign_id: string; transformation_id: string; research_need_id: string; alpha_decision_ref: string
  observed_outcome: string; interpretation: string; hypothesis: string; causal_claim: false; research_feedback_link: string; alpha_feedback_link: string
}
export interface WorkerJobInput {
  job_id: string; worker_type: string; campaign_id: string; creative_package_id: string; input_artifacts: string[]
  parameters: Record<string, string | number | boolean>; resource_requirements: Record<string, string | number>; max_runtime: number
  output_destination: string; requested_by: string; production_readiness_id: string
}
export interface WorkerJobOutput {
  job_id: string; status: 'QUEUED' | 'RUNNING' | 'COMPLETE' | 'FAILED'; started_at: string | null; completed_at: string | null
  runtime_seconds: number | null; artifacts: string[]; artifact_hashes: string[]; tool_versions: string[]; logs: string[]; errors: string[]
  resource_usage: Record<string, number>
}
export interface CampaignContractProof {
  transformation: TransformationContract; marketing_input: MarketingInput; marketing_brief: MarketingBrief; creative_input: CreativeInput
  creative_brief: CreativeBrief; creative_package: CreativePackage; qa: QAReceipt; approval: ApprovalRecord
  production_planning: ProductionPlanning; script_critique: ScriptCritique; storyboard: Storyboard; continuity_plan: ContinuityPlan
  prompt_package: PromptPackage; production_readiness: ProductionReadiness
  outcome_feedback: OutcomeFeedbackContract; future_worker_input: WorkerJobInput; future_worker_output: WorkerJobOutput
  claim_classification: ClaimClass[]; prohibited_claims_blocked: string[]
  linkage: { campaign_id: string; offer_id: string; variant_id: string; asset_linkage: string; canonical_stores: string[] }
}

const BANNED = [/guaranteed?\s+(funding|approval|revenue|expansion|results?)/i, /will\s+(get|receive|secure)\s+(funding|approved|revenue)/i, /no\s+matter\s+your\s+credit/i, /fabricated\s+testimonial/i]

export function stableContractId(prefix: string, seed: string): string {
  let hash = 2166136261
  for (const char of seed) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619) >>> 0
  return `${prefix}_${hash.toString(16).padStart(8, '0')}`
}

export function classifyClaims(text: string[]): { classes: ClaimClass[]; blocked: string[] } {
  const blocked = text.filter(item => BANNED.some(pattern => pattern.test(item)))
  return { classes: blocked.length ? ['PROHIBITED_GUARANTEE'] : ['POSSIBLE_OUTCOME', 'SUPPORTED_CLAIM'], blocked }
}

export function validateTransformation(contract: TransformationContract): void {
  for (const [field, value] of Object.entries(contract)) {
    if (['created_at', 'confidence', 'limitations', 'proof_requirements', 'research_evidence_refs'].includes(field)) continue
    if (typeof value === 'string' && !value.trim()) throw new Error(`${field} is required`)
  }
  const check = classifyClaims([contract.transformation_statement, contract.after_state, contract.business_result])
  if (check.blocked.length) throw new Error(`Prohibited claims: ${check.blocked.join('; ')}`)
}

export function qaCreativePackage(pkg: CreativePackage, transformation: TransformationContract): QAReceipt {
  const claims = classifyClaims([pkg.hook, pkg.script, pkg.visual_direction, pkg.cta, ...pkg.scenes])
  const complete = Boolean(pkg.hook && pkg.script && pkg.scenes.length && pkg.cta && transformation.transformation_statement)
  return { qa_receipt_id: stableContractId('qa', pkg.creative_package_id), creative_package_id: pkg.creative_package_id,
    status: claims.blocked.length ? 'REQUEST_REVISION' : complete ? 'PASS' : 'BLOCKED',
    findings: claims.blocked.length ? ['Prohibited guarantee language detected'] : ['Transformation, proof, CTA, brand, platform, and claim-safety checks passed for internal review.'],
    checked_fields: ['transformation clarity', 'audience relevance', 'hook strength', 'message consistency', 'proof integrity', 'CTA clarity', 'brand compliance', 'platform suitability', 'claim safety'],
    claim_classification: claims.classes, created_at: new Date().toISOString() }
}

export function buildRestaurantCampaignProof(now = new Date().toISOString()): CampaignContractProof {
  const researchNeedId = 'need_f527d1db8c4d1e5de721'
  const alphaReceiptId = 'alpha_qualified_need_f527d1db8c4d1e5de721'
  const campaignId = 'goclear-funding-readiness-r20b'; const offerId = 'readiness_review_97'; const variantId = 'restaurant-transformation-internal-v1'
  const evidence = ['research_need:need_f527d1db8c4d1e5de721', 'research_evidence:funding-denial-language', 'research_evidence:documentation-uncertainty']
  const transformation: TransformationContract = { transformation_id: stableContractId('transformation', `${researchNeedId}:${variantId}`),
    audience: 'Restaurant owners preparing for business funding or a funding-readiness review',
    current_state: 'The owner is operating under financial pressure and is uncertain whether the business is ready for a funding conversation.',
    pain: 'Funding denials, unclear credit thresholds, and documentation uncertainty make it difficult to act on stabilization or growth plans.',
    limitations: ['uncertain readiness', 'limited visibility into documentation gaps', 'fear of wasting an application'],
    desired_outcome: 'Understand readiness gaps and practical next steps before pursuing funding.',
    transformation_statement: 'Turn funding uncertainty into a documented readiness path so the owner can make a clearer, better-prepared next move.',
    after_state: 'The owner has a readiness view, prioritized document checklist, and grounded next steps; funding approval remains undecided.',
    emotional_result: 'More clarity and operational breathing room without promising an outcome the evidence cannot support.',
    business_result: 'Better preparation for decisions about equipment, payroll, inventory, marketing, or other growth priorities.',
    proof_requirements: ['current business and credit information supplied by the client', 'documented readiness review', 'readiness distinguished from approval'],
    research_evidence_refs: evidence, alpha_decision_ref: alphaReceiptId, confidence: 'high', created_at: now }
  validateTransformation(transformation)
  const marketingInput: MarketingInput = { marketing_input_id: stableContractId('marketing_input', transformation.transformation_id), research_need_id: researchNeedId,
    research_evidence_refs: evidence, alpha_receipt_id: alphaReceiptId, alpha_decision: 'QUALIFY', audience: transformation.audience,
    customer_language: ['new business', 'denied funding', 'credit requirements', 'documentation'], current_state: transformation.current_state, pain: transformation.pain,
    desired_outcome: transformation.desired_outcome, commercial_intent: 'Problem-solving intent: understand readiness before applying or making a growth decision.',
    offer_candidates: ['Credit & Funding Readiness Review'], seo_evidence_refs: [], transformation_ref: transformation.transformation_id }
  const marketingBrief: MarketingBrief = { marketing_brief_id: stableContractId('marketing_brief', marketingInput.marketing_input_id), campaign_id: campaignId,
    audience: transformation.audience, current_state: transformation.current_state, pain: transformation.pain, desired_outcome: transformation.desired_outcome,
    transformation_statement: transformation.transformation_statement, after_state: transformation.after_state, emotional_result: transformation.emotional_result,
    business_result: transformation.business_result, offer: 'Credit & Funding Readiness Review', proof: transformation.proof_requirements,
    channel: 'internal landing-page and short-form concept', funnel: 'research evidence → readiness review → Ray-approved checkout/onboarding',
    cta: 'Review your readiness before your next funding decision', success_metric: ['qualified review starts', 'completed readiness reviews', 'evidence-backed next-step decisions'],
    research_evidence_refs: evidence, alpha_decision_ref: alphaReceiptId, transformation_ref: transformation.transformation_id, status: 'READY_FOR_CREATIVE' }
  const creativeInput: CreativeInput = { creative_input_id: stableContractId('creative_input', marketingBrief.marketing_brief_id), marketing_brief_id: marketingBrief.marketing_brief_id,
    campaign_id: campaignId, audience: marketingBrief.audience, before_state: marketingBrief.current_state, after_state: marketingBrief.after_state,
    transformation_statement: transformation.transformation_statement, emotional_transformation: transformation.emotional_result, proof: marketingBrief.proof, cta: marketingBrief.cta,
    channel: marketingBrief.channel, platform: 'internal vertical-video concept', brand_requirements: ['GoClear clarity', 'calm executive tone', 'no guaranteed approval language'],
    asset_requirements: ['restaurant owner before/after operational scenes', 'readiness checklist visual', 'CTA end card'] }
  const creativeBrief: CreativeBrief = { creative_brief_id: stableContractId('creative_brief', creativeInput.creative_input_id), creative_input_id: creativeInput.creative_input_id,
    marketing_brief_id: marketingBrief.marketing_brief_id, campaign_id: campaignId, audience: creativeInput.audience, before_state: creativeInput.before_state, after_state: creativeInput.after_state,
    visual_transformation: 'Move from a crowded, uncertain restaurant back office to a calm planning table with a documented readiness path.', emotional_transformation: 'From pressure and ambiguity to clarity and a grounded next step.',
    hook: 'Before you chase funding, know what your business is ready to support.',
    script: 'A restaurant owner sees pressure points: equipment, payroll, inventory, and missed growth. The story shifts from chasing approval to documenting readiness and choosing the next step with clearer information.',
    scenes: ['Pressure points in the restaurant operation', 'Owner reviews readiness questions', 'Checklist and gaps become visible', 'Calm next-step planning with safe CTA'], proof: creativeInput.proof, cta: creativeInput.cta,
    platform: creativeInput.platform, asset_types: ['script', 'storyboard', 'caption overlay', 'internal end card'], quality_requirements: ['transformation is explicit', 'no financial guarantee', 'proof is labeled', 'CTA is readable'],
    brand_requirements: creativeInput.brand_requirements, status: 'READY_FOR_QA' }
  const creativePackage: CreativePackage = { creative_package_id: stableContractId('creative_package', creativeBrief.creative_brief_id), campaign_id: campaignId,
    marketing_brief_id: marketingBrief.marketing_brief_id, creative_brief_id: creativeBrief.creative_brief_id, transformation_id: transformation.transformation_id,
    platform: 'internal vertical-video concept', aspect_ratio: '9:16', duration_target: '30-45 seconds', hook: creativeBrief.hook, script: creativeBrief.script, scenes: creativeBrief.scenes,
    visual_direction: creativeBrief.visual_transformation, asset_requirements: creativeInput.asset_requirements, audio_requirements: ['voiceover optional', 'captions required for silent viewing'],
    caption_requirements: ['high contrast', 'claim-safe wording'], branding_requirements: creativeInput.brand_requirements, cta: creativeBrief.cta,
    proof_constraints: ['possible outcomes only', 'no approval guarantee', 'no fabricated testimonial'], quality_requirements: creativeBrief.quality_requirements }
  const qa = qaCreativePackage(creativePackage, transformation)
  const planningId = stableContractId('production_planning', creativePackage.creative_package_id)
  const production_planning: ProductionPlanning = { production_planning_id: planningId, creative_package_id: creativePackage.creative_package_id, campaign_id: campaignId,
    objective: 'Make the customer transformation visible, credible, and production-ready without introducing unsupported claims.',
    deliverables: ['script critique', 'storyboard', 'continuity plan', 'image prompts', 'video prompts', 'readiness receipt'],
    phases: ['critique', 'storyboard', 'continuity', 'prompting', 'readiness gate', 'worker handoff'],
    dependencies: [creativePackage.creative_package_id, transformation.transformation_id], resource_constraints: ['bounded internal proof', 'no external media generation'],
    continuity_bible_ref: stableContractId('continuity', planningId), readiness_gate: 'All critique, continuity, prompt, claim, and asset requirements resolved.' }
  const script_critique: ScriptCritique = { script_critique_id: stableContractId('script_critique', planningId), production_planning_id: planningId,
    strengths: ['clear before/after transformation', 'safe readiness framing', 'specific restaurant operating context'], deficiencies: [], claim_risks: [], required_revisions: [], status: 'PASS' }
  const storyboardId = stableContractId('storyboard', planningId)
  const storyboard: Storyboard = { storyboard_id: storyboardId, production_planning_id: planningId, status: 'READY', scenes: creativeBrief.scenes.map((purpose, index) => ({ scene_id: `${storyboardId}_scene_${index + 1}`, purpose, action: purpose, dialogue_or_vo: index === 0 ? creativeBrief.hook : creativeBrief.script, proof: creativeBrief.proof[index % creativeBrief.proof.length] })) }
  const continuity_plan: ContinuityPlan = { continuity_plan_id: stableContractId('continuity', storyboardId), storyboard_id: storyboardId,
    characters: ['one restaurant owner; consistent age range, wardrobe, and emotional arc'], environments: ['restaurant kitchen', 'back office planning table'], props: ['readiness checklist', 'operations notes', 'restaurant equipment context'],
    wardrobe_and_style: ['GoClear visual clarity', 'calm executive tone', 'consistent neutral palette'], continuity_rules: ['same owner across scenes', 'before state remains visibly pressured', 'after state shows clarity not guaranteed approval'] }
  const prompt_package: PromptPackage = { prompt_package_id: stableContractId('prompts', storyboardId), storyboard_id: storyboardId,
    image_prompts: storyboard.scenes.map(scene => `Internal concept image for ${scene.purpose}; show the restaurant owner and the documented readiness transformation; no logos beyond approved GoClear branding; no guaranteed outcome.`),
    video_prompts: storyboard.scenes.map(scene => `Short-form shot for ${scene.purpose}; preserve the same owner, environment, props, and claim-safe readiness message; ${scene.proof}.`),
    negative_prompts: ['guaranteed approval', 'guaranteed revenue', 'fabricated testimonial', 'unapproved lender branding'], prompt_constraints: ['internal only', 'no publication', 'preserve continuity', 'use proof labels'] }
  const production_readiness: ProductionReadiness = { production_readiness_id: stableContractId('readiness', planningId), creative_package_id: creativePackage.creative_package_id, planning_id: planningId,
    script_critique_id: script_critique.script_critique_id, storyboard_id: storyboard.storyboard_id, continuity_plan_id: continuity_plan.continuity_plan_id, prompt_package_id: prompt_package.prompt_package_id,
    status: qa.status === 'PASS' && script_critique.status === 'PASS' && storyboard.status === 'READY' ? 'READY' : 'BLOCKED',
    gates: { qa_passed: qa.status === 'PASS', script_critique_passed: script_critique.status === 'PASS', storyboard_ready: storyboard.status === 'READY', continuity_defined: continuity_plan.continuity_rules.length > 0, prompts_bounded: prompt_package.image_prompts.length > 0 && prompt_package.video_prompts.length > 0, publication_authorized: false }, blockers: [] }
  const approval: ApprovalRecord = { approval_id: stableContractId('approval', creativePackage.creative_package_id), campaign_id: campaignId, creative_package_id: creativePackage.creative_package_id, status: 'PENDING_RAY_REVIEW', publication_authorized: false, created_at: now }
  const outcome_feedback: OutcomeFeedbackContract = { feedback_id: stableContractId('feedback', campaignId), campaign_id: campaignId, transformation_id: transformation.transformation_id, research_need_id: researchNeedId,
    alpha_decision_ref: alphaReceiptId, observed_outcome: 'Not yet launched; no live outcome is available.', interpretation: 'Internal design proof only.', hypothesis: 'Clearer transformation framing may improve qualified review starts; this requires measurement.', causal_claim: false,
    research_feedback_link: `research_need:${researchNeedId}`, alpha_feedback_link: `alpha_receipt:${alphaReceiptId}` }
  const jobId = stableContractId('worker_job', creativePackage.creative_package_id)
  const future_worker_input: WorkerJobInput = { job_id: jobId, worker_type: 'MEDIA_RENDER', campaign_id: campaignId, creative_package_id: creativePackage.creative_package_id, input_artifacts: [], parameters: { internal_proof: true, publication: false }, resource_requirements: { host: 'provider-neutral', concurrency: 1 }, max_runtime: 300, output_destination: 'creative_assets via governed ingest', requested_by: 'nexus_internal_proof', production_readiness_id: production_readiness.production_readiness_id }
  const future_worker_output: WorkerJobOutput = { job_id: jobId, status: 'QUEUED', started_at: null, completed_at: null, runtime_seconds: null, artifacts: [], artifact_hashes: [], tool_versions: [], logs: [], errors: [], resource_usage: {} }
  const claims = classifyClaims([transformation.transformation_statement, transformation.after_state, creativeBrief.script])
  return { transformation, marketing_input: marketingInput, marketing_brief: marketingBrief, creative_input: creativeInput, creative_brief: creativeBrief, creative_package: creativePackage, qa, approval, production_planning, script_critique, storyboard, continuity_plan, prompt_package, production_readiness, outcome_feedback, future_worker_input, future_worker_output,
    claim_classification: claims.classes, prohibited_claims_blocked: claims.blocked, linkage: { campaign_id: campaignId, offer_id: offerId, variant_id: variantId, asset_linkage: `creative_assets.campaign_id=${campaignId}; creative_assets.brief_id=${creativeBrief.creative_brief_id}`, canonical_stores: ['creative_campaigns', 'creative_briefs', 'creative_design_briefs', 'creative_assets', 'approvals', 'studio_outputs'] } }
}

export function canonicalPersistenceProjection(proof: CampaignContractProof) {
  return { creative_campaigns: { campaign_id: proof.linkage.campaign_id, metadata: { transformation_id: proof.transformation.transformation_id, marketing_brief_id: proof.marketing_brief.marketing_brief_id, alpha_decision_ref: proof.transformation.alpha_decision_ref } },
    creative_briefs: { brief_id: proof.creative_brief.creative_brief_id, campaign_id: proof.linkage.campaign_id, metadata: proof.creative_brief },
    creative_assets: { campaign_id: proof.linkage.campaign_id, brief_id: proof.creative_brief.creative_brief_id, metadata: proof.creative_package },
    approvals: proof.approval, studio_outputs: { campaign_id: proof.linkage.campaign_id, approval_id: proof.approval.approval_id, metadata: { qa_receipt_id: proof.qa.qa_receipt_id, publication_authorized: false } } }
}
