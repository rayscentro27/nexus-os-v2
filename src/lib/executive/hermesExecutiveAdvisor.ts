import { getExecutiveCommandCenterSnapshot } from './executiveCommandCenterAdapter';
import { buildCapabilityOSSummary, getCapabilityRegistry } from '../capabilities/capabilityRegistry';
import { getBrainProfile } from '../brains/brainRegistry';
import { assembleBrainContext } from '../intelligence/contextAssembler';
import { buildKnowledgeHealthSummary } from '../intelligence/knowledgeHealth';
import { getIntelligenceRecord } from '../intelligence/intelligenceRegistry';
import { evaluateBrainHandoff } from '../brains/brainHandoffs';

export type ExecutiveIntent =
  | 'executive_daily_brief'
  | 'executive_priorities'
  | 'executive_system_health'
  | 'executive_customer_risk'
  | 'executive_revenue_status'
  | 'executive_approval_status'
  | 'executive_work_status'
  | 'executive_department_status'
  | 'executive_repo_intelligence'
  | 'executive_deployment_status'
  | 'executive_recommendation_followup'
  | 'capability_status'
  | 'capability_owner'
  | 'capability_health'
  | 'capability_dependencies'
  | 'capability_credentials'
  | 'capability_cost'
  | 'capability_activation'
  | 'capability_approval_requirement'
  | 'capability_execution_block'
  | 'capability_proposal_status'
  | 'capability_compare'
  | 'knowledge_status'
  | 'approved_policy'
  | 'evidence_for_claim'
  | 'research_finding_status'
  | 'knowledge_freshness'
  | 'knowledge_conflict'
  | 'memory_source'
  | 'brain_access_explanation'
  | 'brain_handoff_status'
  | 'knowledge_promotion_status'
  | 'client_safe_knowledge_check';

