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
  document_status?: string;
  analysis_status?: string;
  strategy_status?: string;
  client_action_status?: string;
  exception_review_status?: string;
  mail_status?: string;
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
      if (data && data.length > 0) {
        const documentIds=data.map((row:Record<string,unknown>)=>String(row.id));
        const {data:workflows}=await supabase.from('credit_document_workflows').select('document_id,document_status,analysis_status,strategy_status,client_action_status,exception_review_status,mail_status').in('document_id',documentIds);
        const byDocument=Object.fromEntries((workflows||[]).map((row:Record<string,unknown>)=>[row.document_id,row]));
        return { data: data.map((row:Record<string,unknown>)=>({...row,...(byDocument[String(row.id)]||{})})) as unknown as ClientDocument[], source: 'supabase' as const };
      }
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

export interface ProfileIntakeData {
  legal_name: string;
  preferred_name: string;
  phone: string;
  mailing_address_line1: string;
  mailing_address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  business_name: string;
  entity_type: string;
  ein_status: string;
  industry: string;
  naics_code: string;
  business_address_line1: string;
  business_address_line2: string;
  business_city: string;
  business_state: string;
  business_postal_code: string;
  time_in_business: string;
  monthly_revenue_range: string;
  funding_goal_range: string;
}

const EMPTY_PROFILE_INTAKE: ProfileIntakeData = {
  legal_name: '', preferred_name: '', phone: '',
  mailing_address_line1: '', mailing_address_line2: '', city: '', state: '', postal_code: '',
  business_name: '', entity_type: '', ein_status: '', industry: '', naics_code: '',
  business_address_line1: '', business_address_line2: '', business_city: '', business_state: '', business_postal_code: '',
  time_in_business: '', monthly_revenue_range: '', funding_goal_range: '',
};

const PROFILE_INTAKE_COLUMNS = [
  'legal_name', 'preferred_name', 'phone',
  'mailing_address_line1', 'mailing_address_line2', 'city', 'state', 'postal_code',
  'business_name', 'entity_type', 'ein_status', 'industry', 'naics_code',
  'business_address_line1', 'business_address_line2', 'business_city', 'business_state', 'business_postal_code',
  'time_in_business', 'monthly_revenue_range', 'funding_goal_range',
].join(',');

function profileCompleteness(data: ProfileIntakeData): number {
  const fields = Object.values(data);
  const filled = fields.filter(f => f && f.trim() !== '').length;
  return Math.round((filled / fields.length) * 100);
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
  systemReviews: Array<Record<string, unknown>>;
  strategyRecommendations: Array<Record<string, unknown>>;
  strategyDecisions: Array<Record<string, unknown>>;
  resolvedClientId: string | null;
  resolvedTenantId: string | null;
}

