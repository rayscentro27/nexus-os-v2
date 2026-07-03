/**
 * Nexus OS v2 — Hermes Local Operating Commands.
 *
 * Answers readiness and operating questions in CEO/Jarvis style.
 * Reads from the readiness registry + capability registry + operational contracts.
 * Pure deterministic logic — no I/O, no external calls.
 */
import { READINESS_REGISTRY, getReadinessByArea, getReadinessCeoAnswer } from './nexusReadinessRegistry';

export type OperatingQuestion =
  | 'credit_repair_ready'
  | 'business_funding_ready'
  | 'ready_to_onboard_client'
  | 'missing_credit_repair'
  | 'missing_business_funding'
  | 'can_sell_97_review'
  | 'what_should_ray_do_first'
  | 'draft_ray_review_readiness'
  | 'specialist_handoff_credit'
  | 'specialist_handoff_funding'
  | 'what_parts_manual'
  | 'what_parts_automated'
  | 'what_parts_approval_gated'
  | 'what_can_client_see'
  | 'what_can_admin_see';

export function classifyOperatingQuestion(message: string): OperatingQuestion | null {
  const lower = message.toLowerCase();
  if (/\b(?:is )?credit repair (?:ready|set|good|complete|done)\b/i.test(lower)) return 'credit_repair_ready';
  if (/\b(?:is )?business funding (?:ready|set|good|complete|done)\b/i.test(lower)) return 'business_funding_ready';
  if (/\b(?:are we )?ready to (?:onboard|sign up|start with|take on) (?:a )?client\b/i.test(lower)) return 'ready_to_onboard_client';
  if (/\bwhat (?:is |are )?(?:missing|needed|lacking|left) (?:from |for )?credit repair\b/i.test(lower)) return 'missing_credit_repair';
  if (/\bwhat (?:is |are )?(?:missing|needed|lacking|left) (?:from |for )?business funding\b/i.test(lower)) return 'missing_business_funding';
  if (/\bcan (?:we |you )?(?:sell|launch|offer|deliver|start selling) (?:the )?\$?97\b/i.test(lower)) return 'can_sell_97_review';
  if (/\bwhat should (?:ray |i )(?:do first|start with|focus on|prioritize)\b/i.test(lower)) return 'what_should_ray_do_first';
  if (/\b(?:create|draft|prepare).*(?:ray review).*(?:readiness|offer|review)\b/i.test(lower)) return 'draft_ray_review_readiness';
  if (/\b(?:prepare|draft).*(?:specialist|handoff).*(?:credit)\b/i.test(lower)) return 'specialist_handoff_credit';
  if (/\b(?:prepare|draft).*(?:specialist|handoff).*(?:funding|business)\b/i.test(lower)) return 'specialist_handoff_funding';
  if (/\bwhat (?:parts?|steps?) (?:are |is )?manual\b/i.test(lower)) return 'what_parts_manual';
  if (/\bwhat (?:parts?|steps?) (?:are |is )?automated\b/i.test(lower)) return 'what_parts_automated';
  if (/\bwhat (?:parts?|steps?) (?:are |is )?(?:approval[- ]?gated|gated|need approval)\b/i.test(lower)) return 'what_parts_approval_gated';
  if (/\bwhat can (?:the )?client (?:see|view|access|do)\b/i.test(lower)) return 'what_can_client_see';
  if (/\bwhat can (?:admin|ray|i as admin) (?:see|view|access|do)\b/i.test(lower)) return 'what_can_admin_see';
  return null;
}

export function answerOperatingQuestion(question: OperatingQuestion): string {
  switch (question) {
    case 'credit_repair_ready':
      return answerCreditRepairReady();
    case 'business_funding_ready':
      return answerBusinessFundingReady();
    case 'ready_to_onboard_client':
      return answerReadyToOnboard();
    case 'missing_credit_repair':
      return answerMissingCreditRepair();
    case 'missing_business_funding':
      return answerMissingBusinessFunding();
    case 'can_sell_97_review':
      return answerCanSell97();
    case 'what_should_ray_do_first':
      return answerWhatShouldRayDoFirst();
    case 'draft_ray_review_readiness':
      return answerDraftRayReviewReadiness();
    case 'specialist_handoff_credit':
      return answerSpecialistHandoffCredit();
    case 'specialist_handoff_funding':
      return answerSpecialistHandoffFunding();
    case 'what_parts_manual':
      return answerWhatPartsManual();
    case 'what_parts_automated':
      return answerWhatPartsAutomated();
    case 'what_parts_approval_gated':
      return answerWhatPartsApprovalGated();
    case 'what_can_client_see':
      return answerWhatCanClientSee();
    case 'what_can_admin_see':
      return answerWhatCanAdminSee();
  }
}

