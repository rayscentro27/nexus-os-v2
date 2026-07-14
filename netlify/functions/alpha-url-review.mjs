const json = (status, body) => ({
  statusCode: status,
  headers: { "content-type": "application/json", "cache-control": "no-store" },
  body: JSON.stringify(body),
});

const MAX_CONTENT_CHARS = 12000;
const TIMEOUT_MS = 15000;

const blockedHost = (hostname) => {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (host === "localhost" || host === "::1" || host.endsWith(".localhost") || host === "0.0.0.0") return true;
  if (/^127\./.test(host) || /^10\./.test(host) || /^192\.168\./.test(host)) return true;
  const match = host.match(/^172\.(\d{1,3})\./);
  if (match && Number(match[1]) >= 16 && Number(match[1]) <= 31) return true;
  if (/^169\.254\./.test(host) || /^fc/i.test(host) || /^fd/i.test(host) || /^fe[89ab]/i.test(host)) return true;
  return false;
};

export function validateAlphaReviewUrl(value) {
  let parsed;
  try { parsed = new URL(String(value || "").trim()); } catch { return { ok: false, error: "invalid_url" }; }
  if (!["http:", "https:"].includes(parsed.protocol)) return { ok: false, error: "protocol_not_allowed" };
  if (parsed.username || parsed.password) return { ok: false, error: "credentials_not_allowed" };
  if (!parsed.hostname.includes(".") || blockedHost(parsed.hostname)) return { ok: false, error: "host_not_allowed" };
  return { ok: true, url: parsed.href };
}

export async function handler(event) {
  if (event.httpMethod !== "POST") {
    return json(405, {
      error: "method_not_allowed",
      status: "failed",
      extractionProvider: "none",
    });
  }

  let body = {};
  try {
    body = JSON.parse(event.body || "{}");
  } catch {
    return json(400, {
      error: "invalid_json",
      status: "failed",
      extractionProvider: "none",
    });
  }

  const validation = validateAlphaReviewUrl(body.url);
  if (!validation.ok) {
    return json(400, {
      error: validation.error,
      status: "failed",
      extractionProvider: "none",
    });
  }
  const url = validation.url;

  if (!process.env.FIRECRAWL_API_KEY) {
    return json(503, {
      error: "firecrawl_disabled",
      status: "disabled",
      extractionProvider: "firecrawl",
      reason: "FIRECRAWL_API_KEY not configured on server",
    });
  }

  try {
    const firecrawlRes = await fetch("https://api.firecrawl.dev/v1/scrape", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${process.env.FIRECRAWL_API_KEY}`,
      },
      body: JSON.stringify({
        url,
        formats: ["markdown"],
        onlyMainContent: true,
      }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });

    if (!firecrawlRes.ok) {
      return json(firecrawlRes.status, {
        error: `firecrawl_${firecrawlRes.status}`,
        status: "failed",
        extractionProvider: "firecrawl",
      });
    }

    const data = await firecrawlRes.json();
    const markdown = data.markdown || data.content || "";
    const content = markdown.slice(0, MAX_CONTENT_CHARS);
    const title = data.title || data.metadata?.title || "";

    let finalUrl = url;
    try {
      finalUrl = new URL(data.sourceUrl || data.url || url).href;
    } catch {
      /* keep original url */
    }

    let domain = "";
    try {
      domain = new URL(finalUrl).hostname;
    } catch {
      /* empty */
    }

    return json(200, {
      ok: true,
      title,
      url: finalUrl,
      domain,
      content,
      extractionProvider: "firecrawl",
      extractionStatus: "extracted",
      timestamp: new Date().toISOString(),
      noSupabaseUsed: true,
      clientDataUsed: false,
    });
  } catch (e) {
    const reason = e.name === "AbortError" ? "timeout" : e.message || "unknown";
    return json(502, {
      error: `firecrawl_${reason}`,
      status: "failed",
      extractionProvider: "firecrawl",
      reason,
    });
  }
}
