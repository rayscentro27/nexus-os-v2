import { isSupabaseConfigured, supabase } from '../lib/supabaseClient';

export type Row = Record<string, any>;
export type ConnectionStatus =
  | 'missing_env'
  | 'no_authenticated_session'
  | 'not_admin'
  | 'rls_denied_no_access'
  | 'query_error'
  | 'no_records'
  | 'connected_with_records';

export interface TableQueryDiagnostic {
  table: string;
  filter: string;
  supabaseConfigured: boolean;
  authSessionPresent: boolean;
  userEmail: string | null;
  userIdPrefix: string | null;
  status: ConnectionStatus;
  resultCount: number;
  errorCategory: ConnectionStatus | null;
  errorMessage: string | null;
}

export interface TableQueryResult<T extends Row = Row> extends TableQueryDiagnostic {
  data: T[];
}

export interface AdminDiagnostic {
  found: boolean | null;
  active: boolean | null;
  role: string | null;
  status: 'found' | 'not_found' | 'unknown' | 'no_session' | 'missing_env' | 'query_error' | 'rls_denied_no_access';
  errorMessage: string | null;
}

function safeErrorMessage(error: unknown): string | null {
  if (!error || typeof error !== 'object') return null;
  const message = 'message' in error ? String((error as { message?: unknown }).message ?? '') : '';
  if (!message) return null;
  return message.replace(/Bearer\s+[A-Za-z0-9._-]+/g, 'Bearer [redacted]').slice(0, 180);
}

function categorizeError(error: unknown): ConnectionStatus {
  const raw = `${safeErrorMessage(error) ?? ''} ${'code' in (error as any || {}) ? (error as any).code : ''}`.toLowerCase();
  if (raw.includes('permission denied') || raw.includes('row-level') || raw.includes('rls') || raw.includes('42501')) {
    return 'rls_denied_no_access';
  }
  if (raw.includes('jwt') || raw.includes('auth') || raw.includes('not authenticated')) return 'no_authenticated_session';
  return 'query_error';
}

function filterLabel(opts: { limit?: number; order?: string; ascending?: boolean; eq?: [string, string] } = {}): string {
  const parts = [`limit=${opts.limit ?? 50}`, `order=${opts.order ?? 'created_at'}.${opts.ascending ? 'asc' : 'desc'}`];
  if (opts.eq) parts.push(`${opts.eq[0]}=eq.${opts.eq[1]}`);
  return parts.join(' ');
}

function emptyResult<T extends Row>(
  table: string,
  opts: { limit?: number; order?: string; ascending?: boolean; eq?: [string, string] },
  status: ConnectionStatus,
  extras: Partial<TableQueryDiagnostic> = {},
): TableQueryResult<T> {
  return {
    table,
    filter: filterLabel(opts),
    supabaseConfigured: isSupabaseConfigured,
    authSessionPresent: false,
    userEmail: null,
    userIdPrefix: null,
    status,
    resultCount: 0,
    errorCategory: status === 'no_records' || status === 'connected_with_records' ? null : status,
    errorMessage: null,
    ...extras,
    data: [],
  };
}

export async function listTableDetailed<T extends Row = Row>(
  table: string,
  opts: { limit?: number; order?: string; ascending?: boolean; eq?: [string, string] } = {},
): Promise<TableQueryResult<T>> {
  if (!supabase || !isSupabaseConfigured) return emptyResult<T>(table, opts, 'missing_env');

  const sessionRes = await supabase.auth.getSession();
  const session = sessionRes.data.session;
  const base = {
    authSessionPresent: Boolean(session),
    userEmail: session?.user.email ?? null,
    userIdPrefix: session?.user.id ? session.user.id.slice(0, 8) : null,
  };
  if (!session) return emptyResult<T>(table, opts, 'no_authenticated_session', base);

  let q = supabase.from(table).select('*').limit(opts.limit ?? 50);
  q = q.order(opts.order ?? 'created_at', { ascending: opts.ascending ?? false });
  if (opts.eq) q = q.eq(opts.eq[0], opts.eq[1]);
  const { data, error } = await q;
  if (error) {
    const category = categorizeError(error);
    return emptyResult<T>(table, opts, category, {
      ...base,
      errorCategory: category,
      errorMessage: safeErrorMessage(error),
    });
  }

  const rows = (data ?? []) as T[];
  return {
    table,
    filter: filterLabel(opts),
    supabaseConfigured: true,
    ...base,
    status: rows.length > 0 ? 'connected_with_records' : 'no_records',
    resultCount: rows.length,
    errorCategory: null,
    errorMessage: null,
    data: rows,
  };
}

export async function getAdminDiagnostic(): Promise<AdminDiagnostic> {
  if (!supabase || !isSupabaseConfigured) return { found: null, active: null, role: null, status: 'missing_env', errorMessage: null };
  const { data: sessionData } = await supabase.auth.getSession();
  const userId = sessionData.session?.user.id;
  if (!userId) return { found: null, active: null, role: null, status: 'no_session', errorMessage: null };

  const { data, error } = await supabase
    .from('admin_users')
    .select('id,email,active,role')
    .eq('id', userId)
    .maybeSingle();
  if (error) {
    const category = categorizeError(error);
    return { found: null, active: null, role: null, status: category === 'rls_denied_no_access' ? 'rls_denied_no_access' : 'query_error', errorMessage: safeErrorMessage(error) };
  }
  if (!data) return { found: false, active: null, role: null, status: 'not_found', errorMessage: null };
  return { found: true, active: Boolean(data.active), role: data.role ?? null, status: 'found', errorMessage: null };
}

/** Generic read for any table the admin can SELECT. Empty array when unconfigured/blocked. */
export async function listTable(
  table: string,
  opts: { limit?: number; order?: string; ascending?: boolean; eq?: [string, string] } = {},
): Promise<Row[]> {
  const result = await listTableDetailed(table, opts);
  if (result.errorMessage) console.warn(`[db] ${table}:`, result.errorMessage);
  return result.data;
}

export async function countRows(table: string): Promise<number> {
  if (!supabase) return 0;
  const { count, error } = await supabase.from(table).select('*', { count: 'exact', head: true });
  if (error) return 0;
  return count ?? 0;
}
