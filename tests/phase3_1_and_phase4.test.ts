import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '..')

describe('Phase 3.1 — Ray Review routing', () => {
  const routingPath = resolve(ROOT, 'src/lib/testerFeedbackRouting.ts')

  it('routing file exists', () => {
    expect(existsSync(routingPath)).toBe(true)
  })

  it('exports routeFeedbackToRayReview', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).toContain('routeFeedbackToRayReview')
  })

  it('exports routeAllBlockerHighFeedback', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).toContain('routeAllBlockerHighFeedback')
  })

  it('inserts into task_requests with task_type ray_review_item', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).toContain("task_type: 'ray_review_item'")
    expect(code).toContain("from('task_requests')")
  })

  it('links back to tester_feedback.ray_review_item_id', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).toContain('ray_review_item_id')
    expect(code).toContain("from('tester_feedback')")
  })

  it('deduplicates by feedback_record_id', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).toContain('feedback_record_id')
    expect(code).toContain('duplicate')
  })

  it('only routes blocker/high severity', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).toContain("severity !== 'blocker'")
    expect(code).toContain("severity !== 'high'")
  })

  it('sanitizes text fields', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).toContain('sanitize(')
    expect(code).toContain('replace')
  })

  it('does not expose service role key', () => {
    const code = readFileSync(routingPath, 'utf8')
    expect(code).not.toContain('SUPABASE_SERVICE_ROLE_KEY')
  })
})

describe('Phase 4 — Client journey model', () => {
  const journeyPath = resolve(ROOT, 'src/lib/clientJourneyModel.ts')

  it('journey model file exists', () => {
    expect(existsSync(journeyPath)).toBe(true)
  })

  it('exports computeJourneyState', () => {
    const code = readFileSync(journeyPath, 'utf8')
    expect(code).toContain('computeJourneyState')
  })

  it('defines all 6 stages', () => {
    const code = readFileSync(journeyPath, 'utf8')
    expect(code).toContain('credit_profile')
    expect(code).toContain('credit_improvement')
    expect(code).toContain('business_foundation')
    expect(code).toContain('business_bankability')
    expect(code).toContain('funding_readiness')
    expect(code).toContain('review_plan')
  })

  it('defines all valid statuses', () => {
    const code = readFileSync(journeyPath, 'utf8')
    expect(code).toContain('not_started')
    expect(code).toContain('action_needed')
    expect(code).toContain('in_progress')
    expect(code).toContain('ready_to_review')
    expect(code).toContain('complete')
    expect(code).toContain('blocked')
    expect(code).toContain('insufficient_information')
  })

  it('exports getStageIndex, getPreviousStage, getNextStage', () => {
    const code = readFileSync(journeyPath, 'utf8')
    expect(code).toContain('getStageIndex')
    expect(code).toContain('getPreviousStage')
    expect(code).toContain('getNextStage')
  })

  it('does not include guarantee language', () => {
    const code = readFileSync(journeyPath, 'utf8')
    expect(code).not.toContain('guaranteed')
    expect(code).not.toContain('guarantee')
  })
})

describe('Phase 4 — Funding readiness header', () => {
  const headerPath = resolve(ROOT, 'src/components/client/FundingReadinessHeader.jsx')

  it('header component exists', () => {
    expect(existsSync(headerPath)).toBe(true)
  })

  it('renders overall score', () => {
    const code = readFileSync(headerPath, 'utf8')
    expect(code).toContain('overallScore')
  })

  it('renders current stage', () => {
    const code = readFileSync(headerPath, 'utf8')
    expect(code).toContain('currentStage')
    expect(code).toContain('displayName')
  })

  it('renders completed/remaining counts', () => {
    const code = readFileSync(headerPath, 'utf8')
    expect(code).toContain('completedCount')
    expect(code).toContain('totalCount')
  })

  it('renders continue button', () => {
    const code = readFileSync(headerPath, 'utf8')
    expect(code).toContain('Continue')
    expect(code).toContain('onNavigate')
  })

  it('renders progress dots', () => {
    const code = readFileSync(headerPath, 'utf8')
    expect(code).toContain('progress')
  })
})

