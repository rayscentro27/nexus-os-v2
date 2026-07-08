import { supabase, isSupabaseConfigured } from '../lib/supabaseClient'

export type EmailTemplate = 'welcome' | 'document_received' | 'review_requested' | 'review_complete' | 'status_update'

interface SendEmailOptions {
  to: string
  template: EmailTemplate
  subject?: string
  data?: Record<string, string>
}

export async function sendClientEmail(options: SendEmailOptions): Promise<{ success: boolean; error?: string }> {
  if (!isSupabaseConfigured) {
    return { success: false, error: 'Supabase not configured' }
  }

  try {
    const { data: { session } } = await supabase!.auth.getSession()
    if (!session) {
      return { success: false, error: 'Not authenticated' }
    }

    const response = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/send-client-email`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(options),
    })

    if (!response.ok) {
      const result = await response.json()
      return { success: false, error: result.error || 'Failed to send email' }
    }

    return { success: true }
  } catch (error) {
    console.error('[sendClientEmail]', error)
    return { success: false, error: 'Network error' }
  }
}

export async function sendWelcomeEmail(to: string, name: string) {
  return sendClientEmail({
    to,
    template: 'welcome',
    data: { name },
  })
}

export async function sendDocumentReceivedEmail(to: string, documentName: string) {
  return sendClientEmail({
    to,
    template: 'document_received',
    data: { documentName },
  })
}

export async function sendReviewRequestedEmail(to: string) {
  return sendClientEmail({
    to,
    template: 'review_requested',
  })
}

export async function sendReviewCompleteEmail(to: string) {
  return sendClientEmail({
    to,
    template: 'review_complete',
  })
}

export async function sendStatusUpdateEmail(to: string, status: string, message: string) {
  return sendClientEmail({
    to,
    template: 'status_update',
    data: { status, message },
  })
}
