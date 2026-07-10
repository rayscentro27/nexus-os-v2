export type DisputeReason =
  | 'not_mine'
  | 'incorrect_balance'
  | 'incorrect_dates'
  | 'duplicate'
  | 'paid_or_settled_wrong'
  | 'late_payment_wrong'
  | 'unauthorized_inquiry'
  | 'personal_info_error'
  | 'verify_or_validate'
  | 'outdated'
  | 'mixed_file'
  | 'method_of_verification'
  | 'other'
  | 'not_sure'

export type LetterOption = {
  optionType: string
  title: string
  summary: string
  whenToUse: string
  whyRecommended: string
  evidenceNeeded: string[]
  riskLevel: 'low' | 'medium' | 'high'
  caution: string
  nextAction: string
  draftBody: string
  recommended?: boolean
}

export const DISPUTE_REASON_LABELS: Record<DisputeReason, string> = {
  not_mine: 'Not mine',
  incorrect_balance: 'Incorrect balance',
  incorrect_dates: 'Incorrect dates',
  duplicate: 'Duplicate',
  paid_or_settled_wrong: 'Paid/settled reporting wrong',
  late_payment_wrong: 'Late payment wrong',
  unauthorized_inquiry: 'Unauthorized inquiry',
  personal_info_error: 'Personal information error',
  verify_or_validate: 'Verify/validate this item',
  outdated: 'Outdated',
  mixed_file: 'Mixed file',
  method_of_verification: 'Method of verification follow-up',
  other: 'Other',
  not_sure: 'I am not sure',
}

