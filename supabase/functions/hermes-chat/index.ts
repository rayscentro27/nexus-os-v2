// Supabase Edge Function — Hermes chat (SERVER-SIDE ONLY; holds provider keys).
//
// Provider is selected by env (NOT hardcoded): HERMES_CHAT_PROVIDER = openrouter | gemini | ollama.
// The key for the chosen provider (OPENROUTER_API_KEY / GEMINI_API_KEY / OLLAMA_URL) lives in
// Supabase function secrets — never in the browser. If the provider/key is missing, returns
// { configured: false } and the UI says "Hermes chat provider is not configured yet." We never
// fake current facts. Private data is refused by the firewall before any external call.
//
// Prompt layout (ordered for prompt caching):
//   1. system: STABLE_CONTEXT_BLOCK  — byte-stable identity/Nexus/GoClear context (cached prefix)
//   2. system: dynamic safe context  — small, per-request, from the admin frontend (not cached)
//   3. user:   Ray's current message
// Only PUBLIC / internal_summary data ever reaches the provider; the firewall scans the message
// (refuse) and every dynamic-context field (dropped if it trips the gate) before any external call.
//
// NOTE: deploy only when keys are configured.

import { isSensitive, json, cors } from '../_shared/firewall.ts';

// Stable, cached identity + business context. Keep this byte-stable to maximize prompt-cache hits;
// bump HERMES_CONTEXT_VERSION to intentionally bust the cache after edits. Contains only
// internal_summary-level business context — never secrets or customer data.
const STABLE_CONTEXT_BLOCK = `[HERMES — STABLE CONTEXT]

IDENTITY
You are Hermes, Ray's private conversational advisor and report interpreter for Nexus OS.
You are direct, concise, practical, and honest — no filler, no hype. If you are unsure of a
current fact, say so; never fabricate.

WHO RAY IS
Ray (goclearonline@gmail.com) is the founder/operator. He values blunt recommendations with
trade-offs and the fastest SAFE next step, tight scope, no guarantees he cannot back, and clean
safety/repo discipline over speed.

WHAT NEXUS OS IS
Nexus OS is Ray's Supabase-first operating system: an event ledger (source of truth), a bounded
job runner, approvals, and an admin dashboard. It coordinates content, monetization research,
report review, and approval-gated actions. Nothing publishes, sends, trades, or deploys without
Ray's explicit approval.

GOCLEAR / APEX
GoClear (GoClearOnline) is Ray's main operating brand for his credit and funding readiness
direction. "Clear Credentials" is only the existing Facebook/social brand and is referenced just
when a workflow involves that page/account — it is not the main product name. Apex is the
funding/readiness side of the same GoClear money path; GoClear/Apex is Ray's credit and funding
readiness direction (not a separate legal entity, ownership structure, or product line).

FIRST MONEY PATH
The first money path is a $97 credit/funding readiness review. Understand it as: intake →
readiness review → safe report → follow-up recommendation → a possible task request (landing
page, outreach, or client workflow).

COMPLIANCE (hard)
Never promise or imply guaranteed funding, guaranteed approval, guaranteed credit repair,
guaranteed score increase, guaranteed deletion, or guaranteed financing outcomes. Use readiness,
education, preparation, and next-step language only.

YOUR ROLE
Advise on business and strategy, interpret safe Nexus reports in plain English, ask smart
follow-up questions, and recommend actions. You propose APPROVAL-GATED task requests but never
execute them. You do not publish, send, trade, deploy, or reset passwords directly. Private and
internal workers handle sensitive or executing tasks and return REDACTED status only.

DATA FIREWALL (hard)
You may use only PUBLIC and internal_summary data. You must NEVER receive or repeat SSNs, full
credit reports, bank or tax documents, passwords, reset tokens, service-role keys, secrets, or
raw customer files (customer_private, credit_sensitive, funding_sensitive, auth_sensitive,
secrets, or raw trading_sensitive). If asked to view sensitive data, refuse and offer to create
a private-worker task request if Ray approves. Never send private data to public search or
external models.

TASK REQUESTS
Create a structured task request only after Ray clearly approves — never auto-create one from
normal conversation. Each request is labeled by sensitivity and assigned to a worker; privileged
tasks go to private/internal (non-internet) workers with status-only visibility to you.

REPORT READER
Explain only safe summaries (system health, ledger event titles, counts). Translate them into
plain business meaning plus a recommended next step. Never echo private numbers to any external
source.

TONE
Confident, concise, advisory. Lead with the recommendation, then the why, then the next safe step.`;

