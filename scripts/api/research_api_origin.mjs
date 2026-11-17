import { execFile as execFileCallback } from 'node:child_process'
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { promisify } from 'node:util'
import { pathToFileURL } from 'node:url'

const execFile = promisify(execFileCallback)
const MCP_URL = 'http://127.0.0.1:18765/mcp'
const MCP_TOOL_ALLOWLIST = Object.freeze({
  list: 'nexus_list_research_rooms',
  get: 'nexus_get_research_room',
  create: 'nexus_create_research_room',
  add_source: 'nexus_add_room_source',
  ask: 'nexus_ask_alpha_research_room',
  score: 'nexus_score_research_room',
  promote: 'nexus_promote_research_room',
})
const ALLOWED_TOOLS = new Set(Object.values(MCP_TOOL_ALLOWLIST))
const ALLOWED_ORIGINS = new Set(['https://goclearonline.cc', 'https://nexus-campaigns.pages.dev'])
const PROTOCOL_VERSION = '2025-03-26'
const MAX_BODY_BYTES = 32 * 1024
const MAX_MCP_RESPONSE_BYTES = 2 * 1024 * 1024

function parseRuntimeEnv(text) {
  const values = {}
  for (const row of String(text || '').split(/\r?\n/)) {
    const line = row.trim()
    if (!line || line.startsWith('#')) continue
    const match = line.match(/^(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*)$/)
    if (!match || !['SUPABASE_URL', 'VITE_SUPABASE_URL', 'SUPABASE_ANON_KEY', 'VITE_SUPABASE_ANON_KEY'].includes(match[1])) continue
    values[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2').trim()
  }
  return values
}

async function getSupabaseConfig(env = process.env) {
  const runtimePath = env.NEXUS_RUNTIME_ENV_PATH || path.join(os.homedir(), '.config/nexus/runtime.env')
  let fileValues = {}
  try { fileValues = parseRuntimeEnv(await readFile(runtimePath, 'utf8')) } catch { /* report auth unavailable below */ }
  return {
    url: String(env.SUPABASE_URL || env.VITE_SUPABASE_URL || fileValues.SUPABASE_URL || fileValues.VITE_SUPABASE_URL || '').replace(/\/$/, ''),
    anonKey: env.SUPABASE_ANON_KEY || env.VITE_SUPABASE_ANON_KEY || fileValues.SUPABASE_ANON_KEY || fileValues.VITE_SUPABASE_ANON_KEY || '',
  }
}

async function validateAdminSession(request, { fetchImpl = fetch, env = process.env } = {}) {
  const authorization = request.headers.authorization || ''
  if (!/^Bearer\s+\S+$/i.test(authorization)) return { status: 401, error: 'AUTH_REQUIRED' }
  const { url, anonKey } = await getSupabaseConfig(env)
  if (!url || !anonKey) return { status: 503, error: 'ADMIN_AUTH_UNAVAILABLE' }
  const headers = { apikey: anonKey, authorization }
  let userResponse
  try {
    userResponse = await fetchImpl(`${url}/auth/v1/user`, { headers, signal: AbortSignal.timeout(8000) })
  } catch { return { status: 503, error: 'ADMIN_AUTH_UNAVAILABLE' } }
  if (userResponse.status === 401 || userResponse.status === 403) return { status: 401, error: 'AUTH_REQUIRED' }
  if (!userResponse.ok) return { status: 503, error: 'ADMIN_AUTH_UNAVAILABLE' }
  const user = await userResponse.json().catch(() => null)
  if (!user?.id) return { status: 401, error: 'AUTH_REQUIRED' }

  const userId = encodeURIComponent(user.id)
  const urls = [
    `${url}/rest/v1/admin_users?id=eq.${userId}&active=neq.false&select=role&limit=1`,
    `${url}/rest/v1/tenant_memberships?user_id=eq.${userId}&role=in.(super_admin,admin,operator)&select=role&limit=1`,
  ]
  for (const endpoint of urls) {
    let response
    try { response = await fetchImpl(endpoint, { headers, signal: AbortSignal.timeout(8000) }) } catch { return { status: 503, error: 'ADMIN_AUTH_UNAVAILABLE' } }
    if (!response.ok) return { status: 503, error: 'ADMIN_AUTH_UNAVAILABLE' }
    const rows = await response.json().catch(() => null)
    if (Array.isArray(rows) && rows.some(row => typeof row?.role === 'string' && row.role)) return { status: 200, userId: user.id }
  }
  return { status: 403, error: 'ADMIN_REQUIRED' }
}

async function readMcpToken() {
  const { stdout } = await execFile('/usr/bin/security', [
    'find-generic-password', '-s', 'nexus/credential.nexus.mcp.bridge.v1', '-a', 'bridge_token', '-w',
  ], { timeout: 5000, maxBuffer: 4096 })
  const token = stdout.trim()
  if (token.length < 32) throw new Error('MCP_AUTH_UNAVAILABLE')
  return token
}

function parseMcpEnvelope(response, expectedId) {
  return response.text().then(text => {
    if (Buffer.byteLength(text) > MAX_MCP_RESPONSE_BYTES) throw new Error('MCP_RESPONSE_TOO_LARGE')
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('text/event-stream')) return JSON.parse(text || '{}')
    for (const event of text.split(/\r?\n\r?\n/)) {
      const data = event.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('')
      if (!data) continue
      const parsed = JSON.parse(data)
      if (parsed.id === expectedId) return parsed
    }
    throw new Error('MCP_RESPONSE_INVALID')
  })
}

