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
  return json(503, {
    error: "provider_governance_unavailable",
    status: "disabled_fail_closed",
    extractionProvider: "none",
    url,
  });
}
