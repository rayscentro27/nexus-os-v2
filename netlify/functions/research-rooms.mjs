import { requireAdmin } from './_admin-auth.mjs'

const TOOL_ALLOWLIST = new Set([
  'nexus_create_research_room',
  'nexus_get_research_room',
  'nexus_list_research_rooms',
  'nexus_add_room_source',
  'nexus_ask_alpha_research_room',
  'nexus_score_research_room',
  'nexus_promote_research_room',
])
const MAX_REQUEST_BYTES = 32768
const MAX_RESPONSE_BYTES = 2_000_000
const PROTOCOL_VERSION = '2025-03-26'
const json = (statusCode, body) => ({
  statusCode,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
})

function parsePath(event) {
  const route = String(event.path || '').replace(/^\/.netlify\/functions\/research-rooms/, '').replace(/^\/api\/research\/rooms/, '').replace(/\/$/, '')
  const segments = route.split('/').filter(Boolean).map(decodeURIComponent)
  if (!segments.length) return { action: 'list' }
  if (segments.length === 1) return { action: 'get', roomId: segments[0] }
  if (segments.length === 2 && segments[1] === 'sources') return { action: 'add_source', roomId: segments[0] }
  if (segments.length === 2 && segments[1] === 'alpha') return { action: 'ask_alpha', roomId: segments[0] }
  if (segments.length === 2 && segments[1] === 'score') return { action: 'score', roomId: segments[0] }
  if (segments.length === 2 && segments[1] === 'promote') return { action: 'promote', roomId: segments[0] }
  return null
}

function boundedArgs(action, roomId, input, query = {}) {
  const id = roomId && String(roomId).trim()
  if (id && (id.length > 160 || !/^[\w-]+$/.test(id))) throw Object.assign(new Error('invalid_room_id'), { statusCode: 400 })
  if (action === 'list') return {
    status: String(query.status || '').slice(0, 32),
    query: String(query.query || '').slice(0, 256),
    limit: Math.max(1, Math.min(Number(query.limit) || 20, 50)),
  }
  if (action === 'get') return { room_id: id }
  if (action === 'create') {
    const title = String(input.title || '').trim()
    if (!title || title.length > 200) throw Object.assign(new Error('title_required'), { statusCode: 400 })
    const sourceContent = String(input.source_content || '')
    if (sourceContent.length > 20000) throw Object.assign(new Error('source_too_large'), { statusCode: 413 })
    const sourceType = String(input.source_type || 'TEXT').toUpperCase()
    if (!['TEXT', 'URL', 'YOUTUBE', 'EXISTING_RESEARCH'].includes(sourceType)) throw Object.assign(new Error('source_type_invalid'), { statusCode: 400 })
    return { title, source_content: sourceContent, source_type: sourceType, source_title: String(input.source_title || '').slice(0, 200) }
  }
  if (action === 'add_source') {
    const sourceType = String(input.source_type || '').toUpperCase()
    const content = String(input.content_or_url || '')
    if (!['TEXT', 'URL', 'YOUTUBE', 'EXISTING_RESEARCH'].includes(sourceType) || !content || content.length > 20000) throw Object.assign(new Error('source_request_invalid'), { statusCode: 400 })
    return { room_id: id, source_type: sourceType, content_or_url: content, title: String(input.title || '').slice(0, 200) }
  }
  if (action === 'ask_alpha') {
    const question = String(input.question || '').trim()
    if (!question || question.length > 4000) throw Object.assign(new Error('question_required'), { statusCode: 400 })
    return { room_id: id, question }
  }
  if (action === 'score') return { room_id: id }
  if (action === 'promote') return { room_id: id, requested_objective: String(input.requested_objective || '').slice(0, 2000) }
  return null
}

function readMcpResult(response) {
  const contentType = response.headers.get('content-type') || ''
  const rawPromise = response.text()
  return rawPromise.then(raw => {
    if (raw.length > MAX_RESPONSE_BYTES) throw new Error('MCP_RESPONSE_TOO_LARGE')
    if (!contentType.includes('text/event-stream')) return JSON.parse(raw || '{}')
    for (const event of raw.split(/\r?\n\r?\n/)) {
      const data = event.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('')
      if (data) {
        const parsed = JSON.parse(data)
        if (parsed.id !== undefined) return parsed
      }
    }
    throw new Error('MCP_RESPONSE_INVALID')
  })
}

