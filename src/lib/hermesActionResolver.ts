import type { HermesIntentFrame } from './hermesIntentFrame';
import type { NexusSessionContext } from './hermesAdvisorSession';
import type { HermesDecisionState } from './hermesDecisionState';

export interface ResolvedActionTarget {
  id?: string;
  label: string;
  type: 'record' | 'recommendation' | 'report' | 'session_item' | 'page' | 'unknown';
  source: string;
}

export function resolveHermesActionTarget(input: {
  message: string; intentFrame: HermesIntentFrame; uiSelectedItem?: Record<string, unknown> | null;
  activeSession: NexusSessionContext | null; decisionState: HermesDecisionState;
}): ResolvedActionTarget | null {
  const { intentFrame, uiSelectedItem, activeSession, decisionState } = input;
  if (intentFrame.target.label) return { id: intentFrame.target.id, label: intentFrame.target.label, type: 'record', source: 'explicit_target' };
  if (intentFrame.target.rank && activeSession?.activeList) {
    const item = activeSession.activeList.find((entry) => entry.rank === intentFrame.target.rank);
    if (item) return { id: item.id, label: item.label, type: activeSession.activeMode === 'report_inventory_review' ? 'report' : 'session_item', source: item.source };
  }
  if (uiSelectedItem) {
    const label = String(uiSelectedItem.title || uiSelectedItem.name || uiSelectedItem.label || '').trim();
    if (label) return { id: uiSelectedItem.id ? String(uiSelectedItem.id) : undefined, label, type: 'record', source: 'ui_context' };
  }
  if (decisionState.lastRecommendation) return { label: decisionState.lastRecommendation.label, type: 'recommendation', source: decisionState.lastRecommendation.source };
  if (activeSession?.currentFocus) return { id: activeSession.currentFocus.id, label: activeSession.currentFocus.label, type: activeSession.activeMode === 'report_inventory_review' ? 'report' : 'session_item', source: activeSession.currentFocus.source || 'active_session' };
  if (decisionState.lastAnswer?.target) return { ...decisionState.lastAnswer.target, source: decisionState.lastAnswer.sources[0] || 'last_answer' };
  return null;
}
