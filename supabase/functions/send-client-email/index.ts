import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface EmailRequest {
  to: string
  subject: string
  template: 'welcome' | 'document_received' | 'review_requested' | 'review_complete' | 'status_update'
  data?: Record<string, string>
}

const templates = {
  welcome: (data: Record<string, string>) => ({
    subject: 'Welcome to GoClear Client Portal',
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Welcome to GoClear, ${data.name || 'there'}!</h1>
        <p style="color: #4a5568; line-height: 1.6;">Your client portal is ready. You can now track your funding readiness progress, upload documents, and view your personalized guidance.</p>
        <div style="background: #f8fbff; border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid #d6e3f3;">
          <h3 style="color: #0f1729; margin: 0 0 10px;">Next Steps:</h3>
          <ul style="color: #4a5568; line-height: 1.8;">
            <li>Log in to your portal</li>
            <li>Upload your required documents</li>
            <li>Review your readiness checklist</li>
          </ul>
        </div>
        <p style="color: #6b7b99; font-size: 12px;">GoClear Client Portal · Advisory services only · Not a lender</p>
      </div>
    `,
  }),
  document_received: (data: Record<string, string>) => ({
    subject: 'Document Received - GoClear',
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Document Received</h1>
        <p style="color: #4a5568; line-height: 1.6;">We've received your document: <strong>${data.documentName || 'Unknown'}</strong></p>
        <p style="color: #4a5568; line-height: 1.6;">Our team will review it within 2 business days. You'll receive an update once the review is complete.</p>
        <p style="color: #6b7b99; font-size: 12px;">GoClear Client Portal · Advisory services only</p>
      </div>
    `,
  }),
  review_requested: (data: Record<string, string>) => ({
    subject: 'Review Request Submitted - GoClear',
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Review Request Submitted</h1>
        <p style="color: #4a5568; line-height: 1.6;">Your readiness review request has been submitted successfully.</p>
        <p style="color: #4a5568; line-height: 1.6;">Our team will review your profile and documents. You'll receive an update once the review is complete.</p>
        <p style="color: #6b7b99; font-size: 12px;">GoClear Client Portal · Advisory services only</p>
      </div>
    `,
  }),
  review_complete: (data: Record<string, string>) => ({
    subject: 'Review Complete - GoClear',
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Review Complete</h1>
        <p style="color: #4a5568; line-height: 1.6;">Your readiness review has been completed.</p>
        <p style="color: #4a5568; line-height: 1.6;">Log in to your portal to view the updated status and any recommended next steps.</p>
        <p style="color: #6b7b99; font-size: 12px;">GoClear Client Portal · Advisory services only</p>
      </div>
    `,
  }),
  status_update: (data: Record<string, string>) => ({
    subject: `Status Update - ${data.status || 'Update'} - GoClear`,
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Status Update</h1>
        <p style="color: #4a5568; line-height: 1.6;">${data.message || 'Your status has been updated.'}</p>
        <p style="color: #6b7b99; font-size: 12px;">GoClear Client Portal · Advisory services only</p>
      </div>
    `,
  }),
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const resendApiKey = Deno.env.get('RESEND_API_KEY')!

    if (!resendApiKey) {
      return new Response(
        JSON.stringify({ error: 'Email service not configured' }),
        { status: 503, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'Missing authorization' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      global: { headers: { Authorization: authHeader } },
    })

    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const { to, subject, template, data = {} }: EmailRequest = await req.json()

    if (!to || !template) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const templateFn = templates[template]
    if (!templateFn) {
      return new Response(
        JSON.stringify({ error: 'Invalid template' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const { subject: emailSubject, html } = templateFn(data)

    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${resendApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'GoClear <notifications@goclearonline.cc>',
        to: [to],
        subject: subject || emailSubject,
        html,
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      console.error('[send-client-email]', error)
      return new Response(
        JSON.stringify({ error: 'Failed to send email' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const result = await response.json()

    return new Response(
      JSON.stringify({ success: true, id: result.id }),
      { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    console.error('[send-client-email]', error)
    return new Response(
      JSON.stringify({ error: 'Internal error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