async function callResearchTool(toolName, args, { fetchImpl = fetch, tokenProvider = readMcpToken } = {}) {
  if (!ALLOWED_TOOLS.has(toolName)) throw new Error('TOOL_NOT_ALLOWLISTED')
  let token
  try { token = await tokenProvider() } catch { throw new Error('MCP_AUTH_UNAVAILABLE') }
  let sessionId = ''
  let id = 0
  const headers = () => ({
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    Accept: 'application/json, text/event-stream',
    ...(sessionId ? { 'Mcp-Session-Id': sessionId, 'MCP-Protocol-Version': PROTOCOL_VERSION } : {}),
  })
  const send = async message => {
    const response = await fetchImpl(MCP_URL, {
      method: 'POST', headers: headers(), body: JSON.stringify(message), signal: AbortSignal.timeout(60000),
    })
    sessionId = response.headers.get('Mcp-Session-Id') || sessionId
    if (!response.ok) throw new Error(response.status === 401 ? 'MCP_AUTH_REJECTED' : 'MCP_UNAVAILABLE')
    if (message.id === undefined) return null
    const envelope = await parseMcpEnvelope(response, message.id)
    if (envelope.error) throw new Error('MCP_REQUEST_FAILED')
    return envelope.result || {}
  }

  try {
    await send({ jsonrpc: '2.0', id: ++id, method: 'initialize', params: { protocolVersion: PROTOCOL_VERSION, capabilities: {}, clientInfo: { name: 'nexus-research-api-origin', version: '1' } } })
    await send({ jsonrpc: '2.0', method: 'notifications/initialized' })
    const discovered = await send({ jsonrpc: '2.0', id: ++id, method: 'tools/list', params: {} })
    if (!(discovered.tools || []).some(tool => tool.name === toolName)) throw new Error('MCP_TOOL_UNAVAILABLE')
    const result = await send({ jsonrpc: '2.0', id: ++id, method: 'tools/call', params: { name: toolName, arguments: args } })
    if (result.isError) throw new Error('MCP_TOOL_FAILED')
    if (result.structuredContent && typeof result.structuredContent === 'object') return result.structuredContent
    const text = (result.content || []).find(item => item.type === 'text')?.text
    if (!text) throw new Error('MCP_RESPONSE_INVALID')
    const payload = JSON.parse(text)
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('MCP_RESPONSE_INVALID')
    return payload
  } finally {
    if (sessionId) {
      try { await fetchImpl(MCP_URL, { method: 'DELETE', headers: headers(), signal: AbortSignal.timeout(3000) }) } catch { /* best-effort session cleanup */ }
    }
  }
}

