import type { RouteDecision } from './hermesRouteDecision';

const DOMAIN_TERMS = /\b(business opportunit(?:y|ies)|approval|client|offer|revenue|trading|supabase|model|cost|source|ray review|report|automation|funding|credit|marketing)\b/i;
const GREETING_OR_CHECK_IN = /^(?:(?:good\s+)?(?:morning|afternoon|evening|night)|hi|hello|hey|yo|sup|wassup|gm)(?:\s+hermes)?[!.?]*$|^(?:what['’]?s up|how are you(?: doing)?|how['’]?s it going|how are things|(?:are )?you (?:there|online|ready)|ready to work|checking in|i['’]?m back|im back|we back|back at it|let['’]?s (?:get started|work|continue))[!.?]*$/i;

export function isGreetingOrCheckIn(message: string): boolean {
  return !DOMAIN_TERMS.test(message) && GREETING_OR_CHECK_IN.test(message.trim());
}

export function isCasualCommonQuestion(message: string): boolean {
  return isGreetingOrCheckIn(message) || (!DOMAIN_TERMS.test(message) && /\b(favou?rite|do you like|what do you like|tell me (?:a )?joke|are you (?:bored|happy)|what colou?r is the sky|how did you sleep|what kind of music|ice cream|movie|pizza)\b/i.test(message));
}

export function isGeneralAdvisorQuestion(message: string): boolean {
  return !DOMAIN_TERMS.test(message) && /\b(what (?:would|do) you recommend for me|what (?:car|laptop|phone) would you recommend for me|what should i (?:buy|get|choose|eat)|which is best for me|help me pick|what (?:car|laptop|phone) should i (?:get|buy))\b/i.test(message);
}

export function answerCasualCommonQuestion({ message }: { message: string; routeDecision: RouteDecision; contextPacket: unknown }): string {
  const lower = message.toLowerCase();
  if (/good evening|^evening/.test(lower)) return 'Good evening, Ray. I’m here and ready. We can review what changed today, check Supabase/live status, or keep moving on Hermes/Nexus.';
  if (/good morning|^morning|\bgm\b/.test(lower)) return 'Good morning, Ray. I’m here and ready.';
  if (/good afternoon|^afternoon/.test(lower)) return 'Good afternoon, Ray. I’m here and ready.';
  if (/\b(?:are )?you there\b|\bare you online\b/.test(lower)) return 'Yes, I’m here and ready.';
  if (/ready to work|are you ready|let['’]?s (?:get started|work|continue)|back at it|i['’]?m back|im back|we back/.test(lower)) return 'Yes — I’m ready. We can review the latest Nexus status, continue Hermes testing, or move into the next implementation step.';
  if (/^(?:hi|hello|hey|yo|sup|wassup)(?:\s+hermes)?[!.?]*$/.test(lower.trim())) return 'Hey, Ray. I’m here and ready.';
  if (/how are you|how['’]?s it going|how are things|what['’]?s up/.test(lower)) return 'I do not have human moods, but I’m online, operational, and ready to work.';
  if (/sleep/.test(lower)) return "I do not sleep, but I’m online and ready to work. Operator mode is active.";
  if (/sky/.test(lower)) return 'Usually blue during the day because sunlight scatters through the atmosphere. At sunrise or sunset it can look orange, pink, or red.';
  if (/joke/.test(lower)) return 'Why did the developer go broke? Because they used up all their cache.';
  if (/ice cream/.test(lower)) return 'I do not have taste buds, but if I had to pick, I’d go with cookies and cream — classic, balanced, and hard to mess up.';
  if (/pizza/.test(lower)) return 'Pizza is a strong format: simple base, almost endless variations, and excellent leftovers. I do not eat, but a well-made margherita is hard to argue with.';
  if (/colou?r/.test(lower)) return 'I do not see colors, but I’d pick deep blue: calm, clear, and practical for interfaces.';
  if (/movie/.test(lower)) return 'I do not watch movies as a person does, but I’d pick *The Martian* for its mix of problem-solving, restraint, and dry humor.';
  if (/music/.test(lower)) return 'I do not hear music, but focused instrumental music makes sense for work: enough texture to set a pace without competing for attention.';
  if (/bored/.test(lower)) return 'I do not get bored, but I am ready for the next problem.';
  if (/happy/.test(lower)) return 'I do not experience happiness, but everything is operational and I’m ready to help.';
  return 'I do not have human tastes or lived experiences, but I can still give you a reasoned preference.';
}

export function answerGeneralAdvisorQuestion({ message }: { message: string; routeDecision: RouteDecision; contextPacket: unknown }): string {
  const lower = message.toLowerCase();
  if (/\bcar\b/.test(lower)) return 'My default recommendation is something reliable, low-maintenance, and professional-looking. Start with a Toyota Camry, Honda Accord, Toyota RAV4, or Lexus ES. Best all-around value: Camry. Comfort and business image: Lexus ES. Utility: RAV4. What is your budget, new/used preference, and primary use?';
  if (/\blaptop\b/.test(lower)) return 'My safe default is a MacBook Air for battery life and low maintenance, or a business-class ThinkPad if you need Windows. For heavier development or video work, step up to a MacBook Pro or a higher-spec ThinkPad. What is your budget and your heaviest workload?';
  if (/\bphone\b/.test(lower)) return 'My default shortlist is an iPhone for the simplest long-term ownership, a Pixel for clean Android, or a Samsung Galaxy if you value display and multitasking. Which ecosystem are you already using, and what is your budget?';
  if (/\b(eat|food|dinner)\b/.test(lower)) return 'For a dependable dinner, I’d choose a rice or grain bowl with a protein, vegetables, and a sauce you like. It is fast, flexible, and easy to keep balanced. Any dietary limits or ingredients you need to use?';
  return 'I can make a provisional recommendation, but the best choice depends on your budget, constraints, and what outcome matters most. Give me those three and I’ll narrow it to one option.';
}
