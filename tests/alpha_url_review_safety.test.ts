import { describe, expect, it } from 'vitest'
import { validateAlphaReviewUrl } from '../netlify/functions/alpha-url-review.mjs'

describe('Alpha URL review server boundary', () => {
  it('accepts public HTTP(S) URLs and normalizes them', () => {
    expect(validateAlphaReviewUrl('https://example.com/research')).toMatchObject({ ok: true, url: 'https://example.com/research' })
  })
  it.each([
    ['/relative', 'invalid_url'], ['not a URL', 'invalid_url'], ['ftp://example.com/a', 'protocol_not_allowed'],
    ['http://localhost/a', 'host_not_allowed'], ['http://127.0.0.1/a', 'host_not_allowed'],
    ['http://10.0.0.2/a', 'host_not_allowed'], ['http://172.20.1.2/a', 'host_not_allowed'],
    ['http://192.168.1.2/a', 'host_not_allowed'], ['http://169.254.1.2/a', 'host_not_allowed'],
    ['https://user:secret@example.com/a', 'credentials_not_allowed'],
  ])('rejects unsafe URL %s', (url, error) => expect(validateAlphaReviewUrl(url)).toEqual({ ok: false, error }))
})
