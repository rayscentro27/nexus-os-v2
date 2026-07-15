import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { execSync } from 'node:child_process';

const git = (command: string, fallback: string) => { try { return execSync(command, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim() || fallback; } catch { return fallback; } };
const buildMetadata = {
  VITE_BUILD_COMMIT: process.env.VITE_BUILD_COMMIT || process.env.COMMIT_REF || git('git rev-parse --short HEAD', 'unversioned'),
  VITE_BUILD_BRANCH: process.env.VITE_BUILD_BRANCH || process.env.BRANCH || git('git branch --show-current', 'unknown'),
  VITE_BUILD_TIMESTAMP: process.env.VITE_BUILD_TIMESTAMP || new Date().toISOString(),
};

function nexusLocalBridges() {
  return {
    name: 'nexus-local-static-and-alpha-bridge',
    configureServer(server: any) {
      server.middlewares.use(async (req: any, res: any, next: any) => {
        const path = String(req.url || '').split('?')[0];

        if (path === '/got-funding' || path === '/got-funding/') {
          try {
            res.statusCode = 200;
            res.setHeader('Content-Type', 'text/html; charset=utf-8');
            res.end(await readFile(resolve(process.cwd(), 'public/got-funding/index.html')));
          } catch {
            next();
          }
          return;
        }

        if (path !== '/api/alpha/status' && path !== '/api/alpha/chat' && path !== '/api/alpha/search' && path !== '/api/alpha/url-review') return next();
        res.setHeader('Content-Type', 'application/json');

        if (path === '/api/alpha/search') {
          let raw = '';
          for await (const chunk of req) raw += chunk;
          let body: any = {};
          try { body = JSON.parse(raw); } catch {}

          const query = String(body.query || '').trim().slice(0, 500);
          if (!query) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'query_required', status: 'failed', provider: 'none', results: [] }));
            return;
          }

          const base = process.env.ALPHA_SEARXNG_URL;
          if (!base) {
            res.statusCode = 503;
            res.end(JSON.stringify({ error: 'search_connector_missing', status: 'connector_missing', provider: 'none', results: [] }));
            return;
          }

          try {
            const reply = await fetch(`${base.replace(/\/$/, '')}/search?q=${encodeURIComponent(query)}&format=json`, {
              signal: AbortSignal.timeout(5000),
              headers: { accept: 'application/json' },
            });
            const data: any = await reply.json();
            const results = (data.results || []).slice(0, 5).map((item: any) => {
              let domain = '';
              try { domain = new URL(item.url).hostname; } catch {}
              return {
                title: String(item.title || 'Untitled').slice(0, 160),
                url: String(item.url || ''),
                domain,
                snippet: String(item.content || '').slice(0, 500),
                provider: 'searxng',
                timestamp: new Date().toISOString(),
              };
            });
            res.statusCode = reply.ok ? 200 : 502;
            res.end(JSON.stringify({ results, provider: 'searxng', status: reply.ok ? 'searched' : 'failed', count: results.length }));
          } catch {
            res.statusCode = 502;
            res.end(JSON.stringify({ error: 'searxng_unavailable', status: 'failed', provider: 'searxng', results: [] }));
          }
          return;
        }

        if (path === '/api/alpha/url-review') {
          let raw = '';
          for await (const chunk of req) raw += chunk;
          let body: any = {};
          try { body = JSON.parse(raw); } catch {}

          const url = String(body.url || '').trim();
          if (!url || !/^https?:\/\/.+/.test(url)) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'url_required_and_valid', status: 'failed', extractionProvider: 'none' }));
            return;
          }

          const apiKey = process.env.FIRECRAWL_API_KEY;
          if (!apiKey) {
            res.statusCode = 503;
            res.end(JSON.stringify({
              error: 'firecrawl_disabled',
              status: 'disabled',
              extractionProvider: 'firecrawl',
              reason: 'FIRECRAWL_API_KEY not configured on server',
            }));
            return;
          }

          try {
            const firecrawlRes = await fetch('https://api.firecrawl.dev/v1/scrape', {
              method: 'POST',
              headers: { 'content-type': 'application/json', authorization: `Bearer ${apiKey}` },
              body: JSON.stringify({ url, formats: ['markdown'], onlyMainContent: true }),
              signal: AbortSignal.timeout(15000),
            });

            if (!firecrawlRes.ok) {
              res.statusCode = firecrawlRes.status;
              res.end(JSON.stringify({ error: `firecrawl_${firecrawlRes.status}`, status: 'failed', extractionProvider: 'firecrawl' }));
              return;
            }

            const data: any = await firecrawlRes.json();
            const markdown = data.markdown || data.content || '';
            const content = markdown.slice(0, 12000);
            const title = data.title || data.metadata?.title || '';
            let finalUrl = url;
            try { finalUrl = new URL(data.sourceUrl || data.url || url).href; } catch {}
            let domain = '';
            try { domain = new URL(finalUrl).hostname; } catch {}

            res.statusCode = 200;
            res.end(JSON.stringify({
              ok: true,
              title,
              url: finalUrl,
              domain,
              content,
              extractionProvider: 'firecrawl',
              extractionStatus: 'extracted',
              timestamp: new Date().toISOString(),
              noSupabaseUsed: true,
              clientDataUsed: false,
            }));
          } catch (e: any) {
            const reason = e.name === 'AbortError' ? 'timeout' : (e.message || 'unknown');
            res.statusCode = 502;
            res.end(JSON.stringify({ error: `firecrawl_${reason}`, status: 'failed', extractionProvider: 'firecrawl', reason }));
          }
          return;
        }

        const ollamaUrl = process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434';
        let ollama = false;
        let models: string[] = [];
        try {
          const reply = await fetch(`${ollamaUrl}/api/tags`, { signal: AbortSignal.timeout(1500) });
          const data: any = await reply.json();
          ollama = reply.ok;
          models = (data.models || [])
            .filter((x: any) => !x.remote_host)
            .map((x: any) => String(x.name))
            .sort((a: string, b: string) => Number(b.startsWith('gemma3:1b')) - Number(a.startsWith('gemma3:1b')));
        } catch {}

        const status = {
          activeProvider: 'deterministic_local',
          providers: {
            deterministic_local: { available: true, reason: 'Always-available local fallback' },
            ollama_local: { available: ollama, reason: ollama ? 'Local Ollama is reachable' : 'Local Ollama is not reachable', models },
            groq: { available: false, reason: 'Hosted provider requires the deployed Netlify bridge' },
            openrouter: { available: false, reason: 'Hosted provider requires the deployed Netlify bridge' },
          },
          liveWeb: Boolean(process.env.ALPHA_SEARXNG_URL),
          webSearch: {
            available: Boolean(process.env.ALPHA_SEARXNG_URL),
            provider: process.env.ALPHA_SEARXNG_URL ? 'searxng' : 'none',
            reason: process.env.ALPHA_SEARXNG_URL ? 'SearXNG backend configured' : 'No verified backend search connector',
          },
          urlReview: {
            available: Boolean(process.env.FIRECRAWL_API_KEY),
            provider: process.env.FIRECRAWL_API_KEY ? 'firecrawl' : 'none',
            reason: process.env.FIRECRAWL_API_KEY ? 'Firecrawl backend configured' : 'FIRECRAWL_API_KEY not configured on server',
          },
          supabase: false,
          clientData: false,
        };

        if (path === '/api/alpha/status') {
          res.end(JSON.stringify(status));
          return;
        }

        let raw = '';
        for await (const chunk of req) raw += chunk;
        let body: any = {};
        try { body = JSON.parse(raw); } catch {}

        if (body.provider !== 'ollama_local' || !ollama) {
          res.statusCode = 503;
          res.end(JSON.stringify({ error: 'selected_provider_unavailable', status }));
          return;
        }

        const model = String(body.model || models[0] || 'qwen2.5:0.5b');
        const system = 'You are Hermes Alpha, Ray strategy and opportunity partner. Use plain language. Never claim current web facts, use client data, access Supabase, or execute actions. State uncertainty. Never guarantee funding, credit, approvals, or trading results.';

        try {
          const reply = await fetch(`${ollamaUrl}/api/chat`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ model, stream: false, messages: [{ role: 'system', content: system }, { role: 'user', content: String(body.prompt || '') }] }),
            signal: AbortSignal.timeout(60000),
          });
          const data: any = await reply.json();
          res.statusCode = reply.ok ? 200 : 502;
          res.end(JSON.stringify({ provider: 'ollama_local', model, text: data.message?.content || '', externalCallPerformed: false, noSupabaseUsed: true, clientDataUsed: false }));
        } catch {
          res.statusCode = 502;
          res.end(JSON.stringify({ error: 'ollama_request_failed' }));
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [nexusLocalBridges(), react()],
  define: Object.fromEntries(Object.entries(buildMetadata).map(([key,value]) => [`import.meta.env.${key}`, JSON.stringify(value)])),
  build: { outDir: 'dist' },
  test: { exclude: ['tests/e2e/**', 'node_modules/**', '.netlify/**'] },
});