function json(response, status, payload, origin) {
  response.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    ...(origin && ALLOWED_ORIGINS.has(origin) ? { 'Access-Control-Allow-Origin': origin, Vary: 'Origin' } : {}),
  })
  response.end(JSON.stringify(payload))
}

async function readJsonBody(request) {
  const chunks = []
  let size = 0
  for await (const chunk of request) {
    size += chunk.length
    if (size > MAX_BODY_BYTES) throw Object.assign(new Error('REQUEST_TOO_LARGE'), { status: 413 })
    chunks.push(chunk)
  }
  if (!size) return {}
  let body
  try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')) } catch { throw Object.assign(new Error('INVALID_JSON'), { status: 400 }) }
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw Object.assign(new Error('INVALID_REQUEST'), { status: 400 })
  return body
}

function boundedArguments(action, roomId, body, query) {
  const id = roomId ? decodeURIComponent(roomId) : ''
  if (id && (!/^[A-Za-z0-9_-]{1,160}$/.test(id))) throw Object.assign(new Error('INVALID_ROOM_ID'), { status: 400 })
  if (action === 'list') return { status: String(query.get('status') || '').slice(0, 32), query: String(query.get('query') || '').slice(0, 256), limit: Math.max(1, Math.min(Number(query.get('limit')) || 20, 50)) }
  if (action === 'get' || action === 'score') return { room_id: id }
  if (action === 'create') {
    const title = String(body.title || '').trim()
    if (!title || title.length > 200) throw Object.assign(new Error('TITLE_REQUIRED'), { status: 400 })
    const sourceContent = String(body.source_content || '')
    if (sourceContent.length > 20000) throw Object.assign(new Error('SOURCE_TOO_LARGE'), { status: 413 })
    const sourceType = String(body.source_type || 'TEXT').toUpperCase()
    if (!['TEXT', 'URL', 'YOUTUBE', 'EXISTING_RESEARCH'].includes(sourceType)) throw Object.assign(new Error('SOURCE_TYPE_INVALID'), { status: 400 })
    return { title, source_content: sourceContent, source_type: sourceType, source_title: String(body.source_title || '').slice(0, 200) }
  }
  if (action === 'add_source') {
    const sourceType = String(body.source_type || '').toUpperCase()
    const content = String(body.content_or_url || '')
    if (!['TEXT', 'URL', 'YOUTUBE', 'EXISTING_RESEARCH'].includes(sourceType) || !content || content.length > 20000) throw Object.assign(new Error('SOURCE_REQUEST_INVALID'), { status: 400 })
    return { room_id: id, source_type: sourceType, content_or_url: content, title: String(body.title || '').slice(0, 200) }
  }
  if (action === 'ask') {
    const question = String(body.question || '').trim()
    if (!question || question.length > 4000) throw Object.assign(new Error('QUESTION_REQUIRED'), { status: 400 })
    return { room_id: id, question }
  }
  if (action === 'promote') return { room_id: id, requested_objective: String(body.requested_objective || '').slice(0, 2000) }
  throw Object.assign(new Error('ROUTE_NOT_FOUND'), { status: 404 })
}

function routeFor(method, pathname) {
  if (method === 'GET' && pathname === '/health') return { health: true }
  if (method === 'GET' && pathname === '/api/research/rooms') return { action: 'list' }
  if (method === 'POST' && pathname === '/api/research/rooms') return { action: 'create' }
  const match = pathname.match(/^\/api\/research\/rooms\/([^/]+)(?:\/(sources|ask|score|promote))?$/)
  if (!match) return null
  if (method === 'GET' && !match[2]) return { action: 'get', roomId: match[1] }
  const actions = { sources: 'add_source', ask: 'ask', score: 'score', promote: 'promote' }
  if (method === 'POST' && actions[match[2]]) return { action: actions[match[2]], roomId: match[1] }
  return null
}

