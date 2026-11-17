import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const authMock = vi.hoisted(() => ({ requireAdmin: vi.fn() }))
const sessionMock = vi.hoisted(() => ({ getSession: vi.fn() }))
vi.mock('../netlify/functions/_admin-auth.mjs', () => authMock)
vi.mock('../src/lib/supabaseClient', () => ({ supabase: { auth: sessionMock } }))

import { handler, invokeResearchRoomTool, researchRoomHttpInternals } from '../netlify/functions/research-rooms.mjs'
import {
  addResearchRoomSourceLive, askAlphaLive, createResearchRoomLive, getResearchRoomLive,
  listResearchRoomsLive, promoteResearchRoomLive, scoreResearchRoomLive,
} from '../src/lib/researchRoomApi'

const endpointEnv = {
  NEXUS_MCP_HTTP_URL: 'https://nexus.example/mcp',
  NEXUS_MCP_BRIDGE_TOKEN: 'x'.repeat(48),
}

function mcpResponse(body: unknown, status = 200, session = 'test-session') {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...(session ? { 'Mcp-Session-Id': session } : {}) },
  })
}

function mockMcpTool(result: Record<string, unknown> = { status: 'OK', room_id: 'room_test' }, expectedTool?: string) {
  const calls: any[] = []
  const fetchMock = vi.fn(async (_url: string, init: RequestInit = {}) => {
    const method = init.method || 'GET'
    if (method === 'DELETE') return new Response(null, { status: 200 })
    const message = JSON.parse(String(init.body || '{}'))
    calls.push(message)
    if (message.method === 'initialize') return mcpResponse({ jsonrpc: '2.0', id: message.id, result: { protocolVersion: '2025-03-26' } })
    if (message.method === 'notifications/initialized') return new Response(null, { status: 202, headers: { 'Mcp-Session-Id': 'test-session' } })
    if (message.method === 'tools/list') return mcpResponse({ jsonrpc: '2.0', id: message.id, result: { tools: [{ name: expectedTool }] } })
    if (message.method === 'tools/call') return mcpResponse({ jsonrpc: '2.0', id: message.id, result: { content: [{ type: 'text', text: JSON.stringify(result) }] } })
    throw new Error('unexpected MCP method')
  })
  return { calls, fetchMock }
}

function event(method: string, path: string, body?: unknown) {
  return { httpMethod: method, path, body: body === undefined ? '' : JSON.stringify(body), queryStringParameters: {} } as any
}

beforeEach(() => {
  authMock.requireAdmin.mockReset().mockResolvedValue({ ok: true, userId: 'admin-1', role: 'admin' })
  sessionMock.getSession.mockReset().mockResolvedValue({ data: { session: { access_token: 'admin-jwt' } }, error: null })
  vi.stubEnv('NEXUS_MCP_HTTP_URL', endpointEnv.NEXUS_MCP_HTTP_URL)
  vi.stubEnv('NEXUS_MCP_BRIDGE_TOKEN', endpointEnv.NEXUS_MCP_BRIDGE_TOKEN)
})
afterEach(() => vi.unstubAllGlobals())

