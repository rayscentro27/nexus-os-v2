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

const ACCEPTANCE_LINK_PREVIEW = 'https://goclearonline.cc/invite/[secure-invitation-token]';
const INPUT_STYLE = { padding: '7px 10px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#f8fafc', fontSize: 13, width: '100%', boxSizing: 'border-box' };
const LABEL_STYLE = { color: '#94a3b8', fontSize: 12, display: 'block', marginBottom: 4 };
const FIELD_GROUP = { marginBottom: 12 };

function maskEmail(email = '') {
  const [local = '', domain = ''] = email.split('@');
  if (!domain) return '';
  return `${local.slice(0, 2)}***@${domain}`;
}

function ConfirmationModal({ open, title, message, onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 110, display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(0,0,0,0.7)' }}>
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

function InvitationEmailPreview({ invitation }) {
  const isFree = invitation.testingLevel === 'friends_family_free';
  const typeLabel = LEVEL_LABELS[invitation.testingLevel] || invitation.testingLevel;
  return (
    <div className="tester-email-preview" data-testid="create-email-preview">
      <div className="preview-row"><span>FROM</span><strong>Ray Davis &lt;ray@goclearonline.cc&gt;</strong></div>
      <div className="preview-row"><span>TO</span><strong>{maskEmail(invitation.testerEmail) || 'Recipient pending'}</strong></div>
      <div className="preview-row"><span>SUBJECT</span><strong>You're Invited to GoClear - A Personal Note from Ray</strong></div>
      <div className="preview-message">
        <p>Hi {invitation.testerName || 'there'},</p>
        <p>I built GoClear to help people take control of their credit and funding future. I would like your eyes on it before we go wider.</p>
        <p>You have been invited to the <strong>{typeLabel}</strong>.</p>
        {isFree ? (
          <p>No payment is required for this Friends & Family Free Preview. Your feedback helps shape the client experience.</p>
        ) : (
          <p>This is a controlled $1 product-testing pilot. It is invitation-only, test-mode gated, and does not activate public live payments.</p>
        )}
        {invitation.personalMessage && <p className="personal-note">{invitation.personalMessage}</p>}
        <div className="link-preview">
          <span>ACCEPTANCE LINK</span>
          <code>{ACCEPTANCE_LINK_PREVIEW}</code>
          <strong>goclearonline.cc</strong>
        </div>
      </div>
    </div>
  );
}

function CreateDrawer({ open, onClose, newInv, setNewInv, onCreate, message }) {
  const [step, setStep] = useState('details');
  useEffect(() => {
    if (open) {
      setStep('details');
      document.body.classList.add('tester-invite-drawer-open');
    }
    return () => document.body.classList.remove('tester-invite-drawer-open');
  }, [open]);
  if (!open) return null;
  const canPreview = Boolean(newInv.testerName && newInv.testerEmail);
  return (
    <div className="tester-invite-drawer-backdrop" data-testid="create-invitation-drawer">
      <div onClick={onClose} className="tester-invite-drawer-overlay" />
      <div className="tester-invite-drawer" role="dialog" aria-modal="true" aria-label="Create tester invitation">
        <div className="tester-invite-drawer-header">
          <div>
            <h2>Create Invitation</h2>
            <p>{step === 'details' ? 'Step 1 of 3 - Details' : step === 'preview' ? 'Step 2 of 3 - Email Preview' : 'Step 3 of 3 - Confirmation'}</p>
          </div>
          <button onClick={onClose} aria-label="Close create invitation drawer">&times;</button>
        </div>

        <div className="tester-invite-drawer-body" data-testid="create-drawer-body">
          {step === 'details' && (
            <>
              <div className="tester-invite-form-grid">
                <div style={FIELD_GROUP}>
                  <label style={LABEL_STYLE}>Recipient Name *</label>
                  <input type="text" value={newInv.testerName} onChange={e => setNewInv(p => ({ ...p, testerName: e.target.value }))} placeholder="Full name" style={INPUT_STYLE} data-testid="new-inv-name" />
                </div>
                <div style={FIELD_GROUP}>
                  <label style={LABEL_STYLE}>Recipient Email *</label>
                  <input type="email" value={newInv.testerEmail} onChange={e => setNewInv(p => ({ ...p, testerEmail: e.target.value }))} placeholder="email@example.com" style={INPUT_STYLE} data-testid="new-inv-email" />
                </div>
                <div style={FIELD_GROUP}>
                  <label style={LABEL_STYLE}>Invitation Type</label>
                  <select value={newInv.testingLevel} onChange={e => setNewInv(p => ({ ...p, testingLevel: e.target.value }))} style={{ ...INPUT_STYLE, cursor: 'pointer' }} data-testid="new-inv-level">
                    <option value="friends_family_free">Free Friends & Family Preview</option>
                    <option value="friends_family_one_dollar">$1 Friends & Family Pilot</option>
                  </select>
                  <p style={{ color: '#64748b', fontSize: 11, marginTop: 4 }}>{LEVEL_DESCRIPTIONS[newInv.testingLevel]}</p>
                </div>
                <div style={FIELD_GROUP}>
                  <label style={LABEL_STYLE}>Device Preference</label>
                  <select value={newInv.devicePreference || 'any'} onChange={e => setNewInv(p => ({ ...p, devicePreference: e.target.value }))} style={{ ...INPUT_STYLE, cursor: 'pointer' }} data-testid="new-inv-device">
                    <option value="any">Any Device</option>
                    <option value="iphone">iPhone</option>
                    <option value="android">Android</option>
                    <option value="desktop">Desktop</option>
                  </select>
                </div>
                <div style={FIELD_GROUP}>
                  <label style={LABEL_STYLE}>Journey</label>
                  <select value={newInv.taskChecklistVersion} onChange={e => setNewInv(p => ({ ...p, taskChecklistVersion: e.target.value }))} style={{ ...INPUT_STYLE, cursor: 'pointer' }} data-testid="new-inv-journey">
                    <option value="v1">GoClear guided preview</option>
                    <option value="funding_readiness_v1">Funding readiness focus</option>
                  </select>
                </div>
                <div style={FIELD_GROUP}>
                  <label style={LABEL_STYLE}>Expiration (days)</label>
                  <input type="number" value={newInv.expiresInDays} onChange={e => setNewInv(p => ({ ...p, expiresInDays: Number(e.target.value) }))} min={1} max={30} style={INPUT_STYLE} data-testid="new-inv-expiry" />
                </div>
                <div style={FIELD_GROUP}>
                  <label style={LABEL_STYLE}>Max Sessions</label>
                  <input type="number" value={newInv.maxSessions} onChange={e => setNewInv(p => ({ ...p, maxSessions: Number(e.target.value) }))} min={1} max={10} style={INPUT_STYLE} data-testid="new-inv-sessions" />
                </div>
              </div>
              <div style={FIELD_GROUP}>
                <label style={LABEL_STYLE}>Personal Message (optional)</label>
                <textarea value={newInv.personalMessage} onChange={e => setNewInv(p => ({ ...p, personalMessage: e.target.value }))} placeholder="A personal note from Ray..." rows={3} style={{ ...INPUT_STYLE, resize: 'vertical', lineHeight: 1.5 }} data-testid="new-inv-personal-note" />
              </div>

              <div style={{ background: '#1e293b', borderRadius: 8, padding: 12, border: '1px solid #334155', marginTop: 4 }}>
                <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 6 }}>PREVIEW SUMMARY</div>
                <div style={{ fontSize: 13, color: '#e2e8f0' }}>
                  <strong>{LEVEL_LABELS[newInv.testingLevel]}</strong>
                  {newInv.testingLevel === 'friends_family_free' && <span style={{ color: '#10b981', marginLeft: 8 }}>No payment required</span>}
                  {newInv.testingLevel === 'friends_family_one_dollar' && <span style={{ color: '#f59e0b', marginLeft: 8 }}>$1.00 pilot</span>}
                </div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
                  {newInv.maxSessions} session{newInv.maxSessions !== 1 ? 's' : ''} - {newInv.expiresInDays} days expiry - {newInv.devicePreference || 'any'} device
                </div>
                {newInv.personalMessage && <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4, fontStyle: 'italic' }}>"{newInv.personalMessage}"</div>}
              </div>
            </>
          )}

          {step === 'preview' && <InvitationEmailPreview invitation={newInv} />}

          {step === 'confirm' && (
            <div className="tester-create-confirm" data-testid="create-confirmation-step">
              <h3>Ready to save draft</h3>
              <p>Review is complete. Saving creates a draft invitation and keeps approval and sending gated to admin actions.</p>
              <div><strong>Recipient</strong><span>{maskEmail(newInv.testerEmail)}</span></div>
              <div><strong>Type</strong><span>{LEVEL_LABELS[newInv.testingLevel]}</span></div>
              <div><strong>Domain</strong><span>goclearonline.cc</span></div>
              <p className="safe-note">No password, raw token, localhost, or Netlify link appears in the preview.</p>
            </div>
          )}

          {message && <p style={{ color: '#f59e0b', fontSize: 12, marginTop: 12, padding: '8px 12px', background: '#1e293b', borderRadius: 6 }}>{message}</p>}
        </div>

        <div className="tester-invite-drawer-footer" data-testid="create-drawer-footer">
          <button onClick={onClose} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #475569', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>Cancel</button>
          {step !== 'details' && <button onClick={() => setStep(step === 'confirm' ? 'preview' : 'details')} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #475569', background: 'transparent', color: '#e2e8f0', cursor: 'pointer', fontSize: 13 }}>Back to Edit</button>}
          {step === 'details' && <button onClick={() => canPreview ? setStep('preview') : null} disabled={!canPreview} style={{ padding: '8px 20px', borderRadius: 6, border: 'none', background: canPreview ? '#10b981' : '#475569', color: '#fff', cursor: canPreview ? 'pointer' : 'not-allowed', fontSize: 13, fontWeight: 600 }} data-testid="preview-create-btn">Preview Email</button>}
          {step === 'preview' && <button onClick={() => setStep('confirm')} style={{ padding: '8px 20px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }} data-testid="continue-confirm-btn">Continue</button>}
          {step === 'confirm' && (
            <>
              <button disabled style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#64748b', cursor: 'not-allowed', fontSize: 12 }}>Approve after save</button>
              <button disabled style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #334155', background: '#1e293b', color: '#64748b', cursor: 'not-allowed', fontSize: 12 }}>Send after approval</button>
              <button onClick={onCreate} style={{ padding: '8px 20px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }} data-testid="confirm-create-btn">Save Draft</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function EmailPreviewModal({ open, onClose, inv }) {
  if (!open || !inv) return null;
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 110, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.7)' }}>
      <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 12, maxWidth: 560, width: '95%', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <h3 style={{ margin: 0, fontSize: 15, color: '#f8fafc' }}>Email Preview</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: 20, cursor: 'pointer' }}>&times;</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          <div style={{ background: '#0f172a', borderRadius: 8, padding: 16, border: '1px solid #334155' }}>
            <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>FROM</div>
            <div style={{ fontSize: 13, color: '#e2e8f0', marginBottom: 12 }}>Ray Davis &lt;ray@goclearonline.cc&gt;</div>
            <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>TO</div>
            <div style={{ fontSize: 13, color: '#e2e8f0', marginBottom: 12 }}>{inv.tester_email}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>SUBJECT</div>
            <div style={{ fontSize: 13, color: '#e2e8f0', marginBottom: 16, fontWeight: 600 }}>You're Invited to GoClear — A Personal Note from Ray</div>

            <div style={{ borderTop: '1px solid #334155', paddingTop: 16 }}>
              <p style={{ color: '#e2e8f0', fontSize: 13, lineHeight: 1.7, margin: '0 0 12px' }}>Hi {inv.tester_name || 'there'},</p>
              <p style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.7, margin: '0 0 12px' }}>
                I built GoClear to help people take control of their credit and funding future. I'd love your eyes on it before we go wider.
              </p>
              <p style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.7, margin: '0 0 12px' }}>
                You've been invited to the <strong style={{ color: '#10b981' }}>Friends & Family Free Preview</strong> — full access, no payment, just your honest feedback.
              </p>

              <div style={{ background: '#1e293b', borderRadius: 8, padding: 14, margin: '16px 0' }}>
                <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>What's Inside</div>
                <ul style={{ color: '#cbd5e1', fontSize: 12, lineHeight: 1.8, margin: 0, paddingLeft: 16 }}>
                  <li>Credit Profile Dashboard</li>
                  <li>Document Vault</li>
                  <li>Clyde — AI Credit Coach</li>
                  <li>Business Setup & Bankability</li>
                  <li>Funding Readiness Tools</li>
                </ul>
              </div>

              <p style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.7, margin: '0 0 16px' }}>
                Click below to create your account and get started:
              </p>

              <div style={{ textAlign: 'center', margin: '20px 0' }}>
                <div style={{ display: 'inline-block', padding: '12px 28px', background: '#10b981', color: '#fff', borderRadius: 8, fontWeight: 600, fontSize: 14 }}>
                  Create My Account →
                </div>
              </div>

              <div style={{ marginTop: 16, padding: '10px 14px', background: '#0f172a', borderRadius: 6, border: '1px solid #1e3a5f' }}>
                <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>LINK DOMAIN</div>
                <span style={{ display: 'inline-block', padding: '3px 8px', background: '#10b98120', color: '#10b981', borderRadius: 4, fontSize: 11, fontWeight: 600, fontFamily: 'monospace' }}>goclearonline.cc</span>
              </div>
            </div>
          </div>
        </div>
        <div style={{ padding: '12px 20px', borderTop: '1px solid #334155', display: 'flex', gap: 8, justifyContent: 'flex-end', flexShrink: 0 }}>
          <button onClick={onClose} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #475569', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function TesterInvitationPanel() {
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [showDrawer, setShowDrawer] = useState(false);
  const [newInv, setNewInv] = useState({ testerName: '', testerEmail: '', testingLevel: 'friends_family_free', maxSessions: 3, taskChecklistVersion: 'v1', expiresInDays: 14, personalMessage: '', devicePreference: 'any' });
  const [controls, setControls] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);
  const [copiedToken, setCopiedToken] = useState(null);
  const [previewEmail, setPreviewEmail] = useState(null);
  const [showHiddenOffers, setShowHiddenOffers] = useState(false);

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
    setShowDrawer(false);
    setNewInv({ testerName: '', testerEmail: '', testingLevel: 'friends_family_free', maxSessions: 3, taskChecklistVersion: 'v1', expiresInDays: 14, personalMessage: '', devicePreference: 'any' });
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

  const chipStyle = (count, color) => ({
    display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 8,
    background: 'rgba(15,23,42,0.6)', border: '1px solid #1e3a5f', minWidth: 0,
  });
  const displayControls = controls || {
    mode: 'test',
    invitations_enabled: true,
    test_mode_purchases_enabled: true,
    controlled_live_pilot_enabled: false,
    public_live_enabled: false,
  };

  return (
    <div className="tester-invitation-panel" data-testid="tester-invitation-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 0, overflow: 'hidden' }}>

      {/* ROW 1: Header */}
      <div className="tester-invitation-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 0 10px', flexShrink: 0 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 17, color: '#f8fafc', fontWeight: 600 }}>Tester Invitations - GoClear Friends & Family Preview</h2>
          <p style={{ margin: '2px 0 0', color: '#64748b', fontSize: 12 }}>Create, manage, and send tester invitations</p>
        </div>
        <div className="tester-invitation-actions" style={{ display: 'flex', gap: 8 }}>
          <button onClick={load} style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #334155', background: 'transparent', color: '#94a3b8', cursor: 'pointer', fontSize: 12 }}>Refresh</button>
          <button onClick={() => setShowDrawer(true)} style={{ padding: '7px 16px', borderRadius: 6, border: 'none', background: '#10b981', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600 }} data-testid="create-invitation-btn">+ Create Invitation</button>
        </div>
      </div>

      {/* ROW 2: Compact Metrics */}
      <div className="tester-metric-chips" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: '0 0 8px', flexShrink: 0 }}>
        {[
          { label: 'Total', value: stats.total, color: '#e2e8f0' },
          { label: 'Draft', value: stats.draft, color: '#6b7280' },
          { label: 'Sent', value: stats.sent, color: '#8b5cf6' },
          { label: 'Accepted', value: stats.accepted, color: '#10b981' },
          { label: 'Completed', value: stats.completed, color: '#10b981' },
          { label: 'Revoked', value: stats.revoked, color: '#ef4444' },
        ].map(s => (
          <div key={s.label} style={chipStyle()}>
            <span style={{ color: '#64748b', fontSize: 11 }}>{s.label}</span>
            <span style={{ color: s.color, fontSize: 15, fontWeight: 700 }}>{s.value}</span>
          </div>
        ))}
      </div>

      {/* ROW 3: Safety Status Strip */}
      {(
        <div className="tester-safety-strip" style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '6px 10px', borderRadius: 8, background: 'rgba(15,23,42,0.5)', border: '1px solid #1e3a5f', flexShrink: 0, marginBottom: 8, flexWrap: 'wrap' }} data-testid="payment-safety-strip">
          <span style={{ color: '#64748b', fontSize: 11, fontWeight: 600, marginRight: 4 }}>SAFETY</span>
          {[
            { label: 'Mode', value: displayControls.mode, color: '#3b82f6' },
            { label: 'Invites', value: displayControls.invitations_enabled ? 'ON' : 'OFF', color: displayControls.invitations_enabled ? '#10b981' : '#ef4444' },
            { label: 'Test $', value: displayControls.test_mode_purchases_enabled ? 'ON' : 'OFF', color: displayControls.test_mode_purchases_enabled ? '#10b981' : '#ef4444' },
            { label: 'Live', value: displayControls.controlled_live_pilot_enabled ? 'ON' : 'OFF', color: displayControls.controlled_live_pilot_enabled ? '#f59e0b' : '#10b981' },
            { label: 'Public', value: displayControls.public_live_enabled ? 'ON' : 'OFF', color: displayControls.public_live_enabled ? '#f59e0b' : '#10b981' },
          ].map(s => (
            <span key={s.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 4, fontSize: 11, background: 'rgba(0,0,0,0.3)' }}>
              <span style={{ color: '#64748b' }}>{s.label}: </span>
              <span style={{ color: s.color, fontWeight: 600 }}>{s.value}</span>
            </span>
          ))}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            <button onClick={toggleInvitations} disabled={!controls} style={{ padding: '3px 10px', borderRadius: 4, border: 'none', background: displayControls.invitations_enabled ? '#10b98130' : '#ef444430', color: displayControls.invitations_enabled ? '#10b981' : '#ef4444', cursor: controls ? 'pointer' : 'wait', fontSize: 11, fontWeight: 600 }} data-testid="invitations-toggle">
              {displayControls.invitations_enabled ? 'Invitations ON' : 'Invitations OFF'}
            </button>
            <button onClick={toggleTestPurchases} disabled={!controls} style={{ padding: '3px 10px', borderRadius: 4, border: 'none', background: displayControls.test_mode_purchases_enabled ? '#10b98130' : '#ef444430', color: displayControls.test_mode_purchases_enabled ? '#10b981' : '#ef4444', cursor: controls ? 'pointer' : 'wait', fontSize: 11, fontWeight: 600 }} data-testid="test-purchases-toggle">
              {displayControls.test_mode_purchases_enabled ? 'Test $ ON' : 'Test $ OFF'}
            </button>
          </div>
        </div>
      )}

      {message && (
        <div style={{ padding: '6px 12px', borderRadius: 6, background: '#1e293b', border: '1px solid #334155', color: '#f59e0b', fontSize: 12, marginBottom: 8, flexShrink: 0 }}>{message}</div>
      )}

      {copiedToken && (
        <div style={{ padding: '8px 12px', borderRadius: 6, background: '#1e293b', border: '1px solid #f59e0b40', marginBottom: 8, flexShrink: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong style={{ color: '#f59e0b', fontSize: 12 }}>One-Time Token</strong>
            <button onClick={() => setCopiedToken(null)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 14 }}>&times;</button>
          </div>
          <code style={{ display: 'block', fontFamily: 'monospace', fontSize: 11, color: '#94a3b8', marginTop: 4, wordBreak: 'break-all' }}>{copiedToken}</code>
          <button onClick={() => navigator.clipboard.writeText(copiedToken)} style={{ marginTop: 6, padding: '3px 10px', borderRadius: 4, border: '1px solid #475569', background: 'transparent', color: '#e2e8f0', cursor: 'pointer', fontSize: 11 }}>Copy</button>
        </div>
      )}

      {/* ROW 4: Invitation Table */}
      <div className="tester-invitation-table" style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', borderRadius: 8, border: '1px solid #1e3a5f', background: 'rgba(15,23,42,0.4)' }}>
        <div className="tester-invitation-table-head" style={{ padding: '8px 12px', borderBottom: '1px solid #1e3a5f', display: 'grid', gridTemplateColumns: '140px 1fr 160px 80px 90px 80px 120px', gap: 8, fontSize: 11, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, flexShrink: 0 }}>
          <span>Name</span>
          <span>Email</span>
          <span>Type</span>
          <span>Status</span>
          <span>Sessions</span>
          <span>Expires</span>
          <span style={{ textAlign: 'right' }}>Actions</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }} data-testid="invitation-table-body">
          {loading && <div style={{ padding: 20, textAlign: 'center', color: '#64748b', fontSize: 13 }}>Loading invitations...</div>}
          {!loading && invitations.length === 0 && <div style={{ padding: 20, textAlign: 'center', color: '#64748b', fontSize: 13 }}>No invitations yet. Click "+ Create Invitation" to start.</div>}
          {invitations.map(inv => (
            <div key={inv.id} className="tester-invitation-row" style={{ display: 'grid', gridTemplateColumns: '140px 1fr 160px 80px 90px 80px 120px', gap: 8, padding: '8px 12px', borderTop: '1px solid #0f172a', fontSize: 12, alignItems: 'center', minHeight: 44 }} data-testid="invitation-row">
              <span style={{ color: '#e2e8f0', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{inv.tester_name}</span>
              <span style={{ color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{inv.tester_email.slice(0, 3)}***@{inv.tester_email.split('@')[1]}</span>
              <span style={{ color: '#94a3b8', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{LEVEL_LABELS[inv.testing_level] || inv.testing_level}</span>
              <span>
                <span style={{ padding: '2px 7px', borderRadius: 10, fontSize: 10, fontWeight: 600, backgroundColor: (STATUS_COLORS[inv.invitation_status] || '#6b7280') + '20', color: STATUS_COLORS[inv.invitation_status] || '#6b7280' }}>
                  {inv.invitation_status}
                </span>
              </span>
              <span style={{ color: '#94a3b8' }}>{inv.sessions_used}/{inv.max_sessions}</span>
              <span style={{ color: '#94a3b8', fontSize: 11 }}>{new Date(inv.expires_at).toLocaleDateString()}</span>
              <div className="tester-row-actions" style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                {['draft', 'awaiting_approval'].includes(inv.invitation_status) && (
                  <button onClick={() => approve(inv)} style={{ padding: '3px 8px', borderRadius: 4, border: 'none', background: '#3b82f6', color: '#fff', cursor: 'pointer', fontSize: 10 }} data-testid={'approve-' + inv.id}>Approve</button>
                )}
                {['approved', 'sent'].includes(inv.invitation_status) && (
                  <button onClick={() => send(inv)} style={{ padding: '3px 8px', borderRadius: 4, border: 'none', background: '#8b5cf6', color: '#fff', cursor: 'pointer', fontSize: 10 }} data-testid={'send-' + inv.id}>Send</button>
                )}
                {['approved', 'sent'].includes(inv.invitation_status) && (
                  <button onClick={() => setPreviewEmail(inv)} style={{ padding: '3px 8px', borderRadius: 4, border: '1px solid #475569', background: 'transparent', color: '#e2e8f0', cursor: 'pointer', fontSize: 10 }} data-testid={'preview-' + inv.id}>Preview</button>
                )}
                {['approved', 'sent'].includes(inv.invitation_status) && (
                  <button onClick={() => extend(inv)} style={{ padding: '3px 8px', borderRadius: 4, border: '1px solid #475569', background: 'transparent', color: '#e2e8f0', cursor: 'pointer', fontSize: 10 }} data-testid={'extend-' + inv.id}>Extend</button>
                )}
                {!['revoked', 'completed', 'expired'].includes(inv.invitation_status) && (
                  <button onClick={() => setConfirmAction({ title: 'Revoke?', message: 'Permanently revoke this invitation.', action: () => revoke(inv) })} style={{ padding: '3px 8px', borderRadius: 4, border: 'none', background: '#ef4444', color: '#fff', cursor: 'pointer', fontSize: 10 }} data-testid={'revoke-' + inv.id}>Revoke</button>
                )}
                {inv.invitation_status === 'accepted' && (
                  <button onClick={() => markCompleted(inv)} style={{ padding: '3px 8px', borderRadius: 4, border: 'none', background: '#10b981', color: '#fff', cursor: 'pointer', fontSize: 10 }} data-testid={'complete-' + inv.id}>Done</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Collapsible: Hidden Pilot Offers */}
      <div className="tester-hidden-offers" style={{ marginTop: 8, flexShrink: 0 }}>
        <button onClick={() => setShowHiddenOffers(!showHiddenOffers)} style={{ background: 'none', border: 'none', color: '#64748b', fontSize: 11, cursor: 'pointer', padding: '4px 0', display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ transform: showHiddenOffers ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s', display: 'inline-block' }}>&#9654;</span>
          Hidden Pilot Offers ({HIDDEN_PILOT_OFFERS.length}): {HIDDEN_PILOT_OFFERS.map(offer => offer.slug).join(', ')}
        </button>
        {showHiddenOffers && (
          <div style={{ marginTop: 4, padding: '8px 12px', borderRadius: 6, background: 'rgba(15,23,42,0.4)', border: '1px solid #1e3a5f' }} data-testid="hidden-pilot-offers">
            {HIDDEN_PILOT_OFFERS.map(offer => (
              <div key={offer.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 11, borderBottom: '1px solid #0f172a' }}>
                <span style={{ color: '#e2e8f0' }}>{offer.name} <span style={{ color: '#64748b' }}>{offer.slug}</span></span>
                <span style={{ color: '#64748b' }}>${(offer.price_cents / 100).toFixed(2)} · {offer.active ? 'Active' : 'Off'}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="tester-security-notes" data-testid="tester-security-notes">
        <strong>Security Notes</strong>
        <span>Raw tokens displayed once at creation only. No passwords stored. Public live payments remain disabled. Controlled live pilot requires separate Ray approval.</span>
      </div>

      {/* Create Drawer */}
      <CreateDrawer
        open={showDrawer}
        onClose={() => { setShowDrawer(false); setMessage(''); }}
        newInv={newInv}
        setNewInv={setNewInv}
        onCreate={create}
        message={message}
      />

      {/* Email Preview Modal */}
      <EmailPreviewModal open={!!previewEmail} onClose={() => setPreviewEmail(null)} inv={previewEmail} />

      {/* Confirmation Modal */}
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
