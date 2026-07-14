import { describe, expect, it } from 'vitest'
import { compareCanonicalReportAccounts, validateOutcomeLanguage } from '../src/lib/outcomeAnalytics'

describe('non-causal strategy outcome analytics', () => {
  it('records later observations without causal claims', () => {
    const observations = compareCanonicalReportAccounts(
      [{canonicalAccountId:'a',matchConfidence:'high',balance:2450,accountStatus:'open',bureaus:['experian','equifax']},{canonicalAccountId:'b',matchConfidence:'high',balance:20}],
      [{canonicalAccountId:'a',matchConfidence:'high',balance:2100,accountStatus:'closed',bureaus:['experian'] }],
    )
    expect(observations.map(item=>item.type)).toEqual(expect.arrayContaining(['balance_changed','status_changed','bureau_coverage_changed','account_not_found_on_later_report']))
    expect(observations.every(item=>item.causal === false)).toBe(true)
  })
  it('does not call an uncertain match a deletion', () => {
    expect(compareCanonicalReportAccounts([{canonicalAccountId:'x',matchConfidence:'low'}],[])[0]).toMatchObject({type:'uncertain_comparison',summary:expect.stringMatching(/could not confidently match/i)})
  })
  it('blocks causal and guarantee language', () => {
    expect(validateOutcomeLanguage('A later report showed a different balance.')).toMatchObject({safe:true})
    expect(validateOutcomeLanguage('This strategy caused deletion and guaranteed funding.')).toMatchObject({safe:false})
  })
})