describe('Research Room authenticated HTTP bridge', () => {
  it('requires the existing Admin session authorization on every route', async () => {
    authMock.requireAdmin.mockResolvedValue({ ok: false, statusCode: 401 })
    const response = await handler(event('GET', '/.netlify/functions/research-rooms'))
    expect(response.statusCode).toBe(401)
    expect(JSON.parse(response.body).error).toBe('AUTH_REQUIRED')
  })

  it.each([
    ['GET', '/.netlify/functions/research-rooms', 'nexus_list_research_rooms', undefined],
    ['GET', '/.netlify/functions/research-rooms/room_test', 'nexus_get_research_room', undefined],
    ['POST', '/.netlify/functions/research-rooms', 'nexus_create_research_room', { title: 'Admira source review' }],
    ['POST', '/.netlify/functions/research-rooms/room_test/sources', 'nexus_add_room_source', { source_type: 'URL', content_or_url: 'https://www.getadmira.com/?r=0', title: 'Admira' }],
    ['POST', '/.netlify/functions/research-rooms/room_test/alpha', 'nexus_ask_alpha_research_room', { question: 'What does the source say?' }],
    ['POST', '/.netlify/functions/research-rooms/room_test/score', 'nexus_score_research_room', {}],
    ['POST', '/.netlify/functions/research-rooms/room_test/promote', 'nexus_promote_research_room', { requested_objective: 'Review pilot' }],
  ])('%s %s calls only the mapped certified tool', async (method, path, tool, body) => {
    const { calls, fetchMock } = mockMcpTool({ status: 'OK', tool_name: tool, room_id: 'room_test' }, tool)
    vi.stubGlobal('fetch', fetchMock)
    const response = await handler(event(method, path, body))
    expect(response.statusCode).toBe(200)
    const toolCall = calls.find(call => call.method === 'tools/call')
    expect(toolCall.params.name).toBe(tool)
    expect(JSON.parse(response.body).tool_name).toBe(tool)
    expect(calls.some(call => call.method === 'tools/call' && !researchRoomHttpInternals.TOOL_ALLOWLIST.has(call.params.name))).toBe(false)
  })

  it('preserves the exact requested URL through the add-source tool arguments', async () => {
    const url = 'https://www.getadmira.com/?r=0'
    const { calls, fetchMock } = mockMcpTool({ status: 'OK', room_id: 'room_test' }, 'nexus_add_room_source')
    vi.stubGlobal('fetch', fetchMock)
    await handler(event('POST', '/.netlify/functions/research-rooms/room_test/sources', { source_type: 'URL', content_or_url: url }))
    const toolCall = calls.find(call => call.method === 'tools/call')
    expect(toolCall.params.arguments.content_or_url).toBe(url)
  })

  it('rejects unrecognized routes and never exposes a generic tool-call action', async () => {
    const response = await handler(event('POST', '/.netlify/functions/research-rooms/call-any-tool/nope', { name: 'nexus_get_system_health' }))
    expect(response.statusCode).toBe(404)
    expect(JSON.parse(response.body).error).toBe('ROUTE_NOT_FOUND')
    await expect(invokeResearchRoomTool('nexus_get_system_health', {}, endpointEnv, vi.fn() as any)).rejects.toThrow('HTTP_TOOL_NOT_ALLOWLISTED')
  })

  it('returns a bounded unavailable error when the MCP bridge is not configured', async () => {
    const response = await invokeResearchRoomTool('nexus_list_research_rooms', {}, {}, vi.fn() as any).catch(error => error.message)
    expect(response).toBe('MCP_BRIDGE_UNAVAILABLE')
  })

  it('does not convert a failed backend tool call into success', async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit = {}) => {
      if (init.method === 'DELETE') return new Response(null, { status: 200 })
      const message = JSON.parse(String(init.body || '{}'))
      if (message.method === 'initialize') return mcpResponse({ id: message.id, result: {} })
      if (message.method === 'notifications/initialized') return new Response(null, { status: 202, headers: { 'Mcp-Session-Id': 'test-session' } })
      if (message.method === 'tools/list') return mcpResponse({ id: message.id, result: { tools: [{ name: 'nexus_ask_alpha_research_room' }] } })
      return mcpResponse({ id: message.id, result: { isError: true, content: [{ type: 'text', text: 'backend error' }] } })
    })
    vi.stubGlobal('fetch', fetchMock)
    const response = await handler(event('POST', '/.netlify/functions/research-rooms/room_test/alpha', { question: 'Question' }))
    expect(response.statusCode).toBe(502)
    expect(JSON.parse(response.body).error).toBe('ALPHA_UNAVAILABLE')
  })
})

describe('Research Room browser API client', () => {
  it('uses authenticated Cloudflare API calls for the seven bounded capabilities', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'OK' }) })
    vi.stubGlobal('fetch', fetchMock)
    await listResearchRoomsLive({ query: 'Admira' })
    await getResearchRoomLive('room_1')
    await createResearchRoomLive({ title: 'Test room' })
    await addResearchRoomSourceLive('room_1', { source_type: 'URL', content_or_url: 'https://www.getadmira.com/?r=0' })
    await askAlphaLive('room_1', 'What does this source say?')
    await scoreResearchRoomLive('room_1')
    await promoteResearchRoomLive('room_1', 'Review the opportunity')
    expect(fetchMock).toHaveBeenCalledTimes(7)
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      'https://nexus-api.goclearonline.cc/api/research/rooms?query=Admira', 'https://nexus-api.goclearonline.cc/api/research/rooms/room_1', 'https://nexus-api.goclearonline.cc/api/research/rooms',
      'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/sources', 'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/alpha',
      'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/score', 'https://nexus-api.goclearonline.cc/api/research/rooms/room_1/promote',
    ])
    for (const [, init] of fetchMock.mock.calls) expect(init.headers.Authorization).toBe('Bearer admin-jwt')
  })
})
