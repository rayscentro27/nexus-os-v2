import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(resolve(process.cwd(), 'src/admin/VoicePushToTalk.jsx'), 'utf8')

describe('private live transcript review UX', () => {
  it('keeps preview advisory and Hermes behind explicit review send', () => {
    expect(source).toContain('/v1/voice/preview')
    expect(source).toContain('LIVE_PREVIEW')
    expect(source).toContain('TRANSCRIPT_READY')
    expect(source).toContain('onTranscript(clean)')
    expect(source).toContain('Send to Hermes')
    expect(source).toContain('sequence >= acceptedPreviewRef.current')
    expect(source).toContain('Live preview unavailable')
  })
})