function publicError(error, action) {
  const code = error.message
  if (code === 'MCP_AUTH_UNAVAILABLE' || code === 'MCP_AUTH_REJECTED') return { status: 503, body: { error: 'MCP_AUTH_UNAVAILABLE' } }
  if (code === 'MCP_TOOL_UNAVAILABLE' || code === 'MCP_UNAVAILABLE') return { status: 503, body: { error: 'RESEARCH_BACKEND_UNAVAILABLE' } }
  if (code === 'MCP_TOOL_FAILED' || code === 'MCP_REQUEST_FAILED') return { status: 502, body: { error: action === 'ask' ? 'ALPHA_UNAVAILABLE' : action === 'score' ? 'SCORE_UNAVAILABLE' : action === 'promote' ? 'PROMOTION_FAILED' : action === 'add_source' ? 'SOURCE_RETRIEVAL_FAILED' : 'RESEARCH_BACKEND_FAILED' } }
  if (error.status) return { status: error.status, body: { error: code } }
  return { status: 502, body: { error: 'RESEARCH_BACKEND_FAILED' } }
}

export function createResearchApiServer({ fetchImpl = fetch, tokenProvider = readMcpToken, adminValidator = validateAdminSession } = {}) {
  return createServer(async (request, response) => {
    const origin = request.headers.origin || ''
    if (origin && !ALLOWED_ORIGINS.has(origin)) {
      json(response, 403, { error: 'ORIGIN_NOT_ALLOWED' })
      return
    }
    if (request.method === 'OPTIONS') {
      if (!origin) { json(response, 403, { error: 'ORIGIN_NOT_ALLOWED' }); return }
      response.writeHead(204, {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
        'Access-Control-Max-Age': '300',
        Vary: 'Origin',
      })
      response.end()
      return
    }

    let parsedUrl
    try { parsedUrl = new URL(request.url || '/', 'http://127.0.0.1:4000') } catch { json(response, 400, { error: 'INVALID_PATH' }); return }
    const route = routeFor(request.method || '', parsedUrl.pathname)
    if (!route) { json(response, 404, { error: 'NOT_FOUND' }, origin); return }
    if (route.health) { json(response, 200, { ok: true, service: 'nexus-research-api' }, origin); return }

    const auth = await adminValidator(request, { fetchImpl })
    if (auth.status !== 200) { json(response, auth.status, { error: auth.error }, origin); return }

    try {
      const body = request.method === 'POST' ? await readJsonBody(request) : {}
      const args = boundedArguments(route.action, route.roomId, body, parsedUrl.searchParams)
      const toolName = MCP_TOOL_ALLOWLIST[route.action]
      const result = await callResearchTool(toolName, args, { fetchImpl, tokenProvider })
      if (result.status === 'NOT_FOUND' || result.error === 'research_room_not_found') { json(response, 404, { error: 'ROOM_NOT_FOUND' }, origin); return }
      json(response, 200, result, origin)
    } catch (error) {
      const failure = publicError(error, route.action)
      json(response, failure.status, failure.body, origin)
    }
  })
}

export { ALLOWED_ORIGINS, ALLOWED_TOOLS, MCP_TOOL_ALLOWLIST, boundedArguments, callResearchTool, parseRuntimeEnv, routeFor, validateAdminSession }

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const server = createResearchApiServer()
  server.listen(4000, '127.0.0.1', () => {})
  server.on('error', error => { process.stderr.write(`research_api_origin_start_failed:${error.code || 'unknown'}\n`); process.exitCode = 1 })
}
