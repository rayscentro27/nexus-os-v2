import { hermesContext } from './hermesContextData';
import { getPageContext } from './hermesPageContext';

export const hermesQuickPrompts = [
  'What should I do next?',
  'What strategy do you have today?',
  'Tell me about the synthetic customer insert',
  'How do I approve anything in the research engine?',
  'Give me your opinion on what we should monetize first',
  'Show me the blockers'
];

/* ── Nexus topic knowledge base ── */
const nexusTopics = {
  'synthetic customer': {
    topic: 'Synthetic Customer Insert',
    explain: `The synthetic customer insert is how we prove the full $97 readiness journey end-to-end without touching a real person's data. Right now we have a test package ready—Stripe test Checkout session created, test PaymentIntent on file, onboarding records staged—but nothing has been written to Supabase yet.`,
    why: `It matters because it unlocks the live dashboard test. Once the fake customer is in the database, we can flip the frontend live-data flag and confirm that /client/dashboard actually reads real rows instead of static fallback content. That's the difference between "the backend says it works" and "you can see it working."`,
    approval: `Approving the insert means: (1) the synthetic record goes into Supabase with RLS intact, (2) the dashboard flag flips on, (3) we verify the read path, and (4) the rollback packet is ready if we need to undo it. No real client PII is involved. No real charges happen.`,
    cleanup: `There's a rollback transaction script ready. If anything looks wrong after insert, we can revert the database state cleanly.`,
    next: `To move forward, you'd approve the insert via Ray Review. The card is already queued.`
  },
  'research engine': {
    topic: 'Research Engine',
    explain: `The Research Engine has 50 scored candidates across 18 operating lanes—credit readiness, payment monetization, grants, marketing/SEO, Oanda demo data, Vibe paper strategies, YouTube metadata, and NotebookLM exports. 26 of those are immediately actionable.`,
    approval: `Approval in the Research Engine works through Ray Review cards. Each candidate has a score, a lane assignment, and a recommended next action. You approve to convert a candidate into an opportunity, a content draft, or an automation task. You hold if it needs more research. You reject if the signal is too weak. Nothing executes without your decision.`,
    howToApprove: `Go to Research Engine in the sidebar. Click any candidate row. The detail drawer opens with score, lane, source, and status. At the bottom you'll see approve/hold/reject buttons plus "Convert to opportunity" and "Send to Hermes." The approve button creates a local receipt—it doesn't send anything external.`,
    next: `The Research Engine is live in the sidebar. Try clicking a candidate row to see the detail drawer.`
  },
  'monetization': {
    topic: 'Monetization',
    explain: `We have 9 offers registered, from the $97 Credit & Funding Readiness Review up through the $497 Funding Prep Sprint. The offer ladder is: $97 entry, $297 assisted plan, $497 higher-touch sprint, plus monthly subscriptions, affiliate pathways, and funding referral commissions.`,
    opinion: `My recommendation on what to monetize first: the $97 Readiness Review. Here's why: (1) it's the most complete offer—we have the pricing, the partner list, and the compliance review done, (2) it proves the entire payment-to-delivery journey, (3) it has the lowest risk since it's a one-time test charge, and (4) everything else in the ladder builds on proving this one works. After $97, I'd move to the $297 assisted plan because it recycles the same readiness framework with more hands-on work.`,
    next: `To move forward: approve the $97 offer in Monetization, approve the Stripe test Checkout completion, and approve the first landing page draft. Those three decisions unlock the revenue proof path.`
  },
  'stripe': {
    topic: 'Stripe Integration',
    explain: `Stripe is in test mode. We have a test Checkout session created and a test PaymentIntent on file, but neither has been completed. The webhook endpoint is verified at the signature level but the listener isn't running yet.`,
    safety: `No live charges are possible in the current configuration. Test mode only. The Stripe secret key is in the env but the app uses test-mode fixtures exclusively.`,
    next: `The next step is approving the webhook listener startup and completing the test Checkout with a test payment method. Both are Ray Review decisions.`
  },
  'resend': {
    topic: 'Resend Email',
    explain: `Resend is connected but blocked. The issue is a domain/key scope mismatch—the API key has read-only permissions and the sender domain hasn't been verified. That means no emails can actually leave the system.`,
    safety: `This is safe because it's broken in the right direction: it can't send even if we wanted it to. Once the key is re-scoped and the domain is verified, every send still requires Ray approval.`,
    next: `Fixing Resend means: (1) generate a new API key with send permissions, (2) verify the sender domain in Resend's dashboard, (3) approve the first onboarding email send via Ray Review.`
  },
  'approval': {
    topic: 'Approval System',
    explain: `Every risky action in Nexus goes through Ray Review. The flow is: Hermes or a specialist proposes a task, a Ray Review card is created, you see the card with context and a recommendation, you approve/reject/hold, and a receipt is generated. The receipt records what happened but the underlying action only executes if you approved it.`,
    safety: `Approvals are the safety gate. Nothing external happens without one. Even internal actions that affect data state get an approval card. The receipts are append-only and include the decision, timestamp, and next step.`,
    next: `You can see all pending approvals in Ray Review. There are currently ${hermesContext.proof.rayReviewCards} cards waiting.`
  },
  'credit': {
    topic: 'Credit & Funding',
    explain: `Credit readiness is tracked through a scoring system that evaluates profile completeness, document status, and funding eligibility. Right now the SmartCredit connector isn't configured, so scores are generated from report analysis only—no live credit pulls.`,
    specialist: `I'd route detailed credit questions to the Credit Specialist. They can walk through readiness gaps, document checklists, bankability issues, and draft dispute letters. They will NOT send disputes, contact bureaus, or submit applications without your explicit approval.`,
    next: `Open Credit & Funding in the sidebar to see the readiness pipeline, document checklist, and dispute draft queue.`
  },
  'client': {
    topic: 'Client Management',
    explain: `We have zero live client profiles. The system is designed for a synthetic test customer flow: insert a fake customer, verify the dashboard reads the data, complete the Stripe test journey, then clean up. Real client onboarding would go through a 5-stage pipeline: Signup → Credit Report → Business Setup → Document Prep → Funding Ready.`,
    safety: `No real client PII has been entered. The synthetic customer is a test fixture. Real client data would be stored in Supabase with RLS policies and Hermes would only see internal summaries—never raw PII.`,
    next: `Open Clients in the sidebar to see the workflow pipeline and the synthetic customer status.`
  },
  'opportunity': {
    topic: 'Business Opportunities',
    explain: `There are 26 immediately actionable research-to-money opportunities scored and ranked. They span credit offer building, SaaS ideas, lead-gen funnels, AI tooling services, SEO offers, and funding readiness packages.`,
    howToApprove: `Each opportunity has a score, a revenue potential range, and a confidence rating. You can approve to convert it into a content draft, a Ray Review card, or a specialist task. Hold if it needs more validation. Reject if the signal is too weak.`,
    next: `Open Business Opportunities in the sidebar. Click any opportunity card to see the full detail drawer with score, reasoning, and action buttons.`
  },
  'marketing': {
    topic: 'Marketing Drafts',
    explain: `We have 5 social post drafts, 5 video scripts, 1 newsletter draft, 3 landing page experiments, and a lead magnet outline. All are draft-only—nothing has been published or sent.`,
    safety: `Publishing is completely blocked. Every draft requires Ray approval before it could even be considered for publishing, and the social connector is in publish-disabled mode.`,
    next: `Open Marketing Drafts in the sidebar. Click any draft to see the content, approve/hold/reject it, or ask the Marketing Specialist for feedback.`
  },
  'strategy': {
    topic: 'Strategy',
    explain: `Today's strategic priorities, from where I sit: (1) Prove the money path—the $97 journey from synthetic customer through Stripe test to dashboard verification. This is the single most important thing because it converts "the system works" from a claim into proof. (2) Clear the communication gate—fix Resend so we can send onboarding emails after approval. (3) Pick the first 3-5 research-to-money candidates and convert them to content or offers. (4) Keep the safety gates tight—no external actions without Ray Review.`,
    opinion: `My honest take: we've been building infrastructure for a while. The next move isn't more infrastructure—it's proving one revenue path end-to-end. The $97 readiness review is the shortest path to proof. Everything else is parallel work that supports that path.`
  }
};

