import { useEffect, useState } from 'react';
import { supabase, isSupabaseConfigured } from '../../lib/supabaseClient';

const TEST_CHECKLISTS: Record<string, { label: string; tasks: string[] }> = {
  full: {
    label: 'Full 12-Task Checklist',
    tasks: ['Sign up', 'Set password', 'Complete onboarding', 'Navigate portal', 'Upload test document', 'Submit feedback', 'Verify checklist progress', 'Test responsive layout', 'Test accessibility', 'Verify session isolation', 'Complete Stripe test purchase', 'Submit final feedback'],
  },
  payment_only: {
    label: 'Payment-Only Checklist',
    tasks: ['Sign up', 'Set password', 'Navigate to checkout', 'Complete Stripe test purchase', 'Verify order created', 'Submit payment feedback'],
  },
  mobile_only: {
    label: 'Mobile-Only Checklist',
    tasks: ['Sign up', 'Set password', 'Complete onboarding on mobile', 'Navigate portal on mobile', 'Test responsive layout', 'Submit mobile feedback'],
  },
};

const LEVEL_LABELS: Record<string, string> = {
  invited_test_mode: 'Invited Test Mode',
  controlled_live_pilot: 'Controlled $1 Live Pilot',
};

export default function TesterTasksPage() {
  const [user, setUser] = useState<any>(null);
  const [invitation, setInvitation] = useState<any>(null);
  const [checklist, setChecklist] = useState<string[]>([]);
  const [completedTasks, setCompletedTasks] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false);

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) { setLoading(false); return; }
    (async () => {
      const { data: { user: u } } = await supabase.auth.getUser();
      if (!u) { setLoading(false); return; }
      setUser(u);

      const { data: inv } = await supabase
        .from('tester_invitations')
        .select('*')
        .eq('auth_user_id', u.id)
        .eq('invitation_status', 'accepted')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle();

      if (inv) {
        setInvitation(inv);
        const checklistKey = inv.task_checklist_version === 'payment_only' ? 'payment_only'
          : inv.task_checklist_version === 'mobile_only' ? 'mobile_only'
          : 'full';
        setChecklist(TEST_CHECKLISTS[checklistKey]?.tasks || TEST_CHECKLISTS.full.tasks);
      }
      setLoading(false);
    })();
  }, []);

  const startSession = () => {
    setSessionStarted(true);
  };

  const toggleTask = (index: number) => {
    setCompletedTasks(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const submitFeedback = async () => {
    if (!feedbackText.trim() || !supabase || !invitation) return;
    await supabase.from('tester_feedback').insert({
      session_id: null,
      persona: invitation.assigned_persona || 'a',
      issue_title: 'Tester feedback',
      issue_description: feedbackText,
      severity: 'medium',
      status: 'open',
      tester_name: invitation.tester_name,
      build_commit: invitation.build_commit,
      fixture_version: invitation.fixture_version,
    });
    setFeedbackSubmitted(true);
    setFeedbackText('');
  };

  if (loading) return <div className="nxos-stack" style={{ padding: 40 }}><p>Loading...</p></div>;
  if (!user) return (
    <div className="nxos-stack" style={{ maxWidth: 500, margin: '60px auto', padding: '0 20px' }} data-testid="tester-login-required">
      <p style={{ color: '#94a3b8' }}>Please sign in to access your testing tasks.</p>
      <a href="/goclear/login" style={{ color: '#3b82f6' }}>Sign in</a>
    </div>
  );
  if (!invitation) return (
    <div className="nxos-stack" style={{ maxWidth: 500, margin: '60px auto', padding: '0 20px' }} data-testid="no-invitation">
      <p style={{ color: '#94a3b8' }}>No accepted invitation found for your account.</p>
      <a href="/invite" style={{ color: '#3b82f6' }}>Enter invitation token</a>
    </div>
  );

  const progress = checklist.length > 0 ? Math.round((completedTasks.size / checklist.length) * 100) : 0;

  return (
    <div className="nxos-stack" style={{ maxWidth: 700, margin: '40px auto', padding: '0 20px' }} data-testid="tester-tasks-page">
      <div className="nxos-callout" style={{ borderLeft: '4px solid #3b82f6' }}>
        <strong>Tester Assignment</strong>
        <p>Complete your assigned tasks and submit feedback. Your session is isolated from other testers and client data.</p>
      </div>

      <section className="nxos-table-card">
        <h2>Your Assignment</h2>
        <div style={{ display: 'grid', gap: 8 }}>
          <div><strong>Name:</strong> {invitation.tester_name}</div>
          <div><strong>Level:</strong> {LEVEL_LABELS[invitation.testing_level] || invitation.testing_level}</div>
          {invitation.assigned_persona && <div><strong>Persona:</strong> {invitation.assigned_persona.toUpperCase()}</div>}
          <div><strong>Checklist Version:</strong> {invitation.task_checklist_version}</div>
        </div>
      </section>

      {!sessionStarted ? (
        <button onClick={startSession} className="nxos-button" style={{ padding: '10px 20px', background: '#10b981', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer' }} data-testid="start-session-btn">
          Start Testing Session
        </button>
      ) : (
        <>
          <section className="nxos-table-card">
            <h2>Task Checklist ({completedTasks.size}/{checklist.length}) — {progress}%</h2>
            <div style={{ background: '#1e293b', height: 8, borderRadius: 4, overflow: 'hidden', marginBottom: 12 }}>
              <div style={{ background: '#10b981', height: '100%', width: `${progress}%`, transition: 'width 0.3s' }} />
            </div>
            <div style={{ display: 'grid', gap: 4 }}>
              {checklist.map((task, i) => (
                <label key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', color: '#e2e8f0', fontSize: 13, cursor: 'pointer', textDecoration: completedTasks.has(i) ? 'line-through' : 'none', opacity: completedTasks.has(i) ? 0.6 : 1 }}>
                  <input type="checkbox" checked={completedTasks.has(i)} onChange={() => toggleTask(i)} data-testid={`task-${i}`} />
                  {task}
                </label>
              ))}
            </div>
          </section>

          <section className="nxos-table-card">
            <h2>Submit Feedback</h2>
            <textarea value={feedbackText} onChange={(e) => setFeedbackText(e.target.value)} placeholder="Share your testing experience, issues found, or suggestions..." rows={4} style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc', resize: 'vertical', boxSizing: 'border-box' }} data-testid="feedback-input" />
            <button onClick={submitFeedback} disabled={!feedbackText.trim() || feedbackSubmitted} className="nxos-button" style={{ marginTop: 8, padding: '8px 16px', background: feedbackSubmitted ? '#6b7280' : '#3b82f6', color: '#fff', borderRadius: 8, border: 'none', cursor: feedbackText.trim() && !feedbackSubmitted ? 'pointer' : 'default' }} data-testid="submit-feedback-btn">
              {feedbackSubmitted ? 'Feedback Submitted' : 'Submit Feedback'}
            </button>
          </section>

          <button onClick={async () => { if (supabase) await supabase.auth.signOut(); window.location.href = '/'; }} className="nxos-button" style={{ padding: '8px 16px', background: '#6b7280', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13 }} data-testid="end-session-btn">
            End Session & Sign Out
          </button>
        </>
      )}
    </div>
  );
}
