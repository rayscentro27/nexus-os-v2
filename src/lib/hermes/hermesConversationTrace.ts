import type { HermesConversationResult, HermesConversationTrace } from './hermesConversationTypes';

export function createHermesConversationTrace(
  result: Omit<HermesConversationResult, 'trace' | 'quality'>,
  responseQualityScore: number,
  memoryTrace: Partial<Pick<
    HermesConversationTrace,
    'activeAdvisoryIdBefore' | 'activeAdvisoryIdAfter' | 'resolvedAdvisoryId' | 'resolutionMethod' | 'topicSwitched' | 'supersededAdvisoryId' | 'followUpSemantic'
  >> = {},
): HermesConversationTrace {
  return {
    traceId: result.traceId || `hermes-trace-${Date.now()}`,
    channel: result.session.channel,
    mode: result.mode,
    intent: result.intent,
    confidence: result.confidence,
    memoryUsed: result.memoryUsed,
    contextUsed: result.contextUsed,
    referencesResolved: result.referencesResolved,
    responseStrategy: result.responseStrategy,
    provider: result.responseStrategy === 'SAFE_FALLBACK' ? 'fallback' : 'nexus_native',
    actionDetected: Boolean(result.action),
    policyBlocks: result.warnings.filter((warning) => /blocked|prohibited|denied/i.test(warning)),
    responseQualityScore,
    ...memoryTrace,
    generatedAt: new Date().toISOString(),
  };
}
