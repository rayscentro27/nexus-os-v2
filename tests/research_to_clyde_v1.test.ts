import {describe,expect,it} from 'vitest'
import fixture from './fixtures/credit/research_to_clyde_three_bureau.json'
import {compareCreditReportAcrossBureaus} from '../src/lib/crossBureauCreditComparison'
import {CREDIT_STRATEGY_CATALOG} from '../src/lib/creditStrategyCatalog'
import {matchCreditStrategies} from '../src/lib/creditStrategyMatcher'
import {buildStructuredClydeGuidance,classifyResearchClaim,evaluateResearchToClydeException,generateSafeStrategyDraft,rankApprovedStrategies,validateStrategyDraft} from '../src/lib/researchToClydeEngine'
import {generateClydeStructuredStrategyAnswer} from '../src/lib/clydeActionEngine'

describe('research-to-Clyde v1 synthetic flow',()=>{
 const compared=compareCreditReportAcrossBureaus({accounts:fixture.accounts as any})
 it('produces the expected synthetic pipeline totals',()=>{
  expect(compared.canonicalAccounts).toHaveLength(3);expect(compared.discrepancies).toHaveLength(6)
  expect(matchCreditStrategies({canonicalAccounts:compared.canonicalAccounts,discrepancies:compared.discrepancies})).toHaveLength(5)
 })
 it('groups three bureau rows while retaining the same-creditor second account',()=>{
  const grouped=compared.canonicalAccounts.find(a=>a.maskedAccountReference.endsWith('4412'))!
  expect(grouped.bureauRecords).toHaveLength(3)
  expect(compared.canonicalAccounts.some(a=>a.maskedAccountReference.endsWith('8821'))).toBe(true)
  expect(grouped.bureauRecords.map(r=>r.balance)).toEqual([2450,3190,2450])
 })
 it('detects objective balance, status, and ownership differences',()=>{
  expect(compared.discrepancies.map(d=>d.discrepancyType)).toEqual(expect.arrayContaining(['balance_mismatch','account_status_mismatch','ownership_mismatch']))
 })
 it('matches approved strategies and excludes retired or low-confidence inputs',()=>{
  const matches=matchCreditStrategies({canonicalAccounts:compared.canonicalAccounts,discrepancies:compared.discrepancies})
  expect(matches.some(m=>m.primaryStrategy.strategyId==='cross_bureau_balance_review')).toBe(true)
  const balance=compared.discrepancies.find(d=>d.discrepancyType==='balance_mismatch')!
  const retired={...CREDIT_STRATEGY_CATALOG[0],strategyId:'retired_test',approvalStatus:'retired' as const}
  const ranked=rankApprovedStrategies(balance,[retired])
  expect(ranked.matches).toHaveLength(0);expect(ranked.excluded[0].reasons).toContain('strategy_not_approved')
 })
 it('gives Clyde detected facts, approved strategy provenance, uncertainty, and client-only questions',()=>{
  const balance=compared.discrepancies.find(d=>d.discrepancyType==='balance_mismatch')!;const account=compared.canonicalAccounts.find(a=>a.canonicalAccountId===balance.canonicalAccountId)!
  const match=rankApprovedStrategies(balance,CREDIT_STRATEGY_CATALOG,account).matches[0]
  const guidance=buildStructuredClydeGuidance({account,discrepancy:balance,match})
  expect(guidance.detectedFact).toMatch(/differs by/);expect(guidance.approvedEducationalStrategy.version).toBe(1);expect(guidance.limitations).toMatch(/does not determine accuracy/i);expect(guidance.clientQuestions).not.toContain('Does this balance appear correct?')
  const answer=generateClydeStructuredStrategyAnswer({question:'What did Nexus find?',detectedFact:guidance.detectedFact,bureauValues:guidance.bureauValues,strategyTitle:guidance.approvedEducationalStrategy.title,strategyVersion:1,clientQuestions:guidance.clientQuestions,evidenceNeeded:['statement'],limitations:guidance.limitations,readinessImpact:guidance.readiness.creditProfileImpact})
  expect(answer).toMatch(/Nexus detected fact:/);expect(answer).toMatch(/Approved educational strategy:/);expect(answer).not.toMatch(/guaranteed|must delete/i)
 })
 it('preserves rejected practitioner claims but blocks them from client use',()=>{
  expect(classifyResearchClaim('Remove everything in four days with guaranteed deletion')).toMatchObject({approvalState:'rejected',clientSafe:false,promotional:true,guarantee:true})
  expect(classifyResearchClaim('Compare three bureau balance fields as a discovery lead')).toMatchObject({approvalState:'needs_review',clientSafe:false})
 })
 it('blocks unsafe drafts and never permits mail',()=>{
  expect(validateStrategyDraft('Please review the documented balance difference.')).toMatchObject({safe:true,clientReviewRequired:true,mailAllowed:false})
  expect(validateStrategyDraft('This guarantees deletion and automatic damages.')).toMatchObject({safe:false,mailAllowed:false})
  const draft=generateSafeStrategyDraft({strategyId:'cross_bureau_balance_review',strategyVersion:1,templateVersion:'balance-v1',outputType:'bureau_comparison_summary',accountReference:'account-reference-4412',detectedFacts:['Equifax reports a different balance.']})
  expect(draft).toMatchObject({status:'draft_ready',accountReference:'****4412',clientReviewRequired:true,clientAuthorized:false,mailCreated:false});expect(draft.text).not.toContain('account-reference-4412')
 })
 it('routes only genuine exceptions',()=>{
  expect(evaluateResearchToClydeException({approvedMatches:1})).toMatchObject({exceptionRequired:false})
  expect(evaluateResearchToClydeException({approvedMatches:0,highImpact:true})).toMatchObject({exceptionRequired:true,code:'no_approved_strategy'})
 })
})
