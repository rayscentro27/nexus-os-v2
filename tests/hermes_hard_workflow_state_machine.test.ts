import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

const edge = readFileSync('supabase/functions/hermes-chat/index.ts', 'utf8');

describe('Hermes hard workflow state machine boundary', () => {
  it('loads server-owned conversation state before model-first routing', () => {
    expect(edge).toContain('loadHermesState(userId, conversationId)');
    expect(edge).toContain('runConversationalOpenRouter(');
    expect(edge).toContain('stateContextBlock(session.state, initialLane)');
    expect(edge).toContain('resolveLane(message, session.state)');
  });

  it('resolves hard lanes before the evidence obligation gate can run', () => {
    const laneIndex = edge.indexOf('const initialLane = resolveLane(message, session.state)');
    const scheduleIndex = edge.indexOf("if (initialLane.lane === 'SCHEDULE_WORKFLOW')");
    const reportIndex = edge.indexOf("if (initialLane.lane === 'REPORT_REFERENCE')");
    const factIndex = edge.indexOf("if (initialLane.lane === 'CURRENT_FACT')");
    const evidenceIndex = edge.indexOf('const initialObligation = evidenceObligation(message, baseMessages)');
    expect(laneIndex).toBeGreaterThan(0);
    expect(scheduleIndex).toBeGreaterThan(laneIndex);
    expect(reportIndex).toBeGreaterThan(laneIndex);
    expect(factIndex).toBeGreaterThan(laneIndex);
    expect(evidenceIndex).toBeGreaterThan(factIndex);
  });

  it('suppresses unrelated schedule tools until explicit draft creation', () => {
    expect(edge).toContain("allowedTools = createRequested && next.status === 'ready' ? ['draft_schedule'] : []");
    expect(edge).toContain('Do not call current-fact tools. Do not create a draft unless the server supplied draft_schedule.');
    expect(edge).toContain("openRouterToolsFor(initialLane.allowedTools)");
    expect(edge).not.toContain("openRouterTools(), startTime");
  });

  it('supports server-owned report search and exact report follow-ups', () => {
    expect(edge).toContain('search_reports');
    expect(edge).toContain("buildReferenceState('report_search'");
    expect(edge).toContain("initialLane.lane === 'REPORT_REFERENCE'");
    expect(edge).toContain("toolName: 'summarize_report'");
  });

  it('keeps browser-supplied state non-authoritative', () => {
    expect(edge).toContain("const rawContext = safeObject(body?.context)");
    expect(edge).toContain("conversationId = String(body?.conversationId || rawContext.conversationId || 'default')");
    expect(edge).toContain('loadHermesState(userId, conversationId)');
    expect(edge).not.toContain('body?.pendingAction');
    expect(edge).not.toContain('body?.referenceState');
  });
});
