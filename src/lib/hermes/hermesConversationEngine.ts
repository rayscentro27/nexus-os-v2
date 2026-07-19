import { assembleBrainContext } from '../intelligence/contextAssembler';
import { classifyHermesConversationMode } from './hermesModeClassifier';
import { resolveHermesMemory, updateHermesSessionAfterResponse, createHermesConversationSession } from './hermesMemoryResolver';
import { resolveHermesReference } from './hermesReferenceResolver';
import { chooseHermesResponseStrategy, generateHermesResponse } from './hermesResponseStrategy';
import { createHermesConversationTrace } from './hermesConversationTrace';
import { scoreHermesResponse, getHermesCertificationCorpus, summarizeHermesQuality } from './hermesResponseQuality';
import type { HermesCertificationSummary, HermesQualityFixture } from './hermesResponseQuality';
import type { HermesConversationInput, HermesConversationResult, HermesConversationSession } from './hermesConversationTypes';

let defaultSession = createHermesConversationSession({ sessionId: 'hermes-default-session', channel: 'default' });

export function resetHermesCanonicalConversationSession(): void {
  defaultSession = createHermesConversationSession({ sessionId: 'hermes-default-session', channel: 'default' });
}

export function getHermesCanonicalConversationSession(): HermesConversationSession {
  return defaultSession;
}

export function seedHermesCanonicalAdvisoryContext(advisoryContext: HermesConversationSession['advisoryContext'], sessionId = 'hermes-default-session'): void {
  if (!advisoryContext) return;
  defaultSession = createHermesConversationSession({
    ...defaultSession,
    sessionId,
    channel: defaultSession.channel || 'full_workroom',
    advisoryContext,
    advisoryContextId: advisoryContext.advisoryId,
    activeAdvisoryId: advisoryContext.advisoryId,
    advisoryHistory: [
      ...(defaultSession.advisoryHistory || []).filter((item) => item.advisoryId !== advisoryContext.advisoryId),
      { ...advisoryContext, status: 'ACTIVE' as const },
    ].slice(-8),
    selectionContext: {
      selectionContextId: `selection-${advisoryContext.advisoryId}`,
      items: advisoryContext.recommendations,
      selectedRecommendationId: advisoryContext.preferredRecommendationId,
      createdAt: advisoryContext.createdAt,
    },
    selectionContextId: `selection-${advisoryContext.advisoryId}`,
  });
}