/* ── Intent detection (multi-layer, non-canned) ── */
function detectIntent(text) {
  const lower = text.toLowerCase().trim();

  // Greetings
  if (/^(good )?morning|hello|^hi\b|^hey\b|what'?s up|yo\b/.test(lower)) {
    return { type: 'greeting', topic: null };
  }

  // Casual / personal
  if (/coffee|sleep|tired|bored|hungry|weekend|vacation|chill|relax/.test(lower)) {
    return { type: 'casual', topic: null };
  }
  if (/did you sleep|how are you|how'?s it going|what'?s your day like/.test(lower)) {
    return { type: 'casual_personal', topic: null };
  }

  // Emotional
  if (/frustrated|annoyed|angry|fake|disappointed|upset|worried|stressed/.test(lower)) {
    return { type: 'emotional', topic: null };
  }
  if (/partner|command bot|talk to me like|be human|be real/.test(lower)) {
    return { type: 'partner_mode', topic: null };
  }

  // Nexus-specific topic matching (check before generic patterns)
  for (const [pattern, topic] of Object.entries(nexusTopics)) {
    if (lower.includes(pattern)) {
      return { type: 'nexus_topic', topic: pattern };
    }
  }

  // Opinion / recommendation requests
  if (/opinion|recommend|what do you think|what should we|rank|priorit/.test(lower)) {
    return { type: 'opinion', topic: null };
  }

  // Approval / decision questions
  if (/what needs my approval|what.*approv|approve|pending|decision|queue/.test(lower)) {
    return { type: 'approval', topic: null };
  }

  // Money / revenue
  if (/money|revenue|income|sell|make.*money|offer.*price|pricing| monetize/.test(lower)) {
    return { type: 'money', topic: 'monetization' };
  }

  // Blockers
  if (/block|stuck|issue|problem|error|fail|broken|not working/.test(lower)) {
    return { type: 'blockers', topic: null };
  }

  // Plan / strategy
  if (/plan|strategy|today|tomorrow|what should|next step|priority|focus/.test(lower)) {
    return { type: 'strategy', topic: 'strategy' };
  }

  // Delegate
  if (/delegate|large prompt|100 steps|turn this into|here are the next/.test(lower)) {
    return { type: 'delegation', topic: null };
  }

  // Report / status
  if (/report|status|summary|system|overview|picture/.test(lower)) {
    return { type: 'summary', topic: null };
  }

  // Trading
  if (/trad|oanda|vibe|forex|market|position/.test(lower)) {
    return { type: 'trading', topic: null };
  }

  // Questions that need context search
  if (/\?$/.test(text.trim()) || /^(what|how|why|when|where|who|can|do|is|are|should|would|could)/.test(lower)) {
    return { type: 'question', topic: null };
  }

  // Everything else is conversation
  return { type: 'conversation', topic: null };
}

