import test from 'node:test';
import assert from 'node:assert/strict';
import { handler } from '../../netlify/functions/alpha-url-review.mjs';
import { tiktok } from '../../netlify/functions/_tiktok.mjs';
import { handler as tiktokAuthStart } from '../../netlify/functions/tiktok-auth-start.mjs';
import { handler as tiktokCallback } from '../../netlify/functions/tiktok-oauth-callback.mjs';
import { handler as tiktokRefresh } from '../../netlify/functions/tiktok-token-refresh.mjs';
import { handler as tiktokDisconnect } from '../../netlify/functions/tiktok-disconnect.mjs';

test('Firecrawl function fails closed before network access', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('network reached'); };
  try {
    const response = await handler({ httpMethod: 'POST', body: JSON.stringify({ url: 'https://example.com/a' }) });
    assert.equal(response.statusCode, 503);
    assert.match(response.body, /disabled_fail_closed/);
  } finally {
    globalThis.fetch = original;
  }
});

test('TikTok adapter denies before network access', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('network reached'); };
  try {
    await assert.rejects(tiktok({}, 'no-value', '/v2/user/info/'), /GOVERNOR_DENIED/);
  } finally {
    globalThis.fetch = original;
  }
});

test('TikTok OAuth, refresh, and disconnect routes fail closed without network access', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('network reached'); };
  try {
    for (const route of [tiktokAuthStart, tiktokCallback, tiktokRefresh, tiktokDisconnect]) {
      const response = await route({ httpMethod: 'POST', headers: {}, body: '{}', queryStringParameters: {} });
      assert.equal(response.statusCode, 503);
      assert.match(response.body, /disabled_fail_closed/);
    }
  } finally {
    globalThis.fetch = original;
  }
});
