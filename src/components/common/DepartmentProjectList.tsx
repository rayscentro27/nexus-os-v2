import type { NexusProject } from '../../config/nexusProjectTypes';
import { timeAgo } from '../ui';

function badgeClass(status: string): string {
  if (['done', 'approved', 'scored', 'summarized'].includes(status)) return 'ok';
  if (['blocked', 'rejected'].includes(status)) return 'bad';
  if (['needs_review', 'scheduled', 'implementing'].includes(status)) return 'warn';
  return 'info';
}

export function DepartmentProjectList({
  projects,
  selectedId,
  emptyFeed,
  onSelect,
}: {
  projects: NexusProject[];
  selectedId: string | null;
  emptyFeed: string;
  onSelect: (project: NexusProject) => void;
}) {
  return (
    <div className="dept-panel dept-list-panel">
      <div className="dept-panel-head">
        <h3>Work Items</h3>
        <span className="meta">{projects.length}</span>
      </div>
      {projects.length === 0 ? (
        <div className="empty">
          <div>No live projects yet.</div>
          <div style={{ marginTop: 8 }}>This department will be fed by: {emptyFeed}.</div>
        </div>
      ) : (
        <div className="dept-project-list">
          {projects.map((project) => (
            <button
              key={project.project_id}
              className={`dept-project-card ${selectedId === project.project_id ? 'active' : ''}`}
              onClick={() => onSelect(project)}
            >
              <div className="dept-project-title">{project.title}</div>
              <div className="dept-project-meta">
                <span className={`pill ${badgeClass(project.status)}`}>{project.status.replaceAll('_', ' ')}</span>
                <span>{project.project_type.replaceAll('_', ' ')}</span>
                {project.score != null && <span>{project.score}/100</span>}
              </div>
              <div className="dept-project-foot">
                <span>{project.priority}</span>
                <span>{timeAgo(project.updated_at || project.created_at)}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
