import { clientDataMode } from '../data/clientDataMode';
import { listTableDetailed, type ConnectionStatus, type Row } from './db';
import { resolveClientContextForCurrentUser, type ResolvedClientContext } from '../lib/clientAuthContext';

export interface ClientDashboardLiveResult {
  enabled: boolean;
  status: ConnectionStatus | 'feature_disabled' | 'no_client_context';
  profile: Row | null;
  tasks: Row[];
  scores: Row[];
  documents: Row[];
  resolvedClientId: string | null;
  resolvedTenantId: string | null;
}

export async function loadClientDashboardLiveData(forcedContext?: ResolvedClientContext): Promise<ClientDashboardLiveResult> {
  if (!clientDataMode.liveSupabaseTestClientEnabled) {
    return { enabled: false, status: 'feature_disabled', profile: null, tasks: [], scores: [], documents: [], resolvedClientId: null, resolvedTenantId: null };
  }

  let ctx: ResolvedClientContext | null = forcedContext ?? null
  if (!ctx) {
    ctx = await resolveClientContextForCurrentUser()
  }

  if (!ctx) {
    return { enabled: false, status: 'no_client_context', profile: null, tasks: [], scores: [], documents: [], resolvedClientId: null, resolvedTenantId: null };
  }

  const clientId = ctx.clientId
  const tenantId = ctx.tenantId

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
