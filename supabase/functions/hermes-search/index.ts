// Supabase Edge Function — Hermes public search (SERVER-SIDE ONLY; holds search keys).
//
// Provider selected by env (NOT hardcoded): HERMES_SEARCH_PROVIDER = brave | tavily | serpapi.
// The key lives in Supabase function secrets — never in the browser. PUBLIC questions only; the
// firewall refuses anything that references private data. If unconfigured, returns
// { configured: false } and the UI says "Public search is not configured yet…". Never fakes facts.
//
// NOTE: this function is not deployed by default; deploy it only when keys are configured.

import { isSensitive, json, cors } from '../_shared/firewall.ts';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors() });

  const { query = '' } = await req.json().catch(() => ({}));
  if (isSensitive(String(query)))
    return json({ configured: true, summary: "That looks like private data — refusing to search public sources." });

  const provider = (Deno.env.get('HERMES_SEARCH_PROVIDER') ?? 'none').toLowerCase();

  try {
    if (provider === 'brave') {
      const key = Deno.env.get('BRAVE_SEARCH_API_KEY');
      if (!key) return json({ configured: false });
      const r = await fetch(`https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}`, {
        headers: { 'X-Subscription-Token': key, accept: 'application/json' },
      });
      const d = await r.json();
      const items = (d?.web?.results ?? []).slice(0, 5).map((x: any) => `• ${x.title} — ${x.url}`);
      return json({ configured: true, summary: items.join('\n') || 'No public results found.' });
    }

    if (provider === 'tavily') {
      const key = Deno.env.get('TAVILY_API_KEY');
      if (!key) return json({ configured: false });
      const r = await fetch('https://api.tavily.com/search', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ api_key: key, query, max_results: 5, include_answer: true }),
      });
      const d = await r.json();
      const items = (d?.results ?? []).map((x: any) => `• ${x.title} — ${x.url}`);
      return json({ configured: true, summary: `${d?.answer ? d.answer + '\n' : ''}${items.join('\n')}`.trim() || 'No public results found.' });
    }

    if (provider === 'serpapi') {
      const key = Deno.env.get('SERPAPI_KEY');
      if (!key) return json({ configured: false });
      const r = await fetch(`https://serpapi.com/search.json?q=${encodeURIComponent(query)}&api_key=${key}`);
      const d = await r.json();
      const items = (d?.organic_results ?? []).slice(0, 5).map((x: any) => `• ${x.title} — ${x.link}`);
      return json({ configured: true, summary: items.join('\n') || 'No public results found.' });
    }

    return json({ configured: false });
  } catch (e) {
    return json({ configured: false, error: String(e) });
  }
});
