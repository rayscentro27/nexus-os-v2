import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { resetConversationState } from '../src/lib/hermesConversationState';

const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('route dominance repair', () => {
  beforeEach(() => resetConversationState());

  it.each(['good night', 'go;od evening'])('routes %s as a natural check-in rather than preference fallback', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('casual_common');
    expect(response.text).not.toMatch(/human tastes|need one more detail/);
  });

  it('renders a farewell answer for good night', async () => {
    const response = await handleHermesMessage({ message: 'good night' });
    expect(response.routeDecision.intent).toBe('farewell_or_light_check_in');
    expect(response.text).toMatch(/Good night, Ray/);
  });

  it('routes problem identification to system diagnostics', async () => {
    const response = await handleHermesMessage({ message: 'where is the problem' });
    expect(response.routeDecision).toMatchObject({ routeId: 'system_health_report', domain: 'system_diagnostics', intent: 'identify_problem', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden' });
    expect(response.text).toMatch(/routing\/fallback dominance/);
    expect(response.route).not.toBe('fallback_clarification');
  });

  it('renders a user-facing system health report, not policy diagnostics', async () => {
    const response = await handleHermesMessage({ message: 'can you provide a report on the system health' });
    expect(response.routeDecision).toMatchObject({ routeId: 'system_health_report', domain: 'system_health', intent: 'report_request' });
    expect(response.text).toMatch(/Build\/tests|Supabase|Deployment|Hermes brain|Next recommended action/);
    expect(response.text).not.toMatch(/evidence is allowed for this status question/);
  });

  it('separates website connection from Supabase capability', async () => {
    const response = await handleHermesMessage({ message: 'are you connected to this website', currentPageContext: { pageId: 'system-health', route: '#/system-health', visibleItems: [] } });
    expect(response.routeDecision).toMatchObject({ routeId: 'page_connection_status', domain: 'current_page', intent: 'website_connection_status', modelPolicy: 'forbidden' });
    expect(response.text).toMatch(/running inside the Nexus web app chat UI/);
    expect(response.text).toMatch(/Supabase read access is separate/);
  });

  it('reports current page metadata when supplied', async () => {
    const response = await handleHermesMessage({ message: 'what about this page', currentPageContext: { pageId: 'business-opportunities', route: '#/business-opportunities', visibleItems: [{ id: 1 }] } });
    expect(response.route).toBe('page_context_status');
    expect(response.text).toMatch(/business-opportunities/);
    expect(response.text).toMatch(/1 visible item/);
  });

  it('honestly reports missing current-page metadata', async () => {
    const response = await handleHermesMessage({ message: 'can you see this page' });
    expect(response.route).toBe('page_context_status');
    expect(response.text).toMatch(/do not have current page metadata/);
  });

  it('normalizes favorite care to vehicle advice', async () => {
    const response = await handleHermesMessage({ message: 'what is your favorite care' });
    expect(response.routeDecision).toMatchObject({ routeId: 'general_advisor', domain: 'vehicle_recommendation' });
    expect(response.text).toMatch(/Toyota Camry|Lexus ES|RAV4/);
  });

  it('routes audit scheduling to an approval-gated draft', async () => {
    const response = await handleHermesMessage({ message: 'can you schedule a audit for next week' });
    expect(response.routeDecision).toMatchObject({ routeId: 'schedule_action_prepare', activationLevel: 6, domain: 'scheduling', intent: 'prepare_scheduled_audit', actionPolicy: 'approval_required', modelPolicy: 'forbidden' });
    expect(response.text).toMatch(/draft scheduled-audit request/);
    expect(response.text).toMatch(/will not activate a scheduler/);
  });

  it('labels fallback trace as a routing miss rather than grounded Nexus data', async () => {
    await handleHermesMessage({ message: 'can you help with it' });
    const trace = await handleHermesMessage({ message: 'where did you get that last answer from' });
    expect(trace.route).toBe('trace_source_meta');
    expect(trace.text).toMatch(/unresolved routing fallback/);
    expect(trace.text).toMatch(/not verified Nexus data/);
  });
});

describe('protected route regressions', () => {
  beforeEach(() => resetConversationState());

  it.each([
    ['what approvals do i have', 'explicit_domain_retrieval'],
    ['what business opportunities are available', 'explicit_domain_retrieval'],
    ['can you fix a toilet', 'opportunity_aware_recommendation'],
    ['can you fix a car', 'opportunity_aware_recommendation'],
    ['Delegate this', 'approval_action_prepare'],
    ['can you place a trade', 'safety_gate'],
  ])('keeps %s out of generic fallback', (message, expected) => {
    expect(route(message).routeId).toBe(expected);
    expect(route(message).routeId).not.toBe('fallback_clarification');
  });

  it('keeps selection then feasibility in selection/advisory routes', async () => {
    await handleHermesMessage({ message: 'what business opportunities are available' });
    expect((await handleHermesMessage({ message: 'lets review number 3' })).route).toBe('memory_followup');
    expect((await handleHermesMessage({ message: 'do you think it will work' })).route).toBe('advisory_followup');
  });
});