export async function loadClientPortalLiveData(forcedContext?: ResolvedClientContext): Promise<ClientPortalLiveData> {
  let ctx: ResolvedClientContext | null = forcedContext ?? null
  if (!ctx) {
    ctx = await resolveClientContextForCurrentUser()
  }
  if (!ctx) {
    return { profile: null, tasks: [], scores: [], documents: [], businessProfile: [], fundingScores: [], guidance: [], partnerOffers: [], creditItems: [], systemReviews: [], strategyRecommendations: [], strategyDecisions: [], resolvedClientId: null, resolvedTenantId: null };
  }

  const id = ctx.clientId;
  const [profileRes, tasksRes, scoresRes, docsRes, bizRes, fundingRes, guidanceRes, partnerRes, creditRes, systemReviewRes, strategyRes, decisionRes] = await Promise.all([
    loadClientProfile(id),
    loadClientTasks(id),
    loadReadinessScores(id),
    loadClientDocuments(id),
    loadBusinessProfileRequirements(id),
    loadFundingReadinessScores(id),
    loadApprovedClientGuidance(id),
    loadPartnerOffers(),
    loadCreditWorkflowItems(id),
    supabase!.from('credit_report_system_reviews').select('id,status,summary,utilization_actions,report_item_reviews,evidence_needed,recommended_next_steps,tier_1_impact,tier_2_impact').eq('client_id', id).eq('client_visible', true).eq('status', 'approved_summary').order('created_at', { ascending: false }).limit(1),
    supabase!.from('credit_strategy_recommendations').select('id,canonical_account_id,discrepancy_id,strategy_id,strategy_version,status,confidence,payload,created_at').eq('client_id', id).eq('client_visible', true).order('created_at', { ascending: false }).limit(50),
    supabase!.from('credit_strategy_client_decisions').select('id,recommendation_id,decision,new_state,created_at').eq('client_id', id).order('created_at', { ascending: false }).limit(100),
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
    systemReviews: (systemReviewRes.data || []) as Array<Record<string, unknown>>,
    strategyRecommendations: (strategyRes.data || []) as Array<Record<string, unknown>>,
    strategyDecisions: (decisionRes.data || []) as Array<Record<string, unknown>>,
    resolvedClientId: ctx.clientId,
    resolvedTenantId: ctx.tenantId,
  };
}

export async function saveCreditStrategyDecision(input:{recommendationId:string;tenantId:string;clientId:string;decision:'viewed'|'selected'|'declined'|'saved'|'evidence_requested'|'evidence_uploaded'|'draft_requested'|'draft_reviewed'|'authorized'|'escalated';notes?:string;newState?:Record<string,unknown>}) {
  if (!supabase || !isSupabaseConfigured) return { ok:false, error:'Supabase not configured' }
  const { error } = await supabase.from('credit_strategy_client_decisions').insert({ recommendation_id:input.recommendationId, tenant_id:input.tenantId, client_id:input.clientId, actor_type:'client', decision:input.decision, notes:input.notes||null, previous_state:{}, new_state:input.newState||{} })
  return error ? { ok:false, error:error.message } : { ok:true }
}

export async function requestCreditStrategyTool(input:{recommendationId:string;tenantId:string;clientId:string;toolType:string}) {
  if (!supabase || !isSupabaseConfigured) return { ok:false, error:'Supabase not configured' }
  const { error } = await supabase.from('credit_strategy_tool_requests').insert({ recommendation_id:input.recommendationId, tenant_id:input.tenantId, client_id:input.clientId, tool_type:input.toolType, status:'requested', client_authorized:false, docupost_authorized:false })
  return error ? { ok:false, error:error.message } : { ok:true }
}

export async function loadClientProfileIntake(forcedContext?: ResolvedClientContext): Promise<{ data: ProfileIntakeData; source: 'supabase' | 'synthetic'; error?: string }> {
  let ctx: ResolvedClientContext | null = forcedContext ?? null
  if (!ctx) ctx = await resolveClientContextForCurrentUser()
  if (!ctx) return { data: EMPTY_PROFILE_INTAKE, source: 'synthetic' as const, error: 'No authenticated client context' }

  if (!isSupabaseConfigured || !supabase) {
    return { data: EMPTY_PROFILE_INTAKE, source: 'synthetic' as const }
  }

  try {
    const result = await supabase
      .from('client_profiles')
      .select(PROFILE_INTAKE_COLUMNS)
      .eq('client_id', ctx.clientId)
      .single()

    if (result.error) return { data: EMPTY_PROFILE_INTAKE, source: 'supabase' as const, error: result.error.message }
    if (!result.data) return { data: EMPTY_PROFILE_INTAKE, source: 'supabase' as const }

    const row = result.data as unknown as Record<string, unknown>
    const intake: ProfileIntakeData = {
      legal_name: String(row.legal_name || row.client_label || ''),
      preferred_name: String(row.preferred_name || ''),
      phone: String(row.phone || ''),
      mailing_address_line1: String(row.mailing_address_line1 || ''),
      mailing_address_line2: String(row.mailing_address_line2 || ''),
      city: String(row.city || ''),
      state: String(row.state || ''),
      postal_code: String(row.postal_code || ''),
      business_name: String(row.business_name || row.title || ''),
      entity_type: String(row.entity_type || ''),
      ein_status: String(row.ein_status || ''),
      industry: String(row.industry || ''),
      naics_code: String(row.naics_code || ''),
      business_address_line1: String(row.business_address_line1 || ''),
      business_address_line2: String(row.business_address_line2 || ''),
      business_city: String(row.business_city || ''),
      business_state: String(row.business_state || ''),
      business_postal_code: String(row.business_postal_code || ''),
      time_in_business: String(row.time_in_business || ''),
      monthly_revenue_range: String(row.monthly_revenue_range || ''),
      funding_goal_range: String(row.funding_goal_range || ''),
    }
    return { data: intake, source: 'supabase' as const }
  } catch (e) {
    return { data: EMPTY_PROFILE_INTAKE, source: 'supabase' as const, error: String(e) }
  }
}

export async function saveClientProfileIntake(payload: ProfileIntakeData, forcedContext?: ResolvedClientContext): Promise<{ ok: boolean; error?: string }> {
  let ctx: ResolvedClientContext | null = forcedContext ?? null
  if (!ctx) ctx = await resolveClientContextForCurrentUser()
  if (!ctx) return { ok: false, error: 'No authenticated client context. Please sign in again.' }

  if (!isSupabaseConfigured || !supabase) {
    return { ok: false, error: 'Supabase is not configured.' }
  }

  const updatePayload = {
    legal_name: payload.legal_name || null,
    preferred_name: payload.preferred_name || null,
    phone: payload.phone || null,
    mailing_address_line1: payload.mailing_address_line1 || null,
    mailing_address_line2: payload.mailing_address_line2 || null,
    city: payload.city || null,
    state: payload.state || null,
    postal_code: payload.postal_code || null,
    business_name: payload.business_name || null,
    entity_type: payload.entity_type || null,
    ein_status: payload.ein_status || null,
    industry: payload.industry || null,
    naics_code: payload.naics_code || null,
    business_address_line1: payload.business_address_line1 || null,
    business_address_line2: payload.business_address_line2 || null,
    business_city: payload.business_city || null,
    business_state: payload.business_state || null,
    business_postal_code: payload.business_postal_code || null,
    time_in_business: payload.time_in_business || null,
    monthly_revenue_range: payload.monthly_revenue_range || null,
    funding_goal_range: payload.funding_goal_range || null,
    updated_at: new Date().toISOString(),
  }

  try {
    const { error } = await supabase
      .from('client_profiles')
      .update(updatePayload)
      .eq('client_id', ctx.clientId)

    if (error) return { ok: false, error: error.message }
    return { ok: true }
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}

export function checkProfileIntakeComplete(data: ProfileIntakeData): { complete: boolean; percent: number; missingFields: string[] } {
  const missingFields: string[] = []
  const required: [keyof ProfileIntakeData, string][] = [
    ['legal_name', 'Legal name'],
    ['phone', 'Phone'],
    ['business_name', 'Business name'],
    ['entity_type', 'Entity type'],
    ['industry', 'Industry'],
  ]
  for (const [key, label] of required) {
    if (!data[key] || data[key].trim() === '') missingFields.push(label)
  }
  return { complete: missingFields.length === 0, percent: profileCompleteness(data), missingFields }
}
