import type { NexusProject } from '../../config/nexusProjectTypes';
import { getProjectReviewState, getProjectScheduleLabel } from '../../lib/nexusProjects';
import { Pill, timeAgo } from '../ui';

function ListBlock({ title, items, fallback }: { title: string; items: string[]; fallback?: string }) {
  const clean = items.filter(Boolean);
  return (
    <div>
      <div className="dept-kicker">{title}</div>
      {clean.length ? (
        <ul className="dept-plain-list">{clean.map((item) => <li key={item}>{item}</li>)}</ul>
      ) : (
        <div className="meta muted">{fallback ?? 'None recorded yet.'}</div>
      )}
    </div>
  );
}

export function DepartmentProjectSummary({ project }: { project: NexusProject | null }) {
  if (!project) {
    return (
      <div className="dept-panel">
        <div className="empty">Select a project/source to open the summary and Hermes advisor.</div>
      </div>
    );
  }

  const pending = !project.summary.trim();
  return (
    <div className="dept-panel">
      <div className="dept-summary-head">
        <div>
          <div className="dept-kicker">{project.project_type.replaceAll('_', ' ')}</div>
          <h3>{project.title}</h3>
        </div>
        <Pill status={project.status} />
      </div>
      <div className="dept-summary-grid">
        <div><span className="dept-kicker">Score</span><strong>{project.score == null ? 'Not scored' : `${project.score}/100`}</strong></div>
        <div><span className="dept-kicker">Review</span><strong>{getProjectReviewState(project)}</strong></div>
        <div><span className="dept-kicker">Updated</span><strong>{timeAgo(project.updated_at || project.created_at) || 'Unknown'}</strong></div>
      </div>
      {project.source_url && (
        <a className="dept-source-link" href={project.source_url} target="_blank" rel="noreferrer">
          {project.source_title || project.source_url}
        </a>
      )}
      <div className={pending ? 'empty' : 'dept-body'}>
        {pending ? 'Saved. Summary/enrichment pending.' : project.summary}
      </div>
      <div className="dept-two">
        <ListBlock title="Pros" items={project.pros} />
        <ListBlock title="Cons" items={project.cons} />
      </div>
      <div>
        <div className="dept-kicker">Recommendation</div>
        <div className="dept-body">{project.recommendation || 'Review with Hermes before routing.'}</div>
      </div>
      <div>
        <div className="dept-kicker">Proposed Schedule</div>
        <div className="dept-body">{project.proposed_schedule || getProjectScheduleLabel(project)}</div>
      </div>
      <div>
        <div className="dept-kicker">Next Action</div>
        <div className="dept-body">{project.next_action || 'Choose a safe internal action.'}</div>
      </div>
      {project.risk_triggers.length > 0 && (
        <div>
          <div className="dept-kicker">Risk Triggers</div>
          <div className="chips">{project.risk_triggers.map((risk) => <span className="pill warn" key={risk}>{risk}</span>)}</div>
        </div>
      )}
      <div className="meta muted">
        Data: {project.data_sources.join(', ') || 'live Supabase source'}{project.proof_event_id ? ` · proof ${project.proof_event_id}` : ''}
      </div>
    </div>
  );
}
