import React, { useMemo } from 'react';
import { getAllSectionStatuses, getSectionSummary, getResearchEngineStatus } from '../lib/nexusSectionStatusRegistry';
import NexusSectionStatusCard from './NexusSectionStatusCard';

/**
 * NexusActivationStatus — full dashboard showing activation proof for all sections.
 *
 * Header: summary counts (live/static/blocked/unknown)
 * Body: grid of status cards
 * Research Engine: special detailed card with YouTube proof
 */
export default function NexusActivationStatus({ onNavigate }) {
  const sections = useMemo(() => getAllSectionStatuses(), []);
  const summary = useMemo(() => getSectionSummary(), []);
  const researchStatus = useMemo(() => getResearchEngineStatus(), []);

  const liveSections = sections.filter((s) => s.status === 'live');
  const staticSections = sections.filter((s) => s.status === 'static');
  const otherSections = sections.filter((s) => s.status !== 'live' && s.status !== 'static');

  return (
    <div className="nxos-activation-status">
      <section className="nxos-callout" style={{ marginBottom: 16 }}>
        <h2>Nexus Activation Status</h2>
        <p style={{ color: '#555', margin: '4px 0 8px' }}>
          Visual proof of which sections are live, static, or blocked. All data from the section status registry — no model calls needed.
        </p>
        <div className="nxos-metric-grid" style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <MetricBadge label="Live" value={summary.live} total={summary.total} color="#22c55e" />
          <MetricBadge label="Static" value={summary.static} total={summary.total} color="#f59e0b" />
          <MetricBadge label="Mismatch" value={summary.mismatch} total={summary.total} color="#ef4444" />
          <MetricBadge label="Blocked" value={summary.blocked} total={summary.total} color="#ef4444" />
          <MetricBadge label="Unknown" value={summary.unknown} total={summary.total} color="#9ca3af" />
        </div>
      </section>

      {/* Research Engine — detailed card */}
      <section style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 8 }}>Research Engine — Detailed Status</h3>
        <div style={{
          padding: '12px 16px', borderRadius: 8,
          background: '#22c55e18', border: '1px solid #22c55e44',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <strong style={{ color: '#16a34a' }}>✅ Research Engine</strong>
            <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: '0.78em', background: '#22c55e18', border: '1px solid #22c55e44', color: '#16a34a', fontWeight: 600 }}>LIVE</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '0.85em', color: '#444' }}>
            <div>Live research_sources count: <strong>{researchStatus.rowCount}</strong></div>
            <div>YouTube research proof: <strong style={{ color: '#d97706' }}>{researchStatus.youtubeProofStatus}</strong></div>
            <div>Scheduler installed: <strong>{researchStatus.schedulerInstalled ? 'yes' : 'no'}</strong></div>
            <div>Scheduler running: <strong style={{ color: researchStatus.schedulerRunning ? '#16a34a' : '#d97706' }}>{researchStatus.schedulerRunning ? 'yes' : 'not confirmed'}</strong></div>
            <div>Supabase write proof: <strong>{researchStatus.supabaseWriteProof ? 'yes' : 'no'}</strong></div>
            <div>Last report: <strong>{researchStatus.lastReportTimestamp || 'unknown'}</strong></div>
            <div>Watched channels: <strong>{researchStatus.watchedChannels}</strong></div>
            <div>Verified: <strong>{researchStatus.verifiedAt?.split('T')[0] || 'never'}</strong></div>
          </div>
          {researchStatus.blockers.length > 0 && (
            <div style={{ marginTop: 8, padding: '4px 8px', background: '#fef2f2', borderRadius: 4, fontSize: '0.82em', color: '#991b1b' }}>
              <strong>Blockers:</strong> {researchStatus.blockers.join('; ')}
            </div>
          )}
          <div style={{ marginTop: 4, fontSize: '0.82em', color: '#555' }}>
            <strong>Next:</strong> {researchStatus.nextAction}
          </div>
        </div>
      </section>

      {/* Live sections */}
      {liveSections.length > 0 && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 8 }}>Live Sections ({liveSections.length})</h3>
          {liveSections.filter(s => s.id !== 'research_engine').map((s) => (
            <NexusSectionStatusCard key={s.id} section={s} onNavigate={onNavigate} />
          ))}
        </section>
      )}

      {/* Static sections */}
      {staticSections.length > 0 && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 8 }}>Static Sections ({staticSections.length})</h3>
          {staticSections.map((s) => (
            <NexusSectionStatusCard key={s.id} section={s} onNavigate={onNavigate} />
          ))}
        </section>
      )}

      {/* Other sections */}
      {otherSections.length > 0 && (
        <section style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 8 }}>Other Sections ({otherSections.length})</h3>
          {otherSections.map((s) => (
            <NexusSectionStatusCard key={s.id} section={s} onNavigate={onNavigate} />
          ))}
        </section>
      )}

      <section className="nxos-table-card" style={{ marginTop: 16 }}>
        <h2>How to read this</h2>
        <div className="nxos-table-row"><strong>✅ Live</strong><span>Data loaded from Supabase in real time</span></div>
        <div className="nxos-table-row"><strong>⚠️ Static</strong><span>Local static data only — not connected to Supabase</span></div>
        <div className="nxos-table-row"><strong>🚫 Blocked</strong><span>Section exists but has blockers preventing full operation</span></div>
        <div className="nxos-table-row"><strong>❓ Unknown</strong><span>Proof level not determined</span></div>
        <div className="nxos-table-row"><strong>Proof verified</strong><span>Section status confirmed by live data load or process evidence</span></div>
        <div className="nxos-table-row"><strong>Not proven</strong><span>Section exists but no live proof — do not claim it is running</span></div>
      </section>
    </div>
  );
}

function MetricBadge({ label, value, total, color }) {
  return (
    <div style={{
      padding: '8px 16px', borderRadius: 8, minWidth: 100, textAlign: 'center',
      background: color + '18', border: `1px solid ${color}44`,
    }}>
      <div style={{ fontSize: '1.5em', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '0.82em', color: '#666' }}>{label}</div>
      <div style={{ fontSize: '0.72em', color: '#999' }}>of {total}</div>
    </div>
  );
}
