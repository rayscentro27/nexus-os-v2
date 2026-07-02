export type HermesDomain =
  | 'source_trace' | 'casual_identity' | 'business_opportunity' | 'monetization' | 'credit_funding'
  | 'trading' | 'research_youtube' | 'reports' | 'settings' | 'tools_cli'
  | 'approvals' | 'clients' | 'system_health' | 'model_cost_status'
  | 'automation' | 'marketing' | 'unknown';

export interface DomainClassification {
  domain: HermesDomain;
  confidence: 'high' | 'medium' | 'low';
  signals: string[];
  explicit: boolean;
}

const DOMAIN_FAMILIES: Array<{ domain: HermesDomain; pattern: RegExp; signal: string }> = [
  { domain: 'source_trace', pattern: /\b(where\s+(?:did|does|are).*?(?:answer|response|that|this|source)|what\s+source|where\s+did\s+that\s+come\s+from|did\s+(?:that|you).*?(?:supabase|database|model|ai|memory)|are\s+you\s+using\s+(?:supabase|the\s+database|strategic reasoning|a model|ai)|what\s+domain\s+did|why\s+did\s+you\s+answer|what\s+route\s+did|what\s+(?:was|context was)\s+allowed|why.*not use.*(?:memory|supabase|database|model|ai)|why\s+did\s+you.*previous recommendation)\b/i, signal: 'routing/source/trace terms' },
  { domain: 'model_cost_status', pattern: /\b(tokens?|supabase|database|route|routing|activation level|source used|cost of (?:that|the) answer)\b|\b(?:what|which) model (?:did|do|are|is|was)|\b(?:using|use|used|running|run) (?:the |a |which )?model\b|\b(?:ai|gpt|llm|openrouter|primary|fallback|reasoning|cheapest) model\b|\bmodel cost\b/i, signal: 'AI model/database/routing status terms' },
  { domain: 'trading', pattern: /\b(trad(?:e|ing)|forex|stock|crypto|broker|paper[- ]?trad|backtest|market setup|position|strategy lab)\b/i, signal: 'trading and market terms' },
  { domain: 'research_youtube', pattern: /\b(youtube|video|transcript|channel|research|sources?|candidate scoring)\b/i, signal: 'research or YouTube terms' },
  { domain: 'settings', pattern: /\b(settings?|configuration|configured|environment variable|feature flag|missing setup)\b/i, signal: 'settings/configuration terms' },
  { domain: 'reports', pattern: /\b(reports?|briefs?|audit files?|what changed|latest findings)\b/i, signal: 'report/audit terms' },
  { domain: 'tools_cli', pattern: /\b(cli|command line|terminal|tools?|scripts?|shell)\b/i, signal: 'tool/CLI terms' },
  { domain: 'approvals', pattern: /\b(approvals?|approve|ray review|review cards?|pending review|task requests?)\b/i, signal: 'approval/Ray Review terms' },
  { domain: 'clients', pattern: /\b(clients?|customers?|profiles?|onboarding)\b/i, signal: 'client/customer terms' },
  { domain: 'credit_funding', pattern: /\b(credit|funding|readiness|dispute|tradeline|fundability)\b/i, signal: 'credit/funding terms' },
  { domain: 'marketing', pattern: /\b(marketing|campaign|landing page|seo|social post|content plan)\b/i, signal: 'marketing terms' },
  { domain: 'system_health', pattern: /\b(system health|incident|errors?|runtime|uptime|broken|failure)\b/i, signal: 'system health terms' },
  { domain: 'automation', pattern: /\b(automation|scheduler|scheduled|background job|workflow|process running)\b/i, signal: 'automation/process terms' },
  { domain: 'monetization', pattern: /\b(monetiz\w*|revenue|money|earn(?:ing|ings)?|income|profitable|pricing|offer to launch)\b|\bhow much\b.*\b(?:make|earn)\b/i, signal: 'revenue/monetization terms' },
  { domain: 'business_opportunity', pattern: /\b(business|opportunit|startup|start (?:a|the)|launch first|low[- ]cost offer)\b/i, signal: 'business/opportunity terms' },
];

const CASUAL_IDENTITY = /\b(favou?rite|prefer|would you choose|who are you|your name|call you|how are you|how do you feel|food|car|hobby|personality)\b/i;

export function classifyHermesDomain(message: string, currentPage?: string | null, previousDomain?: HermesDomain | string | null): DomainClassification {
  const normalized = message.trim().toLowerCase();
  if (CASUAL_IDENTITY.test(normalized)) {
    return { domain: 'casual_identity', confidence: 'high', signals: ['casual/identity conversational terms'], explicit: true };
  }
  for (const family of DOMAIN_FAMILIES) {
    if (family.pattern.test(normalized)) return { domain: family.domain, confidence: 'high', signals: [family.signal], explicit: true };
  }
  if (previousDomain && previousDomain !== 'unknown' && /^(?:but|so|and|also)\b/i.test(normalized) && /\b(strategy|strategies|recommend|available|which one|what do you have)\b/i.test(normalized)) {
    return { domain: previousDomain as HermesDomain, confidence: 'medium', signals: [`continuation of previous ${previousDomain} topic`], explicit: false };
  }
  if (currentPage) {
    const pageMatch = DOMAIN_FAMILIES.find(family => family.pattern.test(currentPage.replace(/[-_]/g, ' ')));
    if (pageMatch) return { domain: pageMatch.domain, confidence: 'medium', signals: [`current page: ${currentPage}`], explicit: false };
  }
  return { domain: 'unknown', confidence: 'low', signals: [], explicit: false };
}

export function isCasualIdentityDomain(domain: HermesDomain): boolean { return domain === 'casual_identity'; }
export function isBusinessDomain(domain: HermesDomain): boolean { return domain === 'business_opportunity' || domain === 'monetization'; }
