// Small shared pieces for live Nexus state, built only from the approved design's existing
// tokens (white rounded-2xl cards, slate text, TruthBadge). No new visual language.
import React from 'react';
import { useNexus } from '../../context/NexusContext';
import { TruthBadge } from '../common/TruthBadge';

export const fmt = (v: unknown, fallback = 'UNKNOWN') =>
  v === null || v === undefined || v === '' ? fallback : typeof v === 'number' ? v.toLocaleString() : String(v);

export const when = (iso?: string | null) => {
  if (!iso) return 'UNKNOWN';
  const t = Date.parse(iso);
  return Number.isNaN(t) ? iso : new Date(t).toLocaleString();
};

export const Card: React.FC<{ title?: string; right?: React.ReactNode; children: React.ReactNode; className?: string }> = ({ title, right, children, className = '' }) => (
  <div className={`bg-white rounded-2xl border border-slate-200/90 p-4 ${className}`}>
    {(title || right) && (
      <div className="flex items-center justify-between gap-2 mb-3">
        {title && <h3 className="text-sm font-semibold text-slate-900">{title}</h3>}
        {right}
      </div>
    )}
    {children}
  </div>
);

export const Field: React.FC<{ label: string; value: unknown; truth?: string; fallback?: string }> = ({ label, value, truth, fallback }) => (
  <div className="flex items-center justify-between gap-3 py-1.5 border-b border-slate-100 last:border-0">
    <span className="text-xs text-slate-500">{label}</span>
    <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-800 text-right">
      {fmt(value, fallback ?? (truth === 'NOT_CONNECTED' ? 'NOT CONNECTED' : 'UNKNOWN'))}
      {truth && <TruthBadge truth={truth} size="xs" />}
    </span>
  </div>
);

/** Live provenance line shown under page headers. */
export const LiveProvenance: React.FC<{ source: string }> = ({ source }) => {
  const { liveStatus, liveGeneratedAt, liveFreshness } = useNexus();
  const truth = liveStatus !== 'ready' ? 'NOT_CONNECTED' : liveFreshness === 'LIVE' ? 'VERIFIED' : 'UNKNOWN';
  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
      <TruthBadge truth={truth} size="xs" label={liveStatus !== 'ready' ? (liveStatus === 'forbidden' ? 'ADMIN ROLE REQUIRED' : 'NOT CONNECTED') : liveFreshness === 'STALE' ? 'STALE' : 'LIVE'} />
      <span>Source: {source}</span>
      <span>· Updated {when(liveGeneratedAt)}</span>
    </div>
  );
};

/** Notice placed above approved-design sections whose data has no live Nexus source yet. */
export const PrototypeNotice: React.FC<{ area: string }> = ({ area }) => (
  <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 flex items-center gap-2">
    <TruthBadge truth="DEMO" size="xs" />
    <span>{area}: sections below this line are the approved design's reference layout. No live Nexus source is connected for them yet — values are not operational facts.</span>
  </div>
);
