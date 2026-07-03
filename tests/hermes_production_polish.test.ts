import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { resetConversationState } from '../src/lib/hermesConversationState';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory, setHermesMemoryScope } from '../src/lib/hermesMemoryStores';

const bannedPhrases = /I need one more detail: what specific outcome|I can reason from the allowed|I need a concrete decision/i;
const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('Hermes production polish — casual/common conversation expansion', () => {
  beforeEach(() => { setHermesMemoryScope('default:default'); resetConversationState(); });

  it.each([
    ['do you know any of the football teams'],
    ['did you drink your coffee today'],
    ['did you drink your coffee todayt'],
    ['what is your favorite car'],
    ['give me a preference'],
    ['do you like sports'],
  ])('routes casual prompt "%s" to casual_common without fallback', async (message) => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('casual_common');
    expect(response.usedSupabase).toBe(false);
    expect(response.usedModel).toBe(false);
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it.each([
    ['is there a grant specialist agent'],
    ['who handles credit repair'],
    ['is the research specialist live'],
  ])('routes specialist inventory prompt "%s" correctly', async (message) => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('specialist_agent_inventory');
    expect(response.text).toMatch(/Specialist asked about:|Status:|Source checked:|Verification state:|Next safe action:/i);
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it.each([
    ['what is nexus health'],
    ['how healthy is nexus'],
    ['is nexus healthy'],
    ['what is our system health'],
    ['what is broken'],
    ['what is working'],
  ])('routes system health prompt "%s" to system_health_report', async (message) => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('system_health_report');
    expect(response.text).toMatch(/system is mostly healthy|local reports|next move/i);
    expect(response.text).not.toMatch(/Status summary:|Source checked:|Audit details|reports\//i);
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it.each([
    ['can you see what is on this page'],
    ['what color is the nexus admin page'],
    ['what page are we on'],
    ['what page am I viewing'],
  ])('routes page context prompt "%s" correctly', async (message) => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toMatch(/page_connection_status|page_context_status/);
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it('routes sports score question to external_current_info', async () => {
    const response = await handleHermesMessage({ message: 'what was the score on the soccer game last night' });
    expect(response.route).toBe('external_current_info');
    expect(response.text).toMatch(/I do not have a connected live sports lookup/i);
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it.each([
    ['do you drink coffee'],
    ['what teams do you know'],
    ['what is your preferred car'],
  ])('handles casual variant "%s" without fallback', async (message) => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('casual_common');
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it('provenance for casual answer uses common knowledge label', async () => {
    await handleHermesMessage({ message: 'good morning' });
    const provenance = await handleHermesMessage({ message: 'what did you get that last response from' });
    expect(provenance.route).toBe('trace_source_meta');
    expect(provenance.text).toMatch(/common knowledge|local reasoning/i);
    expect(provenance.text).not.toMatch(/local Nexus context/i);
  });

  it('provenance for fallback uses unresolved routing fallback label', async () => {
    await handleHermesMessage({ message: 'asjkdfhlaskjdfhlakjsdf' });
    const provenance = await handleHermesMessage({ message: 'what did you get that last response from' });
    expect(provenance.text).toMatch(/unresolved routing fallback/i);
  });

  it('client_records contract omits blocker when read succeeds with 0 rows', async () => {
    const response = await handleHermesMessage({ message: 'do we have any clients' });
    expect(response.route).toBe('client_records');
    expect(response.text).not.toMatch(/not verified/i);
    expect(response.text).not.toMatch(/read failed/i);
    expect(response.text).toMatch(/client|table|records/i);
  });

  it('specialist agent inventory differentiates from domain reasoning', async () => {
    const inventory = await handleHermesMessage({ message: 'do we have a credit specialist agent' });
    expect(inventory.route).toBe('specialist_agent_inventory');
    expect(inventory.text).toMatch(/not registered|no verified live specialist/i);
    expect(inventory.text).not.toMatch(/I can reason from the allowed/i);
  });

  it('preserves business opportunity answer', async () => {
    const response = await handleHermesMessage({ message: 'what is the best money making opportunity available to me' });
    expect(response.route).toBe('revenue_reasoning');
    expect(response.text).toMatch(/\$97|next safe action/i);
  });

  it('preserves Tesla Model 3 as new-topic boundary', async () => {
    const response = await handleHermesMessage({ message: 'what do you think about the Tesla Model 3' });
    expect(response.route).toBe('general_advisor');
    expect(response.text).not.toMatch(/token usage|model status/i);
  });
});
