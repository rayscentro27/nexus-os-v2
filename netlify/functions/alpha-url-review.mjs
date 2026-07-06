const json = (status, body) => ({
  statusCode: status,
  headers: { "content-type": "application/json", "cache-control": "no-store" },
  body: JSON.stringify(body),
});

const MAX_CONTENT_CHARS = 12000;
const TIMEOUT_MS = 15000;

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

  const url = String(body.url || "").trim();
  if (!url || !/^https?:\/\/.+\..+/.test(url)) {
    return json(400, {
      error: "url_required_and_valid",
      status: "failed",
      extractionProvider: "none",
    });
  }

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
