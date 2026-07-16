import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface EmailRequest {
  to: string
  subject: string
  template: 'welcome' | 'document_received' | 'review_requested' | 'review_complete' | 'status_update' | 'tester_invitation' | 'invitation_reminder' | 'invitation_revoked' | 'invitation_accepted' | 'test_session_complete'
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
  tester_invitation: (data: Record<string, string>) => ({
    subject: data.subject || `A Special Invitation from Ray to Preview GoClear`,
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #0f1729 0%, #1e3a5f 100%); border-radius: 12px; padding: 28px; margin-bottom: 24px;">
          <h1 style="color: #ffffff; font-size: 22px; margin: 0;">A Personal Invitation from Ray</h1>
          <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0;">GoClear · Friends & Family Preview</p>
        </div>

        <p style="color: #4a5568; line-height: 1.7; font-size: 15px;">Hi ${data.testerName || 'there'},</p>

        <p style="color: #4a5568; line-height: 1.7; font-size: 15px;">I'm personally inviting you to be one of the first people to experience GoClear, a platform I've been building to help individuals better understand their credit, organize important financial documents, strengthen their business foundation, and prepare for future funding opportunities.</p>

        <p style="color: #4a5568; line-height: 1.7; font-size: 15px;">I'm inviting a small group of family and friends to explore GoClear before it is released more broadly. Your feedback will help me make the experience simpler, clearer, and more useful for future clients.</p>

        ${data.personalNote ? `<div style="background: #f8fbff; border-radius: 10px; padding: 16px 20px; margin: 20px 0; border-left: 4px solid #3b82f6;"><p style="color: #4a5568; font-style: italic; margin: 0; line-height: 1.6; font-size: 14px;">"${data.personalNote}"</p></div>` : ''}

        <div style="background: #f8fbff; border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid #d6e3f3;">
          <h3 style="color: #0f1729; margin: 0 0 12px; font-size: 16px;">During your preview, you'll be able to:</h3>
          <ul style="color: #4a5568; line-height: 1.8; margin: 0; padding-left: 20px; font-size: 14px;">
            <li>Explore a guided credit-improvement journey</li>
            <li>Review credit and funding-readiness tools</li>
            <li>Upload test documents securely</li>
            <li>Explore business setup and bankability</li>
            <li>Receive guidance from Clyde</li>
            <li>Request a readiness review</li>
            <li>Share feedback about your experience</li>
          </ul>
        </div>

        ${data.isFree === 'true' ? '<div style="background: #f0fdf4; border-radius: 8px; padding: 12px 16px; margin: 16px 0; border: 1px solid #bbf7d0;"><p style="color: #166534; margin: 0; font-size: 14px;"><strong>There is no charge for this invitation.</strong> This is a free preview of the GoClear experience.</p></div>' : ''}
        ${data.isPilot === 'true' ? '<div style="background: #fffbeb; border-radius: 8px; padding: 12px 16px; margin: 16px 0; border: 1px solid #fde68a;"><p style="color: #92400e; margin: 0; font-size: 13px;">You have also been selected for our controlled $1 Friends & Family Pilot. The one-dollar payment helps us verify the complete payment, onboarding, portal, service-delivery, and refund experience before public launch. This is not the normal GoClear service price, and it is not a promise of credit, funding, deletion, approval, or financial results.</p></div>' : ''}

        <p style="color: #4a5568; line-height: 1.7; font-size: 15px;">This personal invitation is intended only for you and expires on ${data.expiresAt || 'soon'}.</p>

        <div style="text-align: center; margin: 28px 0;">
          <a href="${data.acceptanceUrl || '#'}" style="display: inline-block; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 16px;">Accept My Personal Invitation</a>
        </div>

        <p style="color: #4a5568; line-height: 1.7; font-size: 15px;">Thank you for helping me build something that can make a real difference.</p>

        <p style="color: #4a5568; line-height: 1.7; font-size: 15px; margin-top: 20px;">Ray Davis<br/>Founder, GoClear</p>

        <div style="border-top: 1px solid #e2e8f0; margin-top: 24px; padding-top: 16px;">
          <p style="color: #94a3b8; font-size: 12px; line-height: 1.5; margin: 0;">This is a single-use link. Do not share it. If you did not expect this invitation, please ignore this email.</p>
          <p style="color: #94a3b8; font-size: 12px; line-height: 1.5; margin: 8px 0 0;">GoClear · Advisory services only · goclearonline.cc</p>
        </div>
      </div>
    `,
    text: `Hi ${data.testerName || 'there'},

I'm personally inviting you to be one of the first people to experience GoClear, a platform I've been building to help individuals better understand their credit, organize important financial documents, strengthen their business foundation, and prepare for future funding opportunities.

During your preview, you'll be able to explore a guided credit-improvement journey, review funding-readiness tools, upload documents, receive guidance from Clyde, and share feedback.

${data.isFree === 'true' ? 'There is no charge for this invitation.' : ''}
${data.isPilot === 'true' ? 'You have also been selected for our controlled $1 Friends & Family Pilot.' : ''}

Accept your invitation: ${data.acceptanceUrl || ''}

Ray Davis
Founder, GoClear
GoClear · Advisory services only`,
  }),
  invitation_reminder: (data: Record<string, string>) => ({
    subject: `Reminder: Your Nexus Tester Invitation — GoClear`,
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Invitation Reminder</h1>
        <p style="color: #4a5568; line-height: 1.6;">Hello ${data.testerName || 'Tester'},</p>
        <p style="color: #4a5568; line-height: 1.6;">This is a reminder that your tester invitation is waiting. Please accept before it expires on ${data.expiresAt || 'the expiration date'}.</p>
        <a href="${data.acceptanceUrl || '#'}" style="display: inline-block; background: #3b82f6; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 16px 0;">Accept Invitation</a>
        <p style="color: #6b7b99; font-size: 12px;">GoClear · Nexus OS Testing Program</p>
      </div>
    `,
  }),
  invitation_revoked: (data: Record<string, string>) => ({
    subject: `Invitation Revoked — GoClear`,
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Invitation Revoked</h1>
        <p style="color: #4a5568; line-height: 1.6;">Hello ${data.testerName || 'Tester'},</p>
        <p style="color: #4a5568; line-height: 1.6;">Your tester invitation has been revoked by an administrator. You will no longer be able to access the testing environment.</p>
        <p style="color: #6b7b99; font-size: 12px;">GoClear · Nexus OS Testing Program</p>
      </div>
    `,
  }),
  invitation_accepted: (data: Record<string, string>) => ({
    subject: `Invitation Accepted — Welcome to Nexus Testing`,
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Welcome to Nexus Testing!</h1>
        <p style="color: #4a5568; line-height: 1.6;">Hello ${data.testerName || 'Tester'},</p>
        <p style="color: #4a5568; line-height: 1.6;">Your invitation has been accepted and your account is ready. You can now sign in and begin your testing assignment.</p>
        <a href="${data.tasksUrl || '/tester/tasks'}" style="display: inline-block; background: #10b981; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 16px 0;">Go to Testing Tasks</a>
        <p style="color: #6b7b99; font-size: 12px;">GoClear · Nexus OS Testing Program</p>
      </div>
    `,
  }),
  test_session_complete: (data: Record<string, string>) => ({
    subject: `Testing Session Complete — Thank You!`,
    html: `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #0f1729; font-size: 24px;">Testing Session Complete</h1>
        <p style="color: #4a5568; line-height: 1.6;">Hello ${data.testerName || 'Tester'},</p>
        <p style="color: #4a5568; line-height: 1.6;">Thank you for completing your testing session. Your feedback has been recorded and will help us improve Nexus OS.</p>
        <p style="color: #6b7b99; font-size: 12px;">GoClear · Nexus OS Testing Program</p>
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
