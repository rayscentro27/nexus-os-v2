import { supabase, isSupabaseConfigured } from './supabaseClient';
import { trackEvent } from './clientAnalytics';

export type InvitationStatus = 'draft' | 'awaiting_approval' | 'approved' | 'sent' | 'accepted' | 'expired' | 'revoked' | 'completed' | 'failed';
export type TestingLevel = 'friends_family_free' | 'friends_family_one_dollar' | 'synthetic_internal' | 'invited_test_mode' | 'controlled_live_pilot';

export const TESTER_INVITATION_PAYMENT_GUARDS = {
  friends_family_one_dollar: true,
  controlled_live_pilot: false,
  public_live: false,
} as const;

export interface TesterInvitation {
  id: string;
  tester_name: string;
  tester_email: string;
  testing_level: TestingLevel;
  assigned_persona: string | null;
  assigned_client_id: string | null;
  invitation_status: InvitationStatus;
  token_last_four: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  completed_at: string | null;
  auth_user_id: string | null;
  max_sessions: number;
  sessions_used: number;
  task_checklist_version: string;
  build_commit: string | null;
  payment_offer_slug: string | null;
  payment_mode: string;
  allowlisted_for_pilot: boolean;
  resend_count: number;
  last_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ValidatedInvitation {
  id: string;
  tester_name: string;
  tester_email: string;
  testing_level: string;
  assigned_persona: string | null;
  assigned_client_id: string | null;
  payment_offer_slug: string | null;
  payment_mode: string;
  allowlisted_for_pilot: boolean;
  expires_at: string;
  terms_version: string;
  consent_version: string;
  task_checklist_version: string;
}

export async function createTesterInvitation(input: {
  testerName: string;
  testerEmail: string;
  testingLevel?: TestingLevel;
  assignedPersona?: string;
  maxSessions?: number;
  taskChecklistVersion?: string;
  paymentOfferSlug?: string;
  paymentMode?: string;
  expiresInDays?: number;
}) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('create-tester-invitation', { body: input });
  if (error) return { ok: false, error: error.message || 'creation_failed' } as const;
  trackEvent({ event: 'invitation_created', route: '/admin', detail: input.testingLevel || 'invited_test_mode' });
  return { ok: true, data } as const;
}

export async function createGuestInvitation(input: { name: string; email: string; expiresInDays?: number; note?: string }) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('create-guest-invitation', { body: input });
  if (error) return { ok: false, error: error.message || 'creation_failed' } as const;
  trackEvent({ event: 'invitation_created', route: '/admin', detail: 'GUEST_FREE' });
  return { ok: true, data } as const;
}

export async function acceptGuestInvitation(input: { token: string; password: string; consentAccepted: boolean; name?: string }) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('accept-guest-invitation', { body: input });
  if (error) return { ok: false, error: error.message || 'acceptance_failed' } as const;
  trackEvent({ event: 'invitation_accepted', route: '/guest/accept', detail: 'FREE_GUEST' });
  return { ok: true, data } as const;
}

export async function loadGuestInvitations() {
  if (!supabase || !isSupabaseConfigured) return { invitations: [], error: 'not_configured' } as const;
  const { data, error } = await supabase.from('guest_invitations').select('id,name,email,invite_type,access_tier,status,created_at,expires_at,used_at,provider_message_id').order('created_at', { ascending: false }).limit(100);
  return { invitations: data || [], error: error?.message } as const;
}

export async function loadCustomerCommunications() {
  if (!supabase || !isSupabaseConfigured) return { communications: [], error: 'not_configured' } as const;
  const { data, error } = await supabase.from('customer_communications').select('id,template_id,trigger,recipient,status,created_at,sent_at,provider_message_id,related_invite_id').order('created_at', { ascending: false }).limit(100);
  return { communications: data || [], error: error?.message } as const;
}

