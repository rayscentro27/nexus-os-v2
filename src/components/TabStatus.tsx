/**
 * Honest tab-status UI, driven entirely by src/config/nexusTabs.ts. No actions, no v1 control —
 * it only displays status badges, a per-tab Connection Status panel, and a Command Center overview
 * of all tabs + detected (uncontrolled) v1 legacy workers.
 */
import { NEXUS_TABS, V1_FLEET, badgeFor, tabById, type TabConfig, type TabStatus } from '../config/nexusTabs';

const STATUS_CLASS: Record<TabStatus, string> = {
  live_connected: 'ok',
  partial_connected: 'info',
  manual_cli_backed: 'info',
  v1_available_not_wrapped: 'warn',
  scaffold_only: 'muted',
  hide_until_ready: 'muted',
  deprecated: 'bad',
};

export function StatusBadge({ status, label }: { status: TabStatus; label?: string }) {
  return <span className={`pill ${STATUS_CLASS[status]}`} style={{ marginLeft: 6, fontSize: 10 }}>{label ?? badgeFor(status)}</span>;
}

/** Connection Status card rendered at the top of each tab. */
export function TabConnectionStatus({ tabId }: { tabId: string }) {
  const t = tabById(tabId);
  if (!t) return null;
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <strong>Connection Status</strong>
        <StatusBadge status={t.status} label={t.statusLabel} />
      </div>
      <div className="meta" style={{ marginTop: 6 }}>{t.description}</div>
      <div className="meta muted" style={{ marginTop: 6 }}>
        <b>Data:</b> {t.dataSources.join(', ') || '—'} · <b>Tables:</b> {t.tables.join(', ') || '—'}
        {t.scripts.length ? <> · <b>Scripts:</b> {t.scripts.join(', ')}</> : null}
      </div>
      {t.v1Dependencies.length > 0 && (
        <div className="meta warn" style={{ marginTop: 6 }}>
          Detected legacy worker(s) — not controlled by Nexus OS v2 yet: {t.v1Dependencies.join(', ')}
        </div>
      )}
      <div className="meta" style={{ marginTop: 6 }}><b>You can:</b> {t.actions.join(' · ') || 'read-only'}</div>
      {t.disabledReason && <div className="meta bad" style={{ marginTop: 6 }}>Gate: {t.disabledReason}</div>}
      <div className="meta muted" style={{ marginTop: 6 }}>Next: {t.recommendedNextAction}</div>
    </div>
  );
}

function group(status: TabStatus[]): TabConfig[] {
  return NEXUS_TABS.filter((t) => t.visible && status.includes(t.status));
}

/** Command Center overview: status of all tabs + detected v1 fleet + failing jobs. Read-only. */
export function SystemStatusOverview({ onOpenTab }: { onOpenTab?: (id: string) => void }) {
  const live = group(['live_connected']);
  const partial = group(['partial_connected', 'manual_cli_backed']);
  const legacy = group(['v1_available_not_wrapped']);
  const seed = group(['scaffold_only']);
  const failing = V1_FLEET.filter((w) => w.status === 'failing');
  const unsafe = V1_FLEET.filter((w) => w.actionCapable);

  const row = (label: string, items: TabConfig[]) => (
    <div className="meta" style={{ marginTop: 6 }}>
      <b>{label} ({items.length}):</b>{' '}
      {items.map((t) => (
        <button key={t.id} className="pill" style={{ marginRight: 4, cursor: onOpenTab ? 'pointer' : 'default' }}
          onClick={() => onOpenTab?.(t.id)}>{t.label} · {t.statusLabel}</button>
      ))}
    </div>
  );

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <strong>Systems Status</strong>
      {row('Live', live)}
      {row('Partial / Manual', partial)}
      {row('Legacy (v1, not wrapped)', legacy)}
      {row('Seed required', seed)}
      <div className="meta warn" style={{ marginTop: 8, borderTop: '1px solid var(--border)', paddingTop: 8 }}>
        Detected v1 legacy workers (running outside Nexus OS v2 control): {V1_FLEET.length}.
        {failing.length > 0 && <> Failing: {failing.map((w) => `${w.name} (${w.note ?? 'failing'})`).join('; ')}.</>}
      </div>
      <div className="meta bad" style={{ marginTop: 6 }}>
        Action-capable v1 (never expose raw control in UI): {unsafe.map((w) => w.name).join(', ')}.
      </div>
      <div className="meta muted" style={{ marginTop: 6 }}>
        Buttons open the related tab only. No publish/send/trade/deploy; v1 workers are observed, not controlled.
      </div>
    </div>
  );
}