function answerCreditRepairReady(): string {
  return getReadinessCeoAnswer('credit_repair');
}

function answerBusinessFundingReady(): string {
  return getReadinessCeoAnswer('business_funding');
}

function answerReadyToOnboard(): string {
  const onboarding = getReadinessByArea('client_onboarding');
  const portal = getReadinessByArea('client_portal');
  const payments = getReadinessByArea('payments');

  const issues: string[] = [];
  if (onboarding?.status !== 'ready') issues.push('client onboarding is not wired to the live database');
  if (portal?.status !== 'ready') issues.push('the client portal runs on demo data only');
  if (payments?.status !== 'ready') issues.push('Stripe is in test mode only');

  if (issues.length === 0) return 'Yes. The onboarding pipeline, client portal, and payment system are all ready. You can take on a real client now.';

  return `Not yet. ${issues.join('; ')}. The simplest first version is manual: collect info via conversation, run Hermes scoring, deliver the readiness summary by hand, and upsell the $297 assistant plan. Once that works, wire the live database and portal.`;
}

function answerMissingCreditRepair(): string {
  const item = getReadinessByArea('credit_repair');
  if (!item) return 'I do not have credit repair readiness data.';
  if (item.status === 'ready') return 'Credit repair is fully ready. Nothing is missing.';
  return `Credit repair is missing: ${item.blocker || 'key components'}. The scoring engine works but needs real client data. Document upload, bureau connectors, and mailing are all blocked. Start by applying the Supabase migrations and creating a test client.`;
}

function answerMissingBusinessFunding(): string {
  const item = getReadinessByArea('business_funding');
  if (!item) return 'I do not have business funding readiness data.';
  if (item.status === 'ready') return 'Business funding is fully ready. Nothing is missing.';
  return `Business funding is missing: ${item.blocker || 'key components'}. The scoring engine works but needs real client data. No bank, DUNS, or EIN integrations exist yet. All affiliate URLs are null. Start by applying the Supabase migrations and creating a test client with a business profile.`;
}

function answerCanSell97(): string {
  const item = getReadinessByArea('readiness_review_offer');
  if (!item) return 'I do not have the $97 readiness review offer data.';

  return `**Partial — manual only.**\n\nYou can sell the $97 readiness review right now if you do it by hand:\n\n1. Collect payment (manual or Stripe test)\n2. Gather credit and business info via conversation\n3. Run Hermes to score credit and funding readiness\n4. Produce a plain-English readiness summary\n5. Review and approve it yourself (Ray Review)\n6. Deliver via conversation\n7. Offer the $297 assistant plan as upsell\n\n**What is missing for automation:** No live client database, no report generation from real data, no production Stripe, no email delivery. The simplest first version is conversation-based. Once it works, wire the live pipeline.`;
}

function answerWhatShouldRayDoFirst(): string {
  const missing: string[] = [];
  READINESS_REGISTRY.forEach(r => {
    if (r.status === 'blocked' || r.status === 'not_configured') {
      missing.push(r.displayName);
    }
  });

  return `**First move: enable the manual $97 readiness review.**\n\nEverything else is secondary. The credit repair and business funding engines are built and working — they just need real client data. The fastest path to revenue is:\n\n1. Turn on Stripe production for $97\n2. Create an intake form (Google Form works)\n3. Process one real customer by hand\n4. Use Hermes to score and produce the readiness summary\n5. Deliver it and offer the $297 upsell\n\nOnce that works, apply the Supabase migrations, wire the portal, and automate.`;
}

function answerDraftRayReviewReadiness(): string {
  return `**Ray Review Draft — $97 Readiness Review Offer**\n\n**Target:** $97 Credit & Funding Readiness Review offer launch\n**Decision needed:** Approve manual-first launch of the readiness review\n**Evidence:** Offer defined in offer_registry.json, Stripe test checkout open, public landing page live, scoring engines functional, client guide responses ready\n**Recommended action:** Enable Stripe production, create intake form, process first customer manually\n**Risk:** Low — manual process, no automation, no external sends\n**Upsell path:** $297 assistant plan → Monthly Readiness Subscription\n\nThis is a conversation-only draft. It has not been saved, submitted, or executed.`;
}

