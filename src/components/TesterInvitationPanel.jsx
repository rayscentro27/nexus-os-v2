import React, { useCallback, useEffect, useState } from 'react';
import { createTesterInvitation, resendTesterInvitation, revokeTesterInvitation, loadTesterInvitations, loadPilotControls, updatePilotControls } from '../lib/testerInvitationClient';
import { HIDDEN_PILOT_OFFERS } from '../config/serviceOfferCatalog';
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient';

const LEVEL_LABELS = {
  friends_family_free: 'Free Friends & Family Preview',
  friends_family_one_dollar: '$1 Friends & Family Pilot',
  synthetic_internal: 'Synthetic Internal',
  invited_test_mode: 'Invited Preview',
  controlled_live_pilot: 'Controlled $1 Pilot',
};

const LEVEL_DESCRIPTIONS = {
  friends_family_free: 'No payment · Full system preview · Feedback requested',
  friends_family_one_dollar: 'Full system preview · $1 payment pilot · Allowlist required',
  synthetic_internal: 'Internal synthetic testing',
  invited_test_mode: 'Invited test mode',
  controlled_live_pilot: 'Controlled live pilot',
};

const STATUS_COLORS = {
  draft: '#6b7280', awaiting_approval: '#f59e0b', approved: '#3b82f6', sent: '#8b5cf6',
  accepted: '#10b981', expired: '#ef4444', revoked: '#ef4444', completed: '#10b981', failed: '#ef4444',
};

function ConfirmationModal({ open, title, message, onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.7)' }}>
      <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, padding: 24, maxWidth: 420, width: '90%' }}>
        <h3 style={{ color: '#f8fafc', margin: '0 0 8px', fontSize: 16 }}>{title}</h3>
        <p style={{ color: '#94a3b8', margin: '0 0 20px', fontSize: 13, lineHeight: 1.5 }}>{message}</p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid #475569', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
          <button onClick={onConfirm} style={{ padding: '6px 16px', borderRadius: 6, border: 'none', background: '#ef4444', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Confirm</button>
        </div>
      </div>
    </div>
  );
}

