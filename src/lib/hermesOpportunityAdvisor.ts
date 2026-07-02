import type { RouteDecision } from './hermesRouteDecision';

export type OpportunityAnswerMode = 'personal' | 'business' | 'both';

const PHYSICAL_TASK = /\bcan you (?:physically )?(?:fix|repair|diagnose|troubleshoot|install|paint|clean|cook|replace)\b/i;
const VALUE_QUESTION = /\b(?:is it (?:better|easier) to|should i (?:repair|fix|replace)|which is better|is this worth it|what would you do|what do you recommend|could i be a middleman|can (?:this|i) (?:be a business|make money)|how can (?:this|i) make money|low[- ]cost way to test|affiliate|referral|lead[- ]?gen)\b/i;

export function isPhysicalWorldAdvisoryQuestion(message: string): boolean { return PHYSICAL_TASK.test(message); }

export function isOpportunityAwareRecommendationQuestion(message: string): boolean {
  if (/\bwhat business opportunities are available\b|\b(?:supabase|database|live records?)\b/i.test(message)) return false;
  return PHYSICAL_TASK.test(message) || VALUE_QUESTION.test(message);
}

export function classifyOpportunityAnswerMode(message: string): OpportunityAnswerMode {
  const business = /\b(business|money|middleman|affiliate|referral|lead[- ]?gen|sell(?:ing)? leads?|monetiz|income)\b/i.test(message);
  const decision = /\b(better|easier|repair|fix|replace|buy|worth|recommend|my )\b/i.test(message);
  return business && decision ? 'both' : business ? 'business' : /\b(toilet|car|phone|sink|appliance|roof|camera|room|garage)\b/i.test(message) ? 'both' : 'personal';
}

export interface OpportunityAdvisorResult {
  text: string;
  mode: OpportunityAnswerMode;
  topic: string;
  assumptions: string[];
  recommendation: string;
  risks: string[];
}