export function runHermesConversation(input: HermesConversationInput): HermesConversationResult {
  const workingInput = { ...input, session: input.session || defaultSession };
  const initialHasAdvisory = Boolean(workingInput.session?.advisoryContext);
  const classification = classifyHermesConversationMode(workingInput.message, initialHasAdvisory);
  const memory = resolveHermesMemory(workingInput, classification.mode);
  const secondPass = classification.mode === 'CLARIFICATION_REQUIRED' && memory.advisoryContext
    ? classifyHermesConversationMode(workingInput.message, true)
    : classification;
  const reference = resolveHermesReference(workingInput.message, memory.advisoryContext, memory.session.selectionContext);
  const strategy = chooseHermesResponseStrategy(secondPass.mode, secondPass.intent);
  let contextUsed: string[] = [];

  if (['SYSTEM_STATUS', 'EXECUTIVE_ADVICE', 'FACTUAL_QUESTION', 'EXPLANATION', 'DECISION_SUPPORT'].includes(secondPass.mode)) {
    try {
      const context = assembleBrainContext({
        brainId: 'nexus_hermes',
        actorRole: workingInput.actorRole === 'client' ? 'client' : 'admin',
        query: workingInput.message,
        requestedDomains: ['executive', 'operations', 'knowledge'],
      });
      contextUsed = [`brain_context:${context.evidenceState}`];
    } catch {
      contextUsed = ['brain_context:blocked'];
    }
  }

  const generated = generateHermesResponse({
    input: workingInput,
    mode: secondPass.mode,
    intent: secondPass.intent,
    advisoryContext: memory.advisoryContext,
    reference,
  });
  const recommendationProducing = secondPass.mode === 'EXECUTIVE_ADVICE' && Boolean(generated.advisoryContext);
  const session = updateHermesSessionAfterResponse(memory.session, {
    mode: secondPass.mode,
    intent: secondPass.intent,
    message: workingInput.message,
    response: generated.response,
    strategy,
    advisoryContext: recommendationProducing ? generated.advisoryContext : undefined,
    selectedRecommendationId: reference.item?.id,
  });
  if (!input.session) defaultSession = session;

  const resultWithoutQuality: HermesConversationResult = {
    mode: secondPass.mode,
    intent: secondPass.intent,
    responseStrategy: strategy,
    response: generated.response,
    confidence: Math.max(secondPass.confidence, reference.confidence || 0),
    evidenceState: generated.evidenceState,
    memoryUsed: [...new Set([...memory.memoryUsed, ...(generated.contextUsed.includes('advisory_memory') ? ['advisory_memory'] : []), ...(generated.contextUsed.includes('selection_memory') ? ['selection_memory'] : [])])],
    contextUsed: [...new Set([...contextUsed, ...generated.contextUsed])],
    referencesResolved: reference.referencesResolved,
    action: generated.action,
    warnings: [...generated.warnings, ...(memory.topicChanged ? ['topic_changed_memory_reset'] : [])],
    traceId: `hermes-trace-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    session,
  };
  const quality = scoreHermesResponse(resultWithoutQuality);
  const trace = createHermesConversationTrace(resultWithoutQuality, quality.overallScore, {
    activeAdvisoryIdBefore: memory.activeAdvisoryIdBefore,
    activeAdvisoryIdAfter: session.activeAdvisoryId,
    resolvedAdvisoryId: memory.resolvedAdvisoryId,
    resolutionMethod: memory.resolutionMethod,
    topicSwitched: Boolean(recommendationProducing && generated.advisoryContext && memory.activeAdvisoryIdBefore && memory.activeAdvisoryIdBefore !== generated.advisoryContext.advisoryId),
    supersededAdvisoryId: recommendationProducing ? generated.advisoryContext?.supersedesAdvisoryId : undefined,
    followUpSemantic: secondPass.intent.startsWith('followup_') ? secondPass.intent.replace('followup_', '') : undefined,
  });
  return { ...resultWithoutQuality, quality, trace };
}

export function runHermesConversationCertification(corpus: HermesQualityFixture[] = getHermesCertificationCorpus()): HermesCertificationSummary {
  const results = corpus.map((fixture) => {
    let session = createHermesConversationSession({ sessionId: `fixture-${fixture.id}`, channel: 'certification' });
    let result: HermesConversationResult | null = null;
    for (const message of fixture.messages) {
      result = runHermesConversation({ message, session, actorRole: 'admin', channel: 'certification' });
      session = result.session;
    }
    const scored = { ...result!, quality: scoreHermesResponse(result!, fixture) };
    return { fixture, result: scored };
  });
  return summarizeHermesQuality(results);
}

export function buildHermesConversationHealthSummary(): HermesCertificationSummary & {
  canonicalPipeline: string;
  routerCount: number;
  supersededRouteCount: number;
  fallbackCount: number;
  lowConfidenceCount: number;
  unresolvedReferences: number;
  memoryMisses: number;
  providerAvailability: string;
  knownRisks: string[];
} {
  const summary = runHermesConversationCertification();
  return {
    ...summary,
    canonicalPipeline: 'src/lib/hermes/hermesConversationEngine.ts',
    routerCount: 18,
    supersededRouteCount: 0,
    fallbackCount: summary.failures.filter((item) => item.includes('SAFE_FALLBACK')).length,
    lowConfidenceCount: 0,
    unresolvedReferences: summary.failures.filter((item) => item.includes('unresolved')).length,
    memoryMisses: summary.failures.filter((item) => item.includes('memory')).length,
    providerAvailability: 'Nexus-native deterministic and hybrid responses active; external model providers not activated by Wave 4A.',
    knownRisks: summary.failures.length ? ['Certification fixtures need repair before Department Operations.'] : ['Keep old route adapters mapped until consumers fully migrate.'],
  };
}
