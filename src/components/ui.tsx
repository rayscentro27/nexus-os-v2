import React from 'react';

export function Pill({ status, label }: { status: string; label?: string }) {
  const cls = (status || 'unknown').toLowerCase().replace(/[^a-z_]/g, '_');
  return <span className={`pill ${cls}`}>{label ?? status}</span>;
}

export function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function SetupState({ what }: { what: string }) {
  return (
    <div className="setup">
      <h3>Supabase not configured</h3>
      <p className="muted">
        {what} will appear here once the ledger is connected. Set{' '}
        <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_ANON_KEY</code> in <code>.env</code>,
        apply <code>supabase/migrations/0001_nexus_os_v2_core.sql</code>, then reload.
      </p>
      <p className="muted">No fake data is shown — Supabase is the single source of truth.</p>
    </div>
  );
}

export function Empty({ what }: { what: string }) {
  return <div className="empty">No {what} yet.</div>;
}

export function timeAgo(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
