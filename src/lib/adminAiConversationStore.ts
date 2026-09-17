import { supabase } from './supabaseClient'

export type AdminAiRole = 'user' | 'assistant' | 'error'
export type AdminAiConversation = { id: string; agent: string; title: string; createdAt: string; updatedAt: string }
export type AdminAiMessage = { id: string; role: AdminAiRole; text: string; createdAt: string }

function requireClient() {
  if (!supabase) throw new Error('Admin conversation storage is not configured.')
  return supabase
}

function mapConversation(row: any): AdminAiConversation {
  return { id: row.id, agent: row.agent, title: row.title, createdAt: row.created_at, updatedAt: row.updated_at }
}

function mapMessage(row: any): AdminAiMessage {
  return { id: row.id, role: row.role, text: row.content, createdAt: row.created_at }
}

export async function listAdminAiConversations(agent = 'nova') {
  const client = requireClient()
  const { data, error } = await client.from('admin_ai_conversations').select('id,agent,title,created_at,updated_at').eq('agent', agent).order('updated_at', { ascending: false }).limit(100)
  if (error) throw new Error(`Conversation history unavailable: ${error.message}`)
  return (data || []).map(mapConversation)
}

export async function loadAdminAiConversation(id: string) {
  const client = requireClient()
  const conversation = await client.from('admin_ai_conversations').select('id,agent,title,created_at,updated_at').eq('id', id).maybeSingle()
  if (conversation.error) throw new Error(`Conversation unavailable: ${conversation.error.message}`)
  if (!conversation.data) return null
  const messages = await client.from('admin_ai_messages').select('id,role,content,created_at').eq('conversation_id', id).order('created_at', { ascending: true })
  if (messages.error) throw new Error(`Message history unavailable: ${messages.error.message}`)
  return { ...mapConversation(conversation.data), messages: (messages.data || []).map(mapMessage) }
}

export async function createAdminAiConversation(id: string, agent = 'nova') {
  const client = requireClient()
  const { data, error } = await client.from('admin_ai_conversations').insert({ id, agent, title: 'New conversation' }).select('id,agent,title,created_at,updated_at').single()
  if (error) throw new Error(`New chat could not be created: ${error.message}`)
  return mapConversation(data)
}

export async function appendAdminAiMessage(conversationId: string, role: AdminAiRole, text: string) {
  const client = requireClient()
  const inserted = await client.from('admin_ai_messages').insert({ conversation_id: conversationId, role, content: text }).select('id,role,content,created_at').single()
  if (inserted.error) throw new Error(`Message could not be saved: ${inserted.error.message}`)
  const updated = await client.from('admin_ai_conversations').update({ updated_at: new Date().toISOString() }).eq('id', conversationId)
  if (updated.error) throw new Error(`Conversation timestamp could not be saved: ${updated.error.message}`)
  return mapMessage(inserted.data)
}

export async function updateAdminAiTitle(id: string, title: string) {
  const client = requireClient()
  const { error } = await client.from('admin_ai_conversations').update({ title: title.slice(0, 120), updated_at: new Date().toISOString() }).eq('id', id)
  if (error) throw new Error(`Conversation title could not be saved: ${error.message}`)
}
