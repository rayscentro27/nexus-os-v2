export const hermesAdminData = {
  visibility: 'admin_only',
  reportBacked: true,
  responses: {
    what_is_working: 'Internal engines, client portal routes, dispute simulation, draft generation, connector policy checks, and Supabase-ready exports are working.',
    what_is_blocked: 'Live client data is blocked by migration/RLS approval; YouTube by metadata key or transcript data; external actions by approval gates.',
    what_needs_ray_approval: 'Approve the Supabase migration/RLS plan, $97 payment path, real YouTube intake, and prioritized Ray Review cards.',
    is_youtube_real_yet: 'Check youtube_review_proof_latest. Real review requires imported API metadata or an approved local transcript.',
    can_disputes_be_tested: 'Yes, end-to-end in synthetic/mock mode. Sending, bureau contact, creditor contact, collector contact, and mailing remain blocked.',
    what_can_be_automated_today: 'Local readiness generation, safe source import, drafts, prioritization, proof events, dry-run validation, and bounded loop cycles.',
    next_money_action: 'Approve the $97 offer payment method and tenant-safe client creation path.',
    what_stays_gated: 'Client-facing advice, dispute letters, external messages, publishing, payments, database execution, and any funding recommendation.',
    env_audit: 'Connector key names and masked fingerprints are inventoried; raw values are excluded from reports.',
    supabase_next: 'Review the additive migration, test RLS locally, seed tenant memberships, then approve a dry-run database push.',
  },
}

export default hermesAdminData
