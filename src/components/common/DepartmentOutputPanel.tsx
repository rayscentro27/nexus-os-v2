import type { NexusProject } from '../../config/nexusProjectTypes';

export function DepartmentOutputPanel({ project }: { project: NexusProject | null }) {
  const outputs = project ? [
    project.visual_url ? { label: 'Preview', value: project.visual_url } : null,
    project.related_approval_id ? { label: 'Approval', value: project.related_approval_id } : null,
    project.related_task_request_id ? { label: 'Task request', value: project.related_task_request_id } : null,
    project.proof_event_id ? { label: 'Proof event', value: project.proof_event_id } : null,
  ].filter((x): x is { label: string; value: string } => Boolean(x)) : [];

  return (
    <div className="dept-panel">
      <div className="dept-panel-head">
        <h3>Outputs</h3>
        <span className="meta">generated/live</span>
      </div>
      {!project ? (
        <div className="empty">Select a project to see reports, drafts, previews, implementation plans, or proof events.</div>
      ) : outputs.length === 0 ? (
        <div className="empty">No generated outputs are linked yet.</div>
      ) : (
        <div className="list">
          {outputs.map((output) => (
            <div className="item" key={`${output.label}:${output.value}`}>
              <div className="t">{output.label}</div>
              {/^https?:\/\//.test(output.value) ? (
                <a href={output.value} target="_blank" rel="noreferrer">{output.value}</a>
              ) : (
                <div className="meta">{output.value}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
