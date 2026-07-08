import { clientDataMode } from '../data/clientDataMode';
import { listTableDetailed, type ConnectionStatus, type Row } from './db';

export interface ClientDashboardLiveResult {
  enabled: boolean;
  status: ConnectionStatus | 'feature_disabled';
  profile: Row | null;
  tasks: Row[];
  scores: Row[];
  documents: Row[];
}

const TEST_CLIENT_ID = 'client_test_julius_erving';

export async function loadClientDashboardLiveData(): Promise<ClientDashboardLiveResult> {
  if (!clientDataMode.liveSupabaseTestClientEnabled) {
    return { enabled: false, status: 'feature_disabled', profile: null, tasks: [], scores: [], documents: [] };
  }
  const [profiles, tasks, scores, documents] = await Promise.all([
    listTableDetailed('client_profiles', { eq: ['client_id', TEST_CLIENT_ID], limit: 1 }),
    listTableDetailed('client_tasks', { eq: ['client_id', TEST_CLIENT_ID], limit: 20 }),
    listTableDetailed('readiness_scores', { eq: ['client_id', TEST_CLIENT_ID], limit: 20 }),
    listTableDetailed('client_documents', { eq: ['client_id', TEST_CLIENT_ID], limit: 50 }),
  ]);
  return {
    enabled: true,
    status: profiles.status,
    profile: profiles.data[0] ?? null,
    tasks: tasks.data,
    scores: scores.data,
    documents: documents.data,
  };
}
