import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const session = vi.hoisted(() => ({ getSession: vi.fn() }))
vi.mock('../src/lib/supabaseClient', () => ({ supabase: { auth: session } }))

import {
  addResearchRoomSourceLive, askAlphaLive, createResearchRoomLive,
  getResearchRoomLive, listResearchRoomsLive, promoteResearchRoomLive,
  scoreResearchRoomLive,
} from '../src/lib/researchRoomApi'

beforeEach(() => session.getSession.mockResolvedValue({ data: { session: { access_token: 'session-token' } }, error: null }))
afterEach(() => vi.unstubAllGlobals())

describe('authenticated Research Room API client', () => {
  it('calls only the seven bounded live API operations with the current Admin session', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'OK' }) })
    vi.stubGlobal('fetch', fetchMock)
    await listResearchRoomsLive({ query: 'Admira' })
    await getResearchRoomLive('room_1')
    await createResearchRoomLive({ title: 'Test room' })
    await addResearchRoomSourceLive('room_1', { source_type: 'URL', content_or_url: 'https://www.getadmira.com/?r=0' })
    await askAlphaLive('room_1', 'What does this source say?')
    await scoreResearchRoomLive('room_1')
    await promoteResearchRoomLive('room_1', 'Review the opportunity')

    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      'https://nexus-api.goclearonline.cc/api/research/rooms?query=Admira',
      'https://nexus-api.goclearonline.cc/api/research/rooms/room_1',
      'https://nexus-api.goclearonline.cc/api/research/rooms',
      'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/sources',
      'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/alpha',
      'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/score',
      'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/promote',
    ])
    for (const [, init] of fetchMock.mock.calls) expect(init.headers.Authorization).toBe('Bearer session-token')
    expect(JSON.parse(fetchMock.mock.calls[3][1].body).content_or_url).toBe('https://www.getadmira.com/?r=0')
  })

  it('does not call the API when no authenticated Admin session exists', async () => {
    session.getSession.mockResolvedValue({ data: { session: null }, error: null })
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    await expect(listResearchRoomsLive()).rejects.toMatchObject({ code: 'AUTH_REQUIRED', status: 401 })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
