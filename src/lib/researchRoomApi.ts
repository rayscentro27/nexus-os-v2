import { supabase } from './supabaseClient'

export interface ResearchRoomApiError extends Error { code: string; status: number }

async function request<T>(path: string, method: 'GET' | 'POST', body?: Record<string, unknown>): Promise<T> {
  if (!supabase) throw Object.assign(new Error('Admin session is unavailable.'), { code: 'AUTH_REQUIRED', status: 401 }) as ResearchRoomApiError
  const { data, error } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (error || !token) throw Object.assign(new Error('Admin session is unavailable.'), { code: 'AUTH_REQUIRED', status: 401 }) as ResearchRoomApiError
  const response = await fetch(`https://nexus-api.goclearonline.cc${path}`, {
    method,
    headers: { Authorization: `Bearer ${token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw Object.assign(new Error(payload.error || 'Research Room request failed.'), { code: payload.error || 'RESEARCH_BACKEND_FAILED', status: response.status }) as ResearchRoomApiError
  return payload as T
}

const roomPath = '/api/research/rooms'
const roomIdPath = (roomId: string) => `${roomPath}/${encodeURIComponent(roomId)}`

export const listResearchRoomsLive = (filters: { status?: string; query?: string; limit?: number } = {}) => {
  const query = new URLSearchParams()
  if (filters.status) query.set('status', filters.status)
  if (filters.query) query.set('query', filters.query)
  if (filters.limit) query.set('limit', String(filters.limit))
  return request(`${roomPath}${query.size ? `?${query}` : ''}`, 'GET')
}
export const getResearchRoomLive = (roomId: string) => request(roomIdPath(roomId), 'GET')
export const createResearchRoomLive = (input: { title: string }) => request(roomPath, 'POST', input)
export const addResearchRoomSourceLive = (roomId: string, input: { source_type: string; content_or_url: string; title?: string }) => request(`${roomIdPath(roomId)}/sources`, 'POST', input)
export const askAlphaLive = (roomId: string, question: string) => request(`${roomIdPath(roomId)}/ask`, 'POST', { question })
export const scoreResearchRoomLive = (roomId: string) => request(`${roomIdPath(roomId)}/score`, 'POST', {})
export const promoteResearchRoomLive = (roomId: string, requested_objective = '') => request(`${roomIdPath(roomId)}/promote`, 'POST', { requested_objective })
