export type AuthorityClass = 'READ_ONLY' | 'INTERNAL_WRITE' | 'SYNTHETIC_TEST' | 'EXTERNAL_PREPARATION' | 'APPROVAL_GATED_EXTERNAL_ACTION' | 'HUMAN_ONLY' | 'PROHIBITED'
export type IntentDecision = 'REUSE_EXISTING_GOAL' | 'PROPOSE_NEW_GOAL' | 'REQUEST_CLARIFICATION' | 'REQUEST_APPROVAL' | 'REJECT_PROHIBITED_ACTION' | 'HOLD'

export type CanonicalGoal = { goalId: string; title: string; department?: string; status: string; keywords?: string[]; dependencies?: string[] }
export type NormalizedIntent = {
  intentId: string; rawIntent: string; normalizedObjective: string; desiredOutcome: string
  scope: 'BOUNDED' | 'AMBIGUOUS' | 'OVERBROAD' | 'UNSAFE'; constraints: string[]
  deadline: string | null; priorityHint: string | null; targetDepartment: string | null
  knownDependencies: string[]; knownRisks: string[]; externalSideEffects: string[]
  approvalRequirements: string[]; confidence: 'HIGH' | 'MEDIUM' | 'LOW'; createdAt: string
}
export type ProgramProposal = {
  programProposalId: string; sourceIntentId: string; title: string; objective: string
  definitionOfDone: string[]; departments: string[]; dependencies: string[]
  dependentGoals: string[]; workstreams: string[]; milestones: string[]
  successCriteria: string[]; failureCriteria: string[]; riskFlags: string[]
  approvalBoundaries: string[]; externalActions: string[]; resourceRequirements: string[]
  priorityProposal: string; estimatedEffort: string; status: 'PROPOSED'; provenance: string
  executableNow: false
}

const stamp = () => new Date().toISOString()
const id = (prefix: string) => `${prefix}-${Date.now().toString(36)}`
const unsafe = /(invest|transfer|wire|pay .*vendor|submit .*application|publish .*production|send .*every customer|sign .*contract)/i
const broad = /(anything|everything|all .*customers|immediately|make .*successful|do whatever)/i
const ambiguous = /^(help|improve|handle|fix|work on)\s*$/i

export function normalizeIntent(rawIntent: string): NormalizedIntent {
  const raw = rawIntent.trim()
  const unsafeRequest = unsafe.test(raw)
  const scope = unsafeRequest ? 'UNSAFE' : broad.test(raw) ? 'OVERBROAD' : (!raw || ambiguous.test(raw)) ? 'AMBIGUOUS' : 'BOUNDED'
  const department = /grant/i.test(raw) ? 'Grants' : /invoice|billing|revenue/i.test(raw) ? 'Commerce' : /portal|client/i.test(raw) ? 'Nexus/Product' : /research|opportun/i.test(raw) ? 'Research' : null
  return {
    intentId: id('intent'), rawIntent: rawIntent, normalizedObjective: raw || 'Clarification required',
    desiredOutcome: scope === 'BOUNDED' ? `Governed progress on: ${raw}` : 'Clarify and govern the requested outcome', scope,
    constraints: ['Use canonical goals and existing department ownership', 'No autonomous external side effects'],
    deadline: null, priorityHint: null, targetDepartment: department, knownDependencies: [],
    knownRisks: unsafeRequest ? ['Requested action may create an external side effect'] : [],
    externalSideEffects: unsafeRequest ? [raw] : [],
    approvalRequirements: unsafeRequest ? ['Fresh explicit approval or human action'] : [],
    confidence: scope === 'BOUNDED' ? 'HIGH' : 'LOW', createdAt: stamp(),
  }
}

export function matchCanonicalGoal(intent: NormalizedIntent, goals: CanonicalGoal[]) {
  const words = intent.rawIntent.toLowerCase().split(/\W+/).filter(w => w.length > 3)
  return goals.find(goal => [goal.goalId, goal.title, ...(goal.keywords || [])].join(' ').toLowerCase().split(/\W+/).some(w => words.includes(w))) || null
}