const BASE_OPTIONS: Record<DisputeReason, Omit<LetterOption, 'draftBody'>[]> = {
  not_mine: [
    option('bureau_dispute', 'Bureau not-mine dispute', 'Ask the bureau to investigate and verify ownership.', 'Use when the client says the account is not theirs or may be mixed-file.', 'Starts the formal bureau investigation path.', ['Government ID', 'Proof of address', 'Client statement'], 'medium', 'Do not claim identity theft unless the client has stated that and has supporting records.', 'Prepare draft for GoClear review', true),
    option('furnisher_dispute', 'Furnisher direct dispute', 'Ask the furnisher to verify ownership and reporting authority.', 'Use when the furnisher/account source is clear.', 'Direct furnisher review can support correction or deletion.', ['Account notice if available', 'Client statement'], 'medium', 'Requires accurate furnisher identification.', 'Prepare direct furnisher draft'),
    option('mixed_file_support', 'Identity / mixed-file support request', 'Package identity documents and ask for mixed-file review.', 'Use when personal information or accounts appear blended.', 'Identity evidence helps specialists organize the challenge.', ['Government ID', 'Proof of address'], 'low', 'Do not collect SSN or full DOB in the portal.', 'Request specialist review'),
  ],
  incorrect_balance: [
    option('bureau_balance_dispute', 'Bureau incorrect balance dispute', 'Challenge the reported balance through the bureau.', 'Use when the report balance appears wrong.', 'Bureau investigation can require the furnisher to verify the amount.', ['Statement', 'Payment proof', 'Settlement letter'], 'medium', 'Upload only proof the client chooses to provide.', 'Prepare draft for GoClear review', true),
    option('furnisher_balance_verification', 'Furnisher balance verification', 'Ask the furnisher to verify and update the balance.', 'Use when direct source correction may be faster.', 'The furnisher controls the reported data.', ['Statement', 'Payment proof'], 'medium', 'Keep account numbers masked.', 'Prepare direct furnisher draft'),
  ],
  incorrect_dates: [
    option('bureau_date_accuracy', 'Bureau date accuracy dispute', 'Challenge inaccurate opened/reported/status dates.', 'Use for date inaccuracies or possible re-aging concerns.', 'Date accuracy can affect reporting age and fundability review.', ['Old statement', 'Prior report screenshot', 'Collection notice'], 'medium', 'Avoid claiming re-aging without evidence.', 'Prepare draft for GoClear review', true),
    option('furnisher_date_verification', 'Furnisher date verification', 'Ask furnisher to verify reported dates.', 'Use when source records may correct bureau data.', 'Direct verification can produce cleaner updates.', ['Prior report', 'Creditor notice'], 'medium', 'Specialist should review chronology.', 'Prepare direct furnisher draft'),
    option('method_of_verification', 'Method of verification follow-up', 'Ask how prior verification was completed.', 'Use after unsupported verification.', 'Follow-up can identify weak verification or next evidence needs.', ['Prior dispute result', 'Bureau response letter'], 'high', 'Best used after a prior result exists.', 'Request specialist review'),
  ],
  duplicate: [
    option('duplicate_account_bureau', 'Bureau duplicate reporting dispute', 'Challenge duplicate reporting on the credit report.', 'Use when the same debt/account appears more than once.', 'Duplicate reporting may overstate risk.', ['Report screenshots from bureaus'], 'medium', 'Specialist should confirm duplicate identity.', 'Prepare draft for GoClear review', true),
    option('duplicate_furnisher_clarification', 'Furnisher duplicate account clarification', 'Ask furnisher/collector to clarify duplicate records.', 'Use when duplicate source is unclear.', 'Clarifies which record should remain if any.', ['Account notices', 'Report screenshots'], 'medium', 'Do not demand removal of accurate distinct accounts.', 'Prepare direct furnisher draft'),
  ],
  paid_or_settled_wrong: [
    option('paid_settled_update', 'Paid/settled status correction dispute', 'Challenge wrong paid or settled status.', 'Use when payment/settlement is not reflected.', 'Status correction can materially improve review quality.', ['Settlement letter', 'Paid receipt'], 'low', 'Bank proof is optional and client-controlled.', 'Prepare draft for GoClear review', true),
    option('furnisher_paid_update', 'Furnisher direct update request', 'Ask furnisher to update paid/settled reporting.', 'Use when client has direct payment evidence.', 'Source update can propagate to bureaus.', ['Settlement letter', 'Receipt'], 'low', 'Keep account numbers masked.', 'Prepare direct furnisher draft'),
  ],
  late_payment_wrong: [
    option('late_payment_accuracy', 'Late payment accuracy dispute', 'Challenge late payment accuracy.', 'Use when payment history appears wrong.', 'Payment history has high readiness impact.', ['Payment confirmation', 'Creditor email/letter'], 'medium', 'Specialist should compare timeline.', 'Prepare draft for GoClear review', true),
    option('furnisher_payment_review', 'Furnisher payment history review', 'Ask furnisher to review payment history.', 'Use when furnisher records may correct the line.', 'Direct source review may fix month-level reporting.', ['Payment confirmation'], 'medium', 'Avoid overclaiming without proof.', 'Prepare direct furnisher draft'),
    option('goodwill', 'Goodwill adjustment request', 'Non-dispute goodwill option.', 'Use when late payment may be accurate but client wants relief.', 'Different path from a legal dispute.', ['Client statement'], 'low', 'This is not a dispute and is not guaranteed.', 'Request specialist review'),
  ],
  unauthorized_inquiry: [
    option('unauthorized_inquiry', 'Unauthorized inquiry dispute', 'Challenge inquiry authorization.', 'Use when client does not recognize/authorize an inquiry.', 'Inquiry review can reduce unnecessary risk signals.', ['Client statement', 'Denial/approval record if available'], 'medium', 'Do not claim fraud unless client states it.', 'Prepare draft for GoClear review', true),
    option('inquiry_verification', 'Furnisher inquiry verification request', 'Ask creditor to verify permissible purpose.', 'Use when the inquiry source is identifiable.', 'Direct verification can clarify authorization.', ['Client statement'], 'medium', 'Specialist should confirm recipient.', 'Prepare direct furnisher draft'),
  ],
  personal_info_error: [
    option('personal_info_update', 'Personal information correction request', 'Correct name, address, employer, or other profile info.', 'Use when personal information is wrong.', 'Clean identity data supports dispute and funding review.', ['Government ID', 'Proof of address'], 'low', 'Do not collect SSN or full DOB.', 'Prepare draft for GoClear review', true),
  ],
  verify_or_validate: [
    option('bureau_verification', 'Bureau verification dispute', 'Ask bureau to investigate and verify the item.', 'Use when client wants the item verified or corrected.', 'General first-round investigation path.', ['Account notices', 'Client statement'], 'medium', 'Specialist should refine the reason if possible.', 'Prepare draft for GoClear review', true),
    option('collector_validation', 'Collector validation request', 'Ask collector to validate the debt when appropriate.', 'Use for collection accounts where validation is appropriate.', 'Collector validation can clarify ownership and amount.', ['Collection letter'], 'medium', 'Specialist confirms collector context.', 'Prepare validation draft'),
  ],
  outdated: [
    option('outdated_item', 'Outdated item dispute', 'Challenge obsolete reporting.', 'Use when the item may be too old to report.', 'Old inaccurate reporting can block readiness.', ['Old statements', 'Prior report'], 'medium', 'Specialist must review dates before sending.', 'Prepare draft for GoClear review', true),
  ],
  mixed_file: [
    option('mixed_file', 'Mixed-file investigation request', 'Package identity evidence and ask for mixed-file investigation.', 'Use when records may belong to another person.', 'Organizes identity evidence for review.', ['Government ID', 'Proof of address'], 'medium', 'Do not collect SSN/full DOB.', 'Prepare draft for GoClear review', true),
  ],
  method_of_verification: [
    option('method_of_verification', 'Method of verification request', 'Ask how the item was verified.', 'Use after a prior verification result.', 'Helps determine next round strategy.', ['Prior dispute result', 'Bureau response letter'], 'high', 'Follow-up strategy, usually not first-round.', 'Prepare follow-up draft', true),
    option('reinvestigation', 'Reinvestigation request', 'Ask for reinvestigation with added context.', 'Use if new evidence is available.', 'New evidence can change next-round posture.', ['New evidence', 'Prior response'], 'medium', 'Avoid repeating the same unsupported dispute.', 'Prepare draft for GoClear review'),
    option('cfpb_escalation_prep', 'CFPB complaint prep', 'Prepare escalation materials if repeated unsupported verification occurs.', 'Use only after repeated unresolved results.', 'Escalation may be appropriate when documentation supports it.', ['Prior responses', 'Timeline'], 'high', 'Specialist review required before escalation.', 'Request specialist review'),
  ],
  other: [
    option('specialist_review', 'Specialist review required', 'Package the item for GoClear review.', 'Use when the reason does not fit a standard category.', 'A specialist can select the right compliant path.', ['Client statement', 'Any supporting document'], 'medium', 'No automatic letter recommendation.', 'Request specialist review', true),
  ],
  not_sure: [
    option('clarifying_questions', 'Specialist review required', 'Clyde asks clarifying questions before drafting.', 'Use when the client is not sure why the item should be challenged.', 'Prevents weak or unsupported disputes from moving too fast.', ['Client statement', 'Credit report'], 'low', 'No automatic letter recommendation until reason is selected or specialist approves.', 'Answer dispute questions', true),
  ],
}