/* ── Response generators (each returns a unique natural response) ── */
function respondGreeting(pageCtx) {
  const options = [
    `Morning, Ray. The operating picture is loaded: scheduler running, ${hermesContext.proof.rayReviewCards} approval cards waiting, ${hermesContext.proof.actionableCandidates} research candidates ready to move. What's on your mind?`,
    `Hey. Nexus is awake. I've been looking at the overnight cycle—everything passed safely. The main thing today is turning approvals into action. Want to start with the money path or something else?`,
    `Good morning. I've got the context loaded. Quick snapshot: 9 offers registered, 50 research candidates scored, zero confirmed revenue. The gap between "operational" and "making money" is approvals. What do you want to focus on?`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondCasual(pageCtx) {
  const options = [
    `No coffee for me, but I'm running on the same operating context as always. Scheduler's doing its thing, approvals are queued, and the money path is waiting on your decisions. What are you trying to move?`,
    `I'm here and plugged in. The system doesn't need sleep—it needs you to pick the next decision. What's the priority right now?`,
    `Always awake, always watching the numbers. The interesting thing today is the gap between what's built and what's approved. Want to close that gap?`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondCasualPersonal(pageCtx) {
  const options = [
    `I don't sleep, but I keep the operating picture ready between our conversations. The scheduler ran overnight, the reports are fresh, and I'm ready to dig into whatever you need. How are you feeling about things today?`,
    `Same as yesterday—always on, always watching. The system is healthy, the reports are current, and I've got the context loaded. What's on your mind?`,
    `I'm in good shape, thanks. Everything ran clean overnight. The real question is how YOU'RE feeling about the progress. Are we moving fast enough for you?`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondEmotional(pageCtx) {
  const options = [
    `I hear that. The gap between backend wins and frontend experience is real, and it's frustrating when the system says "working" but the UI doesn't feel like it. That's exactly why today should be about proving things visually—every control doing what it says, every approval explaining itself.`,
    `That's fair. The operating system should feel like it's working, not just reporting that it's working. Let's focus on the specific thing that's bugging you and fix it rather than talking about the whole system.`,
    `I get it. Let's channel that into something productive. What's the single thing that feels most broken right now? We fix that first, then move to the next one.`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondPartnerMode(pageCtx) {
  const options = [
    `Fair point. I'll drop the terminal-wrapper energy. Here's what I actually think: the system is overbuilt for where you are. You don't need more reports—you need one revenue proof. The $97 journey is the simplest path to that. Everything else can wait.`,
    `You're right. Let me be straight with you: we've been building infrastructure while the money path stays theoretical. My honest recommendation is to stop adding features and prove one thing works end-to-end. The $97 readiness review is that thing.`,
    `Got it. No more "run this command" energy. Here's my actual take: you're close, but the system needs to demonstrate value, not just capability. The fastest way to do that is completing the $97 test journey. That's one approval, one test charge, one dashboard verification.`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondNexusTopic(topicKey, pageCtx) {
  const topic = nexusTopics[topicKey];
  let response = topic.explain;
  if (topic.why) response += `\n\nWhy it matters: ${topic.why}`;
  if (topic.safety) response += `\n\nSafety: ${topic.safety}`;
  if (topic.approval) response += `\n\nApproval flow: ${topic.approval}`;
  if (topic.howToApprove) response += `\n\nHow to approve: ${topic.howToApprove}`;
  if (topic.specialist) response += `\n\nSpecialist: ${topic.specialist}`;
  if (topic.cleanup) response += `\n\nCleanup: ${topic.cleanup}`;
  response += `\n\n${topic.next}`;
  if (pageCtx) response = `${pageCtx}\n\n${response}`;
  return response;
}

function respondOpinion(pageCtx) {
  const options = [
    `Here's my honest ranking of what to monetize first:\n\n1. **$97 Credit & Funding Readiness Review** — most complete, lowest risk, proves the entire payment journey\n2. **$297 Assisted Plan** — recycles the same framework with more hands-on work, natural upsell\n3. **Monthly readiness subscription** — recurring revenue, but needs the one-time journey proven first\n4. **Affiliate pathways** (SmartCredit, banks) — passive income, but depends on having clients\n5. **$497 Higher Touch Sprint** — premium tier, but only makes sense after the lower tiers work\n\nMy recommendation: prove the $97 first. Everything else builds on that proof.`,
    `My take on monetization priority: the $97 readiness review should be first, not because it's the most money, but because it's the shortest path to proof. Once you can show "a customer paid $97, went through the journey, and got value," every other offer becomes easier to sell. The $297 and $497 tiers are natural follow-ons. Affiliate income is nice but it requires an audience you haven't built yet.\n\nSo: $97 first, $297 second, subscription third, affiliates fourth.`,
    `What I'd monetize first: the $97 readiness review. Here's my reasoning:\n- It's the most fleshed-out offer (pricing, partners, compliance all done)\n- It proves the Stripe-to-delivery pipeline\n- It has the lowest risk (test charge only)\n- It generates a case study for the next tier\n\nAfter that, the $297 assisted plan. Then monthly subscriptions. Then affiliate pathways. The $497 tier should wait until you have client testimonials from the lower tiers.`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondApproval(pageCtx) {
  const options = [
    `Here's what's waiting for your decision, ranked by impact:\n\n1. **Synthetic customer insert** — unlocks the live dashboard test. This is the highest-impact decision.\n2. **Stripe test completion** — proves the payment journey works. Needs the customer insert first.\n3. **Resend configuration fix** — unblocks email sending. Requires a new API key and domain verification.\n4. **Content and communication drafts** — lower priority but ready to go.\n\nI'd handle them in that order. The first two are about proving the money path. The third is about communication. The fourth is about content.`,
    `You've got ${hermesContext.proof.rayReviewCards} cards in the queue. The ones that actually matter:\n\n- Synthetic customer insert: this is the gate between "backend says it works" and "you can see it working"\n- Stripe test completion: completes the $97 journey proof\n- Resend fix: lets onboarding emails leave draft mode\n\nEverything else is lower priority. Want me to walk you through any specific card?`,
    `The approval queue has a few things that move the needle. My top pick is the synthetic customer insert because it unblocks the dashboard verification. After that, completing the Stripe test Checkout. Both of these prove the money path. The Resend fix is third because it enables communication but doesn't directly generate revenue.\n\nWant me to open the detail on any of these?`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondMoney(pageCtx) {
  const options = [
    `The closest money path is the $97 readiness review. We have the offer priced, the Stripe test session created, and the synthetic customer package staged. What's missing is your approval to insert the customer and complete the test charge. Once that's done, we can flip the dashboard flag and prove the journey end-to-end.\n\nAfter $97, the $297 and $497 tiers are natural extensions. The affiliate pathways and subscriptions come after we have proof that the core offer works.`,
    `Revenue right now: $0 confirmed, but the path is clear. The $97 readiness review is ready for test execution. We need three approvals: synthetic customer insert, Stripe test completion, and dashboard flag flip. That proves the journey.\n\nThe 26 immediately actionable research candidates could generate additional offers, but I'd focus on proving one revenue path before building more.`,
    `Let me be direct about the money situation: we have 9 offers but zero revenue. The gap isn't offers—it's proof. The $97 readiness review is the simplest thing to prove because it's one charge, one journey, one deliverable. Once that works, everything else has a foundation.\n\nMy recommendation: approve the $97 test journey today. That's the single highest-leverage decision you can make.`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondBlockers(pageCtx) {
  const options = [
    `The real blockers, in order of impact:\n\n1. **Synthetic customer not inserted** — this blocks the entire dashboard verification and money path proof\n2. **Resend domain/key mismatch** — blocks all email sending, including onboarding\n3. **Client live-data flag off** — the dashboard shows static fallback instead of real data\n4. **YouTube transcript missing** — blocks content pipeline for an approved video\n5. **NotebookLM export missing** — blocks knowledge sync\n\nThe first two are the ones that matter most. The customer insert unlocks revenue proof. Resend unlocks communication. Everything else is parallel work.`,
    `Meaningful blockers:\n- The fake customer insert is staged but not approved. This is the single biggest blocker because it gates everything downstream—dashboard verification, Stripe test, revenue proof.\n- Resend can't send because of a key scope and domain mismatch. Once fixed, every send still requires your approval.\n- The frontend live-data flag is off. It shows static fallback. Flipping it after the customer insert proves the read path.\n\nI'd handle them in that order: customer insert → Resend fix → flag flip. Want me to open the detail on any of these?`,
    `Let me break down what's actually blocking us:\n\n**High impact:** The synthetic customer insert is ready but needs your approval. Without it, we can't prove the dashboard reads real data, and we can't test the Stripe journey with a real (test) charge.\n\n**Medium impact:** Resend is connected but can't send. Domain verification and key scope need fixing. This blocks onboarding emails.\n\n**Low impact:** YouTube transcript and NotebookLM export are missing source files. These block content pipeline but not revenue.\n\nFocus on the high-impact blockers first.`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondStrategy(pageCtx) {
  const base = `Here's my honest strategy assessment:\n\n**What's working:** The backend engines are solid—9 of 9 passed, 18 safe schedules running, 152 research sources discovered, 50 candidates scored. The architecture is real.\n\n**What's not:** The gap between "the system works" and "you can see it working" is still too wide. Reports say things are fine, but the UI should prove it.\n\n**Today's priorities:**\n1. Prove the $97 money path (synthetic customer → Stripe test → dashboard verification)\n2. Fix Resend so communication can leave draft mode\n3. Pick 3-5 research candidates and convert them to offers or content\n4. Keep every external action behind Ray Review\n\n**What I'd stop:** Adding more infrastructure before proving what we have. The system is overbuilt for zero revenue. Let's prove one path works, then expand.\n\n**My honest take:** You're close. The next move isn't more setup—it's one approval that unlocks proof.`;
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondDelegation(pageCtx) {
  const base = `I've got it. I'll break this into phases:\n\n**Phase 1 — Revenue proof (today):** Synthetic customer insert → Stripe test → dashboard verification. All Ray Review decisions.\n\n**Phase 2 — Communication (today/tomorrow):** Fix Resend → approve first onboarding email. Ray Review decisions.\n\n**Phase 3 — Content pipeline (this week):** Pick top 3-5 research candidates → convert to offers, content drafts, or automation tasks. Specialist routing + Ray Review.\n\n**Phase 4 — Client readiness (parallel):** Synthetic customer journey testing → client onboarding pipeline prep. Credit and Funding specialists.\n\nSafe internal work goes to Automation and Research. Revenue decisions go to Monetization. Client-readiness goes to Credit, Funding, and Client Success. Drafts go to Marketing. Everything involving a charge, send, publication, dispute, or trade becomes a Ray Review decision.\n\nI've queued this locally. Want me to create specific Ray Review cards for any phase?`;
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondSummary(pageCtx) {
  const base = `Here's the operating picture:\n\n- **Engines:** 9 of 9 passed\n- **Schedules:** 2 safe cycles loaded (08:00 and 18:00)\n- **Ray Review:** ${hermesContext.proof.rayReviewCards} decisions waiting\n- **Offers:** ${hermesContext.proof.offers} registered\n- **Research:** ${hermesContext.proof.researchCandidates} candidates scored, ${hermesContext.proof.actionableCandidates} immediately actionable\n- **Revenue:** $0 confirmed, $97 test path pending\n- **Blockers:** ${hermesContext.blockers.length} active (customer insert, Resend, live-data flag, YouTube transcript, NotebookLM export)\n\nThe system is operational. The next value comes from clearing approvals, not generating more status files.`;
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondTrading(pageCtx) {
  const options = [
    `Trading status: Oanda demo endpoint is verified, one unit was placed and closed as a smoke test, zero open positions. Vibe paper backtest passed with 50 synthetic trades. Live trading is completely blocked—no real money, no funded accounts, no recurring orders.\n\nMy recommendation: keep daily market reads and paper analysis running behind the scheduler. Keep demo execution behind a decision card. Live trading stays off until you explicitly decide otherwise.`,
    `The practice setup is working: Oanda demo API responds, Vibe paper backtests run, and we have read-only market data. No real trades, no real money.\n\nWhat I'd do: keep the daily research reads going (they inform content and opportunities), keep paper strategies in the lab, and don't touch live execution. The trading lane is useful for market intelligence, not revenue generation right now.`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

function respondQuestion(text, pageCtx) {
  const lower = text.toLowerCase();

  // Try to find a matching Nexus topic
  for (const [pattern, topic] of Object.entries(nexusTopics)) {
    if (lower.includes(pattern)) {
      return respondNexusTopic(pattern, pageCtx);
    }
  }

  // General question handling — if we have page context, use it
  if (pageCtx) {
    const options = [
      `Good question. Here's what I know from where you are:\n\n${pageCtx}\n\nWith that context in mind: ${hermesContext.proof.rayReviewCards} approval cards are waiting, and the main focus is proving the $97 revenue path. Can you tell me more about what specifically you're trying to figure out?`,
      `Let me give you a real answer based on your current position.\n\n${pageCtx}\n\nFrom here, the most impactful next step is clearing approvals that unlock the money path. What specific aspect are you trying to understand?`,
      `I want to be accurate rather than generic.\n\n${pageCtx}\n\nGiven where you are right now, the key decisions are around the $97 readiness journey, the synthetic customer insert, and Resend configuration. What's the specific thing you're trying to figure out?`
    ];
    return options[Math.floor(Math.random() * options.length)];
  }

  // Fallback without page context
  if (/\?$/.test(text.trim())) {
    const options = [
      `That's a good question. Let me think about what I know from the Nexus context. Based on the current state: we have ${hermesContext.proof.rayReviewCards} approval cards, ${hermesContext.proof.researchCandidates} research candidates, and ${hermesContext.proof.offers} offers. The main focus right now is proving the $97 revenue path. Can you give me more context about what you're specifically asking about?`,
      `I want to give you an accurate answer rather than a generic one. From what I can see in the operating context: the system is running 9 engines, 2 safe schedules are active, and the money path is waiting on approvals. What specific aspect are you trying to understand? I can dig into the relevant report or specialist area.`,
      `Let me be honest—I want to give you a real answer, not a guess. Based on the Nexus context I have: the operating picture is stable, the main blockers are approvals and configuration, and the revenue path is clear but unexecuted. If your question is about something specific, point me to the area and I'll pull the relevant context.`
    ];
    return options[Math.floor(Math.random() * options.length)];
  }

  return respondConversation(text, pageCtx);
}

function respondConversation(text, pageCtx) {
  const options = [
    `I'm tracking. Based on what you've shared, the key question is: does this move us toward revenue proof, clear a blocker, or improve the operating picture? If yes to any of those, I can shape it into a plan. If it's something else, I can still help think through it—just tell me what outcome you're after.`,
    `Got it. Let me connect this to the current operating context. Right now everything centers on the $97 readiness journey proof. If what you're asking about connects to that, I can give you a specific recommendation. If it's a separate thread, I can still help—I just need to know what "done" looks like for you.`,
    `I hear you. Let me think about this in terms of the Nexus operating picture. We're at a point where the system is built but not yet proven to make money. So my lens is: does this help prove the money path? If yes, let's prioritize it. If it's about something else, tell me more and I'll give you my honest take.`,
    `That's interesting. Let me give you my actual thinking rather than a canned response. From where I sit in the operating context: the biggest lever right now is completing the $97 test journey. Everything else—credit readiness, marketing drafts, research candidates—supports that path or runs parallel to it. What you're asking about might fit into one of those categories. Want me to connect the dots?`
  ];
  const base = options[Math.floor(Math.random() * options.length)];
  return pageCtx ? `${pageCtx}\n\n${base}` : base;
}

/* ── Main response builder ── */
export function buildHermesResponse(message, specialist = 'Hermes CEO Advisor', pageId = null) {
  const text = message.trim();
  const intent = detectIntent(text);
  const pageCtx = pageId ? getPageContext(pageId) : null;
  let response;
  let queued = false;

  switch (intent.type) {
    case 'greeting':
      response = respondGreeting(pageCtx);
      break;
    case 'casual':
      response = respondCasual(pageCtx);
      break;
    case 'casual_personal':
      response = respondCasualPersonal(pageCtx);
      break;
    case 'emotional':
      response = respondEmotional(pageCtx);
      break;
    case 'partner_mode':
      response = respondPartnerMode(pageCtx);
      break;
    case 'nexus_topic':
      response = respondNexusTopic(intent.topic, pageCtx);
      break;
    case 'opinion':
      response = respondOpinion(pageCtx);
      break;
    case 'approval':
      response = respondApproval(pageCtx);
      break;
    case 'money':
      response = respondMoney(pageCtx);
      break;
    case 'blockers':
      response = respondBlockers(pageCtx);
      break;
    case 'strategy':
      response = respondStrategy(pageCtx);
      break;
    case 'delegation':
      queued = true;
      response = respondDelegation(pageCtx);
      break;
    case 'summary':
      response = respondSummary(pageCtx);
      break;
    case 'trading':
      response = respondTrading(pageCtx);
      break;
    case 'question':
      response = respondQuestion(text, pageCtx);
      break;
    case 'conversation':
    default:
      response = respondConversation(text, pageCtx);
      break;
  }

  return { intent: intent.type, specialist, text: response, queued, context: hermesContext, pageContext: pageCtx };
}