export function answerOpportunityAwareRecommendation({ message, routeDecision }: { message: string; routeDecision: RouteDecision; contextPacket: unknown }): OpportunityAdvisorResult {
  if (routeDecision.retrievalPolicy !== 'none') throw new Error('Opportunity advisor is local-first and must not receive a retrieval route');
  const lower = message.toLowerCase();
  const mode = classifyOpportunityAnswerMode(message);

  if (/\btoilet\b/.test(lower)) return {
    mode, topic: 'toilet repair-versus-replace opportunity',
    assumptions: ['validate organic demand', 'use licensed local partners', 'avoid inventory and paid ads initially'],
    recommendation: 'test a repair-versus-replace lead-gen/referral page before offering hands-on service.',
    risks: ['local licensing and insurance requirements', 'plumbing safety and liability', 'lead quality', 'installer dependency', 'customer trust'],
    text: `**Direct answer:** Fixing is usually easier and cheaper when the problem is a flapper, fill valve, chain, handle, weak flush, or minor leak. Replacement makes more sense for a cracked bowl or tank, recurring clogs, severe wear, or when a qualified repair estimate approaches replacement value. Current local prices require local research.\n\n**Business opportunity:** Do not start by becoming the plumber. Test a middleman model: a repair-or-replace landing page, quote intake form, licensed plumber/install partners, affiliate parts links, and a simple decision calculator.\n\n**Free or low-cost test:**\n1. Publish a one-page checklist and intake form.\n2. Call 5–10 local plumbers and ask whether they accept qualified leads.\n3. Add relevant affiliate parts or product links where permitted.\n4. Publish local SEO content and validate inquiries manually before buying ads.\n\n**Risk check:** Hands-on plumbing may require licensing, permits, insurance, and safety controls depending on location. Referral disclosure, lead quality, partner fulfillment, and customer trust also matter.\n\n**My recommendation:** Test lead-gen/referral first. It is cheaper, safer, and faster to validate than hands-on plumbing or inventory.`
  };

  if (/\bcar\b/.test(lower)) return {
    mode, topic: 'vehicle troubleshooting and referral opportunity',
    assumptions: ['collect complete symptom details', 'limit advice to safe checks', 'use qualified mechanics for repairs'],
    recommendation: 'collect the year, make, model, symptoms, warning lights, sounds, timing, and recent repairs before deciding the next safe diagnostic step.',
    risks: ['physical safety', 'repair liability', 'misdiagnosis', 'lead quality', 'mechanic partner dependency'],
    text: `I cannot physically fix the car, but I can help troubleshoot it. Tell me the year, make, model, symptoms, warning lights, sounds, when it happens, and recent repairs. I can help narrow likely categories, suggest safe observations, and identify when it is mechanic-level. Do not drive a vehicle with braking, steering, overheating, fuel-smell, smoke, or severe warning symptoms.\n\n**Opportunity angle:** A safer business test is diagnostic content, repair-quote comparison, mechanic referral leads, maintenance reminders, or clearly disclosed affiliate parts/tools content—not hands-on repair.\n\n**Low-cost test:** Interview five mechanics, build a symptom intake form, manually match a few qualified leads, and measure response and conversion before spending on ads.\n\n**Risk check:** Hands-on repair carries skill, safety, insurance, and liability risk. My recommendation is information/referral validation first.`
  };

  if (/\bphone\b/.test(lower)) return {
    mode, topic: 'phone repair and referral opportunity',
    assumptions: ['protect customer data', 'diagnose before parts purchase', 'use qualified repair partners'],
    recommendation: 'start with symptoms, device model, damage history, backup status, and warranty status; test referral or quote comparison before repair inventory.',
    risks: ['battery and electrical safety', 'customer-data exposure', 'parts quality', 'warranty impact', 'refunds'],
    text: `I cannot physically repair the phone, but I can help troubleshoot and plan the next step. Tell me the model, symptoms, damage or liquid exposure, charging behavior, backup status, and warranty status. Swollen, hot, smoking, or damaged batteries require immediate professional handling.\n\n**Opportunity angle:** Test repair quote comparison, local technician referrals, accessory/parts content, or device-care lead generation before buying parts or equipment.\n\n**Low-cost test:** Create a diagnostic intake form, contact five repair shops, manually refer qualified inquiries, and validate demand.\n\n**Risk check:** Battery safety, data privacy, warranty impact, parts quality, fulfillment, and refunds must be controlled.`
  };

  if (/\b(?:sink|plumb|roof|camera|appliance)\b/.test(lower) || PHYSICAL_TASK.test(message)) return {
    mode, topic: 'physical-service planning and referral opportunity',
    assumptions: ['diagnose safely', 'use qualified providers', 'test referrals before equipment or inventory'],
    recommendation: 'collect symptoms and photos, identify urgent hazards, and compare DIY-safe checks with a qualified professional quote.',
    risks: ['licensing or permitting', 'insurance and liability', 'physical safety', 'partner fulfillment', 'customer trust'],
    text: `I cannot perform the physical work, but I can help diagnose the situation, build a checklist, compare repair versus replacement, prepare technician questions, and decide whether it is DIY-safe or professional-level. Stop and use a qualified professional for electrical hazards, gas, structural damage, active flooding, roof work, or other safety-critical conditions.\n\n**Opportunity angle:** The safer first model is a diagnostic guide, quote comparison, qualified-provider referral, or disclosed affiliate content—not regulated hands-on work.\n\n**Low-cost test:** Build a one-page intake form, interview 5–10 local providers, manually route a few leads, and validate organic demand before ads or equipment.\n\n**Risk check:** Verify local licensing, permitting, insurance, and referral-disclosure requirements through current local research.`
  };

  return {
    mode, topic: 'general opportunity recommendation',
    assumptions: ['validate demand manually', 'avoid fixed costs initially', 'use qualified fulfillment partners'],
    recommendation: 'test the smallest manual landing-page, intake, referral, or affiliate version before spending on ads, inventory, staff, or equipment.',
    risks: ['demand uncertainty', 'low margins', 'lead quality', 'partner dependency', 'customer trust', 'refunds'],
    text: `**Direct answer:** Start with the option that solves the problem with the lowest irreversible cost and clearest evidence. Compare outcome, time, total cost, reversibility, and risk.\n\n**Opportunity angle:** If people repeatedly face this decision, test a guide, calculator, quote-comparison intake, referral partnership, affiliate content, or qualified-lead service.\n\n**Free or low-cost test:** Create one page and a no-code form, interview 5–10 customers/providers, fulfill manually, publish useful organic content, and measure inquiries before ads or inventory.\n\n**Risk check:** Check licensing, liability, fulfillment complexity, margins, lead quality, competition, partner dependency, and refund exposure. Current prices and local rules require current research.\n\n**My recommendation:** Validate demand and partner fulfillment manually before committing money.`
  };
}
