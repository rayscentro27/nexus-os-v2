import { describe, expect, it } from 'vitest'
import fs from 'node:fs'

describe('Creative Studio evolution pilot', () => {
  it('provides a visual, interactive workspace over canonical Creative Intelligence', () => {
    const source = fs.readFileSync('src/components/NexusCreativeStudioWorkspace.jsx', 'utf8')
    expect(source).toContain('SAMPLE_TERRITORIES')
    expect(source).toContain('Compare territories')
    expect(source).toContain('Show critique')
    expect(source).toContain('Create variation')
    expect(source).toContain('Send to Ray Review')
    expect(source).toContain('Creative Intelligence')
    expect(source).toContain('novelty: UNKNOWN')
  })
})