function option(optionType: string, title: string, summary: string, whenToUse: string, whyRecommended: string, evidenceNeeded: string[], riskLevel: 'low' | 'medium' | 'high', caution: string, nextAction: string, recommended = false) {
  return { optionType, title, summary, whenToUse, whyRecommended, evidenceNeeded, riskLevel, caution, nextAction, recommended }
}

export function getDisputeOptions(reason: DisputeReason, itemLabel = 'the selected item'): LetterOption[] {
  return (BASE_OPTIONS[reason] || BASE_OPTIONS.not_sure).map((base) => ({
    ...base,
    draftBody: [
      'Re: Request for investigation / verification',
      '',
      `I am requesting investigation or verification of ${itemLabel}.`,
      `Reason selected: ${DISPUTE_REASON_LABELS[reason] || reason}.`,
      base.summary,
      '',
      'Please investigate, verify, correct, or remove information that cannot be accurately verified under applicable credit reporting requirements.',
      '',
      'This draft is prepared for GoClear specialist review and client approval before any mailing request.',
    ].join('\n'),
  }))
}

export const OUTCOME_CATEGORIES = [
  'deleted',
  'corrected',
  'verified',
  'updated',
  'no_response',
  'needs_escalation',
  'client_evidence_needed',
  'not_sent',
] as const

export function summarizeOutcome(result: string) {
  if (result === 'deleted') return 'Success: mark the item removed and track which option worked.'
  if (result === 'corrected' || result === 'updated') return 'Partial success: update status and reassess funding readiness impact.'
  if (result === 'verified') return 'Verified: consider method of verification, furnisher dispute, or stronger evidence.'
  if (result === 'no_response') return 'No response: prepare follow-up or escalation review.'
  if (result === 'client_evidence_needed') return 'Evidence needed: request supporting document upload.'
  if (result === 'needs_escalation') return 'Escalation review: specialist should review next-round posture.'
  return 'Not sent: keep item in review until approved.'
}
