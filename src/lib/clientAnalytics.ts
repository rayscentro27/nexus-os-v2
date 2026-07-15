import { supabase } from './supabaseClient'

export type AnalyticsEvent =
  | 'stage_viewed'
  | 'requirement_viewed'
  | 'next_action_clicked'
  | 'upload_started'
  | 'upload_completed'
  | 'upload_failed'
  | 'resource_viewed'
  | 'partner_offer_clicked'
  | 'review_requested'
  | 'journey_stage_completed'

interface AnalyticsPayload {
  event: AnalyticsEvent
  stage?: string
  requirement?: string
  route?: string
  detail?: string
}

let sessionId: string | null = null

function getOrCreateSessionId(): string {
  if (sessionId) return sessionId
  try {
    const stored = sessionStorage.getItem('nexus-analytics-session')
    if (stored) { sessionId = stored; return sessionId }
  } catch {}
  sessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  try { sessionStorage.setItem('nexus-analytics-session', sessionId) } catch {}
  return sessionId
}

export async function trackEvent(payload: AnalyticsPayload): Promise<void> {
  if (!supabase) return
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return

    const sid = getOrCreateSessionId()

    const insertPromise = supabase.from('nexus_events').insert({
      lane: 'client_analytics',
      action: payload.event,
      status: 'info',
      title: payload.event.replace(/_/g, ' '),
      source: 'client_portal',
      payload: {
        session_id: sid,
        stage: payload.stage || null,
        requirement: payload.requirement || null,
        route: payload.route || null,
        detail: payload.detail || null,
        timestamp: new Date().toISOString(),
      },
    })
    Promise.resolve(insertPromise).catch(() => {})
  } catch {}
}
