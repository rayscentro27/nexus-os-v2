import React from 'react';

/**
 * SourceBanner — shows live/static/mismatch status for any section.
 * Renders a clear truth label so static data never looks live.
 */
export default function SourceBanner({ sourceType, liveData, rowCount, staticCount, mismatch, limitations, tableNamesUsed, error }) {
  const color = sourceType === 'live_supabase' ? '#22c55e' : sourceType === 'static_fallback' ? '#f59e0b' : '#ef4444';
  const icon = sourceType === 'live_supabase' ? '\u{1F534}' : sourceType === 'static_fallback' ? '\u26A0\uFE0F' : '\u{1F534}';
  const label = sourceType === 'live_supabase' ? 'Live Supabase'
    : sourceType === 'static_fallback' ? 'Static Snapshot'
    : sourceType === 'report_snapshot' ? 'Report Snapshot'
    : sourceType === 'localStorage_only' ? 'Local Receipt Only'
    : 'Unavailable';

  const countText = liveData
    ? `${rowCount} live rows`
    : staticCount > 0
      ? `${staticCount} static items${rowCount > 0 ? `, Supabase has ${rowCount} rows` : ', Supabase has 0 rows'}`
      : 'No data';

  return (
    <div className="nxos-source-banner" style={{
      padding: '6px 12px', borderRadius: 6, fontSize: '0.82em',
      background: color + '18', border: `1px solid ${color}44`,
      marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
    }}>
      <span style={{ fontWeight: 600, color }}>{icon} {label}</span>
      <span style={{ color: '#666' }}>{countText}</span>
      {tableNamesUsed && tableNamesUsed.length > 0 && (
        <span style={{ color: '#888' }}>· Table: {tableNamesUsed.join(', ')}</span>
      )}
      {error && <span style={{ color: '#c00' }}>· Error: {String(error).slice(0, 60)}</span>}
      {mismatch && (
        <div style={{ width: '100%', marginTop: 4, padding: '4px 8px', background: '#fff3cd', borderRadius: 4, color: '#856404' }}>
          {mismatch}
        </div>
      )}
    </div>
  );
}
