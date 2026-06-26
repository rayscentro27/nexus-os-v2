import { useState } from 'react';
import type { NexusProject } from '../../config/nexusProjectTypes';
import { getProjectHermesRecommendation } from '../../lib/nexusProjects';

export function HermesAdvisorWorkspace({ project }: { project: NexusProject | null }) {
  const [draft, setDraft] = useState('');
  const pending = project ? !project.summary.trim() : false;

  return (
    <div className="dept-panel hermes-workspace">
      <div className="dept-panel-head">
        <h3>Hermes Advisor</h3>
        <span className="meta">contextual</span>
      </div>
      {!project ? (
        <div className="empty">Select a project so Hermes can advise from saved project data.</div>
      ) : (
        <>
          <div className="hermes">
            <div className="dept-kicker">My recommendation</div>
            <div className="body">{getProjectHermesRecommendation(project)}</div>
          </div>
          <div className="dept-advice-grid">
            <div>
              <div className="dept-kicker">Why this matters</div>
              <div className="meta">{project.hermes_memory_summary || project.summary || 'I can review saved metadata now.'}</div>
            </div>
            <div>
              <div className="dept-kicker">Pros</div>
              <div className="meta">{project.pros.join(' · ') || 'No explicit pros stored yet.'}</div>
            </div>
            <div>
              <div className="dept-kicker">Cons</div>
              <div className="meta">{project.cons.join(' · ') || 'No explicit cons stored yet.'}</div>
            </div>
            <div>
              <div className="dept-kicker">Risk</div>
              <div className="meta">{project.risk_triggers.join(' · ') || (project.approval_required ? 'Approval required.' : 'No stored risk trigger.')}</div>
            </div>
            <div>
              <div className="dept-kicker">Suggested next step</div>
              <div className="meta">{project.next_action || 'Pick the smallest safe internal action.'}</div>
            </div>
            <div>
              <div className="dept-kicker">Proposed schedule</div>
              <div className="meta">{project.proposed_schedule || 'No stored schedule.'}</div>
            </div>
          </div>
          {pending && (
            <div className="note">I can review the saved metadata now. Summary/enrichment is pending.</div>
          )}
          <div className="dept-chat-box">
            <textarea
              className="cmd"
              rows={2}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask Hermes about this selected project..."
            />
            <button className="btn ghost" onClick={() => setDraft('')} disabled={!draft.trim()}>
              Keep as note
            </button>
          </div>
        </>
      )}
    </div>
  );
}
