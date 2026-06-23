import { useEffect, useState, type ReactNode } from 'react';

export function Pill({ status, label }: { status?: string | boolean | null; label?: string }) {
  const s = typeof status === 'boolean' ? (status ? 'enabled' : 'registered') : (status || 'unknown');
  const cls = String(s).toLowerCase().replace(/[^a-z_]/g, '_');
  return <span className={`pill ${cls}`}>{label ?? String(s).replaceAll('_', ' ')}</span>;
}

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return <div className="card"><h3>{title}</h3>{children}</div>;
}

export function Stat({ title, value, sub }: { title: string; value: ReactNode; sub?: string }) {
  return <div className="card"><h3>{title}</h3><div className="big">{value}</div>{sub && <div className="meta muted" style={{ marginTop: 4 }}>{sub}</div>}</div>;
}

export function Empty({ what }: { what: string }) {
  return <div className="empty">No {what} yet. Actions and jobs will populate this from the ledger.</div>;
}

export function SectionTitle({ children, count }: { children: ReactNode; count?: number }) {
  return <div className="section-title">{children}{count != null && <span className="count">· {count}</span>}</div>;
}

export function timeAgo(iso?: string): string {
  if (!iso) return '';
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/** Tiny async-data hook (re-runs when `dep` changes). */
export function useData<T>(fn: () => Promise<T>, fallback: T, dep: unknown = 0): { data: T; reload: () => void } {
  const [data, setData] = useState<T>(fallback);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    fn().then((r) => { if (alive) setData(r); }).catch(() => {});
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, dep]);
  return { data, reload: () => setTick((t) => t + 1) };
}