function answerSpecialistHandoffCredit(): string {
  return `**Specialist Handoff Draft — Credit Repair**\n\n**Specialist lane:** Credit Specialist\n**Objective:** Guide client through credit repair workflow — credit report upload, analysis, dispute letter drafting, mailing preparation\n**Constraints:** Supabase-only data, no internet, no external AI on client data, no bureau/creditor contact without approval\n**Missing:** No live specialist agent registered. This is a conversation-only draft.\n**Context included:** Credit analysis scoring engine (utilization, negatives, inquiries), 7 dispute letter types, mailing method options, compliance requirements\n**Approval required:** Yes — any client-facing credit advice or dispute letter must go through Ray Review\n**Draft status:** Not created, not saved, not assigned, not sent`;
}

function answerSpecialistHandoffFunding(): string {
  return `**Specialist Handoff Draft — Business Funding**\n\n**Specialist lane:** Funding Specialist\n**Objective:** Guide client through business funding readiness — LLC/EIN/DUNS setup, bank account, vendor accounts, fundability scoring, lender matching\n**Constraints:** Supabase-only data, no internet, no funding application submission without approval\n**Missing:** No live specialist agent registered. This is a conversation-only draft.\n**Context included:** 13 business setup items with score impacts, 15 partner offers (all URLs null), 4 funding path options, bankability scoring engine\n**Approval required:** Yes — any funding recommendation or lender referral must go through Ray Review\n**Draft status:** Not created, not saved, not assigned, not sent`;
}

function answerWhatPartsManual(): string {
  return `**Credit Repair — Manual parts:**\n- Credit report collection (no upload system)\n- Dispute letter review and approval\n- Mailing (no DocuPost/USPS integration)\n- Client communication (no email automation)\n- Bureau/creditor contact (all blocked by design)\n\n**Business Funding — Manual parts:**\n- Business profile intake (no form)\n- DUNS/LLC/EIN verification (no integrations)\n- Bank account guidance (no live affiliate links)\n- Lender matching (no application pipeline)\n- Grant detection (no database)\n\n**Both — Manual:**\n- Client intake (conversation-based)\n- Payment collection (manual or Stripe test)\n- Report delivery (conversation-based)\n- Follow-up scheduling (manual reminders)`;
}

function answerWhatPartsAutomated(): string {
  return `**Automated (works now):**\n- Credit readiness scoring (utilization, negatives, inquiries, account age)\n- Business funding scoring (13 setup items with score impacts)\n- Bankability calculation\n- Stuck client detection\n- Hermes recommendation generation\n- Ray Review card creation\n- Specialist handoff draft preparation\n- Activity status summaries\n- Compliance claim classification\n- Client portal rendering (static demo data)\n\n**Automated but needs real data:**\n- Report generation (Python scripts produce local JSON)\n- Dispute simulation (5 synthetic cases)\n- Reminder task generation (templates defined)`;
}

function answerWhatPartsApprovalGated(): string {
  return `**Approval-gated (requires Ray Review):**\n- Any credit analysis published to client\n- Any funding readiness assessment published\n- Any dispute letter sent to bureau/creditor/collector\n- Any physical letter mailed\n- Any funding application submitted\n- Any lender referral\n- Any affiliate link activation\n- Any payment collection (Stripe production)\n- Any client data exposed to specialist\n- Any recommendation to apply for funding\n- Any scheduler or connector activation`;
}

function answerWhatCanClientSee(): string {
  return `**Client can see (via client portal):**\n- Credit repair progress page (10-stage workflow strip)\n- Negative items under review (demo data)\n- Draft letters (demo data)\n- Next actions list\n- Credit profile readiness score\n- Business profile readiness checklist\n- Funding readiness blockers\n- Document checklist\n- Client guide responses (pre-approved Q&A)\n- Messages (demo data)\n\n**Client cannot see:**\n- Internal scoring algorithms\n- Hermes recommendations (internal only)\n- Specialist handoff drafts\n- Ray Review decisions\n- Raw credit report data\n- Affiliate commission details`;
}

function answerWhatCanAdminSee(): string {
  return `**Admin/Ray can see:**\n- All client portal pages and data\n- Credit repair workflow status\n- Business funding readiness scores\n- Hermes executive brief\n- Ray Review queue (64 cards)\n- System health status\n- Revenue dashboard\n- Research pipeline\n- Specialist agent inventory\n- Activity journal and daily summaries\n- All reports (13 registered)\n- Access map and capability status\n- Compliance claim classifications\n\n**Admin/Ray can do:**\n- Create Ray Review cards\n- Approve/reject plans\n- Prepare specialist handoff drafts\n- Run dispute simulations\n- Generate reports\n- Review affiliate opportunities\n- Process payments (with approval)`;
}
