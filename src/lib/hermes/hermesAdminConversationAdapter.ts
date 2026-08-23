import { answerOperationalQuestion, getBundledOperationalSnapshot, probeHermesModelHealth, probeSupabaseHealth } from '../nexusOperationalTruth';
import { classifyHermesConversationMode } from './hermesModeClassifier';
import { buildHermesOperatingContext } from './hermesOperatingContext';
import { runHermesConversation } from './hermesConversationEngine';
import { runHermesModelFirstConversation } from '../hermesModelFirst/hermesModelFirstController';
import { normalizeHermesWorkroomResponse, type HermesWorkroomResponse } from './hermesWorkroomResponse';

export interface HermesAdminConversationInput {
  message: string;
  sessionId: string;
  pageId?: string | null;
  route?: string;
  recentHistory?: Array<{ role: 'user' | 'assistant'; content: string }>;
  visibleItems?: unknown[];
  selectedItem?: unknown;
  availableActions?: unknown[];
}

export async function sendThroughCanonicalHermes(input: HermesAdminConversationInput): Promise<HermesWorkroomResponse> {
  const clean = input.message.trim();
  const now = Date.now();
  const operational = answerOperationalQuestion(clean);
  if (operational.handled) {
    return normalizeHermesWorkroomResponse({
      messageId: `${now}-hermes`, role: 'hermes', text: operational.text, mode: 'SYSTEM_STATUS', intent: 'operational_truth',
      responseStrategy: 'operational_truth_response', evidenceState: operational.provenance.confidence,
      confidence: operational.provenance.confidence === 'CURRENT' ? 0.86 : 0.66, createdAt: new Date().toISOString(),
      actions: [], memoryUsed: [], contextUsed: [operational.provenance.source], warnings: operational.provenance.unavailableSources,
    }, { messageId: `${now}-hermes` });
  }

  const classification = classifyHermesConversationMode(clean);
  const deterministic = ['SOCIAL_GREETING', 'CASUAL_CONVERSATION', 'COMMAND', 'TASK_REQUEST', 'APPROVAL_REQUEST', 'EXECUTIVE_ADVICE', 'SYSTEM_STATUS'].includes(classification.mode)
    || classification.intent === 'current_time_or_date';
  const operatingContext = buildHermesOperatingContext();
  const pageContext = {
    pageId: input.pageId || 'command', sectionName: input.pageId || 'command', route: input.route || '/admin',
    visibleItems: input.visibleItems || [], selectedItem: input.selectedItem || null,
    availableActions: input.availableActions || [], operatingContext,
  };
  let response: unknown;
  if (deterministic) {
    response = runHermesConversation({ message: clean, channel: 'full_workroom', actorRole: 'admin', pageId: input.pageId || undefined, route: input.route || '/admin', sessionId: input.sessionId, pageContext });
  } else {
    const modelFirst = await runHermesModelFirstConversation({ message: clean, actorRole: 'admin', sessionId: input.sessionId, recentHistory: input.recentHistory || [], pageContext });
    response = modelFirst.usedModelFirst && modelFirst.response ? modelFirst.response : runHermesConversation({ message: clean, channel: 'full_workroom', actorRole: 'admin', pageId: input.pageId || undefined, route: input.route || '/admin', sessionId: input.sessionId, pageContext });
  }
  return normalizeHermesWorkroomResponse(response as Parameters<typeof normalizeHermesWorkroomResponse>[0], { messageId: `${now}-hermes` });
}

export function getCanonicalSystemSnapshot() {
  const snapshot = getBundledOperationalSnapshot();
  return {
    processRegistry: { state: snapshot.freshness, checkedAt: snapshot.checkedAt, recordCount: snapshot.processes.length },
    model: probeHermesModelHealth(),
    supabase: probeSupabaseHealth(),
  };
}
