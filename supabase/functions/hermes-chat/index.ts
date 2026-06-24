// Supabase Edge Function — Hermes chat (SERVER-SIDE ONLY; holds provider keys).
//
// Provider is selected by env (NOT hardcoded): HERMES_CHAT_PROVIDER = openrouter | gemini | ollama.
// The key for the chosen provider (OPENROUTER_API_KEY / GEMINI_API_KEY / OLLAMA_URL) lives in
// Supabase function secrets — never in the browser. If the provider/key is missing, returns
// { configured: false } and the UI says "Hermes chat provider is not configured yet." We never
// fake current facts. Private data is refused by the firewall before any external call.
//
// NOTE: this function is not deployed by default; deploy it only when keys are configured.

import { isSensitive, json, cors } from '../_shared/firewall.ts';

const SYSTEM = (mode: string) =>
  `You are Hermes, Ray's private conversational advisor for the Nexus OS. Current mode: ${mode}. ` +
  `Be direct, concise, and practical. You never see or request SSNs, full credit reports, ` +
  `bank/tax documents, passwords, reset tokens, or secrets. You do not publish, send, trade, or ` +
  `deploy directly — you advise and propose approval-gated task requests. If you are unsure of a ` +
  `current fact, say so rather than guessing.`;

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors() });

  const { message = '', mode = 'conversation' } = await req.json().catch(() => ({}));
  if (isSensitive(String(message)))
    return json({ configured: true, reply: "I won't process private data through an external model." });

  const provider = (Deno.env.get('HERMES_CHAT_PROVIDER') ?? 'none').toLowerCase();
  const model = Deno.env.get('HERMES_CHAT_MODEL');

  try {
    if (provider === 'openrouter') {
      const key = Deno.env.get('OPENROUTER_API_KEY');
      if (!key) return json({ configured: false });
      const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
        body: JSON.stringify({
          model: model ?? 'openai/gpt-4o-mini',
          messages: [{ role: 'system', content: SYSTEM(mode) }, { role: 'user', content: message }],
        }),
      });
      const d = await r.json();
      return json({ configured: true, reply: d?.choices?.[0]?.message?.content ?? '' });
    }

    if (provider === 'gemini') {
      const key = Deno.env.get('GEMINI_API_KEY');
      if (!key) return json({ configured: false });
      const m = model ?? 'gemini-1.5-flash';
      const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${key}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: `${SYSTEM(mode)}\n\nRay: ${message}` }] }] }),
      });
      const d = await r.json();
      return json({ configured: true, reply: d?.candidates?.[0]?.content?.parts?.[0]?.text ?? '' });
    }

    if (provider === 'ollama') {
      const base = Deno.env.get('OLLAMA_URL');
      if (!base) return json({ configured: false });
      const r = await fetch(`${base.replace(/\/$/, '')}/api/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          model: model ?? 'llama3.1',
          stream: false,
          messages: [{ role: 'system', content: SYSTEM(mode) }, { role: 'user', content: message }],
        }),
      });
      const d = await r.json();
      return json({ configured: true, reply: d?.message?.content ?? '' });
    }

    return json({ configured: false });
  } catch (e) {
    return json({ configured: false, error: String(e) });
  }
});
