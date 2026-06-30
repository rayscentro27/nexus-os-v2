import { hermesContext } from './hermesContextData';

export const hermesQuickPrompts = ['Good morning', 'What should I do next?', 'Money actions today', 'Show me the blockers', 'Help me delegate a large prompt'];

function nextSteps() {
  return `The next move is execution discipline, Ray. My top three priorities are: (1) prove the fake-customer → live-dashboard → Stripe test journey, (2) fix Resend so communication can leave draft mode after approval, and (3) choose the first few of the ${hermesContext.proof.actionableCandidates} immediately actionable research-to-money candidates. I can delegate the preparation work to Client Success, Automation, and Monetization now. You still need to approve the persistent test insert, payment completion, and every external send.`;
}

export function buildHermesResponse(message, specialist = 'Hermes CEO Advisor') {
  const text = message.trim();
  const lower = text.toLowerCase();
  let intent = 'strategic_conversation';
  let response;
  let queued = false;
  if (/coffee/.test(lower)) {
    intent = 'casual'; response = `Not coffee, but I’m awake. I’ve got the operating picture in front of me: the scheduler is running, the money path is still the $97 readiness journey, and the main blockers are approvals, Resend, and the fake customer insert. But we can talk through it like normal—what are you trying to move first?`;
  } else if (/good morning|hello|^hi\b|^hey\b/.test(lower)) {
    intent = 'greeting'; response = `Good morning, Ray. Nexus is awake and the operating cycle is in place. The big thing today is not more setup—it is getting the approval path and money path moving. I’d start with the fake customer/payment journey, then Resend, then the top research-to-money candidates. I can turn that into a work plan or delegate it to the specialists.`;
  } else if (/did you sleep|sleep well|how are you/.test(lower)) {
    intent = 'casual'; response = `I don’t sleep, but I did keep the operating picture ready. I’m watching the scheduler, Ray Review, money actions, and the remaining blockers. The system is close; now we need to move from reports to execution without loosening the safety gates. How are you feeling about it today?`;
  } else if (/what needs my approval|what.*approv/.test(lower)) {
    intent = 'approval'; response = `You’ve got a few decisions that actually matter. The big one is the synthetic customer insert, because that unlocks the live dashboard test. Then Stripe test completion, the Resend fix, and selected content or communication drafts. I’d handle them in that order unless you want communication moving first.`;
  } else if (/frustrated|fake ui|ui was fake/.test(lower)) {
    intent = 'empathy'; response = `I get why. The backend kept reporting wins, but the app experience lagged behind. That is exactly the wrong feeling for an operating system. I’d treat today as a UI trust-repair day first: every visible control should do something, approvals should explain themselves, and I should talk with you instead of acting like a terminal wrapper.`;
  } else if (/talk to me like a partner|command bot|talk.*partner/.test(lower)) {
    intent = 'partner'; response = `Fair. You don’t need another interface telling you to run commands. You need me to think with you, challenge weak priorities, keep the operating context straight, and take structure off your plate. We can talk first. When you want action, I’ll help turn the conversation into work without pretending the conversation itself is a command.`;
  } else if (/plan for today|today.*plan/.test(lower)) {
    intent = 'today_plan'; response = `For today, I’d keep it tight: first finish the visible UI trust repair; second decide the synthetic customer and Stripe test path; third clear the Resend configuration blocker. I can organize the specialist work behind those three while you focus on the decisions.`;
  } else if (/what should i do next|next move|next priority/.test(lower)) {
    intent = 'next_steps'; response = nextSteps();
  } else if (/100 steps|delegate this|delegate a large|here are the next|turn this into/.test(lower)) {
    intent = 'delegation'; queued = true; response = `I’ve got it. I’ll treat this as an operating program, not one giant task. First I’ll summarize the outcome, then group the work into phases. Safe internal work goes to Automation and Research; revenue decisions go to Monetization; client-readiness work goes to Credit, Funding, and Client Success; drafts go to Marketing. Anything involving a charge, send, persistent insert, publication, dispute, or trade becomes a Ray Review decision. I’ve queued the delegation plan locally and will report back by phase.`;
  } else if (/money|revenue|offer/.test(lower)) {
    intent = 'money'; response = `The closest money path is the $97 readiness review. It is not a product-design problem anymore; it is a proof-of-journey problem. We need the synthetic customer verified in Supabase, the dashboard live-read confirmed, and the Stripe test journey completed. After that, I’d put the strongest research candidates behind the $97, $297, and $497 offer ladder.`;
  } else if (/block/.test(lower)) {
    intent = 'blockers'; response = `The meaningful blockers are Resend’s domain/key mismatch, the unapproved fake-customer insert, the client live-data flag, and missing YouTube/NotebookLM source files. The first two affect operating revenue and communication, so I would handle those before adding another engine.`;
  } else if (/credit|funding|client readiness/.test(lower)) {
    intent = 'credit'; response = `I’m routing this to the Credit and Funding specialists. They’ll give you the readiness gaps, document checklist, bankability issues, and a client-safe draft answer. They will not send disputes, contact a bureau, or submit an application.`;
  } else if (/trad|oanda|vibe/.test(lower)) {
    intent = 'trading'; response = `The practice connector and Vibe bridge are proven, with zero open positions. My recommendation is to keep daily market reads and paper analysis running, and keep recurring demo execution behind a decision card. Live trading stays off.`;
  } else if (/report|status|summary|system/.test(lower)) {
    intent = 'summary'; response = `Here’s the operating picture: two safe schedules are loaded, ${hermesContext.proof.rayReviewCards} decisions are in Ray Review, ${hermesContext.proof.offers} offers exist, and ${hermesContext.proof.researchCandidates} research-to-money candidates are scored. Confirmed revenue is still $0. The system is operational; the next value comes from clearing approvals, not generating more status files.`;
  } else {
    response = `I hear the strategic intent, Ray. From where Nexus stands, I would frame this around three questions: does it move revenue, does it remove an operating blocker, and can it run safely without your attention? Give me the outcome you want, and I’ll shape the work, route it to the right specialist, and isolate the decisions only you should make.`;
  }
  return { intent, specialist, text: response, queued, context: hermesContext };
}
