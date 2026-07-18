import { getExecutiveCommandCenterSnapshot } from './executiveCommandCenterAdapter';

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
  | 'executive_recommendation_followup';

export function classifyExecutiveIntent(message: string): ExecutiveIntent | null {
  const lower = message.toLowerCase();
  if (/\b(persist|persisted|save|saved|source type|supabase)\b/.test(lower) && /\bapproval\b/.test(lower)) return null;
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
