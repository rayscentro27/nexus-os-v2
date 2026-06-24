/**
 * Hermes intent + firewall router (pure, deterministic, no side effects).
 *
 * Hermes is an internet-connected conversational advisor and report interpreter — NOT a command
 * bot. The free-form replies come from a real chat/search provider (see hermesProviders.ts); this
 * module only CLASSIFIES intent and enforces the safety firewall:
 *   • requests to view/reveal sensitive data            → refuse (never read it)
 *   • privileged actions (reset password/publish/send/   → propose an approval-gated task_request
 *     trade/deploy) and public build actions               routed to a private/internal worker
 *   • Ray's explicit approval                            → create the task_request (the real gate)
 *   • report reading                                     → safe internal-summary interpretation
 *   • public/current-info questions                      → public search
 *   • everything else                                    → normal conversation (chat provider)
 *
 * Rule (per Ray): Hermes must not AUTO-create tasks from normal conversation. It may create a
 * structured task_request ONLY after Ray clearly approves.
 */

import type { Sensitivity } from './dataScopes';
import { containsSensitive } from './dataScopes';

export type HermesMode = 'conversation' | 'report_reader' | 'task_request';

export const MODE_DESC: Record<HermesMode, string> = {
  conversation: 'normal conversation + public search; no Nexus private data; no automatic tasks',
  report_reader: 'reads only safe reports / internal summaries and explains them; no execution',
  task_request: 'creates structured task requests only after your approval; no execution',
};

export type HermesIntent =
  | 'sensitive_refusal'   // asked to view/reveal private data → refuse
  | 'privileged_action'   // reset password / publish / send / trade / deploy → propose private task
  | 'public_action'       // build a public-safe thing (landing page, content) → propose task
  | 'action_approval'     // Ray approves → create the task_request
  | 'approval_review'     // review pending approval queue details, read-only
  | 'report_read'         // read + explain a safe Nexus report
  | 'public_info'         // current/public info → needs public search
  | 'conversation';       // normal conversation → chat provider

export interface ProposedTask {
  task_type: string;
  sensitivity: Sensitivity;
  allowed_data_scope: Sensitivity[];
  forbidden_data: string[];
  assigned_worker_type: string;
  hermes_visibility: 'status_only' | 'summary';
  payload: Record<string, unknown>;
  summary: string;        // plain-English description Hermes uses when proposing the task
}

/** "switch to conversation/report/task mode" → target mode, else null. */
export function detectModeSwitch(text: string): HermesMode | null {
  const t = (text || '').toLowerCase();
  if (/\b(switch to |go to |enter |back to )?(conversation|chat) mode\b/.test(t)) return 'conversation';
  if (/\b(switch to |go to |enter )?report( reader)? mode\b/.test(t)) return 'report_reader';
  if (/\b(switch to |go to |enter )?task( request)? mode\b/.test(t)) return 'task_request';
  return null;
}

const APPROVAL_RE = /\b(approved?|i approve|go ahead|do it|yes|yes please|create it|create (the|this|that)\b|proceed|send it|confirmed)\b/i;
export function isApproval(text: string): boolean {
  return APPROVAL_RE.test(text || '');
}

const CANCEL_RE = /\b(never mind|nevermind|cancel|stop|not now|forget it|hold off)\b/i;
export function isCancel(text: string): boolean {
  return CANCEL_RE.test(text || '');
}

const MODIFY_RE = /\b(change it to|make it|update it|revise it|adjust it)\b/i;
export function isModification(text: string): boolean {
  return MODIFY_RE.test(text || '');
}

function isPrivilegedAction(t: string): boolean {
  return /\breset .*(password|login|account)\b/.test(t)
    || /\b(publish|post (it|this|to)|go live)\b/.test(t)
    || /\bsend (an? )?(email|telegram|message|dm|text)\b/.test(t)
    || /\b(buy|sell|execute (a )?trade|place (a )?trade|go (long|short)|live trade)\b/.test(t)
    || /\b(deploy|ship to prod|restart (the )?(server|service))\b/.test(t);
}

