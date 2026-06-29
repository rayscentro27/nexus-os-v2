import { clientGuideResponses } from './clientGuideResponses'

export const clientHermesBridgeData = {
  architecture: 'structured_approval_bridge_only',
  hermes_private_admin_only: true,
  client_guide_name: 'Nexus Guide',
  unrestricted_ai_to_ai_chat: false,
  approved_client_guidance: [
    { id: 'guidance-1', category: 'documents', summary: 'Upload current address proof and revenue summary.', approval_status: 'approved_demo', client_visible: true },
    { id: 'guidance-2', category: 'funding_readiness', summary: 'Complete blockers and request GoClear review before applying.', approval_status: 'approved_demo', client_visible: true },
  ],
  client_visible_tasks: ['task-1', 'task-2', 'task-3', 'task-4'],
  client_questions: [],
  client_escalations: [],
  goclear_review_status: 'review_pending',
  approval_cards: ['review-credit-drafts', 'review-funding-path', 'review-partner-fit'],
  hermes_admin_notes: ['Keep client guidance educational and specific to approved records.', 'Do not expose private admin strategy or raw client data.'],
  client_bot_response_templates: Object.keys(clientGuideResponses || {}),
  client_hermes_guidance_latest: 'Only approved_client_guidance is client-visible.',
  admin_review_queue: ['credit-sensitive recommendations', 'draft letters', 'funding path', 'partner fit', 'client escalations'],
  data_mode: 'live_supabase_pending',
  live_bridge_enabled: false,
  safe_status: 'structured_records_ready_for_rls_review',
}
