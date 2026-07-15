import { describe, expect, it } from 'vitest'
import { routeFeedbackToRayReview, type FeedbackRow } from '../src/lib/testerFeedbackRouting'

function feedback(overrides: Partial<FeedbackRow> = {}): FeedbackRow {
  return {
    id: 'feedback-001', persona: 'a', page_route: '/client/dashboard', workflow_step: 'dashboard',
    issue_title: '<unsafe>Blocker title</unsafe>', issue_description: '<script>remove</script>Needs review',
    expected_behavior: 'One Ray Review draft', actual_behavior: 'No draft', severity: 'blocker',
    reproducibility: 'always', evidence_reference: 'synthetic-evidence', browser_device: 'Playwright',
    fixture_version: 'v1', build_commit: 'test-build', status: 'open', ray_review_item_id: null, ...overrides,
  }
}

function fakeClient({ existing = [], insertError = null as any } = {}) {
  const calls: any[] = []
  const builder = (result: any = { data: [], error: null }) => {
    const q: any = {
      select: (...args: any[]) => { calls.push(['select', ...args]); return q },
      eq: (...args: any[]) => { calls.push(['eq', ...args]); return q },
      limit: (...args: any[]) => { calls.push(['limit', ...args]); return q },
      update: (value: any) => { calls.push(['update', value]); return q },
      insert: (value: any) => { calls.push(['insert', value]); return q },
      single: () => Promise.resolve(result),
      then: (resolve: any, reject: any) => Promise.resolve(result).then(resolve, reject),
    }
    return q
  }
  const client: any = {
    calls,
    from(table: string) {
      if (table === 'task_requests') {
        const q = builder({ data: existing, error: null })
        const originalInsert = q.insert
        q.insert = (value: any) => {
          calls.push(['insert', value])
          return builder(insertError ? { data: null, error: insertError } : { data: { id: 'ray-001' }, error: null })
        }
        return q
      }
      return builder({ data: null, error: null })
    },
  }
  return client
}

describe('tester feedback → persisted Ray Review routing', () => {
  it('creates one sanitized, approval-gated draft and links the feedback row', async () => {
    const client = fakeClient()
    const result = await routeFeedbackToRayReview(feedback(), client)
    const insert = client.calls.find((call: any[]) => call[0] === 'insert')?.[1]
    expect(result).toEqual({ ok: true, rayReviewId: 'ray-001' })
    expect(client.calls.filter((call: any[]) => call[0] === 'insert')).toHaveLength(1)
    expect(insert.task_type).toBe('ray_review_item')
    expect(insert.status).toBe('requested')
    expect(insert.payload.requires_ray_review).toBe(true)
    expect(insert.payload.auto_approve).toBe(false)
    expect(insert.payload.auto_execute).toBe(false)
    expect(insert.payload.issue_title).not.toContain('<')
    expect(insert.payload.issue_description).not.toContain('<script>')
    expect(client.calls.some((call: any[]) => call[0] === 'update' && call[1].ray_review_item_id === 'ray-001')).toBe(true)
  })

  it('reuses an existing draft and keeps medium feedback in the backlog', async () => {
    const duplicateClient = fakeClient({ existing: [{ id: 'ray-existing', payload: { feedback_record_id: 'feedback-001' } }] })
    const duplicate = await routeFeedbackToRayReview(feedback(), duplicateClient)
    expect(duplicate).toEqual({ ok: true, rayReviewId: 'ray-existing' })
    expect(duplicateClient.calls.filter((call: any[]) => call[0] === 'insert')).toHaveLength(0)

    const backlog = await routeFeedbackToRayReview(feedback({ id: 'feedback-002', severity: 'medium' }), fakeClient())
    expect(backlog.ok).toBe(false)
    expect(backlog.error).toMatch(/Only blocker\/high/)
  })
})
