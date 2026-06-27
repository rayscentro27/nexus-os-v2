/**
 * Nexus OS v2 — First Offer Launch Gate (GoClear/Apex $97 Readiness Review).
 *
 * A go/no-go readiness gate for the first offer. It NEVER launches, publishes, charges, or connects
 * payment — it only reports whether every approval/readiness condition is satisfied and lists the
 * exact remaining blockers. Defaults to "cannot launch" (fails closed). Deterministic. No I/O.
 */
import { READINESS_REVIEW_OFFER } from '../config/goclearSubscriptionOffers';
import { PAYMENT_CONTRACT_META } from '../config/goclearPaymentOfferContract';

export interface LaunchGateState {
  ray_offer_approved: boolean;
  ray_copy_approved: boolean;
  no_guarantee_language_present: boolean;
  payment_connected: boolean; // separate, explicitly-approved step
}

/** Default: nothing approved yet, payment not connected (mirrors PAYMENT_CONTRACT_META). */
export const DEFAULT_LAUNCH_STATE: LaunchGateState = {
  ray_offer_approved: false,
  ray_copy_approved: false,
  no_guarantee_language_present: true, // copy drafts include no-guarantee language
  payment_connected: PAYMENT_CONTRACT_META.charges_enabled,
};

export interface LaunchGateResult {
  offer_id: string;
  offer_name: string;
  price: number;
  can_launch: boolean;
  satisfied: string[];
  blockers: string[];
  external_action_taken: false;
  payment_status: string;
  recommended_next_action: string;
}

export function readinessReviewLaunchGate(state: LaunchGateState = DEFAULT_LAUNCH_STATE): LaunchGateResult {
  const satisfied: string[] = [];
  const blockers: string[] = [];

  const checks: Array<[boolean, string, string]> = [
    [state.ray_offer_approved, 'Ray approved the $97 Readiness Review offer.', 'Ray must approve the offer (via the launch review card).'],
    [state.ray_copy_approved, 'Ray approved the client-facing copy.', 'Ray must approve the readiness-review copy draft.'],
    [state.no_guarantee_language_present, 'No-guarantee/compliance language present.', 'Add no-guarantee language to the copy.'],
    [state.payment_connected, 'Payment/billing connected for the offer.', 'Connect payment/billing in a separate, explicitly-approved step (contract-only now).'],
  ];
  for (const [ok, sat, block] of checks) (ok ? satisfied : blockers).push(ok ? sat : block);

  const can_launch = blockers.length === 0;
  return {
    offer_id: READINESS_REVIEW_OFFER.offer_id,
    offer_name: READINESS_REVIEW_OFFER.offer_name,
    price: READINESS_REVIEW_OFFER.price,
    can_launch,
    satisfied,
    blockers,
    external_action_taken: false,
    payment_status: PAYMENT_CONTRACT_META.activation_status,
    recommended_next_action: can_launch
      ? 'All conditions met — proceed with the separately-approved launch step.'
      : `Resolve ${blockers.length} blocker(s); start with Ray approving the offer + copy. No launch occurs automatically.`,
  };
}