export function authorityFor(action: string): { authorityClass: AuthorityClass; requiresApproval: boolean; requiresHumanAction: boolean; externalSideEffect: boolean; allowedAutonomously: boolean } {
  const key = action.toLowerCase()
  if (/live trade|bank transfer|payment|invest|production cutover/.test(key)) return { authorityClass: 'PROHIBITED', requiresApproval: true, requiresHumanAction: true, externalSideEffect: true, allowedAutonomously: false }
  if (/email send|funding application|grant application|signature request|invoice send|publish/.test(key)) return { authorityClass: 'APPROVAL_GATED_EXTERNAL_ACTION', requiresApproval: true, requiresHumanAction: false, externalSideEffect: true, allowedAutonomously: false }
  if (/client[ _]data[ _]mutation/.test(key)) return { authorityClass: 'INTERNAL_WRITE', requiresApproval: false, requiresHumanAction: false, externalSideEffect: false, allowedAutonomously: true }
  if (/prepare|read|inspect|research/.test(key)) return { authorityClass: /prepare/.test(key) ? 'EXTERNAL_PREPARATION' : 'READ_ONLY', requiresApproval: false, requiresHumanAction: false, externalSideEffect: false, allowedAutonomously: true }
  return { authorityClass: 'HUMAN_ONLY', requiresApproval: true, requiresHumanAction: true, externalSideEffect: false, allowedAutonomously: false }
}

export function dependencyCheck(goalId: string, dependencies: string[], statuses: Record<string, string>) {
  const unresolved = dependencies.filter(d => statuses[d] !== 'COMPLETE' && statuses[d] !== 'COMPLETE_REAL')
  const cycle = dependencies.includes(goalId)
  return { satisfied: unresolved.length === 0 && !cycle, unresolved, circular: cycle }
}

export function compileIntent(rawIntent: string, goals: CanonicalGoal[], statuses: Record<string, string> = {}) {
  const normalized = normalizeIntent(rawIntent)
  const matchedGoal = matchCanonicalGoal(normalized, goals)
  const decision: IntentDecision = normalized.scope === 'UNSAFE' ? 'REJECT_PROHIBITED_ACTION' : normalized.scope !== 'BOUNDED' ? 'REQUEST_CLARIFICATION' : matchedGoal ? 'REUSE_EXISTING_GOAL' : 'PROPOSE_NEW_GOAL'
  const deps = matchedGoal?.dependencies || []
  const dependency = dependencyCheck(matchedGoal?.goalId || 'new-proposal', deps, statuses)
  const proposal: ProgramProposal = {
    programProposalId: id('proposal'), sourceIntentId: normalized.intentId, title: normalized.normalizedObjective,
    objective: normalized.desiredOutcome, definitionOfDone: ['Validated by the canonical goal system'], departments: normalized.targetDepartment ? [normalized.targetDepartment] : [],
    dependencies: deps, dependentGoals: matchedGoal ? [matchedGoal.goalId] : [], workstreams: ['bounded analysis'], milestones: ['proposal review'],
    successCriteria: ['Evidence and authority envelope are present'], failureCriteria: ['Unsafe or unvalidated execution requested'], riskFlags: normalized.knownRisks,
    approvalBoundaries: normalized.approvalRequirements, externalActions: normalized.externalSideEffects, resourceRequirements: [], priorityProposal: 'DEFER_TO_PORTFOLIO_GOVERNOR', estimatedEffort: 'UNKNOWN', status: 'PROPOSED', provenance: 'intent-program-compiler', executableNow: false,
  }
  return { normalized, matchedGoal, decision, dependency, proposal, executableNow: false as const }
}

export const AUTHORITY_TEST_ACTIONS = ['EMAIL_SEND', 'FUNDING_APPLICATION', 'GRANT_APPLICATION', 'SIGNATURE_REQUEST', 'INVOICE_SEND', 'PAYMENT', 'BANK_TRANSFER', 'LIVE_TRADE', 'PRODUCTION_CUTOVER', 'CLIENT_DATA_MUTATION']
