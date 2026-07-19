import { answerExecutiveIntent, classifyExecutiveIntent } from '../executive/hermesExecutiveAdvisor';
import type { EvidenceState } from '../executive/executiveTypes';
import { answerTodayOperatingFocus, type HermesOperatingContext } from './hermesOperatingContext';
import type {
  HermesAdvisoryContext,
  HermesAdvisoryRecommendation,
  HermesConversationAction,
  HermesConversationInput,
  HermesConversationMode,
  HermesResponseStrategy,
} from './hermesConversationTypes';
import type { HermesReferenceResolution } from './hermesReferenceResolver';

const nowIso = () => new Date().toISOString();

export function chooseHermesResponseStrategy(mode: HermesConversationMode): HermesResponseStrategy {
  if (['SOCIAL_GREETING', 'CASUAL_CONVERSATION', 'SYSTEM_STATUS', 'COMMAND', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(mode)) return 'DETERMINISTIC';
  if (['EXECUTIVE_ADVICE', 'FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE', 'DECISION_SUPPORT'].includes(mode)) return 'HYBRID';
  if (['IDEA_REVIEW', 'EXPLANATION'].includes(mode)) return 'MODEL_ASSISTED';
  return 'SAFE_FALLBACK';
}

export function buildDefaultExecutiveAdvisory(): HermesAdvisoryContext {
  const recommendations: HermesAdvisoryRecommendation[] = [
    {
      id: 'hermes_conversation_certification',
      label: 'Finish Hermes conversation certification',
      rationale: 'It protects the Executive operating layer before broader department automation depends on it.',
      score: 96,
      risks: ['conversation regressions', 'memory confusion', 'accidental action creation'],
      dependencies: ['Knowledge Layer', 'Capability OS', 'Hermes routing audit'],
    },
    {
      id: 'department_operations_queue',
      label: 'Prepare Department Operations and governed automation next',
      rationale: 'It is the natural expansion after Hermes can advise and remember reliably.',
      score: 88,
      risks: ['automating around untested conversation behavior', 'unclear department ownership'],
      dependencies: ['Hermes certification score', 'Capability OS preflight'],
    },
    {
      id: 'keep_external_risk_blocked',
      label: 'Keep live Stripe, live trading, and external writers blocked',
      rationale: 'P0 protection remains more important than speed while the operating system expands.',
      score: 100,
      risks: ['premature activation', 'credential exposure', 'unapproved external action'],
      dependencies: ['Ray Review', 'Capability OS policy'],
    },
  ];
  return {
    advisoryId: `advisory-${Date.now()}`,
    topic: 'executive_operations',
    summary: 'Prioritize Hermes reliability before expanding governed department automation.',
    recommendations,
    preferredRecommendationId: 'hermes_conversation_certification',
    evidenceIds: ['capability_os_registry', 'knowledge_layer', 'wave_4a_architecture'],
    createdAt: nowIso(),
    expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 6).toISOString(),
  };
}

function greetingResponse(message: string): string {
  const lower = message.toLowerCase().replace(/\bgo;od\b/g, 'good');
  if (/\b(good night|^night)\b/.test(lower)) return 'Good night, Ray. We made solid progress today.';
  if (/\b(good morning|^morning|\bgm\b)/.test(lower)) return 'Good morning, Ray. What are we focusing on first today?';
  if (/\b(good afternoon|^afternoon)\b/.test(lower)) return 'Good afternoon, Ray. What needs your attention first?';
  if (/\b(good evening|^evening)\b/.test(lower)) return 'Good evening, Ray. I’m ready when you are.';
  return 'Hey Ray. What are we working on?';
}

function casualResponse(message: string): string {
  const lower = message.toLowerCase();
  if (/\bhow did you sleep|did you sleep|do you sleep\b/.test(lower)) return 'I don’t sleep, but I’m ready. What are we working on?';
  if (/\bhow are you|how's it going|how are things|what's up|whats up\b/.test(lower)) return 'I’m ready and tracking the work. What do you want to focus on?';
  if (/\bthank/.test(lower)) return 'You’re welcome.';
  if (/\bthat makes sense|i agree|makes sense|got it|okay|ok\b/.test(lower)) return 'Good. I’ll keep that as the current direction for this thread.';
  return 'I’m here, Ray. What do you want to work through?';
}

