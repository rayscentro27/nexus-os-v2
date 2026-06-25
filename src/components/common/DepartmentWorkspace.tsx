import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { DepartmentAction, DepartmentWorkspaceConfig, NexusProject } from '../../config/nexusProjectTypes';
import { createTaskRequest } from '../../lib/taskRequests';
import { createApproval, createEvent } from '../../lib/ledger';
import { loadDepartmentProjects } from '../../lib/nexusProjects';
import { DepartmentProjectList } from './DepartmentProjectList';
import { DepartmentProjectSummary } from './DepartmentProjectSummary';
import { HermesAdvisorWorkspace } from './HermesAdvisorWorkspace';
import { DepartmentActionStudio } from './DepartmentActionStudio';
import { DepartmentOutputPanel } from './DepartmentOutputPanel';

export function DepartmentWorkspace({
  config,
  email,
  leading,
}: {
  config: DepartmentWorkspaceConfig;
  email: string | null;
  leading?: ReactNode;
}) {
  const [projects, setProjects] = useState<NexusProject[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let alive = true;
    loadDepartmentProjects(config.tabId).then((rows) => {
      if (!alive) return;
      setProjects(rows);
      setSelectedId((current) => current && rows.some((p) => p.project_id === current) ? current : rows[0]?.project_id ?? null);
    }).catch(() => {
      if (alive) setProjects([]);
    });
    return () => { alive = false; };
  }, [config.tabId]);

  const selected = projects.find((p) => p.project_id === selectedId) ?? null;

  async function handleAction(action: DepartmentAction, project: NexusProject) {
    if (action.category === 'disabled') {
      setMessage('Not connected yet.');
      return;
    }
    if (action.category === 'approval' || project.approval_required) {
      const id = await createApproval({
        lane: project.owner_tab,
        item_type: action.key,
        title: `${action.label}: ${project.title}`.slice(0, 120),
        summary: `${action.description} Project ${project.project_id}.`,
        payload: { project_id: project.project_id, action_key: action.key, source_url: project.source_url },
      });
      await createEvent({
        lane: project.owner_tab,
        action: 'department_action_approval_requested',
        status: 'pending',
        title: action.label,
        summary: id ? `Approval created for ${project.title}` : 'Approval create failed or blocked by RLS.',
        approval_id: id,
      });
      setMessage(id ? `Approval created for Ray review (${id.slice(0, 8)}...).` : 'Could not create approval (check sign-in / RLS).');
      return;
    }

    const id = await createTaskRequest({
      task_type: `department_${action.key}`,
      sensitivity: 'internal_summary',
      allowed_data_scope: ['public', 'internal_summary'],
      forbidden_data: ['customer_private', 'credit_sensitive', 'funding_sensitive', 'auth_sensitive', 'secrets'],
      assigned_worker_type: 'general_worker',
      hermes_visibility: 'summary',
      payload: {
        project_id: project.project_id,
        department: project.department,
        owner_tab: project.owner_tab,
        action_key: action.key,
        source_url: project.source_url,
      },
      summary: `${action.label}: ${project.title}`,
    }, email);
    await createEvent({
      lane: project.owner_tab,
      action: 'department_action_task_requested',
      status: 'pending',
      title: action.label,
      summary: id ? `Task request created for ${project.title}` : 'Task request create failed or blocked by RLS.',
      payload: { project_id: project.project_id, task_request_id: id, action_key: action.key },
    });
    setMessage(id ? `Safe task request created (${id.slice(0, 8)}...).` : 'Could not create task request (check sign-in / RLS).');
  }

  return (
    <div className="dept-workspace">
      <div className="dept-room-head">
        <div>
          <h2>{config.title}</h2>
          <div className="sub">{config.subtitle}</div>
        </div>
        <button className="btn ghost" onClick={() => loadDepartmentProjects(config.tabId).then(setProjects)}>Refresh</button>
      </div>
      {leading}
      {message && <div className="note">{message}</div>}
      <div className="dept-grid">
        <DepartmentProjectList
          projects={projects}
          selectedId={selectedId}
          emptyFeed={config.emptyFeed}
          onSelect={(project) => setSelectedId(project.project_id)}
        />
        <div className="dept-center">
          <DepartmentProjectSummary project={selected} />
          <HermesAdvisorWorkspace project={selected} />
        </div>
        <div className="dept-right">
          <DepartmentActionStudio actions={config.actions} project={selected} onAction={handleAction} />
          <DepartmentOutputPanel project={selected} />
        </div>
      </div>
    </div>
  );
}