describe('Phase 4 — Inline document upload', () => {
  const uploadPath = resolve(ROOT, 'src/components/client/InlineDocumentUpload.jsx')

  it('upload component exists', () => {
    expect(existsSync(uploadPath)).toBe(true)
  })

  it('uploads to client-documents bucket', () => {
    const code = readFileSync(uploadPath, 'utf8')
    expect(code).toContain('client-documents')
  })

  it('creates client_documents metadata', () => {
    const code = readFileSync(uploadPath, 'utf8')
    expect(code).toContain('client_documents')
  })

  it('queues credit analysis for credit reports', () => {
    const code = readFileSync(uploadPath, 'utf8')
    expect(code).toContain('credit_analysis_jobs')
  })

  it('has category selection', () => {
    const code = readFileSync(uploadPath, 'utf8')
    expect(code).toContain('credit_reports')
    expect(code).toContain('business_formation')
    expect(code).toContain('banking')
  })

  it('does not expose signed URLs permanently', () => {
    const code = readFileSync(uploadPath, 'utf8')
    expect(code).not.toContain('getPublicUrl')
  })
})

describe('Phase 4 — Clyde context engine', () => {
  const clydePath = resolve(ROOT, 'src/lib/clydeContextEngine.ts')

  it('clyde context engine exists', () => {
    expect(existsSync(clydePath)).toBe(true)
  })

  it('exports generateClydeMessages', () => {
    const code = readFileSync(clydePath, 'utf8')
    expect(code).toContain('generateClydeMessages')
  })

  it('has route context for all main pages', () => {
    const code = readFileSync(clydePath, 'utf8')
    expect(code).toContain('/client/dashboard')
    expect(code).toContain('/client/credit-profile')
    expect(code).toContain('/client/business-setup')
    expect(code).toContain('/client/funding-readiness')
    expect(code).toContain('/client/documents')
    expect(code).toContain('/client/request-review')
  })

  it('includes causal disclaimer', () => {
    const code = readFileSync(clydePath, 'utf8')
    expect(code).toContain('not guaranteed')
  })

  it('distinguishes observation sources', () => {
    const code = readFileSync(clydePath, 'utf8')
    expect(code).toContain('nexus_observed')
    expect(code).toContain('client_provided')
    expect(code).toContain('uploaded_evidence')
    expect(code).toContain('uncertainty')
  })
})

describe('Phase 4 — Analytics', () => {
  const analyticsPath = resolve(ROOT, 'src/lib/clientAnalytics.ts')

  it('analytics file exists', () => {
    expect(existsSync(analyticsPath)).toBe(true)
  })

  it('exports trackEvent', () => {
    const code = readFileSync(analyticsPath, 'utf8')
    expect(code).toContain('trackEvent')
  })

  it('defines all event types', () => {
    const code = readFileSync(analyticsPath, 'utf8')
    expect(code).toContain('stage_viewed')
    expect(code).toContain('upload_completed')
    expect(code).toContain('review_requested')
    expect(code).toContain('journey_stage_completed')
  })

  it('uses privacy-safe session ID', () => {
    const code = readFileSync(analyticsPath, 'utf8')
    expect(code).toContain('sessionStorage')
    expect(code).not.toContain('localStorage')
  })

  it('does not capture report contents', () => {
    const code = readFileSync(analyticsPath, 'utf8')
    expect(code).not.toContain('account_number')
    expect(code).not.toContain('password')
    expect(code).not.toContain('credit_report')
  })
})

describe('Phase 4 — WorldClassClientPortal integration', () => {
  const portalPath = resolve(ROOT, 'src/pages/client/WorldClassClientPortal.jsx')

  it('imports journey model', () => {
    const code = readFileSync(portalPath, 'utf8')
    expect(code).toContain('computeJourneyState')
  })

  it('imports FundingReadinessHeader', () => {
    const code = readFileSync(portalPath, 'utf8')
    expect(code).toContain('FundingReadinessHeader')
  })

  it('imports analytics', () => {
    const code = readFileSync(portalPath, 'utf8')
    expect(code).toContain('trackEvent')
  })

  it('computes journey state', () => {
    const code = readFileSync(portalPath, 'utf8')
    expect(code).toContain('journey')
    expect(code).toContain('computeJourneyState')
  })

  it('renders FundingReadinessHeader', () => {
    const code = readFileSync(portalPath, 'utf8')
    expect(code).toContain('<FundingReadinessHeader')
  })

  it('simplified navigation has 7 items', () => {
    const code = readFileSync(portalPath, 'utf8')
    const navMatch = code.match(/const navItems = \[([\s\S]*?)\]\s*\n/)
    expect(navMatch).toBeTruthy()
    const navContent = navMatch?.[1] || ''
    const itemCount = (navContent.match(/\[.*?\/client\//g) || []).length
    expect(itemCount).toBe(7)
  })
})