export default function TesterInvitationPanel() {
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newInv, setNewInv] = useState({ testerName: '', testerEmail: '', testingLevel: 'friends_family_free', maxSessions: 3, taskChecklistVersion: 'v1', expiresInDays: 14, personalMessage: '' });
  const [controls, setControls] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);
  const [copiedToken, setCopiedToken] = useState(null);

  const load = useCallback(async () => {
    if (!isSupabaseConfigured) { setLoading(false); return; }
    setLoading(true);
    const result = await loadTesterInvitations();
    setInvitations(result.invitations);
    const ctrl = await loadPilotControls();
    setControls(ctrl.controls);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!newInv.testerName || !newInv.testerEmail) { setMessage('Name and email are required.'); return; }
    setMessage('');
    const result = await createTesterInvitation(newInv);
    if (!result.ok) { setMessage('Creation failed: ' + (result.error || 'unknown')); return; }
    setMessage('Invitation created. Token available for one-time copy.');
    if (result.data && result.data.raw_token) setCopiedToken(result.data.raw_token);
    setShowCreate(false);
    setNewInv({ testerName: '', testerEmail: '', testingLevel: 'friends_family_free', maxSessions: 3, taskChecklistVersion: 'v1', expiresInDays: 14, personalMessage: '' });
    await load();
  };

  const approve = async (inv) => {
    if (!supabase) return;
    setMessage('');
    const { error } = await supabase.from('tester_invitations').update({ invitation_status: 'approved' }).eq('id', inv.id);
    if (error) { setMessage('Approval failed.'); return; }
    await supabase.from('invitation_events').insert({ invitation_id: inv.id, event_type: 'invitation_approved', metadata: {} });
    setMessage('Invitation approved.');
    await load();
  };

  const send = async (inv) => {
    setMessage('');
    const result = await resendTesterInvitation(inv.id);
    if (!result.ok) { setMessage('Send failed: ' + (result.error || '')); return; }
    setMessage('Invitation sent. Provider result: ' + (result.data?.provider_result || 'unknown'));
    await load();
  };

  const revoke = async (inv) => {
    setMessage('');
    const result = await revokeTesterInvitation(inv.id, 'admin_revocation');
    if (!result.ok) { setMessage('Revoke failed.'); return; }
    setMessage('Invitation revoked.');
    await load();
  };

  const extend = async (inv) => {
    if (!supabase) return;
    const newExpiry = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
    await supabase.from('tester_invitations').update({ expires_at: newExpiry }).eq('id', inv.id);
    setMessage('Expiration extended by 7 days.');
    await load();
  };

  const markCompleted = async (inv) => {
    if (!supabase) return;
    await supabase.from('tester_invitations').update({ invitation_status: 'completed', completed_at: new Date().toISOString() }).eq('id', inv.id);
    setMessage('Invitation marked completed.');
    await load();
  };

  const toggleInvitations = async () => {
    if (!controls) return;
    const newState = !controls.invitations_enabled;
    setConfirmAction({
      title: newState ? 'Enable Invitations?' : 'Disable Invitations?',
      message: newState ? 'This will allow admins to create new invitations.' : 'This will prevent new invitation creation.',
      action: async () => {
        await updatePilotControls({ invitations_enabled: newState });
        setMessage(newState ? 'Invitations enabled.' : 'Invitations disabled.');
        await load();
      },
    });
  };

  const toggleTestPurchases = async () => {
    if (!controls) return;
    const newState = !controls.test_mode_purchases_enabled;
    setConfirmAction({
      title: newState ? 'Enable Test Purchases?' : 'Disable Test Purchases?',
      message: newState ? 'This will allow testers to make test-mode purchases.' : 'This will block all test-mode purchases.',
      action: async () => {
        await updatePilotControls({ test_mode_purchases_enabled: newState });
        setMessage(newState ? 'Test purchases enabled.' : 'Test purchases disabled.');
        await load();
      },
    });
  };

  const stats = {
    total: invitations.length,
    draft: invitations.filter(i => i.invitation_status === 'draft').length,
    sent: invitations.filter(i => i.invitation_status === 'sent').length,
    accepted: invitations.filter(i => i.invitation_status === 'accepted').length,
    completed: invitations.filter(i => i.invitation_status === 'completed').length,
    revoked: invitations.filter(i => i.invitation_status === 'revoked').length,
  };

  return (
    <div className="nxos-stack" data-testid="tester-invitation-panel">
      <div className="nxos-callout" style={{ borderLeft: '4px solid #10b981' }}>
        <strong>GoClear Friends & Family Preview Program</strong>
        <p>Create, manage, and track Friends & Family invitations. Tokens are shown only once at creation. All state changes are audit-logged.</p>
      </div>

      <div className="nxos-metric-grid">
        <article><small>Total</small><strong>{stats.total}</strong></article>
        <article><small>Draft</small><strong>{stats.draft}</strong></article>
        <article><small>Sent</small><strong>{stats.sent}</strong></article>
        <article><small>Accepted</small><strong>{stats.accepted}</strong></article>
        <article><small>Completed</small><strong>{stats.completed}</strong></article>
        <article><small>Revoked</small><strong>{stats.revoked}</strong></article>
      </div>

      {controls && (
        <section className="nxos-table-card">
          <h2>Payment Controls</h2>
          <div style={{ display: 'grid', gap: 8 }}>
            <div><strong>Mode:</strong> {controls.mode}</div>
            <div><strong>Invitations:</strong> {controls.invitations_enabled ? 'ON' : 'OFF'}</div>
            <div><strong>Test Purchases:</strong> {controls.test_mode_purchases_enabled ? 'Enabled' : 'Disabled'}</div>
            <div><strong>Controlled Live:</strong> {controls.controlled_live_pilot_enabled ? 'ENABLED' : 'Disabled'}</div>
            <div><strong>Public Live:</strong> {controls.public_live_enabled ? 'ENABLED' : 'Disabled'}</div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
            <button onClick={toggleInvitations} style={{ padding: '6px 14px', borderRadius: 6, border: 'none', background: controls.invitations_enabled ? '#10b981' : '#6b7280', color: '#fff', cursor: 'pointer', fontSize: 13 }} data-testid="invitations-toggle">
              {controls.invitations_enabled ? 'Invitations: ON' : 'Invitations: OFF'}
            </button>
            <button onClick={toggleTestPurchases} style={{ padding: '6px 14px', borderRadius: 6, border: 'none', background: controls.test_mode_purchases_enabled ? '#10b981' : '#6b7280', color: '#fff', cursor: 'pointer', fontSize: 13 }} data-testid="test-purchases-toggle">
              {controls.test_mode_purchases_enabled ? 'Test Purchases: ON' : 'Test Purchases: OFF'}
            </button>
          </div>
        </section>
      )}

      {message && <p className="nxos-callout">{message}</p>}

      {copiedToken && (
        <div className="nxos-callout" style={{ borderLeft: '4px solid #f59e0b' }}>
          <strong>One-Time Token Display</strong>
          <p style={{ fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all' }}>{copiedToken}</p>
          <button onClick={() => { navigator.clipboard.writeText(copiedToken); }} style={{ marginTop: 8, padding: '4px 12px', borderRadius: 4, border: '1px solid #475569', background: 'transparent', color: '#e2e8f0', cursor: 'pointer', fontSize: 12 }}>Copy Token</button>
          <button onClick={() => setCopiedToken(null)} style={{ marginTop: 8, marginLeft: 8, padding: '4px 12px', borderRadius: 4, border: '1px solid #475569', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 12 }}>Dismiss</button>
        </div>
      )}

      <section className="nxos-table-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Invitations</h2>
          <button onClick={() => setShowCreate(!showCreate)} className="nxos-button" style={{ padding: '6px 14px', background: '#10b981', color: '#fff', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 13 }} data-testid="create-invitation-btn">
            {showCreate ? 'Cancel' : 'Create Invitation'}
          </button>
        </div>

        {showCreate && (
          <div style={{ background: '#0f172a', padding: 16, borderRadius: 8, border: '1px solid #334155', marginBottom: 16 }}>
            <div style={{ display: 'grid', gap: 12 }}>
              <input type="text" value={newInv.testerName} onChange={e => setNewInv(p => ({ ...p, testerName: e.target.value }))} placeholder="Recipient name" style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} data-testid="new-inv-name" />
              <input type="email" value={newInv.testerEmail} onChange={e => setNewInv(p => ({ ...p, testerEmail: e.target.value }))} placeholder="Recipient email" style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} data-testid="new-inv-email" />

              <div>
                <select value={newInv.testingLevel} onChange={e => setNewInv(p => ({ ...p, testingLevel: e.target.value }))} style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} data-testid="new-inv-level">
                  <option value="friends_family_free">Free Friends & Family Preview</option>
                  <option value="friends_family_one_dollar">$1 Friends & Family Pilot</option>
                </select>
                <p style={{ color: '#94a3b8', fontSize: 11, marginTop: 4 }}>{LEVEL_DESCRIPTIONS[newInv.testingLevel]}</p>
              </div>

              <textarea value={newInv.personalMessage} onChange={e => setNewInv(p => ({ ...p, personalMessage: e.target.value }))} placeholder="Personal note from Ray (optional)" rows={2} style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc', fontSize: 13, resize: 'vertical' }} data-testid="new-inv-personal-note" />

              <div style={{ display: 'flex', gap: 12 }}>
                <label style={{ color: '#94a3b8', fontSize: 12 }}>Sessions: <input type="number" value={newInv.maxSessions} onChange={e => setNewInv(p => ({ ...p, maxSessions: Number(e.target.value) }))} min={1} max={10} style={{ width: 60, padding: '4px 8px', borderRadius: 4, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} /></label>
                <label style={{ color: '#94a3b8', fontSize: 12 }}>Expires: <input type="number" value={newInv.expiresInDays} onChange={e => setNewInv(p => ({ ...p, expiresInDays: Number(e.target.value) }))} min={1} max={30} style={{ width: 60, padding: '4px 8px', borderRadius: 4, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc' }} /> days</label>
              </div>

              <button onClick={create} className="nxos-button" style={{ padding: '8px 16px', background: '#10b981', color: '#fff', borderRadius: 6, border: 'none', cursor: 'pointer', fontWeight: 600 }} data-testid="confirm-create-btn">Create Invitation</button>
            </div>
          </div>
        )}

        {loading && <p>Loading invitations...</p>}
        {!loading && invitations.length === 0 && <p>No invitations created yet.</p>}
        {invitations.map(inv => (
          <article key={inv.id} className="nxos-table-row" style={{ display: 'grid', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <strong>{inv.tester_name}</strong>
                <small style={{ marginLeft: 8 }}>{inv.tester_email.slice(0, 3)}***@{inv.tester_email.split('@')[1]}</small>
              </div>
              <span style={{ padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 600, backgroundColor: (STATUS_COLORS[inv.invitation_status] || '#6b7280') + '20', color: STATUS_COLORS[inv.invitation_status] || '#6b7280' }}>
                {inv.invitation_status}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#94a3b8', flexWrap: 'wrap' }}>
              <span>{LEVEL_LABELS[inv.testing_level] || inv.testing_level}</span>
              <span>Sessions: {inv.sessions_used}/{inv.max_sessions}</span>
              <span>Expires: {new Date(inv.expires_at).toLocaleDateString()}</span>
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
              {['draft', 'awaiting_approval'].includes(inv.invitation_status) && (
                <button onClick={() => approve(inv)} style={{ padding: '3px 10px', borderRadius: 4, border: 'none', background: '#3b82f6', color: '#fff', cursor: 'pointer', fontSize: 11 }} data-testid={'approve-' + inv.id}>Approve</button>
              )}
              {['approved', 'sent'].includes(inv.invitation_status) && (
                <button onClick={() => send(inv)} style={{ padding: '3px 10px', borderRadius: 4, border: 'none', background: '#8b5cf6', color: '#fff', cursor: 'pointer', fontSize: 11 }} data-testid={'send-' + inv.id}>Send</button>
              )}
              {['approved', 'sent'].includes(inv.invitation_status) && (
                <button onClick={() => extend(inv)} style={{ padding: '3px 10px', borderRadius: 4, border: '1px solid #475569', background: 'transparent', color: '#e2e8f0', cursor: 'pointer', fontSize: 11 }} data-testid={'extend-' + inv.id}>Extend</button>
              )}
              {!['revoked', 'completed', 'expired'].includes(inv.invitation_status) && (
                <button onClick={() => setConfirmAction({ title: 'Revoke Invitation?', message: 'This will permanently revoke the invitation.', action: () => revoke(inv) })} style={{ padding: '3px 10px', borderRadius: 4, border: 'none', background: '#ef4444', color: '#fff', cursor: 'pointer', fontSize: 11 }} data-testid={'revoke-' + inv.id}>Revoke</button>
              )}
              {inv.invitation_status === 'accepted' && (
                <button onClick={() => markCompleted(inv)} style={{ padding: '3px 10px', borderRadius: 4, border: 'none', background: '#10b981', color: '#fff', cursor: 'pointer', fontSize: 11 }} data-testid={'complete-' + inv.id}>Mark Completed</button>
              )}
            </div>
          </article>
        ))}
      </section>

      <section className="nxos-table-card">
        <h2>Hidden Pilot Offers (Foundation)</h2>
        <p style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8 }}>These offers exist but are not publicly visible and not active.</p>
        {HIDDEN_PILOT_OFFERS.map(offer => (
          <div key={offer.id} className="nxos-table-row" style={{ display: 'grid', gap: 4 }}>
            <div><strong>{offer.name}</strong> <small>{offer.slug}</small></div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>
              Price: ${(offer.price_cents / 100).toFixed(2)} · Active: {offer.active ? 'YES' : 'No'} · Public: {offer.publicly_visible ? 'YES' : 'No'}
            </div>
          </div>
        ))}
      </section>

      <div className="nxos-callout">
        <strong>Security Notes</strong>
        <p>Raw tokens displayed once at creation only. No passwords stored. All mutations admin-only and audit-logged. Public live payments disabled. Controlled live pilot requires separate Ray approval.</p>
      </div>

      <ConfirmationModal
        open={!!confirmAction}
        title={confirmAction ? confirmAction.title : ''}
        message={confirmAction ? confirmAction.message : ''}
        onConfirm={() => { if (confirmAction) confirmAction.action(); setConfirmAction(null); }}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  );
}
