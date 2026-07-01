import { classifyHermesDomain, isBusinessDomain, type HermesDomain } from './hermesDomainClassifier';
import type { ConversationItem } from './hermesConversationState';

export interface TopicBoundaryInput {
  message: string;
  detectedIntent?: string | null;
  detectedDomain?: HermesDomain;
  previousTopic?: string | null;
  previousIntent?: string | null;
  previousSelectedItem?: ConversationItem | null;
  previousRankedItems?: ConversationItem[];
  previousListedItems?: ConversationItem[];
  currentPage?: string | null;
  previousPage?: string | null;
}

export interface TopicBoundaryDecision {
  detectedTopic: string;
  isNewTopic: boolean;
  shouldUsePriorMemory: boolean;
  reason: string;
  confidence: 'high' | 'medium' | 'low';
  followUpMarkers: string[];
  namedMemoryMatches: ConversationItem[];
  domainOverrideApplied: boolean;
  casualOverrideApplied: boolean;
}

const FOLLOW_UP_MARKERS: Array<[string, RegExp]> = [
  ['pronoun_reference', /\b(that(?: one)?|this|it)\b/i],
  ['number_reference', /\b(?:number|option|#)\s*\d+\b/i],
  ['ordinal_reference', /\b(?:the\s+)?(?:first|second|third|fourth|last)\s+(?:one|option|item)?\b/i],
  ['selection_continuation', /\b(?:pick|choose)\s+one|do that|continue|next step\b/i],
  ['recommendation_reference', /\bwhich one (?:do|would|should) (?:you|we|i)|which one.*recommend\b/i],
  ['implementation_reference', /\bhow do (?:we|i) implement (?:it|that|this)\b/i],
  ['card_reference', /\bcreate (?:a )?(?:ray review )?card for (?:that|it|this)\b/i],
];

function normalizeEntity(value: string): string[] {
  const normalized = value.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  const withoutPrice = normalized.replace(/^\d+\s+/, '');
  return [normalized, withoutPrice].filter(value => value.length >= 5);
}

export function evaluateTopicBoundary(input: TopicBoundaryInput): TopicBoundaryDecision {
  const domain = input.detectedDomain || classifyHermesDomain(input.message, input.currentPage).domain;
  const previousTopic = input.previousTopic || 'unknown';
  const followUpMarkers = FOLLOW_UP_MARKERS.filter(([, pattern]) => pattern.test(input.message)).map(([name]) => name);
  const memoryItems = [input.previousSelectedItem, ...(input.previousRankedItems || []), ...(input.previousListedItems || [])]
    .filter((item): item is ConversationItem => Boolean(item));
  const normalizedMessage = input.message.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  const namedMemoryMatches = memoryItems.filter(item => normalizeEntity(item.title).some(name => normalizedMessage.includes(name)));
  const casualOverrideApplied = domain === 'casual_identity';
  const explicitNewDomain = domain !== 'unknown' && domain !== previousTopic && !namedMemoryMatches.length;
  const statusBoundary = ['model_cost_status', 'settings', 'reports', 'tools_cli', 'research_youtube', 'trading', 'system_health', 'automation'].includes(domain);
  const pageChanged = Boolean(input.currentPage && input.previousPage && input.currentPage !== input.previousPage);
  const broadFreshStrategy = isBusinessDomain(domain) && !followUpMarkers.length && !namedMemoryMatches.length;

  if (casualOverrideApplied) return { detectedTopic: domain, isNewTopic: true, shouldUsePriorMemory: false, reason: 'Casual/identity questions always start a new topic.', confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: true, casualOverrideApplied: true };
  if (namedMemoryMatches.length) {
    const namedTopic = namedMemoryMatches[0].type === 'opportunity' ? 'business_opportunity' : (domain === 'unknown' ? previousTopic : domain);
    return { detectedTopic: namedTopic, isNewTopic: namedTopic !== previousTopic, shouldUsePriorMemory: true, reason: 'Message names an entity stored in prior ranked/listed memory.', confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: false, casualOverrideApplied: false };
  }
  if (statusBoundary && explicitNewDomain) return { detectedTopic: domain, isNewTopic: true, shouldUsePriorMemory: false, reason: `Explicit ${domain} domain overrides stale ${previousTopic} memory.`, confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: true, casualOverrideApplied: false };
  if (explicitNewDomain && domain !== 'approvals') return { detectedTopic: domain, isNewTopic: true, shouldUsePriorMemory: false, reason: `Detected a new explicit domain (${domain}) without an eligible same-domain continuation.`, confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: true, casualOverrideApplied: false };
  if (pageChanged && !followUpMarkers.length && !namedMemoryMatches.length) return { detectedTopic: domain, isNewTopic: true, shouldUsePriorMemory: false, reason: 'Current page changed domains and the message has no follow-up reference.', confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: true, casualOverrideApplied: false };
  if (broadFreshStrategy) return { detectedTopic: domain, isNewTopic: true, shouldUsePriorMemory: false, reason: 'Broad strategy question creates a fresh recommendation context.', confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: false, casualOverrideApplied: false };
  if (followUpMarkers.length) return { detectedTopic: previousTopic === 'unknown' ? domain : previousTopic, isNewTopic: false, shouldUsePriorMemory: true, reason: 'Explicit follow-up marker makes prior memory eligible.', confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: false, casualOverrideApplied: false };
  const sameDomainAndPage = domain !== 'unknown' && domain === previousTopic && (!input.currentPage || !input.previousPage || input.currentPage === input.previousPage);
  if (sameDomainAndPage && /\b(?:also|more|why|compare|continue|next)\b/i.test(input.message)) return { detectedTopic: domain, isNewTopic: false, shouldUsePriorMemory: true, reason: 'Same-domain, same-page continuation marker.', confidence: 'medium', followUpMarkers, namedMemoryMatches, domainOverrideApplied: false, casualOverrideApplied: false };
  return { detectedTopic: domain, isNewTopic: domain !== previousTopic, shouldUsePriorMemory: false, reason: 'No explicit reference, named memory match, or same-domain continuation.', confidence: 'high', followUpMarkers, namedMemoryMatches, domainOverrideApplied: explicitNewDomain, casualOverrideApplied: false };
}
