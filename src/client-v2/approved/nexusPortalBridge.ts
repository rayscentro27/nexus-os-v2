import { getNexusClientPortalBridge, type NexusClientPortalBridge, type PortalSnapshot, type PortalActionResult } from './integration/nexusClientPortalBridge';
import type { BankabilityPillar, BusinessSetupStep, ClientProfile, ClydeMessage, DocumentItem, JourneyNode, Mission, Recommendation, ResourceItem } from './types/portal';
import { loadClientPortalLiveData } from '../../lib/clientPortalDataAdapter';
import { buildClientFundingReadiness } from '../../lib/clientFundingReadiness';
import { computeJourneyState } from '../../lib/clientJourneyModel';
import { generateClydeMessages } from '../../lib/clydeContextEngine';
import { resolveClientContextForCurrentUser } from '../../lib/clientAuthContext';
import { isSupabaseConfigured, supabase } from '../../lib/supabaseClient';
import { askClientAI } from '../../lib/clientAiGateway';

const approvedAvatar = new URL('./assets/images/client_avatar_executive_1790366592448.jpg', import.meta.url).href;
const fundingGuide = new URL('./assets/images/resource_funding_blueprint_1790366602825.jpg', import.meta.url).href;
const underwritingGuide = new URL('./assets/images/resource_underwriting_guide_1790366613726.jpg', import.meta.url).href;

const text = (value: unknown, empty = 'Not available') => {
  const result = String(value ?? '').trim();
  return result || empty;
};

const score = (rows: Array<Record<string, unknown>>, kind: string) => {
  const row = rows.find((item) => String(item.score_type || '').toLowerCase() === kind);
  return Math.max(0, Math.min(100, Number(row?.score || 0)));
};

function levelIndex(points: number) {
  if (points >= 98) return 6;
  if (points >= 93) return 5;
  if (points >= 85) return 4;
  if (points >= 71) return 3;
  if (points >= 56) return 2;
  if (points >= 36) return 1;
  return 0;
}

function statusForStage(status: string): JourneyNode['status'] {
  if (status === 'complete') return 'completed';
  if (status === 'blocked' || status === 'action_needed' || status === 'in_progress' || status === 'almost_ready') return 'in-progress';
  return 'pending';
}

