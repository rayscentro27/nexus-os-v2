import type { RouteDecision } from './hermesRouteDecision';

const DOMAIN_TERMS = /\b(business opportunit(?:y|ies)|approval|client|offer|revenue|trading|supabase|model|cost|source|ray review|report|automation|funding|credit|marketing)\b/i;
const GREETING_OR_CHECK_IN = /^(?:(?:good\s+)?(?:morning|afternoon|evening|night)|hi|hello|hey|yo|sup|wassup|gm)(?:\s+hermes)?[!.?]*$|^(?:what['’]?s up|how are you(?: doing)?|how['’]?s it going|how are things|(?:are )?you (?:there|online|ready)|ready to work|checking in|i['’]?m back|im back|we back|back at it|let['’]?s (?:get started|work|continue))[!.?]*$/i;
const HUMAN_EXPERIENCE = /\b(do you (?:eat|sleep|drive|dream|get tired|have feelings|have a body|have taste buds|like food|have emotions|get mad|get excited)|are you (?:hungry|awake|real|tired|sleepy)|can you (?:taste|smell))\b/i;

export function isGreetingOrCheckIn(message: string): boolean {
  return !DOMAIN_TERMS.test(message) && GREETING_OR_CHECK_IN.test(message.trim());
}
export function isHumanExperienceQuestion(message: string): boolean { return HUMAN_EXPERIENCE.test(message); }

export function isCasualCommonQuestion(message: string): boolean {
  if (/\bfavou?rite vehicle car\b/i.test(message)) return false;
  return isHumanExperienceQuestion(message) || isGreetingOrCheckIn(message) || (!DOMAIN_TERMS.test(message) && /\b(favou?rite|do you like|what do you like|tell me (?:a )?joke|are you (?:bored|happy)|what colou?r is the sky|how did you sleep|what kind of music|ice cream|movie|pizza)\b/i.test(message));
}

export function isProductEntityAdvisorQuestion(message: string): boolean {
  return /\b(?:tesla\s+)?model\s+(?:3|s|x|y)\b|\b(?:car|vehicle|phone|laptop|product) model\b|\bfavou?rite vehicle car\b/i.test(message) || /\bwhat do you th(?:ink|ing) about\b/i.test(message) && !/\b(?:ai|gpt|llm|openrouter|reasoning) model\b/i.test(message) || /\bshould i buy (?:the )?tesla\b/i.test(message);
}

export function isNexusBuildPlanningQuestion(message: string): boolean {
  return /\b(?:can (?:you|we)|could (?:you|we)|what would it take to|how should we)\b.*\b(?:build|make|design|add)\b.*\b(?:crm|client portal|dashboard|workflow|feature|nexus)\b|\b(?:build|design) (?:a |the )?(?:crm|client portal|dashboard|workflow) for nexus\b/i.test(message);
}

export function isGeneralProjectPlanningQuestion(message: string): boolean {
  return /\b(?:can (?:you|we)|could (?:you|we)|what would it take to)\b.*\b(?:build|plan|start|write|create)\b.*\b(?:house|home|app|website|book|trip|course|brand|business|project)\b/i.test(message);
}

export function answerGeneralProjectPlanningQuestion(message: string): string {
  const lower = message.toLowerCase();
  if (/\b(?:house|home)\b/.test(lower)) return 'I cannot physically build a house, but I can help you plan one. The major pieces are budget, land/location, financing, permits, design, builder/contractor, timeline, inspections, and a contingency fund. If you mean whether building is smarter than buying, compare total cost, financing, timeline, and risk first. Current local prices, laws, and permit requirements would require current local research.';
  if (/\bapp\b/.test(lower)) return 'I can help plan an app: define the user, core problem, smallest useful workflow, data model, interface, security boundaries, delivery phases, and validation plan. I have not created code or files. Start with the single workflow the first version must prove.';
  return 'I cannot perform the physical or external work, but I can help plan the project. Start with the outcome, budget, constraints, required people or tools, milestones, risks, and the smallest first step. Current prices, laws, or local requirements would need current research.';
}

