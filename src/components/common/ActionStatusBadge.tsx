/** Universal action-status badge + approval-visibility note. Driven by nexusActionPolicy so every
 *  tab labels actions the same way. No actions, display-only. */
import { getActionStatusLabel, getApprovalRequirement, getActionSafetyCopy, type NexusAction } from '../../config/nexusActionPolicy';

const CLASS: Record<string, string> = {
  Live: 'ok', 'Safe capture': 'ok', 'Draft only': 'infob', 'Auto-routed': 'ok',
  'Needs Ray review': 'warnb', 'Approval required': 'warnb', Disabled: 'warnb', Blocked: 'warnb',
};

export function ActionStatusBadge({ action }: { action: NexusAction }) {
  const label = getActionStatusLabel(action);
  return <span className={`nx-badge ${CLASS[label] ?? 'infob'}`}>{label}</span>;
}

export function ApprovalVisibilityNote({ action }: { action: NexusAction }) {
  const needs = getApprovalRequirement(action);
  return (
    <div className={needs ? 'nx-amber' : 'nx-green'} style={{ fontSize: 12 }}>
      {getActionSafetyCopy(action)}{' '}
      {needs ? '→ appears in Approvals for Ray.' : '→ stays in this tab’s queue (not in Approvals).'}
    </div>
  );
}
