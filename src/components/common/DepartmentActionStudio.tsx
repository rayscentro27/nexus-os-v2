import type { DepartmentAction, NexusProject } from '../../config/nexusProjectTypes';

function classFor(category: DepartmentAction['category']): string {
  if (category === 'approval') return 'warn';
  if (category === 'disabled') return 'ghost';
  return '';
}

export function DepartmentActionStudio({
  actions,
  project,
  onAction,
}: {
  actions: DepartmentAction[];
  project: NexusProject | null;
  onAction?: (action: DepartmentAction, project: NexusProject) => void;
}) {
  return (
    <div className="dept-panel">
      <div className="dept-panel-head">
        <h3>Action Studio</h3>
        <span className="meta">policy gated</span>
      </div>
      <div className="dept-action-grid">
        {actions.map((action) => (
          <button
            key={action.key}
            className={`btn ${classFor(action.category)}`}
            disabled={!project || action.category === 'disabled'}
            title={action.description}
            onClick={() => project && onAction?.(action, project)}
          >
            {action.label}
          </button>
        ))}
      </div>
      <div className="meta muted" style={{ marginTop: 10 }}>
        Safe internal actions create task requests or metadata updates. Risky actions create approvals. Publish, send, trade, deploy, scheduler activation, and raw local/v1 execution remain gated.
      </div>
      {actions.some((a) => a.category === 'disabled') && (
        <div className="note" style={{ marginTop: 10 }}>Disabled buttons show “Not connected yet” behavior; no fake functionality is triggered.</div>
      )}
    </div>
  );
}
