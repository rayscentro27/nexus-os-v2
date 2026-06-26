import { useData } from '../ui';
import { loadRayReviewQueue, summarizeRayReviewCounts } from '../../lib/rayReviewQueue';

export function RayReviewQueueView() {
  const { data } = useData(() => loadRayReviewQueue(50), []);
  const counts = summarizeRayReviewCounts(data);
  return (
    <div className="nx-scope">
      <div className="nx-glass">
        <div className="nx-between" style={{ marginBottom: 10 }}>
          <div>
            <h3 style={{ margin: 0 }}>Ray Review Queue</h3>
            <div className="nx-muted" style={{ fontSize: 12 }}>Focused decision room. Research backlog stays in departments.</div>
          </div>
          <span className="nx-badge warnb">{counts.total} decisions</span>
        </div>
        <div className="nx-chiprow" style={{ marginBottom: 10 }}>
          <span className="nx-pill">urgent {counts.urgent}</span>
          <span className="nx-pill">campaign/send {counts.campaign}</span>
          <span className="nx-pill">revenue {counts.revenue}</span>
          <span className="nx-pill">scheduler {counts.scheduler}</span>
          <span className="nx-pill">connector {counts.connector}</span>
          <span className="nx-pill">strategy {counts.strategy}</span>
        </div>
        {data.length === 0 ? (
          <div className="empty">No true Ray decisions visible. Autonomous research can continue without review.</div>
        ) : (
          <div className="dept-project-list">
            {data.map((item) => (
              <div key={item.review_id} className="dept-project-card">
                <div className="dept-project-title">{item.title}</div>
                <div className="dept-project-meta">
                  <span>{item.decision_type.replaceAll('_', ' ')}</span>
                  <span>{item.priority}</span>
                  <span>{item.risk_level}</span>
                  <span>{item.status.replaceAll('_', ' ')}</span>
                </div>
                <div className="dept-body" style={{ marginTop: 8 }}>{item.summary}</div>
                <div className="meta" style={{ marginTop: 8 }}>Hermes: {item.hermes_recommendation}</div>
                <div className="meta muted" style={{ marginTop: 6 }}>Options: {item.options.join(' · ') || 'Review, request changes, park, or escalate.'}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