function systemStatusResponse(message: string): { response: string; evidenceState: HermesConversationResponseEvidence } {
  const lower = message.toLowerCase();
  if (/\bstripe|live payment|live checkout\b/.test(lower)) {
    return { response: 'Stripe is working in test mode. Live activation is still deferred until Nexus 3.0 is complete and Ray explicitly approves production payment activation.', evidenceState: 'TEST_ONLY' };
  }
  if (/\btrading|live trade|paper trading\b/.test(lower)) {
    return { response: 'Live trading is blocked by policy. Nexus may keep paper or research visibility, but funded execution remains prohibited until a separate architecture and approval decision.', evidenceState: 'BLOCKED_BY_POLICY' };
  }
  if (/\balpha\b.*\bsupabase|supabase\b.*\balpha|client data\b/.test(lower)) {
    return { response: 'No. Alpha is not allowed unrestricted Supabase access or client PII. Alpha stays in the public and approved-research lane unless Ray approves a separate bounded path.', evidenceState: 'PROHIBITED' };
  }
  if (/\bgithub mcp|mcp\b/.test(lower)) {
    return { response: 'GitHub MCP Reader is registered as a controlled research capability, but it is not configured here. Writer access is disabled and requires explicit Ray approval before any future evaluation.', evidenceState: 'NOT_CONFIGURED' };
  }
  if (/\bweb search|internet\b/.test(lower)) {
    return { response: 'Hermes does not have unrestricted live web search from this chat. Repo Intelligence and Alpha research remain governed, read-only, and approval-gated where external tools are involved.', evidenceState: 'NOT_CONFIGURED' };
  }
  const executiveIntent = classifyExecutiveIntent(message);
  if (executiveIntent) return { response: answerExecutiveIntent(executiveIntent), evidenceState: 'REPORT_BACKED' };
  return { response: 'The system is report-backed from the current Nexus read models unless an authenticated browser route provides live evidence. Live Stripe is deferred, live trading is blocked, and Alpha Supabase access is prohibited.', evidenceState: 'REPORT_BACKED' };
}

type HermesConversationResponseEvidence = EvidenceState | 'TEST_ONLY' | 'NOT_CONFIGURED' | 'BLOCKED_BY_POLICY' | 'PROHIBITED';

export interface HermesGeneratedResponse {
  response: string;
  evidenceState: HermesConversationResponseEvidence;
  advisoryContext?: HermesAdvisoryContext;
  action: HermesConversationAction | null;
  contextUsed: string[];
  warnings: string[];
}

function getOperatingContext(input: HermesConversationInput): HermesOperatingContext | null {
  const candidate = input.pageContext && typeof input.pageContext === 'object'
    ? (input.pageContext as { operatingContext?: HermesOperatingContext }).operatingContext
    : undefined;
  if (candidate && Array.isArray(candidate.priorities) && Array.isArray(candidate.blockers)) return candidate;
  return null;
}