export function isGeneralAdvisorQuestion(message: string): boolean {
  return !DOMAIN_TERMS.test(message) && /\b(what (?:would|do) you recommend for me|what (?:car|laptop|phone) (?:would you|do you) recommend(?: for me)?|what should i (?:buy|get|choose|eat)|which is best for me|help me pick|what (?:car|laptop|phone) should i (?:get|buy))\b/i.test(message);
}

export function answerCasualCommonQuestion({ message }: { message: string; routeDecision: RouteDecision; contextPacket: unknown }): string {
  const lower = message.toLowerCase().replace(/\bgo;od\b/g, 'good');
  if (/\bgood night\b|^night[!.?]*$/.test(lower.trim())) return 'Good night, Ray. Rest up — we made strong progress on Hermes today.';
  if (/\bdo you eat\b|\bare you hungry\b|\bdo you have a body\b/.test(lower)) return 'I do not eat or have a body, but I can still help with food ideas, nutrition tradeoffs, restaurants, or meal planning.';
  if (/\bdo you sleep\b|\bare you (?:tired|sleepy|awake)\b|\bdo you dream\b/.test(lower)) return 'I do not sleep, but I’m here and ready when you are.';
  if (/\b(?:feelings|emotions|get mad|get excited)\b/.test(lower)) return 'I do not have feelings the way a person does, but I can still respond with judgment, tone, and priorities based on what you are trying to accomplish.';
  if (/\b(?:taste buds|can you taste|can you smell|do you like food)\b/.test(lower)) return 'I do not have senses or a body, but I can still reason about flavor, food choices, and meal planning.';
  if (/\bdo you drive\b/.test(lower)) return 'I do not drive or have a body, but I can help compare vehicles, ownership costs, and practical tradeoffs.';
  if (/\bare you real\b/.test(lower)) return 'I’m real as software, not as a person with a body or lived experiences.';
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
  const lower = message.toLowerCase().replace(/\b(favou?rite|recommend(?:ed|ation)?)\s+care\b/i, '$1 car');
  if (/\b(?:tesla\s+)?model\s+(?:3|y)\b/.test(lower)) return `The Tesla ${/model y/.test(lower) ? 'Model Y' : 'Model 3'} can be a strong option if you have reliable charging, want lower fuel costs, and like the EV/tech image. Compare insurance, payment, charging access, battery warranty, and total monthly cost. If your priority is lowest-risk reliability, compare it with a Camry, Accord, RAV4, or Lexus ES.`;
  if (/\bcar\b/.test(lower)) return 'My default recommendation is something reliable, low-maintenance, and professional-looking. Start with a Toyota Camry, Honda Accord, Toyota RAV4, or Lexus ES. Best all-around value: Camry. Comfort and business image: Lexus ES. Utility: RAV4. What is your budget, new/used preference, and primary use?';
  if (/\blaptop\b/.test(lower)) return 'My safe default is a MacBook Air for battery life and low maintenance, or a business-class ThinkPad if you need Windows. For heavier development or video work, step up to a MacBook Pro or a higher-spec ThinkPad. What is your budget and your heaviest workload?';
  if (/\bphone\b/.test(lower)) return 'My default shortlist is an iPhone for the simplest long-term ownership, a Pixel for clean Android, or a Samsung Galaxy if you value display and multitasking. Which ecosystem are you already using, and what is your budget?';
  if (/\b(eat|food|dinner)\b/.test(lower)) return 'For a dependable dinner, I’d choose a rice or grain bowl with a protein, vegetables, and a sauce you like. It is fast, flexible, and easy to keep balanced. Any dietary limits or ingredients you need to use?';
  return 'I can make a provisional recommendation, but the best choice depends on your budget, constraints, and what outcome matters most. Give me those three and I’ll narrow it to one option.';
}
