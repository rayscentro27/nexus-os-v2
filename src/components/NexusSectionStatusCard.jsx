import React from 'react';

const STATUS_COLORS = {
  live: { bg: '#22c55e18', border: '#22c55e44', text: '#16a34a', icon: '\u2705' },
  static: { bg: '#f59e0b18', border: '#f59e0b44', text: '#d97706', icon: '\u26A0\uFE0F' },
  mismatch: { bg: '#ef444418', border: '#ef444444', text: '#dc2626', icon: '\u274C' },
  blocked: { bg: '#ef444418', border: '#ef444444', text: '#dc2626', icon: '\uD83D\uDEAB' },
  unknown: { bg: '#9ca3af18', border: '#9ca3af44', text: '#6b7280', icon: '\u2753' },
};

const PROOF_LABELS = {
  verified: 'Proof verified',
  unproven: 'Not proven',
  no_proof: 'No proof',
};

/**
 * NexusSectionStatusCard — visual proof card for a single section.
 *
 * Compact mode: inline badge for embedding in panels.
 * Full mode: card with details, blockers, next action.
 */
export default function NexusSectionStatusCard({ section, compact = false, onNavigate }) {
  if (!section) return null;

  const style = STATUS_COLORS[section.status] || STATUS_COLORS.unknown;
  const verifiedDate = section.verifiedAt ? new Date(section.verifiedAt).toLocaleDateString() : 'never';

  if (compact) {
    return (
      <span
        className="nxos-section-status-compact"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '2px 8px', borderRadius: 4, fontSize: '0.78em',
          background: style.bg, border: `1px solid ${style.border}`, color: style.text,
          cursor: onNavigate ? 'pointer' : 'default',
        }}
        onClick={() => onNavigate?.(section.id)}
        title={`${section.name}: ${section.status} — ${section.notes}`}
      >
        <span>{style.icon}</span>
        <span style={{ fontWeight: 600 }}>{section.status}</span>
      </span>
    );
  }

  return (
    <div
      className="nxos-section-status-card"
      style={{
        padding: '12px 16px', borderRadius: 8,
        background: style.bg, border: `1px solid ${style.border}`,
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '1.2em' }}>{style.icon}</span>
          <div>
            <strong style={{ color: style.text }}>{section.name}</strong>
            <small style={{ color: '#666', marginLeft: 8 }}>{section.description}</small>
          </div>
        </div>
        <span style={{
          padding: '2px 8px', borderRadius: 4, fontSize: '0.78em',
          background: style.bg, border: `1px solid ${style.border}`, color: style.text, fontWeight: 600,
        }}>
          {section.status.toUpperCase()}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: '0.82em', color: '#555' }}>
        <div>Source: <strong>{section.source}</strong></div>
        <div>Proof: <strong>{PROOF_LABELS[section.proofLevel]}</strong></div>
        {section.tableNames.length > 0 && <div>Table: <strong>{section.tableNames.join(', ')}</strong></div>}
        {section.rowCount > 0 && <div>Rows: <strong>{section.rowCount}</strong></div>}
        {section.schedulerInstalled && <div>Scheduler: <strong>{section.schedulerRunning ? 'running' : 'installed'}</strong></div>}
        {section.supabaseWrites && <div>Supabase writes: <strong>yes</strong></div>}
        <div>Verified: <strong>{verifiedDate}</strong></div>
      </div>

      {section.blockers.length > 0 && (
        <div style={{ marginTop: 6, padding: '4px 8px', background: '#fef2f2', borderRadius: 4, fontSize: '0.82em', color: '#991b1b' }}>
          <strong>Blockers:</strong> {section.blockers.join('; ')}
        </div>
      )}

      {section.nextAction && (
        <div style={{ marginTop: 4, fontSize: '0.82em', color: '#555' }}>
          <strong>Next:</strong> {section.nextAction}
        </div>
      )}
    </div>
  );
}