export async function invokeResearchRoomTool(toolName, arguments_, env = process.env, fetchImpl = fetch) {
  if (!TOOL_ALLOWLIST.has(toolName)) throw new Error('HTTP_TOOL_NOT_ALLOWLISTED')
  const endpoint = env.NEXUS_MCP_HTTP_URL || ''
  const token = env.NEXUS_MCP_BRIDGE_TOKEN || ''
  if (!endpoint || token.length < 32) throw new Error('MCP_BRIDGE_UNAVAILABLE')
  const parsed = new URL(endpoint)
  if (!['https:', 'http:'].includes(parsed.protocol) || !parsed.pathname.endsWith('/mcp')) throw new Error('MCP_BRIDGE_CONFIGURATION_INVALID')

  let sessionId = ''
  let requestId = 0
  const headers = () => ({
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    Accept: 'application/json, text/event-stream',
    ...(sessionId ? { 'Mcp-Session-Id': sessionId, 'MCP-Protocol-Version': PROTOCOL_VERSION } : {}),
  })
  const send = async (message) => {
    const response = await fetchImpl(endpoint, { method: 'POST', headers: headers(), body: JSON.stringify(message) })
    sessionId = response.headers.get('Mcp-Session-Id') || sessionId
    if (!response.ok) throw Object.assign(new Error(`MCP_HTTP_${response.status}`), { statusCode: response.status })
    if (message.id === undefined) return null
    const envelope = await readMcpResult(response)
    if (envelope.error) throw new Error('MCP_REQUEST_FAILED')
    return envelope.result || {}
  }
  try {
    await send({ jsonrpc: '2.0', id: ++requestId, method: 'initialize', params: { protocolVersion: PROTOCOL_VERSION, capabilities: {}, clientInfo: { name: 'nexus-admin-research-room', version: '1' } } })
    await send({ jsonrpc: '2.0', method: 'notifications/initialized' })
    const tools = await send({ jsonrpc: '2.0', id: ++requestId, method: 'tools/list', params: {} })
    if (!(tools.tools || []).some(tool => tool.name === toolName)) throw new Error('MCP_TOOL_UNAVAILABLE')
    const result = await send({ jsonrpc: '2.0', id: ++requestId, method: 'tools/call', params: { name: toolName, arguments: arguments_ } })
    if (result.isError) throw new Error('MCP_TOOL_FAILED')
    const structured = result.structuredContent
    if (structured && typeof structured === 'object') return structured
    const text = (result.content || []).find(item => item.type === 'text')?.text
    if (typeof text !== 'string') throw new Error('MCP_TOOL_RESPONSE_INVALID')
    const parsedResult = JSON.parse(text)
    if (!parsedResult || typeof parsedResult !== 'object') throw new Error('MCP_TOOL_RESPONSE_INVALID')
    return parsedResult
  } finally {
    if (sessionId) {
      try { await fetchImpl(endpoint, { method: 'DELETE', headers: headers() }) } catch { /* best-effort session cleanup */ }
    }
  }
}

export async function handler(event) {
  let auth
  try { auth = await requireAdmin(event) } catch { return json(401, { error: 'AUTH_REQUIRED' }) }
  if (!auth.ok) return json(auth.statusCode === 403 ? 403 : 401, { error: auth.statusCode === 403 ? 'ADMIN_REQUIRED' : 'AUTH_REQUIRED' })

  const route = parsePath(event)
  if (!route) return json(404, { error: 'ROUTE_NOT_FOUND' })
  const method = String(event.httpMethod || '').toUpperCase()
  let action = route.action
  if (method === 'POST' && action === 'list') action = 'create'
  const allowedMethod = action === 'list' || action === 'get' ? method === 'GET' : method === 'POST'
  if (!allowedMethod) return json(405, { error: 'METHOD_NOT_ALLOWED' })

  let body = {}
  if (method === 'POST') {
    if (Buffer.byteLength(event.body || '', 'utf8') > MAX_REQUEST_BYTES) return json(413, { error: 'REQUEST_TOO_LARGE' })
    try { body = JSON.parse(event.body || '{}') } catch { return json(400, { error: 'INVALID_JSON' }) }
    if (!body || typeof body !== 'object' || Array.isArray(body)) return json(400, { error: 'INVALID_REQUEST' })
  }
  try {
    const args = boundedArgs(action, route.roomId, body, event.queryStringParameters || {})
    const name = {
      list: 'nexus_list_research_rooms', get: 'nexus_get_research_room', create: 'nexus_create_research_room',
      add_source: 'nexus_add_room_source', ask_alpha: 'nexus_ask_alpha_research_room',
      score: 'nexus_score_research_room', promote: 'nexus_promote_research_room',
    }[action]
    const result = await invokeResearchRoomTool(name, args)
    if (result.status === 'NOT_FOUND' || result.error === 'research_room_not_found') return json(404, { error: 'ROOM_NOT_FOUND' })
    return json(200, result)
  } catch (error) {
    const status = error.statusCode || 502
    const message = String(error.message || '')
    const contractError = status < 500 ? message.toUpperCase() : message.includes('MCP_BRIDGE') || message.includes('MCP_HTTP') ? 'RESEARCH_BACKEND_UNAVAILABLE' : action === 'ask_alpha' ? 'ALPHA_UNAVAILABLE' : action === 'score' ? 'SCORE_UNAVAILABLE' : action === 'promote' ? 'PROMOTION_FAILED' : action === 'add_source' ? 'SOURCE_RETRIEVAL_FAILED' : 'RESEARCH_BACKEND_FAILED'
    return json(status, { error: contractError })
  }
}

export const researchRoomHttpInternals = { TOOL_ALLOWLIST, parsePath, boundedArgs }
