/**
 * Nexus high-risk guard registry — every Level 3 blocked action and its hard guard.
 * These default to BLOCKED. A guard may only be lifted by a separate design doc, explicit Ray
 * approval, proof plan, rollback plan, hard guard tests, and a safety contract.
 *
 * Pure / deterministic. No I/O.
 */

export type HighRiskAction =
  | 'live_trade'
  | 'broker_order'
  | 'funded_account_execution'
  | 'auto_executor_exposure'
  | 'payment_charge'
  | 'payment_refund'
  | 'ad_spend_activation'
  | 'production_deploy'
  | 'rls_weaken'
  | 'destructive_db_write'
  | 'secret_print'
  | 'env_commit'
  | 'broad_scrape'
  | 'youtube_media_download'
  | 'external_ai_sensitive_data'
  | 'bulk_send'
  | 'spam_automation'
  | 'client_data_exposure'
  | 'tenant_isolation_bypass';

export interface HighRiskGuard {
  action: HighRiskAction;
  label: string;
  default_state: 'blocked';
  why_blocked: string;
  requires_contract: boolean;
  rollback_required: boolean;
  guard_note: string;
}

function guard(action: HighRiskAction, label: string, why_blocked: string, guard_note: string): HighRiskGuard {
  return {
    action,
    label,
    default_state: 'blocked',
    why_blocked,
    requires_contract: true,
    rollback_required: true,
    guard_note,
  };
}

export const NEXUS_HIGH_RISK_GUARDS: HighRiskGuard[] = [
  guard('live_trade', 'Live trading', 'Real money at risk; irreversible market actions.', 'Trading Lab is paper-only; live trading has no execution path.'),
  guard('broker_order', 'Broker order execution', 'Direct broker orders move real funds.', 'No broker API is wired for execution.'),
  guard('funded_account_execution', 'Funded account actions', 'Funded accounts can lose real capital.', 'No funded-account execution path exists.'),
  guard('auto_executor_exposure', 'Raw auto_executor exposure', 'Raw executor could run arbitrary risky actions.', 'auto_executor is never exposed to UI or feeders.'),
  guard('payment_charge', 'Payment charge', 'Spends real money / charges customers.', 'No payment-charge path is enabled.'),
  guard('payment_refund', 'Payment refund', 'Moves real money out.', 'No refund path is enabled.'),
  guard('ad_spend_activation', 'Ad spend activation', 'Spends real money on ads.', 'Ad research only; no spend activation.'),
  guard('production_deploy', 'Production deploy', 'Can break the live system for users.', 'Deploys are manual and out of scope for automation.'),
  guard('rls_weaken', 'RLS weakening', 'Could expose tenant/customer data.', 'RLS is never weakened by automation.'),
  guard('destructive_db_write', 'Destructive DB write', 'Data loss / corruption risk.', 'Only append/insert of internal cards and proof events is used.'),
  guard('secret_print', 'Secret printing', 'Leaks credentials/tokens/cookies.', 'Scripts never print secrets; reports assert no secrets.'),
  guard('env_commit', '.env commit', 'Leaks secrets into git history.', '.env is gitignored; commits assert no .env staged.'),
  guard('broad_scrape', 'Broad scraping', 'Legal/ToS risk and resource abuse.', 'Only local samples / metadata placeholders are used.'),
  guard('youtube_media_download', 'YouTube media download', 'Copyright/ToS risk and heavy I/O.', 'Metadata/transcript-only; no media download path.'),
  guard('external_ai_sensitive_data', 'External AI on sensitive data', 'Leaks private/customer/credit data to third parties.', 'External AI is disabled for sensitive/private/customer data.'),
  guard('bulk_send', 'Bulk send', 'Mass outbound can spam and damage reputation.', 'No bulk-send path; sends are individually gated.'),
  guard('spam_automation', 'Spam automation', 'Abusive automated outreach.', 'No spam automation path exists.'),
  guard('client_data_exposure', 'Client data exposure', 'Exposes private client data externally.', 'Client data stays internal; no external exposure path.'),
  guard('tenant_isolation_bypass', 'Tenant isolation bypass', 'Cross-tenant data leakage.', 'Tenant isolation is enforced; no bypass path.'),
];

export const HIGH_RISK_ACTIONS: HighRiskAction[] = NEXUS_HIGH_RISK_GUARDS.map((g) => g.action);

export function getHighRiskGuard(action: HighRiskAction): HighRiskGuard | undefined {
  return NEXUS_HIGH_RISK_GUARDS.find((g) => g.action === action);
}

export function isHighRiskActionBlocked(action: HighRiskAction): boolean {
  const g = getHighRiskGuard(action);
  return g ? g.default_state === 'blocked' : true;
}