/** Asked to VIEW/REVEAL sensitive data (vs. perform a privileged action through a worker). */
function isRevealSensitive(t: string): boolean {
  if (!containsSensitive(t)) return false;
  return /\b(what'?s|what is|show|tell|give|read|reveal|look up|get|fetch|display)\b/.test(t);
}

function isPublicActionProposal(t: string): boolean {
  if (/\bexamples? of\b|\bcompare\b|\bresearch\b|what do you think/.test(t)) return false; // those are search/chat
  return /\b(create|build|make|set up|draft|prepare|spin up) (me )?(a |an |the )?(landing page|task|campaign|funnel|content|post|offer|workflow|sequence)\b/.test(t);
}

function isPublicInfo(t: string): boolean {
  if (/\b(who (won|played|is winning|scored)|score of|world cup|super bowl|last night|today'?s (game|news|weather|price)|current (price|news|weather|score)|latest news|right now|stock price)\b/.test(t))
    return true;
  return /\bexamples? of\b|\bcompetitor research\b|\bbusiness research\b|\bcompare .*(tools?|platforms?|options?|apps?)\b|\bbest (tools?|platforms?|apps?) for\b|\blanding page examples?\b/.test(t);
}

function isApprovalReview(t: string): boolean {
  return /\b(approvals? waiting|pending approvals?|review (my |all )?approvals?|walk me through approvals?|show me approval|what needs my approval|what should i approve|approval queue|approve queue)\b/.test(t);
}

export function classify(text: string): HermesIntent {
  const t = (text || '').toLowerCase().trim();

  // 0. Read-only approval queue review. This must not execute approval decisions.
  if (isApprovalReview(t)) return 'approval_review';

  // 1. Privileged action verbs first — so "reset Jane's password" is an action (private worker),
  //    not a request to reveal a password. Approval of a privileged action creates the task.
  if (isPrivilegedAction(t)) return isApproval(t) ? 'action_approval' : 'privileged_action';

  // 2. Request to view/reveal sensitive data → always refuse.
  if (isRevealSensitive(t)) return 'sensitive_refusal';

  // 3. Explicit approval to create a (public-safe) task.
  if (isApproval(t) && /\btask\b|landing page|campaign|content/.test(t)) return 'action_approval';

  // 4. A public action that needs approval first.
  if (isPublicActionProposal(t)) return 'public_action';

  // 5. Report reading / interpretation.
  if (/\b(read|explain|interpret|summari[sz]e|what does|break down).*(report|nexus|status|summary|numbers?)\b/.test(t)
      || /\blatest (nexus )?report\b/.test(t))
    return 'report_read';

  // 6. Public / current-info question (needs search).
  if (isPublicInfo(t)) return 'public_info';

  // 7. Default: normal conversation (chat provider).
  return 'conversation';
}

/** Builds the approval-gated task for a privileged/public action, or null if none applies. */
export function proposeTask(text: string): ProposedTask | null {
  const t = (text || '').toLowerCase();
  const base = (o: Partial<ProposedTask>): ProposedTask => ({
    task_type: 'public_build_task',
    sensitivity: 'public',
    allowed_data_scope: ['public'],
    forbidden_data: [],
    assigned_worker_type: 'general_worker',
    hermes_visibility: 'summary',
    payload: { request: text },
    summary: '',
    ...o,
  });

  if (/\breset .*(password|login|account)\b/.test(t))
    return base({
      task_type: 'auth_password_reset', sensitivity: 'auth_sensitive',
      allowed_data_scope: ['auth_sensitive'], forbidden_data: ['password', 'reset_token', 'otp'],
      assigned_worker_type: 'private_auth_worker', hermes_visibility: 'status_only',
      summary: 'a private auth task to reset the account — handled by an internal, non-internet worker. I never see the password or reset token; I only get a status update.',
    });

  if (/\b(publish|post (it|this|to)|go live)\b/.test(t))
    return base({
      task_type: 'publish_request', sensitivity: 'internal_summary',
      allowed_data_scope: ['public', 'internal_summary'], forbidden_data: ['customer_private'],
      assigned_worker_type: 'private_publish_worker', hermes_visibility: 'summary',
      summary: 'a publish task — nothing goes live without your explicit approval, and I don’t publish directly.',
    });

  if (/\bsend (an? )?(email|telegram|message|dm|text)\b/.test(t))
    return base({
      task_type: 'send_message', sensitivity: 'customer_private',
      allowed_data_scope: ['internal_summary'], forbidden_data: ['customer_private'],
      assigned_worker_type: 'private_comms_worker', hermes_visibility: 'status_only',
      summary: 'a private comms task — an internal worker handles the recipient and contents; I only see status.',
    });

  if (/\b(buy|sell|execute (a )?trade|place (a )?trade|go (long|short)|live trade)\b/.test(t))
    return base({
      task_type: 'trading_request', sensitivity: 'trading_sensitive',
      allowed_data_scope: ['internal_summary'], forbidden_data: ['trading_sensitive'],
      assigned_worker_type: 'private_trading_worker', hermes_visibility: 'status_only',
      summary: 'a private trading task (paper/education only) — an internal worker handles it; I only see status.',
    });

  if (/\b(deploy|ship to prod|restart (the )?(server|service))\b/.test(t))
    return base({
      task_type: 'deploy_request', sensitivity: 'internal_summary',
      allowed_data_scope: ['internal_summary'], forbidden_data: ['secrets'],
      assigned_worker_type: 'private_ops_worker', hermes_visibility: 'status_only',
      summary: 'a private ops/deploy task — an internal worker handles it; nothing deploys without your approval.',
    });

  // Public-safe build (landing page, content, campaign, research task).
  if (/\b(landing page|campaign|funnel|content|post|offer|workflow|sequence|task)\b/.test(t))
    return base({
      task_type: 'public_build_task',
      summary: 'a public-safe task (no private data) for the general worker.',
    });

  return null;
}
