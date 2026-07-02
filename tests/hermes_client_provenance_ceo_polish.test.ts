import { beforeEach, describe, expect, it, vi } from 'vitest';

const liveContext = vi.hoisted(() => ({ response: null as any }));

vi.mock('../src/lib/hermesLiveContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/lib/hermesLiveContext')>();
  return {
    ...actual,
    buildLiveSupabaseContext: vi.fn(async () => liveContext.response),
  };
});

import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { clearHermesDecisionState } from '../src/lib/hermesDecisionState';
import { resetConversationState } from '../src/lib/hermesConversationState';
import { clearSession } from '../src/lib/hermesAdvisorSession';

const scope = { tenantId: 'client-provenance-polish', sessionId: 'default' };
const scopeKey = `${scope.tenantId}:${scope.sessionId}`;

describe('Hermes client provenance and CEO renderer polish', () => {
  beforeEach(() => {
    clearHermesDecisionState(scopeKey);
    clearSession(scopeKey);
    resetConversationState();
  });

  it('preserves a denied client_profiles attempt in provenance', async () => {
    liveContext.response = {
      text: 'Client read failed.', source: 'supabase_client_profiles', sourceType: 'unavailable', liveData: false,
      timestamp: '2026-07-02T12:00:00Z', tablesQueried: ['client_profiles'], rowCounts: { client_profiles: 0 },
      tableResults: { client_profiles: { status: 'error', rowCount: 0, error: 'access denied' } },
      verificationStatus: 'unverified', blocker: 'client_profiles: access denied',
    };

    const clients = await handleHermesMessage({ message: 'do we have any clients', ...scope });
    expect(clients.text).toMatch(/No verified count is available/i);
    const provenance = await handleHermesMessage({ message: 'where did that come from', ...scope });
    expect(provenance.text).toMatch(/client_profiles/i);
    expect(provenance.text).toMatch(/status: failed|access denied/i);
    expect(provenance.text).toMatch(/No verified client count is available/i);
    expect(provenance.text).toMatch(/did not use approvals or task_requests to count clients/i);
    expect(provenance.text).not.toMatch(/Source:.*approvals|live Supabase data from approvals/i);
  });

  it('preserves an empty successful client_profiles read in provenance', async () => {
    liveContext.response = {
      text: 'No client profiles found.', source: 'supabase_client_profiles', sourceType: 'live_supabase', liveData: true,
      timestamp: '2026-07-02T12:00:00Z', tablesQueried: ['client_profiles'], rowCounts: { client_profiles: 0 },
      tableResults: { client_profiles: { status: 'success', rowCount: 0 } }, verificationStatus: 'verified',
    };

    const clients = await handleHermesMessage({ message: 'do we have any clients', ...scope });
    expect(clients.text).toMatch(/0 client rows returned|empty_success/i);
    expect(clients.text).not.toMatch(/read failed/i);
    const provenance = await handleHermesMessage({ message: 'where did that come from', ...scope });
    expect(provenance.text).toMatch(/client_profiles/i);
    expect(provenance.text).toMatch(/status: empty_success/i);
    expect(provenance.text).not.toMatch(/read failed/i);
    expect(provenance.text).toMatch(/did not use approvals or task_requests to count clients/i);
    expect(provenance.text).not.toMatch(/Source:.*approvals|live Supabase data from approvals/i);
  });

  it('renders system health as a short spoken CEO answer', async () => {
    await handleHermesMessage({ message: 'what is the system health', ...scope });
    const ceo = await handleHermesMessage({ message: 'give me the CEO version', ...scope });
    expect(ceo.text).toMatch(/system is mostly healthy/i);
    expect(ceo.text).toMatch(/local reports.*not a fresh production check/i);
    expect(ceo.text).toMatch(/next move/i);
    expect(ceo.text.split(/[.!?]+/).filter((sentence) => sentence.trim())).toHaveLength(4);
    expect(ceo.text).not.toMatch(/reports\/|Route:|Audit details|RLS|[0-9a-f]{8}-[0-9a-f-]{27,}/i);
  });
});
