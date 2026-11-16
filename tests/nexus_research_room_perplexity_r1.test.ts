import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const component = readFileSync(new URL('../src/components/ResearchRoomWorkspace.jsx', import.meta.url), 'utf8')
const store = readFileSync(new URL('../src/lib/researchRoomStore.ts', import.meta.url), 'utf8')

describe('Research Room live UI safeguards', () => {
  it('uses only the live Research Room API for production actions', () => {
    expect(component).toContain("from '../lib/researchRoomApi'")
    expect(component).toContain('listResearchRoomsLive')
    expect(component).toContain('getResearchRoomLive')
    expect(component).toContain('createResearchRoomLive')
    expect(component).toContain('addResearchRoomSourceLive')
    expect(component).toContain('askAlphaLive')
    expect(component).toContain('scoreResearchRoomLive')
    expect(component).toContain('promoteResearchRoomLive')
    expect(component).not.toContain('researchRoomStore')
  })

  it('does not contain local sample data or fabricated Research operations', () => {
    expect(store).not.toContain('SEED_ROOMS')
    expect(store).not.toContain('localStorage')
    expect(component).not.toContain('Cited evidence excerpt')
    expect(component).not.toContain('fake_project')
    expect(component).not.toContain('compareResearchRooms(')
    expect(component).toContain('Web Search is not connected')
    expect(component).toContain('Deep Research is not connected')
    expect(component).toContain('Thread persistence coming next')
  })

  it('renders citation controls only when a returned source reference resolves', () => {
    expect(component).toContain('const refs = Array.isArray(message.source_refs)')
    expect(component).toContain('if (!source) return <span key={index}>{part}</span>')
    expect(component).toContain('Excerpt unavailable from the backend.')
  })
})
