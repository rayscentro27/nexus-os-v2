import { useEffect, useMemo, useState } from 'react';
import { SourceIntakeReviewPage } from './source-intake/SourceIntakeReviewPage';
import { supabase } from '../lib/supabaseClient';

type Notebook = { id: string; title: string; description: string | null; owner_department: string; parent_goal_id: string | null; status: string; updated_at: string };

/** Notebook shell over the canonical source intake and research_sources flow. */
export function ResearchNotebookWorkspace({ email, onNavigate }: { email: string | null; onNavigate?: (id: string) => void }) {
  const examples = useMemo(() => [
    ['Business Funding Intelligence', 'funding.workflow_expansion'],
    ['GoClear Growth', 'goclear.example_campaign'],
    ['Marketing Intelligence', 'marketing.creative_expansion'],
  ], []);
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  async function loadNotebooks() {
    if (!supabase) return;
    const { data, error } = await supabase.from('research_notebooks').select('id,title,description,owner_department,parent_goal_id,status,updated_at').order('updated_at', { ascending: false });
    if (error) { setMessage('Notebook storage is not available until the R19.1 migration is applied.'); return; }
    const rows = (data || []) as Notebook[];
    setNotebooks(rows); setSelectedId((current) => current && rows.some((row) => row.id === current) ? current : rows[0]?.id || null);
  }
  useEffect(() => { void loadNotebooks(); }, []);
  async function createNotebook() {
    if (!supabase || !title.trim()) return;
    const { data, error } = await supabase.from('research_notebooks').insert({ title: title.trim(), owner_department: 'RESEARCH', status: 'active' }).select('id,title,description,owner_department,parent_goal_id,status,updated_at').single();
    if (error) { setMessage('Could not create notebook. Check Admin authentication and RLS.'); return; }
    setTitle(''); setMessage('Notebook created.'); setNotebooks((rows) => [data as Notebook, ...rows]); setSelectedId((data as Notebook).id);
  }
  async function renameNotebook(notebook: Notebook) {
    const next = window.prompt('Notebook title', notebook.title)?.trim();
    if (!supabase || !next || next === notebook.title) return;
    const { error } = await supabase.from('research_notebooks').update({ title: next, updated_at: new Date().toISOString() }).eq('id', notebook.id);
    if (error) { setMessage('Notebook update failed; no local state was changed.'); return; }
    setNotebooks((rows) => rows.map((row) => row.id === notebook.id ? { ...row, title: next } : row)); setMessage('Notebook updated.');
  }
  return (
    <div className="nx2-page research-notebook-workspace" data-testid="admin-research-notebook">
      <div className="nx2-hero">
        <div><div className="nx2-eyebrow">RESEARCH / NOTEBOOK</div><h2>Organize evidence around decisions.</h2><p>Use the existing source library, Alpha claims, and governed handoffs in one reviewable workspace.</p></div>
        <span className="nx2-status nx2-status-green">Evidence-bound</span>
      </div>
      <div className="nx2-kpi-row">
        <div className="nx2-kpi"><span>Notebooks</span><strong className="nx2-blue">{notebooks.length || examples.length}</strong><small>Decision-oriented collections</small></div>
        <div className="nx2-kpi"><span>Research modes</span><strong className="nx2-green">Once · Monitor</strong><small>Cadence is stored per source</small></div>
        <div className="nx2-kpi"><span>Handoff</span><strong className="nx2-violet">Alpha → Work</strong><small>Claims stay source-bound</small></div>
      </div>
      <section className="nx2-card" aria-label="Notebook collections">
        <div className="nx2-card-head"><div><div className="nx2-eyebrow">NOTEBOOKS</div><h3>Decision collections</h3></div><span className="nx2-muted">Canonical source records remain in Supabase.</span></div>
        <div className="nx2-link-grid">{notebooks.length ? notebooks.map((notebook) => <button type="button" className="nx2-kpi" key={notebook.id} onClick={() => setSelectedId(notebook.id)}><strong>{notebook.title}</strong><small>{notebook.parent_goal_id || 'RESEARCH'} · {notebook.status}</small><span>{selectedId === notebook.id ? 'Selected for source intake' : 'Open notebook'}</span></button>) : examples.map(([exampleTitle, goal]) => <div className="nx2-kpi" key={goal}><strong>{exampleTitle}</strong><small>{goal} · example</small></div>)}</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}><input aria-label="New notebook title" className="nx2-input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="New notebook title" /><button type="button" className="nx2-primary-button" onClick={() => void createNotebook()}>Create notebook</button>{selectedId && notebooks.find((row) => row.id === selectedId) && <button type="button" className="nx2-outline-button" onClick={() => void renameNotebook(notebooks.find((row) => row.id === selectedId) as Notebook)}>Rename selected</button>}<button type="button" className="nx2-outline-button" onClick={() => void loadNotebooks()}>Refresh</button></div>
        {message && <p role="status" className="nx2-muted">{message}</p>}
      </section>
      <SourceIntakeReviewPage email={email} onNavigate={onNavigate} defaultNotebookId={selectedId} />
    </div>
  );
}
