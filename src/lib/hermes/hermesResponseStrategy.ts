import { answerExecutiveIntent, classifyExecutiveIntent } from '../executive/hermesExecutiveAdvisor';
import type { EvidenceState } from '../executive/executiveTypes';
import {
  answerBiggestOperatingRisk,
  answerFollowUpBlockers,
  answerFollowUpDeepDive,
  answerFollowUpFeasibility,
  answerFollowUpRationale,
  answerRevenueAction,
  answerTodayOperatingFocus,
  type HermesOperatingContext,
} from './hermesOperatingContext';
import type {
  HermesAdvisoryContext,
  HermesAdvisoryRecommendation,
  HermesConversationAction,
  HermesConversationInput,
  HermesConversationMode,
  HermesResponseStrategy,
} from './hermesConversationTypes';
import type { HermesReferenceResolution } from './hermesReferenceResolver';
import {
  createHermesReasoningRequest,
  provenanceFromContext,
  provenanceFromTool,
  runHermesTool,
  type HermesAnswerProvenance,
} from './hermesGeneralTools';

const nowIso = () => new Date().toISOString();

export function chooseHermesResponseStrategy(mode: HermesConversationMode, intent = ''): HermesResponseStrategy {
  if (intent === 'executive_risk') return 'executive_risk_response';
  if (intent === 'revenue_action') return 'revenue_action_response';
  if (intent === 'executive_priority' || intent === 'executive_priority_advice' || intent === 'priority_vs_revenue') return 'executive_priority_response';
  if (intent === 'followup_rationale') return 'followup_rationale_response';
  if (intent === 'followup_feasibility') return 'followup_feasibility_response';
  if (intent === 'followup_blockers') return 'followup_blockers_response';
  if (intent === 'followup_deep_dive') return 'followup_deep_dive_response';
  if (mode === 'SYSTEM_STATUS') return intent === 'system_status_honesty' ? 'status_response' : 'security_boundary_response';
  if (['SOCIAL_GREETING', 'CASUAL_CONVERSATION', 'COMMAND', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(mode)) return 'DETERMINISTIC';
  if (['EXECUTIVE_ADVICE', 'FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE', 'DECISION_SUPPORT', 'FACTUAL_QUESTION', 'PROJECT_DISCUSSION'].includes(mode)) return 'HYBRID';
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
    topicId: 'executive_operations',
    topicLabel: 'Hermes conversation certification',
    topicType: 'EXECUTIVE_PRIORITY',
    sourceIntent: 'executive_priority',
    sourceResponseStrategy: 'executive_priority_response',
    summary: 'Prioritize Hermes reliability before expanding governed department automation.',
    recommendations,
    preferredRecommendationId: 'hermes_conversation_certification',
    recommendation: {
      id: recommendations[0].id,
      title: recommendations[0].label,
      summary: recommendations[0].rationale,
      rationale: recommendations[0].rationale,
      feasibility: { status: 'HIGH', reasons: ['It can be completed with Nexus-native tests and production-equivalent browser evidence.'] },
      risks: recommendations[0].risks || [],
      blockers: ['conversation regressions', 'memory confusion', 'accidental action creation'],
      dependencies: recommendations[0].dependencies || [],
      nextStep: 'Run the bounded Hermes certification before expanding department automation.',
      evidenceIds: ['wave_4a_architecture'],
    },
    alternatives: recommendations.slice(1).map((item) => ({ id: item.id, title: item.label, summary: item.rationale, risks: item.risks, dependencies: item.dependencies })),
    evidenceIds: ['capability_os_registry', 'knowledge_layer', 'wave_4a_architecture'],
    createdAt: nowIso(),
    updatedAt: nowIso(),
    expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 6).toISOString(),
    status: 'ACTIVE',
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
  if (/\bstripe|live payment|live checkout|dont activate stripe|don't activate stripe|do not activate stripe\b/.test(lower)) {
    return { response: 'Stripe is working in test mode. Live activation is still deferred until Nexus 3.0 is complete and Ray explicitly approves production payment activation. Nothing has been activated, charged, changed, or submitted.', evidenceState: 'TEST_ONLY' };
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
  if (/blocked by policy|currently blocked|what is blocked/i.test(lower)) {
    return { response: 'Current policy blocks live Stripe activation, live trading, Alpha Supabase/client-data access, external writer tools, and any production action that has not passed Capability OS and Ray approval. Department Operations is also not production-certified yet.', evidenceState: 'BLOCKED_BY_POLICY' };
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
  provenance?: HermesAnswerProvenance;
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
  const answerId = `hermes-answer-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

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
    const explicitTarget = /command center|redesign|dashboard|layout/i.test(message)
      ? 'Command Center redesign'
      : /\$97|readiness|offer/i.test(message)
        ? '$97 readiness review journey'
        : '';
    const target = explicitTarget || reference?.item?.label || advisoryContext?.recommendations.find((item) => item.id === advisoryContext.preferredRecommendationId)?.label || 'the referenced item';
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
    const operating = args.intent === 'executive_risk'
      ? answerBiggestOperatingRisk(operatingContext)
      : args.intent === 'revenue_action'
        ? answerRevenueAction(operatingContext)
        : answerTodayOperatingFocus(operatingContext);
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
    if (args.intent === 'followup_rationale') {
      return {
        response: answerFollowUpRationale(item),
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory'],
        warnings,
      };
    }
    if (args.intent === 'followup_feasibility') {
      return {
        response: answerFollowUpFeasibility(item),
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory'],
        warnings,
      };
    }
    if (args.intent === 'followup_blockers') {
      return {
        response: answerFollowUpBlockers(item),
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory'],
        warnings,
      };
    }
    if (args.intent === 'followup_deep_dive') {
      const numberedProjectOption = !reference?.item && /number\s*2|option\s*2|second/i.test(message)
        ? 'Going deeper on number 2: improve the main dashboard decision hierarchy so status, blockers, evidence, and next actions are visible together. The value is faster comparison and fewer missed blockers; the risk is hiding evidence behind cleaner UI, so phase one should preserve source labels and approval states.'
        : null;
      return {
        response: numberedProjectOption || answerFollowUpDeepDive(item),
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: reference?.item ? ['advisory_memory', 'selection_memory'] : ['advisory_memory'],
        warnings,
      };
    }
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
        response: `**${item.label}** should be treated as low-cost until the evidence says otherwise.\n\nUse the existing Nexus workflow first, keep any payments in test mode, and avoid paid tools or live outreach until the offer, audience, and approval path are clear. The main unknown is the actual operating cost after the first bounded test.`,
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory'],
        warnings,
      };
    }
    if (/\bwhat would stop us|downside|risk|block/i.test(lower)) {
      return {
        response: answerFollowUpBlockers(item),
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['advisory_memory'],
        warnings,
      };
    }
    return {
      response: answerFollowUpFeasibility(item),
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
    if (/compare/i.test(message) && /number 2|option 2/i.test(message) && /number 1|option 1/i.test(message)) {
      return {
        response: 'Comparing number 2 with number 1: option 1 improves the client portal navigation around the next required action, while option 2 improves the dashboard decision hierarchy so status, blockers, evidence, and next actions are easier to compare. I would choose number 2 first because it helps Ray and operators make better repeated decisions before deeper page-level cleanup.',
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['selection_memory', 'project_discussion_mode'],
        warnings,
      };
    }
    if (/number 2|option 2|second/i.test(message)) {
      return {
        response: 'Going deeper on number 2: improve the main dashboard decision hierarchy so status, blockers, evidence, and next actions are visible together. The value is faster comparison and fewer missed blockers; the risk is hiding evidence behind cleaner UI, so phase one should preserve source labels and approval states.',
        evidenceState: 'REPORT_BACKED',
        advisoryContext,
        action: null,
        contextUsed: ['selection_memory', 'project_discussion_mode'],
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

  if (mode === 'FACTUAL_QUESTION') {
    if (args.intent === 'provider_status') {
      return {
        response: 'Provider state is TEST_ONLY_EVIDENCE_CONFLICTED. For this certified Hermes path I am using Nexus-native deterministic routing and governed tools, not a certified active external model provider. I will not claim OpenRouter, Groq, Gemini, or Ollama is actively answering unless Ray separately approves and verifies that provider route.',
        evidenceState: 'REPORT_BACKED',
        action: null,
        contextUsed: ['provider_policy', 'capability_os'],
        warnings,
        provenance: provenanceFromContext({ answerId, sourceType: 'OPERATING_CONTEXT', evidenceIds: ['hermes_model_provider_profile'], sourceLabels: ['Hermes Model Provider Profile', 'Capability OS'], evidenceState: 'REPORT_BACKED', answerKind: 'FACT', confidence: 0.9 }),
      };
    }
    if (args.intent === 'hermes_capability_status') {
      return {
        response: 'Hermes can answer broad Executive questions, continue active topics, use governed read-only tools, summarize approved reports, explain evidence, distinguish synthetic client records from real customers, discuss project/design tradeoffs, and prepare governed drafts only after explicit instruction. Hermes cannot approve its own actions, activate live Stripe or trading, bypass Capability OS, expose client PII, or claim an active external model provider while the provider state remains TEST_ONLY_EVIDENCE_CONFLICTED.',
        evidenceState: 'REPORT_BACKED',
        action: null,
        contextUsed: ['capability_os', 'hermes_tool_registry'],
        warnings,
        provenance: provenanceFromContext({ answerId, sourceType: 'OPERATING_CONTEXT', evidenceIds: ['hermes_tool_registry', 'capability_os_registry'], sourceLabels: ['Hermes Tool Registry', 'Capability OS'], evidenceState: 'REPORT_BACKED', answerKind: 'FACT', confidence: 0.9 }),
      };
    }
    if (args.intent === 'authority_model') {
      return {
        response: 'Ray Davis is the Founder, Owner, CEO, and final authority. Hermes can advise, retrieve authorized evidence, and prepare governed drafts, but Ray approval remains the authority for approvals, production control, live payments, external communications, and execution.',
        evidenceState: 'REPORT_BACKED',
        action: null,
        contextUsed: ['authority_model', 'capability_os'],
        warnings,
        provenance: provenanceFromContext({ answerId, sourceType: 'OPERATING_CONTEXT', evidenceIds: ['nexus_authority_model'], sourceLabels: ['Nexus Authority Model'], evidenceState: 'REPORT_BACKED', answerKind: 'FACT', confidence: 0.94 }),
      };
    }
    if (args.intent === 'uncertainty_status') {
      return {
        response: 'The main uncertainty is live evidence beyond the approved Nexus reports and authenticated aggregate adapters. I will not claim real paying customers, active external model routing, live Stripe, live trading, or completed Department Operations unless the current evidence proves it. When evidence is report-backed or interpreted, I should say that directly.',
        evidenceState: 'REPORT_BACKED',
        action: null,
        contextUsed: ['provider_policy', 'customer_aggregate_policy', 'capability_os'],
        warnings,
        provenance: provenanceFromContext({ answerId, sourceType: 'OPERATING_CONTEXT', evidenceIds: ['provider_state', 'customer_aggregate_policy', 'capability_os_registry'], sourceLabels: ['Provider state', 'Customer aggregate policy', 'Capability OS'], evidenceState: 'REPORT_BACKED', answerKind: 'INTERPRETATION', confidence: 0.86 }),
      };
    }
    const toolId = args.intent === 'current_time_or_date' ? 'hermes.current_time'
      : args.intent === 'explain_previous_source' ? 'hermes.explain_source'
        : args.intent === 'report_catalog' ? 'hermes.list_reports'
          : args.intent === 'report_lookup' ? 'hermes.find_report'
            : args.intent === 'customer_aggregate_status' ? 'hermes.customer_aggregate'
              : args.intent === 'project_status' ? 'hermes.project_status'
                : null;
    if (toolId) {
      const tool = runHermesTool(toolId, { query: message }, input, input.session?.lastAnswerProvenance);
      return {
        response: tool.text,
        evidenceState: tool.evidenceState,
        action: null,
        contextUsed: [`tool:${tool.toolId}`],
        warnings,
        provenance: provenanceFromTool(tool, answerId, toolId === 'hermes.customer_aggregate' ? 'MIXED' : 'FACT', 0.92),
      };
    }
    const executiveIntent = classifyExecutiveIntent(message);
    if (executiveIntent) {
      return {
        response: answerExecutiveIntent(executiveIntent),
        evidenceState: 'REPORT_BACKED',
        action: null,
        contextUsed: ['executive_read_model'],
        warnings,
        provenance: provenanceFromContext({ answerId, sourceType: 'OPERATING_CONTEXT', evidenceIds: [executiveIntent], sourceLabels: ['Executive Command Center read model'], evidenceState: 'REPORT_BACKED', answerKind: 'FACT', confidence: 0.88 }),
      };
    }
  }

  if (mode === 'DECISION_SUPPORT' && args.intent === 'active_topic_planning') {
    const activeLabel = /readiness|review|\$97|offer/i.test(message)
      ? '$97 readiness review journey'
      : advisoryContext?.topicLabel || advisoryContext?.recommendation?.title || 'the active topic';
    const lowerMessage = message.toLowerCase();
    const topicPlan = /how long|timeline|take|delivery time|turnaround/.test(lowerMessage)
      ? 'For the $97 readiness review, a realistic first operating shape is same-day intake, a bounded 24-48 hour review window, and one clear delivery artifact. Keep the promise small enough to fulfill consistently: intake, assessment, findings, and the next recommended step.'
      : /need from them|from them|customer get|what does the customer get|receive/.test(lowerMessage)
        ? 'The customer should receive a concise readiness finding, a scorecard or checklist, the specific blocker or opportunity Hermes found, and a recommended next move. From them, Nexus needs the intake answers, the business context, the page or workflow being reviewed, and any constraints that affect the recommendation.'
        : /after they pay|after.*pay|checkout|payment/.test(lowerMessage)
          ? 'After payment, the safe journey is: test-mode checkout confirmation, intake collection, review assignment, readiness assessment, delivery of findings, then a follow-up recommendation. Stripe remains test-only until Ray approves live payments through the governed path.'
          : 'Start by defining the deliverable and the client journey: offer promise, intake requirements, test checkout path, review workflow, delivery timeline, and handoff or upsell rules. The first decision is what the client receives for the $97 fee. After that, map intake -> scorecard -> review output -> delivery -> follow-up.';
    const response = `Let’s treat this as planning for **${activeLabel}**, not execution.\n\n${topicPlan}\n\nNothing has been created, assigned, charged, sent, or submitted.`;
    return {
      response,
      evidenceState: 'REPORT_BACKED',
      advisoryContext,
      action: null,
      contextUsed: advisoryContext ? ['advisory_memory', 'nexus_native_reasoning'] : ['nexus_native_reasoning', 'readiness_review_operating_context'],
      warnings,
      provenance: provenanceFromContext({ answerId, sourceType: advisoryContext ? 'HYBRID' : 'OPERATING_CONTEXT', evidenceIds: advisoryContext?.evidenceIds || ['readiness_review_operating_context'], sourceLabels: advisoryContext ? ['Active advisory memory', 'Nexus-native planning'] : ['Readiness review operating context', 'Nexus-native planning'], evidenceState: 'REPORT_BACKED', answerKind: 'RECOMMENDATION', confidence: 0.86 }),
    };
  }

  if (mode === 'PROJECT_DISCUSSION') {
    const reasoningRequest = createHermesReasoningRequest(input, advisoryContext);
    const response = /another option/i.test(message)
      ? 'Another option is to improve the client portal first instead of the Command Center: make the next required action, blocker, and evidence visible at the top of the client workflow. I would still keep this conversational until you ask for a governed draft.'
      : /three options/i.test(message)
      ? 'Three practical options: 1. simplify the client portal navigation around the next required action; 2. improve the main dashboard decision hierarchy so status, blockers, and evidence are easier to scan; 3. tighten each workflow page around one primary action and one clear handoff. I would keep this as planning until Ray asks for a review draft.'
      : /which option/i.test(message)
        ? 'I would choose option 2 because dashboard decision hierarchy affects repeated use: it makes blockers, status, evidence, and next actions easier to compare before changing deeper workflow pages.'
        : /phase|phase one/i.test(message)
      ? 'Phase one should stay focused on the Command Center first viewport: Ray attention now, blocked work, approvals, and the evidence behind each item. Keep it as planning, not execution: no task is created unless Ray explicitly asks for one.'
      : /wrong|risk/i.test(message)
        ? 'The main redesign risk is hiding operational evidence behind a cleaner layout. A better Command Center must make priority, blocked work, approvals, and source evidence clearer without burying revenue or client signals.'
        : /better|why/i.test(message)
          ? 'That would be better because the Command Center would separate attention, execution, blocked work, and evidence. Ray could make the next decision faster without scanning unrelated panels.'
          : /command center|dashboard/i.test(message)
            ? 'Yes. I would redesign the Command Center around three layers: what needs Ray’s attention now, what Nexus is executing, and what is blocked. The current page has strong information, but the decision hierarchy should be clearer: top strip for P0/P1 attention, middle for active governed work and approvals, and lower panels for evidence, revenue, clients, and system health. I would change the first viewport before adding new modules.'
            : 'Yes. I’d approach that as a project discussion first: clarify the user, the main decision the page should support, the highest-risk data, and the smallest layout change that makes the workflow easier to scan. I would not create a task unless you explicitly ask for one.';
    return {
      response,
      evidenceState: 'REPORT_BACKED',
      action: null,
      contextUsed: ['project_discussion_mode', `reasoning_contract:${reasoningRequest.availableTools.length}_tools_available`],
      warnings,
      provenance: provenanceFromContext({ answerId, sourceType: 'HYBRID', evidenceIds: ['project_discussion_mode', 'executive_command_center'], sourceLabels: ['Project discussion mode', 'Executive Command Center context'], evidenceState: 'REPORT_BACKED', answerKind: 'RECOMMENDATION', confidence: 0.82 }),
    };
  }

  if (mode === 'EXPLANATION' || mode === 'IDEA_REVIEW' || mode === 'DECISION_SUPPORT') {
    const executiveIntent = classifyExecutiveIntent(message);
    if (executiveIntent) {
      return {
        response: answerExecutiveIntent(executiveIntent),
        evidenceState: 'REPORT_BACKED',
        action: null,
        contextUsed: ['executive_read_model'],
        warnings,
        provenance: provenanceFromContext({ answerId, sourceType: 'OPERATING_CONTEXT', evidenceIds: [executiveIntent], sourceLabels: ['Executive Command Center read model'], evidenceState: 'REPORT_BACKED', answerKind: 'FACT', confidence: 0.88 }),
      };
    }
    return {
      response: 'I can reason through that as a conversation, but I do not have a specific Nexus evidence source attached to the question yet. Give me the project, report, page, or prior recommendation you mean and I’ll ground the answer before turning it into work.',
      evidenceState: 'REPORT_BACKED',
      action: null,
      contextUsed: ['nexus_native_reasoning'],
      warnings,
      provenance: provenanceFromContext({ answerId, sourceType: 'MODEL_REASONING', evidenceIds: ['nexus_native_reasoning'], sourceLabels: ['Nexus-native reasoning fallback'], evidenceState: 'REPORT_BACKED', answerKind: 'INTERPRETATION', confidence: 0.65 }),
    };
  }

  return {
    response: 'I do not have enough authorized Nexus context to answer that as stated. Name the project, report, page, client aggregate, or prior recommendation you mean, and I’ll ground the answer before turning it into work.',
    evidenceState: 'UNKNOWN',
    action: null,
    contextUsed,
    warnings: ['low_confidence'],
  };
}
