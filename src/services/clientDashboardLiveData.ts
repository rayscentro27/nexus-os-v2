import { clientDataMode } from '../data/clientDataMode';
import { listTableDetailed, type ConnectionStatus, type Row } from './db';
import { resolveClientContextForCurrentUser, type ResolvedClientContext } from '../lib/clientAuthContext';

export interface ClientDashboardLiveResult {
  enabled: boolean;
  status: ConnectionStatus | 'feature_disabled';
  profile: Row | null;
  tasks: Row[];
  scores: Row[];
  documents: Row[];
  resolvedClientId: string | null;
  resolvedTenantId: string | null;
}

const TEST_CLIENT_ID = 'client_test_julius_erving';
const TEST_TENANT_ID = 'tenant_demo_goclear';

export async function loadClientDashboardLiveData(forcedContext?: ResolvedClientContext): Promise<ClientDashboardLiveResult> {
  if (!clientDataMode.liveSupabaseTestClientEnabled) {
    return { enabled: false, status: 'feature_disabled', profile: null, tasks: [], scores: [], documents: [], resolvedClientId: null, resolvedTenantId: null };
  }

  let ctx = forcedContext
  if (!ctx) {
    const resolved = await resolveClientContextForCurrentUser()
    if (resolved) ctx = resolved
  }
  const clientId = ctx?.clientId || TEST_CLIENT_ID
  const tenantId = ctx?.tenantId || TEST_TENANT_ID

  const [profiles, tasks, scores, documents] = await Promise.all([
    listTableDetailed('client_profiles', { eq: ['client_id', clientId], limit: 1 }),
    listTableDetailed('client_tasks', { eq: ['client_id', clientId], limit: 20 }),
    listTableDetailed('readiness_scores', { eq: ['client_id', clientId], limit: 20 }),
    listTableDetailed('client_documents', { eq: ['client_id', clientId], limit: 50 }),
  ]);
  return {
    enabled: true,
    status: profiles.status,
    profile: profiles.data[0] ?? null,
    tasks: tasks.data,
    scores: scores.data,
    documents: documents.data,
    resolvedClientId: clientId,
    resolvedTenantId: tenantId,
  };
}