export function classifyExecutiveIntent(message: string): ExecutiveIntent | null {
  const lower = message.toLowerCase();
  if (/\b(persist|persisted|save|saved|source type|supabase)\b/.test(lower) && /\bapproval\b/.test(lower)) return null;
  if (/\b(capabilit(y|ies)|tool policy|activation mode|credential|dependencies|dependency|who owns|approval requirement|can alpha use|access client information|why.*blocked|proposal status|do we already have)\b/.test(lower)) {
    if (/\b(owner|who owns|department)\b/.test(lower)) return 'capability_owner';
    if (/\b(health|healthy|unhealthy)\b/.test(lower)) return 'capability_health';
    if (/\b(dependencies|dependency|depend on)\b/.test(lower)) return 'capability_dependencies';
    if (/\b(credentials?|secrets?|tokens?|keys?)\b/.test(lower)) return 'capability_credentials';
    if (/\b(cost|budget|usage)\b/.test(lower)) return 'capability_cost';
    if (/\b(activate|activation|enabled|active)\b/.test(lower)) return 'capability_activation';
    if (/\b(approval|ray approve|requires approval)\b/.test(lower)) return 'capability_approval_requirement';
    if (/\b(blocked|can't|cannot|deny|denied|prohibited)\b/.test(lower)) return 'capability_execution_block';
    if (/\b(proposal|repo intelligence|candidate)\b/.test(lower)) return 'capability_proposal_status';
    if (/\b(compare|already have|replaces|overlap)\b/.test(lower)) return 'capability_compare';
    return 'capability_status';
  }
  if (/\b(knowledge|evidence|claim|approved policy|research finding|freshness|conflict|memory|brain access|handoff|promotion|client safe|can alpha|client information|client ai)\b/.test(lower)) {
    if (/\b(approved policy|policy)\b/.test(lower)) return 'approved_policy';
    if (/\b(evidence for|where did|source)\b/.test(lower)) return 'evidence_for_claim';
    if (/\b(research finding|alpha finding|alpha research)\b/.test(lower)) return 'research_finding_status';
    if (/\b(fresh|freshness|current|stale)\b/.test(lower)) return 'knowledge_freshness';
    if (/\b(conflict|contradict)\b/.test(lower)) return 'knowledge_conflict';
    if (/\b(memory|remember)\b/.test(lower)) return 'memory_source';
    if (/\b(can alpha|can client ai|brain access|access this)\b/.test(lower)) return 'brain_access_explanation';
    if (/\b(handoff|cross brain|cross-brain)\b/.test(lower)) return 'brain_handoff_status';
    if (/\b(promote|promotion|approve knowledge)\b/.test(lower)) return 'knowledge_promotion_status';
    if (/\b(client safe|client-safe|client ai)\b/.test(lower)) return 'client_safe_knowledge_check';
    return 'knowledge_status';
  }
  if (/\b(daily brief|operating brief|brief me)\b/.test(lower)) return 'executive_daily_brief';
  if (/\b(attention today|what.*first|top priorities|priorit(y|ies)|what should we do first)\b/.test(lower)) return 'executive_priorities';
  if (/\b(system health|healthy|health status|top risks|risk)\b/.test(lower)) return 'executive_system_health';
  if (/\b(customer risk|customers? blocked|client risk|client blocked)\b/.test(lower)) return 'executive_customer_risk';
  if (/\b(revenue status|stripe|money|orders|fulfillment|checkout)\b/.test(lower)) return 'executive_revenue_status';
  if (/\b(approval|ray review|decision queue|waiting.*decision)\b/.test(lower)) return 'executive_approval_status';
  if (/\b(work status|governed work|work orders?|execution queue|jobs running)\b/.test(lower)) return 'executive_work_status';
  if (/\b(department|workforce|agents?)\b/.test(lower)) return 'executive_department_status';
  if (/\b(repo intelligence|github mcp|repository recommendations|external repos?)\b/.test(lower)) return 'executive_repo_intelligence';
  if (/\b(deployment|release|build|production)\b/.test(lower)) return 'executive_deployment_status';
  if (/\b(recommendation followup|turn .* into|send .* ray review|defer that)\b/.test(lower)) return 'executive_recommendation_followup';
  return null;
}

export function answerExecutiveIntent(intent: ExecutiveIntent): string {
  const state = getExecutiveCommandCenterSnapshot();
  const capabilityOS = buildCapabilityOSSummary();
  const capabilities = getCapabilityRegistry();
  const pending = state.approvals.filter((item) => item.state === 'PENDING').length;
  const blockedWork = state.governedWork.filter((item) => item.lifecycle === 'BLOCKED' || item.lifecycle === 'FAILED').length;
  const deferredHealth = state.systemHealth.filter((item) => item.status === 'DEFERRED' || item.status === 'BLOCKED_BY_POLICY' || item.status === 'PROHIBITED');
  const evidence = [
    `${pending} pending approvals visible in the current snapshot`,
    `${blockedWork} blocked or failed governed-work records visible in the current snapshot`,
    `${state.repoIntelligence.length} repo-intelligence candidates`,
    'Stripe remains test mode; live configuration deferred',
  ].join('\n- ');

  if (intent === 'executive_daily_brief') {
    return `Executive daily brief:\n\nFacts:\n- ${evidence}\n\nInterpretation:\n- P0 protections are holding: live Stripe is deferred, live trading is blocked, Alpha Supabase access is prohibited, and repo intelligence is read-only.\n\nRecommendations:\n1. Confirm no external actions are being activated.\n2. Review Ray Review if live approval rows appear after authentication.\n3. Keep repo-intelligence decisions as research dispositions only.\n\nUnknowns:\n- Live Supabase counts require an authenticated admin session in the browser.\n\nBlocked data:\n- Live Stripe credentials and live webhook are intentionally not configured.`;
  }

  if (intent === 'capability_status') {
    return `Capability OS status:\n\nFacts:\n- ${capabilityOS.total} capabilities are registered.\n- ${capabilityOS.byActivationMode.ACTIVE ?? 0} active, ${capabilityOS.byActivationMode.READ_ONLY ?? 0} read-only, ${capabilityOS.byActivationMode.TEST_ONLY ?? 0} test-only, ${capabilityOS.approvalGated} approval-gated.\n- ${capabilityOS.byActivationMode.PROHIBITED ?? 0} prohibited and ${capabilityOS.byActivationMode.BLOCKED_BY_POLICY ?? 0} blocked by policy.\n\nRecommendation:\n- Treat the registry as the deterministic source before running or activating a capability.`;
  }

  if (intent === 'capability_owner') {
    const examples = capabilities.slice(0, 5).map((item) => `${item.name}: ${item.departmentId}`).join('\n- ');
    return `Capability ownership:\n\nFacts:\n- Every registered capability has a primary department and owner type.\n- Examples:\n- ${examples}\n\nRecommendation:\n- Use department ownership for routing, but Ray remains final authority for high-risk activation.`;
  }

  if (intent === 'capability_health') {
    return `Capability health:\n\nFacts:\n- ${capabilityOS.byHealth.HEALTHY ?? 0} healthy.\n- ${capabilityOS.byHealth.NOT_CONFIGURED ?? 0} not configured.\n- ${capabilityOS.byHealth.DEFERRED ?? 0} deferred.\n- ${capabilityOS.byHealth.PROHIBITED ?? 0} prohibited.\n\nInterpretation:\n- Intentional policy blocks are not accidental failures.`;
  }

  if (intent === 'capability_dependencies') {
    const withDeps = capabilities.filter((item) => item.dependencies.length).slice(0, 6).map((item) => `${item.name}: ${item.dependencies.join(', ')}`).join('\n- ');
    return `Capability dependencies:\n\nFacts:\n- Dependency mappings are deterministic and typed.\n- ${withDeps || 'No dependency examples found in the snapshot.'}\n\nRecommendation:\n- Block execution preflight when critical dependencies are unhealthy or unknown.`;
  }

  if (intent === 'capability_credentials') {
    const needsCreds = capabilities.filter((item) => item.credentialRequirements.length).slice(0, 6).map((item) => `${item.name}: ${item.credentialRequirements.join(', ')}`).join('\n- ');
    return `Capability credentials:\n\nFacts:\n- Credential metadata stores identifiers only, never values.\n- ${needsCreds || 'No credential requirements found in the snapshot.'}\n\nRecommendation:\n- Missing credentials should block execution, not trigger credential entry through chat.`;
  }

  if (intent === 'capability_cost') {
    const billable = capabilities.filter((item) => ['USAGE_BASED', 'SUBSCRIPTION', 'SELF_HOSTED', 'UNKNOWN'].includes(item.costModel)).slice(0, 6).map((item) => `${item.name}: ${item.costModel}`).join('\n- ');
    return `Capability cost governance:\n\nFacts:\n- External and billable capabilities are classified by cost model.\n- ${billable || 'No billable capabilities found in the snapshot.'}\n\nRecommendation:\n- Unknown or usage-based cost should require approval before activation.`;
  }

  if (intent === 'capability_activation') {
    return `Capability activation:\n\nFacts:\n- Activation modes include ACTIVE, READ_ONLY, APPROVAL_GATED, TEST_ONLY, NOT_CONFIGURED, DEFERRED, BLOCKED_BY_POLICY, PROHIBITED, and RETIRED.\n- Live Stripe is DEFERRED.\n- Live trading is BLOCKED_BY_POLICY.\n- Alpha Supabase access is PROHIBITED.\n\nRecommendation:\n- Do not treat registered or proposed capabilities as active.`;
  }

  if (intent === 'capability_approval_requirement') {
    return `Capability approval requirements:\n\nFacts:\n- ${capabilityOS.awaitingRayApproval} capabilities are awaiting Ray approval or review state.\n- High-risk activation uses RAY_REVIEW, RAY_EXPLICIT, or LEGAL_AND_RAY.\n- Hermes cannot approve its own proposals.\n\nRecommendation:\n- Use Ray Review for bounded evaluation and Ray explicit approval for live Stripe, writer profiles, or external publishing.`;
  }

  if (intent === 'capability_execution_block') {
    return `Capability execution blocks:\n\nFacts:\n- Preflight blocks prohibited, deferred, not configured, missing-credential, unhealthy-dependency, data-policy, and cost-limit failures.\n- Denials emit sanitized capability preflight events.\n\nRecommendation:\n- Read the denial reason before creating a new task or retrying execution.`;
  }

  if (intent === 'capability_proposal_status') {
    return `Capability proposal status:\n\nFacts:\n- ${capabilityOS.proposals.length} repo-intelligence candidates are mapped into proposals.\n- Proposals do not activate capabilities automatically.\n- Unknown licenses prevent code-reuse approval.\n\nRecommendation:\n- Review proposals through Ray Review before any bounded evaluation.`;
  }

  if (intent === 'capability_compare') {
    return `Capability comparison:\n\nFacts:\n- Repo Intelligence proposals carry existing Nexus overlap before any integration decision.\n- The Capability OS can recommend replacing a candidate with an existing Nexus capability when overlap is stronger.\n\nRecommendation:\n- Prefer studying architecture or using existing Nexus capability before adding a dependency.`;
  }

  if (intent === 'knowledge_status') {
    const health = buildKnowledgeHealthSummary();
    return `Knowledge status:\n\nFacts:\n- ${health.totalRecords} intelligence records are registered.\n- ${health.approvedKnowledge} approved knowledge or policy records.\n- ${health.unverifiedClaims} unverified or under-review claims.\n- ${health.missingProvenance} records missing provenance.\n- Document evidence status: ${health.documentEvidenceStatus}.\n\nInterpretation:\n- Knowledge, evidence, claims, observations, recommendations, memory, context, and model output are separated.\n\nRecommendation:\n- Promote findings through Knowledge Review before treating them as approved knowledge.`;
  }

  if (intent === 'approved_policy') {
    const context = assembleBrainContext({ brainId: 'nexus_hermes', actorRole: 'admin', query: 'approved policy', requestedDomains: ['executive', 'client_safe_guidance'] });
    return `Approved policy:\n\nFacts:\n- ${context.policies.join('\n- ') || 'No approved policy records were retrievable.'}\n\nEvidence state: ${context.evidenceState}.\nUnknowns:\n- ${context.unknowns.join('\n- ') || 'No missing-provenance policy records in this query.'}`;
  }

  if (intent === 'evidence_for_claim') {
    const claim = getIntelligenceRecord('claim_github_mcp_reader_value');
    return `Evidence for claim:\n\nClaim:\n- ${claim?.title || 'Claim unavailable'}\n\nClassification:\n- RESEARCH_CLAIM\n- Approval: ${claim?.approvalState || 'UNKNOWN'}\n- Freshness: ${claim?.freshness || 'UNKNOWN'}\n\nBased on:\n- ${claim?.supportingEvidenceIds.join('\n- ') || 'No supporting evidence IDs recorded.'}\n\nRecommendation:\n- Do not treat this claim as approved implementation authority until Ray Review approves a bounded evaluation.`;
  }

  if (intent === 'research_finding_status') {
    const context = assembleBrainContext({ brainId: 'alpha_research', actorRole: 'alpha', query: 'alpha research', requestedDomains: ['public_research', 'repo_intelligence'] });
    return `Research finding status:\n\nFacts:\n- Alpha can retrieve ${context.evidence.length} evidence/source records and ${context.recommendations.length} recommendations in this scoped query.\n- Alpha findings remain CLAIM or RECOMMENDATION until review.\n\nBlocked from Hermes facts:\n- ${context.excluded.filter((item) => item.reason.includes('POLICY')).length} records were blocked by policy in comparable executive contexts.\n\nRecommendation:\n- Submit source-backed findings to Knowledge Review before Hermes uses them as company knowledge.`;
  }

  if (intent === 'knowledge_freshness') {
    const health = buildKnowledgeHealthSummary();
    return `Knowledge freshness:\n\nFacts:\n- ${health.staleRecords} stale records.\n- ${health.expiredRecords} expired records.\n- ${health.evaluationPassed}/${health.evaluationTotal} retrieval evaluation fixtures passed.\n\nRecommendation:\n- Stale or expired records should be refreshed or superseded before they guide high-risk decisions.`;
  }

  if (intent === 'knowledge_conflict') {
    const context = assembleBrainContext({ brainId: 'nexus_hermes', actorRole: 'admin', query: 'conflicts' });
    return `Knowledge conflicts:\n\nFacts:\n- ${context.conflicts.length} conflicts are visible to Hermes in the current governed context.\n- ${context.conflicts.join('\n- ') || 'No retrievable conflicts in this query.'}\n\nRecommendation:\n- Resolve conflicts through Knowledge Review, not by letting a model choose silently.`;
  }

  if (intent === 'memory_source') {
    const context = assembleBrainContext({ brainId: 'nexus_hermes', actorRole: 'admin', query: 'memory source', requestedDomains: ['executive'] });
    return `Memory source:\n\nFacts:\n- Hermes memory is advisory continuity, not approved knowledge.\n- ${context.memories.map((item) => `${item.memoryType}: ${item.summary}`).join('\n- ') || 'No retrievable Hermes memory records in this query.'}\n\nBoundary:\n- Alpha research memory and Client journey memory are separate. Memory never promotes itself into policy.`;
  }

  if (intent === 'brain_access_explanation') {
    const hermes = getBrainProfile('nexus_hermes');
    const alpha = getBrainProfile('alpha_research');
    const client = getBrainProfile('client_ai');
    return `Brain access:\n\nFacts:\n- Hermes: Supabase ${hermes?.mayUseSupabase ? 'allowed with governed context' : 'blocked'}, client PII ${hermes?.mayAccessClientPii ? 'allowed' : 'blocked'}.\n- Alpha: Supabase ${alpha?.mayUseSupabase ? 'allowed' : 'blocked'}, client PII ${alpha?.mayAccessClientPii ? 'allowed' : 'blocked'}.\n- Client AI: tenant isolation ${client?.tenantIsolationRequired ? 'required' : 'not required'}, Executive data blocked.\n\nRule:\n- The more restrictive Brain Profile and Capability OS policy wins.`;
  }

  if (intent === 'brain_handoff_status') {
    const denied = evaluateBrainHandoff('alpha_research', 'nexus_hermes', ['claim_alpha_raw_market_pattern']);
    return `Cross-brain handoff status:\n\nFacts:\n- Alpha to Hermes unapproved claim handoff: ${denied.allowed ? 'allowed' : 'denied'}.\n- Event: ${denied.event.action}.\n- Reason: ${denied.reasons.join(' ') || 'No block recorded.'}\n\nRecommendation:\n- Use Knowledge Review before promoting Alpha findings into Hermes context.`;
  }

  if (intent === 'knowledge_promotion_status') {
    return `Knowledge promotion status:\n\nFacts:\n- Source -> Evidence -> Claim or Observation -> Review -> Approved Knowledge is the Wave 3 chain.\n- High-risk policy, security, cross-brain permissions, live payments, and live trading decisions require Ray Review or explicit Ray approval.\n\nRecommendation:\n- Create a Knowledge Review item when a finding should become policy or reusable company knowledge.`;
  }

  if (intent === 'client_safe_knowledge_check') {
    const context = assembleBrainContext({ brainId: 'client_ai', actorRole: 'client', tenantId: 'synthetic', clientId: 'persona_a', query: 'client safe', requestedDomains: ['client_safe_guidance', 'documents'] });
    return `Client-safe knowledge check:\n\nFacts:\n- ${context.approvedKnowledge.length} approved policy/knowledge records are available to Client AI in this scoped query.\n- ${context.excluded.length} records are excluded by tenant, data-class, domain, approval, or policy rules.\n\nBoundary:\n- Client AI cannot retrieve Executive records, raw Alpha research, private source code, credentials, or another tenant's data.`;
  }

  if (intent === 'executive_priorities') {
    return `What needs attention first:\n\n1. ${state.topActions[0]?.title || 'Protect external action gates'}\n2. ${state.topActions[1]?.title || 'Review approvals'}\n3. ${state.topActions[2]?.title || 'Monitor customer workflow evidence'}\n\nBased on:\n- ${evidence}\n\nThese are recommendations, not approvals. Ray remains the final authority.`;
  }

  if (intent === 'executive_system_health') {
    return `System health summary:\n\nFacts:\n- ${state.systemHealth.length} normalized health items are available.\n- ${deferredHealth.map((item) => `${item.component}: ${item.status}`).join('\n- ')}\n\nInterpretation:\n- Intentionally deferred systems are not failures.\n\nRecommendation:\n- Keep the Executive System Health adapter as the read authority and retire duplicate health summaries later.`;
  }

  if (intent === 'executive_customer_risk') {
    return `Customer risk summary:\n\nFacts:\n- Founder Mode uses aggregate customer signals only.\n- Client PII is not sent to Alpha or repo intelligence.\n- Document-processing depth remains certified but needs recheck.\n\nRecommendation:\n- Watch customer workflow blockers from the Customers and Readiness admin views before expanding controlled testing.`;
  }

  if (intent === 'executive_revenue_status') {
    return `Revenue status:\n\nFacts:\n- Stripe mode: TEST.\n- The $97 Credit & Funding Readiness Review remains the approval-gated test-mode revenue proof.\n- LIVE STRIPE CONFIGURATION DEFERRED UNTIL NEXUS 3.0 COMPLETION.\n- Test checkout, webhook, order, and fulfillment foundations remain protected.\n\nRecommendation:\n- Do not configure live Stripe or accept a live card until Ray separately approves live payment activation.`;
  }

  if (intent === 'executive_approval_status') {
    return `Approval status:\n\nFacts:\n- ${pending} pending approvals are visible in the current snapshot.\n- Approval states normalize to PENDING, APPROVED, REJECTED, REVISION_REQUESTED, DEFERRED, EXPIRED, and BLOCKED.\n\nRecommendation:\n- Use Ray Review as the decision authority. Hermes can prepare or explain, but cannot approve.`;
  }

  if (intent === 'executive_work_status') {
    return `Governed work status:\n\nFacts:\n- Canonical execution chain is task_requests -> approvals -> agent_jobs -> nexus_events.\n- Report-only work-order artifacts are not execution sources.\n\nRecommendation:\n- Keep work creation explicit and approval-gated for anything risky.`;
  }

  if (intent === 'executive_department_status') {
    return `Department status:\n\nFacts:\n- ${state.departments.length} departments are classified.\n- Trading is blocked by policy; Venture Studio and Sales remain planned rather than autonomous.\n\nRecommendation:\n- Wave 2 should formalize a capability registry before autonomous department expansion.`;
  }

  if (intent === 'executive_repo_intelligence') {
    const githubMcp = state.repoIntelligence.find((item) => item.candidateId === 'github_mcp_server');
    return `Repo Intelligence status:\n\nFacts:\n- ${state.repoIntelligence.length} candidates are listed.\n- No external repository is installed, cloned, vendored, or approved for code reuse.\n- GitHub MCP Server: ${githubMcp ? `${githubMcp.proposedDisposition}, ${githubMcp.accessProfile || 'READ_ONLY planned'}` : 'not found in snapshot'}.\n\nRecommendation:\n- Keep Repo Intelligence in a read-only lane with Ray Review hooks only. Writer access remains disabled until a later explicit approval.`;
  }

  if (intent === 'executive_deployment_status') {
    return `Deployment status:\n\nFacts:\n- Branch and commit are surfaced by the release process and final report, not guessed by Hermes.\n- Build, RLS, route, and deployment evidence must be checked before release claims.\n\nRecommendation:\n- Use the deployment panel as read-only evidence and keep production writes approval-gated.`;
  }

  return `Recommendation follow-up:\n\nI can explain or turn a specific recommended item into a governed work request only when Ray clearly asks for execution or delegation. I will not create work just because Ray asks a question.`;
}