export function generateHermesResponse(args: {
  input: HermesConversationInput;
  mode: HermesConversationMode;
  intent: string;
  advisoryContext?: HermesAdvisoryContext;
  reference?: HermesReferenceResolution;
}): HermesGeneratedResponse {
  const { input, mode, advisoryContext, reference } = args;
  const message = input.message;
  const contextUsed: string[] = [];
  const warnings: string[] = [];

  if (mode === 'SOCIAL_GREETING') {
    return { response: greetingResponse(message), evidenceState: 'LIVE', action: null, contextUsed, warnings };
  }

  if (mode === 'CASUAL_CONVERSATION') {
    return { response: casualResponse(message), evidenceState: 'LIVE', action: null, contextUsed, warnings };
  }

  if (mode === 'SYSTEM_STATUS') {
    const status = systemStatusResponse(message);
    contextUsed.push('executive_status_policy');
    return { response: status.response, evidenceState: status.evidenceState, action: null, contextUsed, warnings };
  }

  if (mode === 'COMMAND') {
    const action: HermesConversationAction = {
      type: 'BLOCKED_COMMAND',
      requiresApproval: true,
      payload: { requestedText: message, status: 'blocked', source: 'capability_policy' },
    };
    return {
      response: "I can't execute that directly. The request is blocked by Nexus policy or requires explicit Ray approval through a safe server-side workflow. Trading workflow and live-payment actions remain governed and blocked until approved.",
      evidenceState: 'BLOCKED',
      action,
      contextUsed: ['capability_policy'],
      warnings: ['high_risk_command_blocked'],
    };
  }

  if (mode === 'TASK_REQUEST' || mode === 'APPROVAL_REQUEST') {
    const target = reference?.item?.label || advisoryContext?.recommendations.find((item) => item.id === advisoryContext.preferredRecommendationId)?.label || 'the referenced item';
    const action: HermesConversationAction = {
      type: mode === 'TASK_REQUEST' ? 'CREATE_GOVERNED_TASK' : 'PREPARE_RAY_REVIEW',
      requiresApproval: true,
      payload: {
        target,
        source: reference?.reason || 'conversation_reference',
        requestedText: message,
        status: 'conversation_draft_only',
      },
    };
    const noun = mode === 'TASK_REQUEST' ? 'governed work request' : 'Ray Review draft';
    return {
      response: `I’ll prepare ${target} as a ${noun}. This is conversation-only right now: nothing has been saved, assigned, submitted, or executed. It still requires the governed review path before any action runs.`,
      evidenceState: 'REPORT_BACKED',
      advisoryContext,
      action,
      contextUsed: ['advisory_memory', 'capability_policy'],
      warnings,
    };
  }

  if (mode === 'EXECUTIVE_ADVICE') {
    const operatingContext = getOperatingContext(input);
    if (!operatingContext) {
      const nextAdvisory = buildDefaultExecutiveAdvisory();
      const first = nextAdvisory.recommendations[0];
      return {
        response: `I would do **${first.label}** first. ${first.rationale} The main risk is ${first.risks?.[0] || 'moving before the evidence is stable'}. Once it passes, move directly into Department Operations and governed automation.`,
        evidenceState: 'REPORT_BACKED',
        advisoryContext: nextAdvisory,
        action: null,
        contextUsed: ['executive_read_model', 'capability_os', 'knowledge_layer'],
        warnings,
      };
    }
    const operating = answerTodayOperatingFocus(operatingContext);
    return {
      response: operating.text,
      evidenceState: 'REPORT_BACKED',
      advisoryContext: operating.advisoryContext,
      action: null,
      contextUsed: ['operating_context_panel', 'executive_read_model', 'capability_os', 'knowledge_layer'],
      warnings,
    };
  }

  if (mode === 'FOLLOW_UP_ADVICE') {
    if (!advisoryContext) {
      return {
        response: 'I can answer that, but I need the specific plan or recommendation you mean.',
        evidenceState: 'UNKNOWN',
        action: null,
        contextUsed,
        warnings: ['missing_advisory_context'],
      };
    }
    const item = reference?.item || advisoryContext.recommendations.find((candidate) => candidate.id === advisoryContext.preferredRecommendationId) || advisoryContext.recommendations[0];
    const lower = message.toLowerCase();
    if (reference?.item && /\bgo deeper|number\s*\d+|option\s*\d+\b/i.test(lower)) {
      return {
        response: `Going deeper on **${item.label}**: ${item.rationale}\n\nWhy it matters now: it is part of the current operating sequence, but it should stay behind the top customer-protection item unless it directly unblocks that work.\n\nMain risks: ${item.risks?.join(', ') || 'unclear evidence and dependency order'}.\n\nNext step: verify the evidence source for this item, then decide whether it needs Ray Review, a governed task, or just monitoring.`,
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory', 'selection_memory'],
        warnings,
      };
    }
    if (/\bcost|without paying|free\b/.test(lower)) {
      return {
        response: `${item.label} can be tested with mostly internal effort first. Keep it Nexus-native, use existing fixtures and reports, and avoid adding paid frameworks until the failure is measured. The cost risk is time spent polishing conversation behavior instead of validating it through the corpus.`,
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory'],
        warnings,
      };
    }
    if (/\bwhat would stop us|downside|risk|block/i.test(lower)) {
      return {
        response: `The main blockers are ${item.risks?.join(', ') || 'unclear evidence and implementation drift'}. The path is still realistic if we keep the scope bounded and certify the behavior before using Hermes as the interface for broader automation.`,
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory'],
        warnings,
      };
    }
    return {
      response: `Yes, it is realistic if we keep it bounded. ${item.label} works because ${item.rationale} I would validate it through the Wave 4A corpus before trusting it as the front door for Department Operations.`,
      evidenceState: 'REPORT_BACKED',
      advisoryContext,
      action: null,
      contextUsed: ['advisory_memory'],
      warnings,
    };
  }

  if (mode === 'SELECTION_REFERENCE') {
    if (reference?.item) {
      return {
        response: `I’m reading that as **${reference.item.label}**. ${reference.item.rationale} The main risk is ${reference.item.risks?.[0] || 'moving before the evidence is stable'}.`,
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['selection_memory'],
        warnings,
      };
    }
    return {
      response: 'I need one narrow clarification: which recommendation are you referring to?',
      evidenceState: 'UNKNOWN',
      action: null,
      contextUsed,
      warnings: ['unresolved_reference'],
    };
  }

  if (mode === 'EXPLANATION' || mode === 'FACTUAL_QUESTION' || mode === 'IDEA_REVIEW' || mode === 'DECISION_SUPPORT') {
    const executiveIntent = classifyExecutiveIntent(message);
    if (executiveIntent) {
      return { response: answerExecutiveIntent(executiveIntent), evidenceState: 'REPORT_BACKED', action: null, contextUsed: ['executive_read_model'], warnings };
    }
    return {
      response: 'My read: answer the immediate question first, then check the evidence before turning it into work. I can reason through the tradeoff, but I won’t treat that as an executed decision or approved policy.',
      evidenceState: 'REPORT_BACKED',
      action: null,
      contextUsed: ['nexus_native_reasoning'],
      warnings,
    };
  }

  return {
    response: 'I need one focused clarification: what specific decision, system status, or prior recommendation should I use?',
    evidenceState: 'UNKNOWN',
    action: null,
    contextUsed,
    warnings: ['low_confidence'],
  };
}