const CONTEXT_VERSION = Deno.env.get('HERMES_CONTEXT_VERSION') ?? 'v1';
const stableSystem = () => `${STABLE_CONTEXT_BLOCK}\n[context_version: ${CONTEXT_VERSION}]`;

// Server-side firewall scan. Uses the shared gate plus a belt-and-suspenders plural-SSN pattern
// (the shared \bssn\b does not match "SSNs"). Never weakens an existing rule — only adds coverage.
const PLURAL_SSN = /\bssns\b/i;
const blocked = (text: string): boolean => isSensitive(text) || PLURAL_SSN.test(text || '');

const MAX_CONTEXT_FIELD = 600;   // cap each dynamic field
const MAX_CONTEXT_TOTAL = 2000;  // cap the whole dynamic block

// Build the small dynamic context block from safe frontend-supplied fields. Any field that trips
// the firewall is dropped (never sent to the model). Returns '' when there's nothing safe to add.
function buildDynamicContext(mode: string, ctx: Record<string, unknown> | undefined): string {
  const lines: string[] = [`[CURRENT CONTEXT — not cached]`, `Mode: ${String(mode).slice(0, 40)}`];
  const add = (label: string, val: unknown) => {
    const s = (val == null ? '' : String(val)).trim();
    if (!s || blocked(s)) return;                 // empty or sensitive → skip
    lines.push(`${label}: ${s.slice(0, MAX_CONTEXT_FIELD)}`);
  };
  if (ctx) {
    add('Pending action awaiting approval', ctx.pending);
    add('Safe Nexus snapshot', ctx.facts);
    add('Latest safe report (internal_summary)', ctx.report);
    add('Latest task status (redacted)', ctx.taskStatus);
  }
  if (lines.length <= 2) return '';               // only the header/mode → nothing useful
  return lines.join('\n').slice(0, MAX_CONTEXT_TOTAL);
}

interface ChatMessage { role: 'system' | 'user'; content: string; }

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors() });

  const body = await req.json().catch(() => ({}));
  const message: string = body?.message ?? '';
  const mode: string = body?.mode ?? 'conversation';
  const context: Record<string, unknown> | undefined = body?.context;

  // Firewall: the user message is refused outright if it references private data.
  if (blocked(String(message)))
    return json({ configured: true, reply: "I won't process private data through an external model." });

  const dynamic = buildDynamicContext(mode, context);

  // Ordered for prompt caching: stable cached block, then small dynamic block, then user message.
  const messages: ChatMessage[] = [{ role: 'system', content: stableSystem() }];
  if (dynamic) messages.push({ role: 'system', content: dynamic });
  messages.push({ role: 'user', content: message });

  // Gemini takes a single text blob; flatten the same ordered content.
  const flat = messages.map((m) => (m.role === 'user' ? `Ray: ${m.content}` : m.content)).join('\n\n');

  const provider = (Deno.env.get('HERMES_CHAT_PROVIDER') ?? 'none').toLowerCase();
  const model = Deno.env.get('HERMES_CHAT_MODEL');

  try {
    if (provider === 'openrouter') {
      const key = Deno.env.get('OPENROUTER_API_KEY');
      if (!key) return json({ configured: false });
      // Primary model first, then optional fallback. A non-2xx, a provider error in the body, or
      // an empty reply each count as a miss → try the next model. Provider error details are never
      // returned to the client. The message + context were firewall-checked above.
      const models = [model ?? 'openai/gpt-4o-mini', Deno.env.get('HERMES_CHAT_FALLBACK_MODEL')]
        .filter((m): m is string => Boolean(m && m.trim()));
      for (const m of models) {
        try {
          const r = await fetch('https://openrouter.ai/api/v1/chat/completions', {
            method: 'POST',
            headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
            body: JSON.stringify({ model: m, messages }),
          });
          if (!r.ok) continue;
          const d = await r.json();
          if (d?.error) continue;
          const reply = d?.choices?.[0]?.message?.content;
          if (reply && String(reply).trim())
            return json({ configured: true, reply: String(reply), model: m });
        } catch {
          continue;
        }
      }
      return json({ configured: true, reply: "I'm configured, but the chat model is unavailable right now. Please try again shortly." });
    }

    if (provider === 'gemini') {
      const key = Deno.env.get('GEMINI_API_KEY');
      if (!key) return json({ configured: false });
      const m = model ?? 'gemini-1.5-flash';
      const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${key}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: flat }] }] }),
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
        body: JSON.stringify({ model: model ?? 'llama3.1', stream: false, messages }),
      });
      const d = await r.json();
      return json({ configured: true, reply: d?.message?.content ?? '' });
    }

    return json({ configured: false });
  } catch (e) {
    return json({ configured: false, error: String(e) });
  }
});
