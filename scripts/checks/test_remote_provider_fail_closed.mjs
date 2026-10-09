import test from 'node:test';
import assert from 'node:assert/strict';
import { handler } from '../../netlify/functions/alpha-url-review.mjs';
import { tiktok } from '../../netlify/functions/_tiktok.mjs';

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
