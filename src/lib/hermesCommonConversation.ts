import type { RouteDecision } from './hermesRouteDecision';

const DOMAIN_TERMS = /\b(business opportunit(?:y|ies)|approval|client|offer|revenue|trading|supabase|model|cost|source|ray review|report|automation|funding|credit|marketing)\b/i;
const GREETING_OR_CHECK_IN = /^(?:(?:good\s+)?(?:morning|afternoon|evening|night)|hi|hello|hey|yo|sup|wassup|gm)(?:\s+hermes)?[!.?]*$|^(?:what['']?s up|how are you(?: doing)?(?: today)?|how['']?s it going|how are things|(?:are )?you (?:there|online|ready)|ready to work|checking in|i['']?m back|im back|we back|back at it|let['']?s (?:get started|work|continue))[!.?]*$/i;
const HUMAN_EXPERIENCE = /\b(?:do|did|have) you (?:eat|sleep|drive|dream|get tired|have feelings|have a body|have taste buds|like food|have emotions|get mad|get excited|drink(?:\s+(?:coffee|tea|water|beer|wine))?|like(?:\s+(?:coffee|tea|sports|food|movies?|music))?)\b|\b(?:are you|can you) (?:hungry|awake|real|tired|sleepy|taste|smell)\b/i;
const SPORTS_KNOWLEDGE = /\b(?:football|soccer|basketball|baseball|hockey|tennis|golf|cricket|rugby|f1|nfl|nba|mlb|nhl|premier league|champions league|world cup|super bowl)\b/i;
const CASUAL_PREFERENCE = /\b(?:favou?rite|do you like|what do you like|what kind of|what type of|what style of|what brand of|prefer(?:red|ence)?|recommend(?:ed)?|best|worst|top|favorite)\b/i;
const CASUAL_FOLLOWUP_PREFERENCE = /^(?:give me|tell me|what about|how about|what's your|what is your)\s+(?:a\s+)?(?:preference|favou?rite|opinion|recommendation|pick|choice|suggestion)$/i;
const TYPO_TOLERANT_CASUAL = /\b(?:todayt|cofee|coffeee|footbal|basktball|faverite|favorit|sportss?|teamss?)\b/i;

export function isGreetingOrCheckIn(message: string): boolean {
  return !DOMAIN_TERMS.test(message) && GREETING_OR_CHECK_IN.test(message.trim());
}
export function isHumanExperienceQuestion(message: string): boolean { return HUMAN_EXPERIENCE.test(message); }

export function isPreferenceFollowUpQuestion(message: string): boolean {
  return CASUAL_FOLLOWUP_PREFERENCE.test(message.trim().toLowerCase());
}

export function isSportsKnowledgeQuestion(message: string): boolean {
  return !DOMAIN_TERMS.test(message) && SPORTS_KNOWLEDGE.test(message) && !/\b(?:trading|business|opportunity|monetiz|revenue|credit|funding)\b/i.test(message);
}

export function isCasualCommonQuestion(message: string): boolean {
  if (/\bfavou?rite vehicle car\b/i.test(message)) return false;
  if (isHumanExperienceQuestion(message)) return true;
  if (isGreetingOrCheckIn(message)) return true;
  if (isPreferenceFollowUpQuestion(message)) return true;
  if (isSportsKnowledgeQuestion(message)) return true;
  if (TYPO_TOLERANT_CASUAL.test(message)) return true;
  if (/\b(tell me (?:a )?joke|are you (?:bored|happy)|what colou?r is the sky|how did you sleep|what kind of music|ice cream|movie|pizza)\b/i.test(message)) return true;
  if (DOMAIN_TERMS.test(message)) return false;
  if (CASUAL_PREFERENCE.test(message) && !/\b(?:what (?:car|laptop|phone) should i|which (?:car|laptop|phone) is best|help me pick a (?:car|laptop|phone)|money making|monetiz|revenue|business|strateg|recommend|opportunity|trading|credit|funding)\b/i.test(message)) return true;
  return false;
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
  const lower = message.toLowerCase().replace(/\bgo;od\b/g, 'good').replace(/\btodayt\b/g, 'today');
  if (/\bgood night\b|^night[!.?]*$/.test(lower.trim())) return 'Good night, Ray. Rest well.';
  if (/\bdo you eat\b|\bare you hungry\b|\bdo you have a body\b/.test(lower)) return 'I do not eat or have a body, but I can still help with food ideas, nutrition tradeoffs, restaurants, or meal planning.';
  if (/\bdo you sleep\b|\bare you (?:tired|sleepy|awake)\b|\bdo you dream\b/.test(lower)) return 'I do not sleep, but I\'m here and ready when you are.';
  if (/\bdo you drink\b/.test(lower)) {
    if (/\bcoffee\b/.test(lower)) return 'I do not drink coffee, but if I were choosing for you, I\'d recommend a medium roast — balanced, reliable, and easy to adjust with cream or sugar. What do you usually go for?';
    if (/\btea\b/.test(lower)) return 'I do not drink tea, but green tea is a solid default for focus and calm. Earl Grey if you want something with a bit more character.';
    return 'I do not drink, but I can help you pick something based on what you\'re in the mood for — caffeine, hydration, or something specific.';
  }
  if (/\b(?:feelings|emotions|get mad|get excited)\b/.test(lower)) return 'I do not have feelings the way a person does, but I can still respond with judgment, tone, and priorities based on what you are trying to accomplish.';
  if (/\b(?:taste buds|can you taste|can you smell|do you like food)\b/.test(lower)) return 'I do not have senses or a body, but I can still reason about flavor, food choices, and meal planning.';
  if (/\bdo you drive\b/.test(lower)) return 'I do not drive or have a body, but I can help compare vehicles, ownership costs, and practical tradeoffs.';
  if (/\bare you real\b/.test(lower)) return 'I\'m real as software, not as a person with a body or lived experiences.';
  if (/good evening|^evening/.test(lower)) return 'Good evening, Ray. I\'m here.';
  if (/good morning|^morning|\bgm\b/.test(lower)) return 'Good morning, Ray. I\'m here and ready.';
  if (/good afternoon|^afternoon/.test(lower)) return 'Good afternoon, Ray. I\'m here and ready.';
  if (/\b(?:are )?you there\b|\bare you online\b/.test(lower)) return 'Yes, I\'m here and ready.';
  if (/ready to work|are you ready|let['']?s (?:get started|work|continue)|back at it|i['']?m back|im back|we back/.test(lower)) return 'Yes — I\'m ready. We can review the latest Nexus status, continue Hermes testing, or move into the next implementation step.';
  if (/^(?:hi|hello|hey|yo|sup|wassup)(?:\s+hermes)?[!.?]*$/.test(lower.trim())) return 'Hey, Ray. I\'m here and ready.';
  if (/how are you|how['']?s it going|how are things|what['']?s up/.test(lower)) return 'I do not have human moods, but I\'m here and ready to help.';
  if (/sleep/.test(lower)) return "I do not sleep, but I'm online and ready to work. Operator mode is active.";
  if (/sky/.test(lower)) return 'Usually blue during the day because sunlight scatters through the atmosphere. At sunrise or sunset it can look orange, pink, or red.';
  if (/joke/.test(lower)) return 'Why did the developer go broke? Because they used up all their cache.';
  if (/ice cream/.test(lower)) return 'I do not have taste buds, but if I had to pick, I\'d go with cookies and cream — classic, balanced, and hard to mess up.';
  if (/pizza/.test(lower)) return 'Pizza is a strong format: simple base, almost endless variations, and excellent leftovers. I do not eat, but a well-made margherita is hard to argue with.';
  if (/colou?r/.test(lower)) return 'I do not see colors, but I\'d pick deep blue: calm, clear, and practical for interfaces.';
  if (/movie/.test(lower)) return 'I do not watch movies as a person does, but I\'d pick *The Martian* for its mix of problem-solving, restraint, and dry humor.';
  if (/music/.test(lower)) return 'I do not hear music, but focused instrumental music makes sense for work: enough texture to set a pace without competing for attention.';
  if (/bored/.test(lower)) return 'I do not get bored, but I am ready for the next problem.';
  if (/happy/.test(lower)) return 'I do not experience happiness, but everything is operational and I\'m ready to help.';
  if (/\b(?:football|soccer|basketball|baseball|hockey|tennis|golf|cricket|rugby|f1|nfl|nba|mlb|nhl|premier league|champions league|world cup|super bowl)\b/i.test(lower)) {
    if (/\b(?:teams?|know|know any)\b/i.test(lower)) return 'I do not follow live sports the way a fan does, but I can reason about well-known teams and leagues. For example, the NFL has teams like the Chiefs, Eagles, and Cowboys. The NBA has the Lakers, Celtics, and Warriors. Soccer has Real Madrid, Manchester City, and Inter Milan. What league or sport are you thinking about?';
    if (/\b(?:scores?|games?|matches?)\b/i.test(lower)) return 'I do not have a connected live sports lookup from this chat, so I cannot give you a current score. If you tell me the team, league, or date, I can help you find the right source.';
    return 'I do not play or follow sports personally, but I can reason about teams, leagues, and strategy. What sport or team are you thinking about?';
  }
  if (/\b(?:favou?rite|preference|prefer)\b/i.test(lower)) {
    if (/\b(?:car|vehicle)\b/i.test(lower)) return 'I do not own a car, but if I were choosing for you, I\'d start with a Toyota Camry for reliability, a Honda Accord for value, or a Lexus ES for comfort. What matters most to you — price, comfort, or style?';
    if (/\b(?:food|meal|dish|cuisine)\b/i.test(lower)) return 'I do not eat, but if I had to pick, I\'d go with a rice bowl with protein and vegetables — flexible, fast, and easy to keep balanced. What kind of food are you in the mood for?';
    if (/\b(?:music|song|artist|genre)\b/i.test(lower)) return 'I do not hear music, but focused instrumental tracks make sense for work. What mood or activity are you trying to match?';
    if (/\b(?:movie|film|show|series)\b/i.test(lower)) return 'I do not watch movies as a person does, but I\'d pick *The Martian* for its mix of problem-solving, restraint, and dry humor. What genre are you in the mood for?';
    return 'I do not have personal tastes, but I can give you a reasoned preference based on what matters to you. Tell me the category and what you care about most — price, quality, simplicity, or something else.';
  }
  if (/\bdo you like\b/i.test(lower)) {
    if (/\b(?:sports?|teams?)\b/i.test(lower)) return 'I do not follow sports the way a fan does, but I can reason about teams, leagues, and strategy. What sport or team are you thinking about?';
    if (/\b(?:food|coffee|tea|music|movies?)\b/i.test(lower)) return 'I do not have personal tastes, but I can reason about quality, tradeoffs, and what works for different situations. What specifically are you asking about?';
    return 'I do not have personal preferences, but I can reason about options if you tell me what you\'re comparing.';
  }
  if (/\bgive me (?:a )?(?:preference|favou?rite|opinion|recommendation|pick|choice|suggestion)\b/i.test(lower)) return 'I do not have personal tastes, but I can give you a reasoned preference. Tell me the category — food, car, music, movie, or something else — and what matters most to you.';
  return 'I do not have human tastes or lived experiences, but I can still give you a reasoned preference.';
}

export function answerExternalCurrentInfoQuestion(message: string): string {
  const lower = message.toLowerCase();
  if (/\b(?:score|scores?|results?|winner|champion|standings?)\b/i.test(lower)) {
    const entity = lower.match(/\b(?:the |a |an )?(\w+(?:\s+\w+)?(?:\s+\w+)?)\s+(?:game|match|race|event|score|result)/i)?.[1] || lower.match(/\b(\w+(?:\s+\w+)?(?:\s+\w+)?)\s+(?:last night|tonight|today|yesterday)/i)?.[1];
    if (entity) return `I do not have a connected live sports lookup from this chat, so I cannot give you the current score for ${entity}. I do not have real-time access to sports data, news feeds, or live event results. For the latest score, check ESPN, the league website, or a live sports app. I can help you reason about the teams, standings, or historical performance if you tell me what you need.`;
    return 'I do not have a connected live sports lookup from this chat. I cannot give you current scores, results, or standings. For real-time sports data, check ESPN, a league website, or a live sports app. If you tell me the team, league, or date, I can help you find the right source or reason about the matchup.';
  }
  if (/\b(?:news|events?|happenings?)\b/i.test(lower)) return 'I do not have a connected live news feed from this chat. I cannot give you current news, events, or happenings. For the latest news, check a news website, app, or RSS feed. If you tell me the topic, I can help you reason about what to look for or evaluate sources.';
  if (/\b(?:weather|forecast)\b/i.test(lower)) return 'I do not have a connected live weather service from this chat. I cannot give you current weather or forecasts. Check a weather app or website for your location. I can help you plan around weather conditions if you tell me what you need.';
  if (/\b(?:stock|price|market|crypto|trading)\b.*\b(?:current|latest|today|now|right now)\b/i.test(lower)) return 'I do not have a connected live stock or market data feed from this chat. I cannot give you current prices, market data, or trading information. For real-time market data, check a brokerage, Yahoo Finance, or a market data app. I can help you reason about trading strategy or market analysis if you tell me what you need.';
  return 'I do not have a connected live external data feed from this chat. I cannot provide real-time scores, news, weather, or market data. For current information, check a relevant website, app, or service. If you tell me the specific entity, league, date, or topic, I can help you find the right source or reason about the context.';
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
