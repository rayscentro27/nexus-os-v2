import test from 'node:test'
import assert from 'node:assert/strict'
import { createResearchApiServer, ALLOWED_TOOLS, MCP_TOOL_ALLOWLIST, callResearchTool, parseRuntimeEnv, routeFor } from '../scripts/api/research_api_origin.mjs'

function response(body, status = 200, sessionId = 'mcp-test-session') {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...(sessionId ? { 'Mcp-Session-Id': sessionId } : {}) },
  })
}

function mcpMock(toolName, payload) {
  const calls = []
  const fetchImpl = async (_url, init = {}) => {
    if (init.method === 'DELETE') return new Response(null, { status: 200 })
    const msg = JSON.parse(String(init.body || '{}'))
    calls.push(msg)
    if (msg.method === 'initialize') return response({ jsonrpc: '2.0', id: msg.id, result: { protocolVersion: '2025-03-26' } })
    if (msg.method === 'notifications/initialized') return new Response(null, { status: 202, headers: { 'Mcp-Session-Id': 'mcp-test-session' } })
    if (msg.method === 'tools/list') return response({ jsonrpc: '2.0', id: msg.id, result: { tools: [{ name: toolName }] } })
    if (msg.method === 'tools/call') return response({ jsonrpc: '2.0', id: msg.id, result: { content: [{ type: 'text', text: JSON.stringify(payload) }] } })
    throw new Error('unexpected MCP method')
  }
  return { calls, fetchImpl }
}

async function withServer(options, fn) {
  const server = createResearchApiServer(options)
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  try { await fn(`http://127.0.0.1:${address.port}`) } finally { await new Promise(resolve => server.close(resolve)) }
}

test('exposes exactly seven fixed Research Room MCP tools', () => {
  assert.equal(ALLOWED_TOOLS.size, 7)
  assert.deepEqual(new Set(Object.values(MCP_TOOL_ALLOWLIST)), ALLOWED_TOOLS)
  assert.equal(routeFor('POST', '/api/mcp'), null)
  assert.equal(routeFor('POST', '/api/research/rooms/room_test/ask').action, 'ask')
})

test('parses only the Supabase Admin auth values from the Nexus runtime environment', () => {
  assert.deepEqual(parseRuntimeEnv('SUPABASE_URL=https://x.test\nSUPABASE_ANON_KEY="anon"\nSERVICE_ROLE_KEY=must_not_read\n'), {
    SUPABASE_URL: 'https://x.test', SUPABASE_ANON_KEY: 'anon',
  })
})

test('health is minimal and unauthenticated Research requests fail closed', async () => {
  await withServer({ adminValidator: async () => ({ status: 401, error: 'AUTH_REQUIRED' }), tokenProvider: async () => { throw new Error('must not be called') } }, async base => {
    const health = await fetch(`${base}/health`)
    assert.equal(health.status, 200)
    assert.deepEqual(await health.json(), { ok: true, service: 'nexus-research-api' })
    const list = await fetch(`${base}/api/research/rooms`)
    assert.equal(list.status, 401)
    assert.deepEqual(await list.json(), { error: 'AUTH_REQUIRED' })
  })
})

test('Research endpoints reject untrusted browser origins', async () => {
  await withServer({}, async base => {
    const res = await fetch(`${base}/api/research/rooms`, { headers: { Origin: 'https://untrusted.example' } })
    assert.equal(res.status, 403)
    assert.deepEqual(await res.json(), { error: 'ORIGIN_NOT_ALLOWED' })
  })
})

test('forwards a bounded live list request through the allowlisted MCP transport', async () => {
  const payload = { tool_name: 'nexus_list_research_rooms', status: 'OK', rooms: [] }
  const mcp = mcpMock('nexus_list_research_rooms', payload)
  await withServer({ adminValidator: async () => ({ status: 200 }), tokenProvider: async () => 'test-token', fetchImpl: mcp.fetchImpl }, async base => {
    const res = await fetch(`${base}/api/research/rooms?query=Admira&limit=99`, { headers: { Authorization: 'Bearer admin-session' } })
    assert.equal(res.status, 200)
    assert.deepEqual(await res.json(), payload)
    const call = mcp.calls.find(message => message.method === 'tools/call')
    assert.equal(call.params.name, 'nexus_list_research_rooms')
    assert.equal(call.params.arguments.limit, 50)
    assert.equal(call.params.arguments.query, 'Admira')
  })
})

test('preserves exact URL source identity when forwarding add-source', async () => {
  const mcp = mcpMock('nexus_add_room_source', { status: 'OK', room_id: 'room_test', room: { sources: [{ requested_url: 'https://www.getadmira.com/?r=0', domain: 'www.getadmira.com' }] } })
  await withServer({ adminValidator: async () => ({ status: 200 }), tokenProvider: async () => 'test-token', fetchImpl: mcp.fetchImpl }, async base => {
    const url = 'https://www.getadmira.com/?r=0'
    const res = await fetch(`${base}/api/research/rooms/room_test/sources`, {
      method: 'POST', headers: { Authorization: 'Bearer admin-session', 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type: 'URL', content_or_url: url }),
    })
    assert.equal(res.status, 200)
    const call = mcp.calls.find(message => message.method === 'tools/call')
    assert.equal(call.params.name, 'nexus_add_room_source')
    assert.equal(call.params.arguments.content_or_url, url)
  })
})

test('rejects arbitrary MCP tools and does not return fabricated output on MCP failure', async () => {
  await assert.rejects(callResearchTool('nexus_get_system_health', {}, { tokenProvider: async () => 'token', fetchImpl: async () => { throw new Error('must not be called') } }), /TOOL_NOT_ALLOWLISTED/)
  await withServer({ adminValidator: async () => ({ status: 200 }), tokenProvider: async () => { throw new Error('MCP_AUTH_UNAVAILABLE') } }, async base => {
    const res = await fetch(`${base}/api/research/rooms`, { headers: { Authorization: 'Bearer admin-session' } })
    assert.equal(res.status, 503)
    assert.deepEqual(await res.json(), { error: 'MCP_AUTH_UNAVAILABLE' })
  })
})
