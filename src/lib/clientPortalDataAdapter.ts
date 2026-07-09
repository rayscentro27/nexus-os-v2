/**
 * Nexus OS v2 — Client Portal Data Adapter
 * Prompt 2: Phase G
 *
 * Replaces mock client portal data with live Supabase queries.
 * Falls back to clearly labeled synthetic demo data when Supabase is unavailable.
 */

import { supabase, isSupabaseConfigured } from './supabaseClient';
import { resolveClientContextForCurrentUser, type ResolvedClientContext } from './clientAuthContext';

export interface ClientProfile {
  id: string;
  client_id: string;
  name: string;
  email: string;
  phone: string;
  membership_tier: string;
  status: string;
  created_at: string;
}

export interface ClientTask {
  id: string;
  client_id: string;
  task_type: string;
  title: string;
  status: string;
  priority: string;
  due_date: string;
}

export interface ReadinessScore {
  id: string;
  client_id: string;
  score_type: string;
  score: number;
  max_score: number;
  details: string;
  updated_at: string;
}

export interface ClientDocument {
  id: string;
  client_id: string;
  doc_type: string;
  filename: string;
  status: string;
  uploaded_at: string;
}

export interface BusinessProfileRequirement {
  id: string;
  client_id: string;
  requirement_type: string;
  status: string;
  details: string;
  updated_at: string;
}

export interface FundingReadinessScore {
  id: string;
  client_id: string;
  score_type: string;
  score: number;
  status: string;
  details: string;
  updated_at: string;
}

export interface ApprovedClientGuidance {
  id: string;
  client_id: string;
  guidance_type: string;
  title: string;
  body: string;
  status: string;
  created_at: string;
}

export interface PartnerOffer {
  id: string;
  title: string;
  category: string;
  status: string;
  fit_score: number;
  details: string;
  created_at: string;
}

export interface CreditWorkflowItem {
  id: string;
  client_id: string;
  item_type: string;
  title: string;
  status: string;
  utilization_pct: number;
  details: string;
  updated_at: string;
}

const DEMO_CLIENT_ID = 'client_test_julius_erving';

const SYNTHETIC_PROFILE: ClientProfile = {
  id: 'synthetic-001',
  client_id: DEMO_CLIENT_ID,
  name: 'Julius Erving (Demo)',
  email: 'demo@goclearonline.cc',
  phone: '(555) 000-0000',
  membership_tier: 'trial',
  status: 'active',
  created_at: '2026-07-05T00:00:00Z',
};

const SYNTHETIC_TASKS: ClientTask[] = [
  { id: 'task-001', client_id: DEMO_CLIENT_ID, task_type: 'credit_profile', title: 'Complete Credit Profile', status: 'pending', priority: 'high', due_date: '' },
  { id: 'task-002', client_id: DEMO_CLIENT_ID, task_type: 'business_setup', title: 'Set Up Business Profile', status: 'pending', priority: 'high', due_date: '' },
  { id: 'task-003', client_id: DEMO_CLIENT_ID, task_type: 'documents', title: 'Upload Required Documents', status: 'pending', priority: 'medium', due_date: '' },
  { id: 'task-004', client_id: DEMO_CLIENT_ID, task_type: 'funding_readiness', title: 'Complete Funding Readiness Assessment', status: 'pending', priority: 'medium', due_date: '' },
];

const SYNTHETIC_SCORES: ReadinessScore[] = [
  { id: 'score-001', client_id: DEMO_CLIENT_ID, score_type: 'overall', score: 35, max_score: 100, details: 'Getting started — complete your profile to improve score', updated_at: '2026-07-05T00:00:00Z' },
  { id: 'score-002', client_id: DEMO_CLIENT_ID, score_type: 'credit', score: 0, max_score: 100, details: 'Credit profile not yet submitted', updated_at: '2026-07-05T00:00:00Z' },
  { id: 'score-003', client_id: DEMO_CLIENT_ID, score_type: 'business', score: 10, max_score: 100, details: 'Business profile incomplete', updated_at: '2026-07-05T00:00:00Z' },
  { id: 'score-004', client_id: DEMO_CLIENT_ID, score_type: 'funding', score: 0, max_score: 100, details: 'Funding readiness not assessed', updated_at: '2026-07-05T00:00:00Z' },
];

export async function loadClientProfile(clientId?: string): Promise<{ data: ClientProfile | null; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('client_profiles')
        .select('*')
        .eq('client_id', id)
        .single();

      if (error) return { data: null, source: 'supabase' as const, error: error.message };
      if (data) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: null, source: 'supabase' as const, error: String(e) };
    }
  }

  return { data: SYNTHETIC_PROFILE, source: 'synthetic' as const };
}

