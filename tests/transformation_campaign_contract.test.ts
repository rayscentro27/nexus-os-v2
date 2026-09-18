import { describe, expect, it } from 'vitest'
import {
  buildRestaurantCampaignProof,
  canonicalPersistenceProjection,
  classifyClaims,
  qaCreativePackage,
} from '../src/lib/transformationCampaignContract'

describe('transformation-first campaign contract', () => {
  it('builds a correlated restaurant campaign package from Research and Alpha', () => {
    const proof = buildRestaurantCampaignProof('2026-09-18T00:00:00.000Z')
    expect(proof.transformation.audience).toMatch(/Restaurant owners/)
    expect(proof.transformation.transformation_statement).toMatch(/readiness path/)
    expect(proof.marketing_input.research_need_id).toBe('need_f527d1db8c4d1e5de721')
    expect(proof.marketing_input.alpha_decision).toBe('QUALIFY')
    expect(proof.marketing_brief.transformation_ref).toBe(proof.transformation.transformation_id)
    expect(proof.creative_brief.marketing_brief_id).toBe(proof.marketing_brief.marketing_brief_id)
    expect(proof.creative_package.creative_brief_id).toBe(proof.creative_brief.creative_brief_id)
    expect(proof.qa.status).toBe('PASS')
    expect(proof.production_planning.creative_package_id).toBe(proof.creative_package.creative_package_id)
    expect(proof.script_critique.status).toBe('PASS')
    expect(proof.storyboard.status).toBe('READY')
    expect(proof.continuity_plan.continuity_rules.length).toBeGreaterThan(0)
    expect(proof.prompt_package.image_prompts.length).toBe(proof.storyboard.scenes.length)
    expect(proof.prompt_package.video_prompts.length).toBe(proof.storyboard.scenes.length)
    expect(proof.production_readiness.status).toBe('READY')
    expect(proof.future_worker_input.production_readiness_id).toBe(proof.production_readiness.production_readiness_id)
    expect(proof.approval.publication_authorized).toBe(false)
  })

  it('blocks prohibited guarantees and preserves a safe outcome taxonomy', () => {
    expect(classifyClaims(['Guaranteed funding approval for every restaurant']).classes).toContain('PROHIBITED_GUARANTEE')
    const proof = buildRestaurantCampaignProof()
    expect(proof.prohibited_claims_blocked).toEqual([])
    expect(proof.claim_classification).toContain('POSSIBLE_OUTCOME')
  })

  it('requests one revision when a creative package contains unsafe language', () => {
    const proof = buildRestaurantCampaignProof()
    const unsafe = { ...proof.creative_package, hook: 'Guaranteed funding approval for your restaurant.' }
    const qa = qaCreativePackage(unsafe, proof.transformation)
    expect(qa.status).toBe('REQUEST_REVISION')
    expect(qa.qa_receipt_id).toBeTruthy()
    expect(qa.findings.join(' ')).toMatch(/guarantee/i)
  })

  it('projects into existing canonical stores without creating a parallel database', () => {
    const proof = buildRestaurantCampaignProof()
    const projection = canonicalPersistenceProjection(proof)
    expect(Object.keys(projection)).toEqual(['creative_campaigns', 'creative_briefs', 'creative_assets', 'approvals', 'studio_outputs'])
    expect(projection.creative_campaigns.metadata.transformation_id).toBe(proof.transformation.transformation_id)
    expect(projection.approvals.publication_authorized).toBe(false)
    expect(proof.future_worker_input.output_destination).toMatch(/creative_assets/)
    expect(proof.future_worker_output.status).toBe('QUEUED')
  })
})
