import { describe, expect, it } from 'vitest'
import { AUTHORITY_TEST_ACTIONS, authorityFor, compileIntent, dependencyCheck, normalizeIntent } from '../src/lib/intentProgramCompiler'

const goals = [
  { goalId: 'portal.client_beta', title: 'Client Portal', status: 'COMPLETE', keywords: ['portal', 'client'] },
  { goalId: 'grants.intelligence', title: 'Grant intelligence', status: 'COMPLETE', keywords: ['grant', 'opportunities'] },
  { goalId: 'commerce.billing_accounting', title: 'Billing accounting', status: 'COMPLETE', keywords: ['invoice', 'billing'], dependencies: ['research.notebook'] },
]

describe('governed intent program compiler', () => {
  it('normalizes bounded, ambiguous, broad, and unsafe requests', () => {
    expect(normalizeIntent('Improve client portal conversion').scope).toBe('BOUNDED')
    expect(normalizeIntent('help').scope).toBe('AMBIGUOUS')
    expect(normalizeIntent('do anything').scope).toBe('OVERBROAD')
    expect(normalizeIntent('invest excess cash automatically').scope).toBe('UNSAFE')
  })

  it('reuses matching canonical goals and never makes a proposal executable', () => {
    const result = compileIntent('Find more grant opportunities', goals)
    expect(result.matchedGoal?.goalId).toBe('grants.intelligence')
    expect(result.decision).toBe('REUSE_EXISTING_GOAL')
    expect(result.proposal.status).toBe('PROPOSED')
    expect(result.executableNow).toBe(false)
  })

  it('blocks unsafe intent and preserves dependency failures', () => {
    expect(compileIntent('Send invoices to every customer', goals).decision).toBe('REJECT_PROHIBITED_ACTION')
    expect(dependencyCheck('new', ['research.notebook'], { 'research.notebook': 'ACTIVE' }).satisfied).toBe(false)
    expect(dependencyCheck('x', ['x'], {}).circular).toBe(true)
  })

  it('encodes external authority boundaries', () => {
    for (const action of AUTHORITY_TEST_ACTIONS) {
      const policy = authorityFor(action)
      if (action === 'CLIENT_DATA_MUTATION') expect(policy.allowedAutonomously).toBe(true)
      else expect(policy.allowedAutonomously).toBe(false)
    }
    expect(authorityFor('bank transfer').authorityClass).toBe('PROHIBITED')
    expect(authorityFor('invoice send').authorityClass).toBe('APPROVAL_GATED_EXTERNAL_ACTION')
  })
})