export async function loadClientTasks(clientId?: string): Promise<{ data: ClientTask[]; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('client_tasks')
        .select('*')
        .eq('client_id', id);

      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }

  return { data: SYNTHETIC_TASKS, source: 'synthetic' as const };
}

export async function loadReadinessScores(clientId?: string): Promise<{ data: ReadinessScore[]; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('readiness_scores')
        .select('*')
        .eq('client_id', id);

      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }

  return { data: SYNTHETIC_SCORES, source: 'synthetic' as const };
}

export async function loadClientDocuments(clientId?: string): Promise<{ data: ClientDocument[]; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('client_documents')
        .select('*')
        .eq('client_id', id);

      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }

  return { data: [], source: 'synthetic' as const };
}

export function getClientDataSource(): 'supabase' | 'synthetic' {
  return isSupabaseConfigured ? 'supabase' : 'synthetic';
}

export async function loadBusinessProfileRequirements(clientId?: string): Promise<{ data: BusinessProfileRequirement[]; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;
  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('business_profile_requirements')
        .select('*')
        .eq('client_id', id);
      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }
  return { data: [], source: 'synthetic' as const };
}

export async function loadFundingReadinessScores(clientId?: string): Promise<{ data: FundingReadinessScore[]; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;
  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('funding_readiness_scores')
        .select('*')
        .eq('client_id', id);
      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }
  return { data: [], source: 'synthetic' as const };
}

export async function loadApprovedClientGuidance(clientId?: string): Promise<{ data: ApprovedClientGuidance[]; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;
  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('approved_client_guidance')
        .select('*')
        .eq('client_id', id);
      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }
  return { data: [], source: 'synthetic' as const };
}

export async function loadPartnerOffers(): Promise<{ data: PartnerOffer[]; source: 'supabase' | 'synthetic'; error?: string }> {
  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('partner_offers')
        .select('*')
        .limit(50);
      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }
  return { data: [], source: 'synthetic' as const };
}

export async function loadCreditWorkflowItems(clientId?: string): Promise<{ data: CreditWorkflowItem[]; source: 'supabase' | 'synthetic'; error?: string }> {
  const id = clientId || DEMO_CLIENT_ID;
  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase
        .from('credit_workflow_items')
        .select('*')
        .eq('client_id', id);
      if (error) return { data: [], source: 'supabase' as const, error: error.message };
      if (data && data.length > 0) return { data, source: 'supabase' as const };
    } catch (e) {
      return { data: [], source: 'supabase' as const, error: String(e) };
    }
  }
  return { data: [], source: 'synthetic' as const };
}

export interface ClientPortalLiveData {
  profile: ClientProfile | null;
  tasks: ClientTask[];
  scores: ReadinessScore[];
  documents: ClientDocument[];
  businessProfile: BusinessProfileRequirement[];
  fundingScores: FundingReadinessScore[];
  guidance: ApprovedClientGuidance[];
  partnerOffers: PartnerOffer[];
  creditItems: CreditWorkflowItem[];
  resolvedClientId: string | null;
  resolvedTenantId: string | null;
}

export async function loadClientPortalLiveData(forcedContext?: ResolvedClientContext): Promise<ClientPortalLiveData> {
  let ctx: ResolvedClientContext | null = forcedContext ?? null
  if (!ctx) {
    ctx = await resolveClientContextForCurrentUser()
  }
  if (!ctx) {
    return { profile: null, tasks: [], scores: [], documents: [], businessProfile: [], fundingScores: [], guidance: [], partnerOffers: [], creditItems: [], resolvedClientId: null, resolvedTenantId: null };
  }

  const id = ctx.clientId;
  const [profileRes, tasksRes, scoresRes, docsRes, bizRes, fundingRes, guidanceRes, partnerRes, creditRes] = await Promise.all([
    loadClientProfile(id),
    loadClientTasks(id),
    loadReadinessScores(id),
    loadClientDocuments(id),
    loadBusinessProfileRequirements(id),
    loadFundingReadinessScores(id),
    loadApprovedClientGuidance(id),
    loadPartnerOffers(),
    loadCreditWorkflowItems(id),
  ]);

  return {
    profile: profileRes.data,
    tasks: tasksRes.data,
    scores: scoresRes.data,
    documents: docsRes.data,
    businessProfile: bizRes.data,
    fundingScores: fundingRes.data,
    guidance: guidanceRes.data,
    partnerOffers: partnerRes.data,
    creditItems: creditRes.data,
    resolvedClientId: ctx.clientId,
    resolvedTenantId: ctx.tenantId,
  };
}