export async function loadClientAiAdminState() {
  if (!supabase || !isSupabaseConfigured) return { conversations: [], escalations: [], error: 'not_configured' } as const;
  const [conversations, escalations, controls] = await Promise.all([
    supabase.from('client_ai_conversations').select('id,client_id,intent,policy_decision,model_tier,estimated_cost_class,created_at').order('created_at', { ascending: false }).limit(100),
    supabase.from('client_ai_escalations').select('id,client_id,intent,recommended_owner,priority,status,created_at').order('created_at', { ascending: false }).limit(100),
    supabase.from('client_ai_controls').select('id,tenant_id,client_id,user_id,clyde_enabled,customer_service_ai_enabled,access_tier,token_daily_limit,session_limit,expensive_call_limit,escalation_only_mode,client_ai_paused,guest_access_revoked,convert_to_paid_workflow,updated_at').order('updated_at', { ascending: false }).limit(100),
  ]);
  return { conversations: conversations.data || [], escalations: escalations.data || [], controls: controls.data || [], error: conversations.error?.message || escalations.error?.message || controls.error?.message } as const;
}

export async function updateClientAiControls(input: { tenant_id: string; client_id: string } & Record<string, unknown>) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('manage-client-ai-controls', { body: input });
  if (error) return { ok: false, error: error.message || 'controls_update_failed' } as const;
  return { ok: true, data } as const;
}

export async function validateInviteToken(token: string) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('validate-invite-token', { body: { token } });
  if (error) return { ok: false, error: error.message || 'validation_failed' } as const;
  return { ok: true, data } as const;
}

export async function acceptTesterInvitation(input: { token: string; password: string; consentAccepted: boolean }) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('accept-tester-invitation', { body: input });
  if (error) return { ok: false, error: error.message || 'acceptance_failed' } as const;
  trackEvent({ event: 'invitation_accepted', route: '/tester/accept', detail: 'password_setup' });
  return { ok: true, data } as const;
}

export async function resendTesterInvitation(invitationId: string) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('send-tester-invitation', { body: { invitationId } });
  if (error) return { ok: false, error: error.message || 'resend_failed' } as const;
  trackEvent({ event: 'invitation_sent', route: '/admin', detail: invitationId });
  return { ok: true, data } as const;
}

export async function revokeTesterInvitation(invitationId: string, reason?: string) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('revoke-tester-invitation', { body: { invitationId, reason } });
  if (error) return { ok: false, error: error.message || 'revoke_failed' } as const;
  trackEvent({ event: 'invitation_revoked', route: '/admin', detail: invitationId });
  return { ok: true, data } as const;
}

export async function createInvitedCheckout(input: {
  offerSlug: string;
  invitationToken: string;
  termsAccepted: boolean;
  termsVersion: string;
}) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('create-invited-checkout', { body: input });
  if (error) return { ok: false, error: error.message || 'checkout_failed' } as const;
  trackEvent({ event: 'test_checkout_started', route: '/tester/tasks', detail: input.offerSlug });
  return { ok: true, data } as const;
}

export async function loadTesterInvitations() {
  if (!supabase || !isSupabaseConfigured) return { invitations: [], error: 'not_configured' } as const;
  const { data, error } = await supabase
    .from('tester_invitations')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(100);
  return { invitations: (data || []) as TesterInvitation[], error: error?.message };
}

export async function loadPilotControls() {
  if (!supabase || !isSupabaseConfigured) return { controls: null, error: 'not_configured' } as const;
  const { data, error } = await supabase
    .from('payment_pilot_controls')
    .select('*')
    .eq('id', 'singleton')
    .maybeSingle();
  return { controls: data, error: error?.message };
}

export async function updatePilotControls(updates: Record<string, unknown>) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'not_configured' } as const;
  const { error } = await supabase
    .from('payment_pilot_controls')
    .update(updates)
    .eq('id', 'singleton');
  if (error) return { ok: false, error: error.message } as const;
  return { ok: true } as const;
}