function buildSnapshot(raw: Awaited<ReturnType<typeof loadClientPortalLiveData>>): PortalSnapshot {
  const profileRow = (raw.profile || {}) as Record<string, unknown>;
  const documents = (raw.documents || []) as unknown as Array<Record<string, unknown>>;
  const tasks = (raw.tasks || []) as unknown as Array<Record<string, unknown>>;
  const businessRows = (raw.businessProfile || []) as unknown as Array<Record<string, unknown>>;
  const readinessScores = (raw.scores || []) as unknown as Array<Record<string, unknown>>;
  const creditScore = score(readinessScores, 'credit');
  const businessScore = score(readinessScores, 'business');
  const fundingScore = score(readinessScores, 'funding');
  const overallScore = score(readinessScores, 'overall') || Math.round((creditScore + businessScore + fundingScore) / 3);
  const docText = (doc: Record<string, unknown>) => `${doc.doc_type || ''} ${doc.filename || ''} ${doc.title || ''} ${doc.category || ''}`.toLowerCase();
  const hasDoc = (patterns: RegExp[]) => documents.some((doc) => patterns.some((pattern) => pattern.test(docText(doc))));
  const profileText = JSON.stringify(profileRow).toLowerCase();
  const journey = computeJourneyState({
    creditScore,
    creditReportUploaded: hasDoc([/credit.?report/, /experian/, /equifax/, /transunion/]),
    hasDiscrepancies: (raw.creditItems || []).length > 0,
    strategySelected: (raw.strategyDecisions || []).some((item) => ['selected', 'authorized', 'saved'].includes(String(item.decision || '').toLowerCase())),
    businessProfileComplete: businessScore >= 80,
    entityEstablished: /entity|formation|incorporat/.test(profileText) || hasDoc([/formation/, /incorporat/, /entity/]),
    einAvailable: Boolean(profileRow.ein_status) || hasDoc([/ein/, /tax/]),
    businessAddress: Boolean(profileRow.business_address_line1) || hasDoc([/address/, /utility/, /lease/]),
    bankAccountReady: Boolean(profileRow.business_bank_account_status) || hasDoc([/bank/, /statement/]),
    revenueDocumented: hasDoc([/revenue/, /income/, /profit/, /tax/]),
    timeInBusiness: Number(profileRow.time_in_business_months || profileRow.months_in_business || 0) || undefined,
    documentsComplete: documents.length,
    documentsMissing: 0,
    reviewRequested: tasks.some((task) => String(task.category || task.task_type || '').toLowerCase() === 'review_request'),
    lastActivity: text(profileRow.updated_at, ''),
    utilizationHigh: Number(profileRow.utilization_pct || 0) > 65,
  });
  const readiness = buildClientFundingReadiness({
    profile: profileRow,
    documents,
    tasks,
    scores: { credit: creditScore, business: businessScore, funding: fundingScore },
    systemReviews: raw.systemReviews,
    strategyRecommendations: raw.strategyRecommendations,
    strategyDecisions: raw.strategyDecisions,
    journey,
  });
  const points = Math.max(0, Math.min(100, readiness.overallScore || overallScore));
  const profile: ClientProfile = {
    name: text(profileRow.preferred_name || profileRow.legal_name || profileRow.name || raw.profile?.email),
    companyName: text(profileRow.business_name || profileRow.company_name || profileRow.name),
    role: text(profileRow.role, 'Authorized client'),
    ein: text(profileRow.ein_status),
    duns: text(profileRow.duns_number || profileRow.duns),
    entityType: text(profileRow.entity_type),
    stateOfFormation: text(profileRow.business_state || profileRow.state),
    industry: text(profileRow.industry),
    naicsCode: text(profileRow.naics_code),
    memberSince: text(profileRow.created_at, ''),
    readinessPoints: points,
    readinessTarget: 100,
    currentLevelIndex: levelIndex(points),
    streakDays: 0,
    avatarUrl: approvedAvatar,
    targetFundingAmount: Number(profileRow.funding_goal_amount || 0),
  };
  const stages: Array<{ id: string; label: string; tab: JourneyNode['tab']; stage: keyof typeof readiness.stages }> = [
    { id: 'profile', label: 'Profile', tab: 'credit-profile', stage: 'credit' },
    { id: 'credit', label: 'Credit Health', tab: 'credit-profile', stage: 'credit' },
    { id: 'business-setup', label: 'Business Foundation', tab: 'business-setup', stage: 'business_foundation' },
    { id: 'bankability', label: 'Bankability', tab: 'business-bankability', stage: 'business_bankability' },
    { id: 'documents', label: 'Documents', tab: 'documents', stage: 'business_bankability' },
    { id: 'funding-readiness', label: 'Funding Ready', tab: 'funding-readiness', stage: 'funding' },
    { id: 'review', label: 'Underwriter Review', tab: 'request-review', stage: 'funding' },
  ];
  const journeyNodes: JourneyNode[] = stages.map((item) => {
    const stage = readiness.stages[item.stage];
    const stageScore = item.id === 'profile' ? businessScore : item.id === 'credit' ? creditScore : stage.contribution;
    return { id: item.id, label: item.label, tab: item.tab, status: statusForStage(stage.status), progress: stageScore, scoreWeight: Math.round(100 / stages.length), description: stage.requirements.find((req) => req.status !== 'complete')?.missing || `${item.label} status is based on persisted client data.` };
  });
  const missions: Mission[] = tasks.map((task, index) => ({
    id: text(task.id, `task-${index}`),
    title: text(task.title || task.task_type),
    category: /document/i.test(String(task.category || task.task_type)) ? 'Documents' : /credit/i.test(String(task.category || task.task_type)) ? 'Credit' : /bank/i.test(String(task.category || task.task_type)) ? 'Bankability' : /fund/i.test(String(task.category || task.task_type)) ? 'Funding' : 'Setup',
    points: 0,
    impact: String(task.priority || '').toLowerCase() === 'high' ? 'High' : 'Medium',
    timeEstimate: text(task.due_date, 'Not scheduled'),
    description: text(task.summary || task.details),
    actionText: 'Review task',
    targetTab: /document/i.test(String(task.category || task.task_type)) ? 'documents' : /credit/i.test(String(task.category || task.task_type)) ? 'credit-profile' : /fund/i.test(String(task.category || task.task_type)) ? 'funding-readiness' : 'business-setup',
    completed: ['complete', 'completed', 'done'].includes(String(task.status || '').toLowerCase()),
    status: ['complete', 'completed', 'done'].includes(String(task.status || '').toLowerCase()) ? 'Completed' : 'In Progress',
  }));
  if (!missions.length) missions.push({ id: 'no-active-task', title: 'No active client task recorded', category: 'Setup', points: 0, impact: 'Medium', timeEstimate: 'Not scheduled', description: 'No executable client task was returned by the authenticated tenant-scoped query.', actionText: 'Review readiness', targetTab: 'dashboard', completed: true, status: 'Completed' });
  const mappedDocuments: DocumentItem[] = documents.map((doc, index) => {
    const rawStatus = `${doc.status || ''} ${doc.document_status || ''} ${doc.goclear_review_status || ''}`.toLowerCase();
    const status: DocumentItem['status'] = /verified|approved|complete/.test(rawStatus) ? 'verified' : /review|pending|processing/.test(rawStatus) ? 'reviewing' : /required|missing|needs/.test(rawStatus) ? 'required' : 'optional';
    return { id: text(doc.id, `document-${index}`), title: text(doc.filename || doc.title || doc.doc_type), category: text(doc.doc_type || doc.category), status, requiredFor: text(doc.recommended_next_action), fileName: text(doc.filename, ''), updatedAt: text(doc.uploaded_at || doc.created_at, 'Not available'), notes: text(doc.summary, '') };
  });
  const missingRequirements = readiness.outstandingRequirements.map((label, index) => ({ id: `missing-${index}`, title: label, category: 'Readiness requirement', status: 'required' as const, requiredFor: 'Client readiness', updatedAt: 'Action required', notes: 'No corresponding completed record was returned by the live client-scoped data query.' }));
  const bankabilityPillars: BankabilityPillar[] = Object.values(readiness.stages).slice(0, 3).map((stage) => ({ id: `pillar-${stage.id}`, name: stage.label, score: stage.contribution, maxScore: 100, weight: `${Math.round(100 / 3)}%`, status: stage.status === 'complete' ? 'strong' : stage.status === 'almost_ready' ? 'good' : stage.status === 'action_needed' ? 'needs-attention' : 'critical', details: stage.requirements.find((req) => req.status !== 'complete')?.missing || 'All returned requirements are complete.', keyItems: stage.requirements.slice(0, 4).map((req) => ({ label: req.label, pass: req.status === 'complete' })) }));
  const setupSteps: BusinessSetupStep[] = businessRows.map((row, index) => ({ id: text(row.id, `setup-${index}`), stepNumber: index + 1, title: text(row.requirement_type || row.title), field: text(row.requirement_type), value: text(row.details, ''), status: /complete|verified|approved/.test(String(row.status || '').toLowerCase()) ? 'completed' : /pending|missing/.test(String(row.status || '').toLowerCase()) ? 'pending' : 'attention', whyItMatters: 'Persisted business setup requirement.', readinessImpact: text(row.status), points: 0 }));
  const recommendations: Recommendation[] = (raw.strategyRecommendations || []).map((row, index) => ({ id: text(row.id, `recommendation-${index}`), title: text(row.title || row.strategy_id), priority: 'IMPORTANT', category: 'Nexus recommendation', impactScore: 'Not calculated', reason: text(row.reason || row.summary || row.status), actionLabel: 'Review recommendation', tabTarget: 'credit-profile', clydePrompt: text(row.title || row.strategy_id) }));
  const resources: ResourceItem[] = (raw.guidance || []).map((row, index) => ({ id: text(row.id, `resource-${index}`), title: text(row.title), type: 'Executive Guide', duration: 'Read in portal', stage: 'Client readiness', summary: text(row.body), author: 'GoClear', imageThumbnail: index % 2 ? underwritingGuide : fundingGuide }));
  const clydeMessages: ClydeMessage[] = generateClydeMessages({ route: '/client/dashboard', stage: journey.currentStage, journey, documents: mappedDocuments.map((doc) => ({ id: doc.id, category: doc.category, title: doc.title, status: doc.status })), profileComplete: businessScore >= 80, primaryBlocker: readiness.primaryBlocker, nextAction: readiness.nextBestAction, readinessState: readiness.state, missingFacts: readiness.missingDocuments, evidenceState: [] }).map((message, index) => ({ id: message.id || `clyde-${index}`, sender: 'clyde', text: message.text, timestamp: 'Live client context', card: index === 0 && readiness.primaryBlocker ? { type: 'blocker', title: 'Current readiness blocker', description: readiness.primaryBlocker, actionText: 'Open next action', actionTab: 'funding-readiness' } : undefined }));
  return { profile, journeyNodes, missions, documents: [...mappedDocuments, ...missingRequirements], bankabilityPillars, setupSteps, recommendations, resources, clydeMessages, simulatedBalance: Number(profileRow.revolving_balance || 0), facts: { creditScore, utilizationPercent: Number(profileRow.utilization_pct || 0), utilizationTargetPercent: Number(profileRow.utilization_target_pct || 10), documentVerifiedCount: mappedDocuments.filter((doc) => doc.status === 'verified').length, documentTotalCount: mappedDocuments.length + missingRequirements.length, bankabilityScore: readiness.stages.business_bankability.contribution, fundingTargetLabel: text(profileRow.funding_goal_range || profileRow.funding_goal_amount, 'No funding target recorded') } };
}

