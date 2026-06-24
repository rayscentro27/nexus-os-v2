// Server-side firewall (defense-in-depth). Rejects any payload that references private data
// before it can reach a public model or public search. The browser already filters; this is the
// second wall. Runs in Deno (Supabase Edge Functions).

const SENSITIVE: RegExp[] = [
  /\bssn\b|social security/i,
  /credit report|full credit file|fico (file|report)/i,
  /bank statement|account number|routing number|bank balance/i,
  /tax (return|transcript)|w-?2\b|1099\b/i,
  /funding document|loan documents/i,
  /\bpassword\b|reset token|\botp\b|one[- ]time (code|password)/i,
  /service[- ]?role|service_role|secret key|api[_ ]?key|private key|access token|bearer token/i,
  /open positions|brokerage balance/i,
];

export function isSensitive(text: string): boolean {
  return SENSITIVE.some((re) => re.test(text || ''));
}

export function cors(): Record<string, string> {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Content-Type': 'application/json',
  };
}

export function json(o: unknown): Response {
  return new Response(JSON.stringify(o), { headers: cors() });
}