async function uploadDocument(file: File | undefined, fileName: string) {
  if (!file || !supabase || !isSupabaseConfigured) return { ok: false, error: 'A live file upload requires an authenticated Supabase session.' };
  const { data: { user } } = await supabase.auth.getUser();
  const context = await resolveClientContextForCurrentUser();
  if (!user || !context) return { ok: false, error: 'Could not resolve the authenticated client context.' };
  const safeName = fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
  const path = `${user.id}/${Date.now()}_${safeName}`;
  const storage = await supabase.storage.from('client-documents').upload(path, file, { cacheControl: '3600', upsert: false });
  if (storage.error) return { ok: false, error: storage.error.message };
  const { error } = await supabase.from('client_documents').insert({ id: `${user.id}_${Date.now()}`, tenant_id: context.tenantId, client_id: context.clientId, category: 'other', title: fileName, summary: `Client portal upload stored at ${path}`, status: 'uploaded', client_visible: true, approval_required: true, goclear_review_status: 'pending_review', source: 'approved_client_portal', source_concept: 'document_upload', created_at: new Date().toISOString(), payload: { storage_path: path, file_size: file.size, mime_type: file.type } });
  return error ? { ok: false, error: error.message } : { ok: true };
}

export function createNexusPortalBridge(): NexusClientPortalBridge {
  return {
    mode: 'live',
    loadSnapshot: async () => buildSnapshot(await loadClientPortalLiveData()),
    uploadDocument: async (_docId, fileName, file): Promise<PortalActionResult> => uploadDocument(file, fileName),
    completeMission: async (missionId) => ({ ok: Boolean(missionId), error: 'Mission completion is recorded only when the existing client workflow supports it.' }),
    toggleSetupStep: async (stepId) => ({ ok: Boolean(stepId), error: 'Business setup updates remain governed by existing client workflow permissions.' }),
    updateRevolvingBalance: async () => ({ ok: false, error: 'Revolving balance updates are not connected to a live client write path.' }),
    sendClydeQuery: async (query) => {
      const result = await askClientAI(query, 'approved-client-portal-clyde', 'clyde');
      if (!result.ok) return { ok: false, error: result.error };
      return { ok: true, data: { id: `clyde-${Date.now()}`, sender: 'clyde', text: String(result.data?.answer || 'Clyde could not answer that safely right now.'), timestamp: 'Just now' } };
    },
    requestUnderwritingReview: async (notes) => {
      if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'Supabase is not configured.' };
      const context = await resolveClientContextForCurrentUser();
      if (!context) return { ok: false, error: 'Could not resolve the authenticated client context.' };
      const { data: active, error: activeError } = await supabase.from('client_tasks').select('id').eq('client_id', context.clientId).eq('category', 'review_request').in('status', ['pending_admin_review', 'in_review']).limit(1);
      if (activeError) return { ok: false, error: activeError.message };
      if (active?.[0]) return { ok: true };
      const { error } = await supabase.from('client_tasks').insert({ id: `${context.authUserId}_review_request_${Date.now()}`, tenant_id: context.tenantId, client_id: context.clientId, category: 'review_request', title: 'Client requested GoClear readiness review', summary: notes || 'Client submitted a review request from the approved portal.', status: 'pending_admin_review', priority: 'high', risk_level: 'medium', automation_level: 'manual', client_visible: true, approval_required: true, goclear_review_status: 'pending_admin_review', source: 'approved_client_portal', source_concept: 'request_review', recommended_next_action: 'Admin review readiness and respond via approved client guidance', created_at: new Date().toISOString() });
      return error ? { ok: false, error: error.message } : { ok: true };
    },
  };
}

export function clearNexusPortalBridge() {
  if (typeof window !== 'undefined') delete window.__NEXUS_CLIENT_PORTAL_BRIDGE__;
}

export function installNexusPortalBridge() {
  if (typeof window !== 'undefined') window.__NEXUS_CLIENT_PORTAL_BRIDGE__ = createNexusPortalBridge();
  return getNexusClientPortalBridge();
}
