import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '..')

describe('tester invitation system', () => {
  describe('database migration', () => {
    const migrationPath = resolve(ROOT, 'supabase/migrations/20260715200000_tester_invitation_system.sql')

    it('migration file exists', () => {
      expect(existsSync(migrationPath)).toBe(true)
    })

    it('creates tester_invitations table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.tester_invitations')
      expect(sql).toContain('tester_name text not null')
      expect(sql).toContain('tester_email text not null')
      expect(sql).toContain('testing_level text not null')
      expect(sql).toContain('invitation_status text not null')
      expect(sql).toContain('token_hash text not null')
      expect(sql).toContain('token_last_four text not null')
      expect(sql).toContain('expires_at timestamptz not null')
    })

    it('creates payment_pilot_allowlist table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.payment_pilot_allowlist')
      expect(sql).toContain('tester_invitation_id uuid')
      expect(sql).toContain('tester_email text not null')
      expect(sql).toContain('enabled boolean not null default true')
      expect(sql).toContain('max_orders integer not null default 1')
      expect(sql).toContain('orders_used integer not null default 0')
    })

    it('creates payment_pilot_controls table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.payment_pilot_controls')
      expect(sql).toContain('mode text not null default')
      expect(sql).toContain('invitations_enabled boolean not null default false')
      expect(sql).toContain('test_mode_purchases_enabled boolean not null default false')
      expect(sql).toContain('controlled_live_pilot_enabled boolean not null default false')
      expect(sql).toContain('public_live_enabled boolean not null default false')
      expect(sql).toContain('emergency_checkout_disabled boolean not null default false')
    })

    it('creates pilot_disclosures table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.pilot_disclosures')
      expect(sql).toContain('invitation_id uuid not null')
      expect(sql).toContain('disclosure_version text not null')
      expect(sql).toContain('disclosure_text text not null')
      expect(sql).toContain('accepted_at timestamptz not null')
    })

    it('creates invitation_events audit table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.invitation_events')
      expect(sql).toContain('event_type text not null')
      expect(sql).toContain('actor_admin_id uuid')
      expect(sql).toContain('metadata jsonb not null default')
    })

    it('creates invite_email_drafts table', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create table if not exists public.invite_email_drafts')
      expect(sql).toContain('template_name text not null')
      expect(sql).toContain('status text not null default')
    })

    it('enables RLS on all tables', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      const tables = ['tester_invitations', 'payment_pilot_allowlist', 'payment_pilot_controls', 'pilot_disclosures', 'invitation_events', 'invite_email_drafts']
      tables.forEach(table => {
        expect(sql).toContain(`alter table public.${table} enable row level security`)
      })
    })

    it('creates admin-only policies', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('nexus_is_active_admin()')
      expect(sql).toContain('tester_invitations_admin_manage')
      expect(sql).toContain('pilot_allowlist_admin_manage')
      expect(sql).toContain('pilot_controls_admin_manage')
    })

    it('creates tester own-select policy', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('tester_invitations_own_select')
      expect(sql).toContain('auth_user_id = auth.uid()')
      expect(sql).toContain("invitation_status = 'accepted'")
    })

    it('has proper check constraints', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain("check (testing_level in ('synthetic_internal', 'invited_test_mode', 'controlled_live_pilot'))")
      expect(sql).toContain("check (invitation_status in ('draft', 'awaiting_approval', 'approved', 'sent', 'accepted', 'expired', 'revoked', 'completed', 'failed'))")
      expect(sql).toContain("check (payment_mode in ('test', 'controlled_live_pilot', 'public_live'))")
    })

    it('creates indexes', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('create index if not exists idx_tester_invitations_email')
      expect(sql).toContain('create index if not exists idx_tester_invitations_status')
      expect(sql).toContain('create index if not exists idx_tester_invitations_token_hash')
      expect(sql).toContain('create index if not exists idx_pilot_allowlist_email')
      expect(sql).toContain('create index if not exists idx_invitation_events_invitation')
    })

    it('creates unique constraint for active invitations', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('one_active_invitation_per_email_level')
    })

    it('creates hash function', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('nexus_hash_invitation_token')
      expect(sql).toContain("encode(digest(raw_token, 'sha256'), 'hex')")
    })

    it('creates updated_at triggers', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain('nexus_set_updated_at')
      expect(sql).toContain('tester_invitations_updated_at')
      expect(sql).toContain('pilot_allowlist_updated_at')
      expect(sql).toContain('pilot_controls_updated_at')
    })

    it('seeds default pilot controls', () => {
      const sql = readFileSync(migrationPath, 'utf8')
      expect(sql).toContain("insert into public.payment_pilot_controls")
      expect(sql).toContain("'singleton'")
      expect(sql).toContain("invitations_enabled")
    })
  })

  describe('edge functions', () => {
    const functions = [
      'create-tester-invitation',
      'accept-tester-invitation',
      'send-tester-invitation',
      'revoke-tester-invitation',
      'create-invited-checkout',
      'validate-invite-token',
    ]

    functions.forEach(fn => {
      it(`${fn} edge function exists`, () => {
        const fnPath = resolve(ROOT, `supabase/functions/${fn}/index.ts`)
        expect(existsSync(fnPath)).toBe(true)
      })
    })

    it('create-tester-invitation validates admin', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/create-tester-invitation/index.ts'), 'utf8')
      expect(fn).toContain('admin_users')
      expect(fn).toContain('admin_required')
    })

    it('create-tester-invitation generates secure token', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/create-tester-invitation/index.ts'), 'utf8')
      expect(fn).toContain('crypto.getRandomValues')
      expect(fn).toContain('SHA-256')
      expect(fn).toContain('token_hash')
    })

    it('accept-tester-invitation enforces single use', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/accept-tester-invitation/index.ts'), 'utf8')
      expect(fn).toContain('invitation_already_accepted')
      expect(fn).toContain('invitation_completed')
    })

    it('accept-tester-invitation enforces expiration', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/accept-tester-invitation/index.ts'), 'utf8')
      expect(fn).toContain('invitation_expired')
    })

    it('accept-tester-invitation enforces revocation', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/accept-tester-invitation/index.ts'), 'utf8')
      expect(fn).toContain('invitation_revoked')
    })

    it('accept-tester-invitation creates or updates auth user and portal baseline', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/accept-tester-invitation/index.ts'), 'utf8')
      expect(fn).toContain('admin.auth.admin.createUser')
      expect(fn).toContain('admin.auth.admin.updateUserById')
      expect(fn).toContain('auth_user_id')
      expect(fn).toContain('bootstrapClientPortal')
      expect(fn).toContain('tenant_memberships')
      expect(fn).toContain('readiness_scores')
      expect(fn).toContain('client_tasks')
    })

    it('accept-tester-invitation does not email password', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/accept-tester-invitation/index.ts'), 'utf8')
      expect(fn).not.toContain('sendEmail')
      expect(fn).not.toContain('send_email')
    })

    it('create-invited-checkout requires accepted invitation', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/create-invited-checkout/index.ts'), 'utf8')
      expect(fn).toContain('invitation_not_accepted')
      expect(fn).toContain('invitation_status')
      expect(fn).toContain('accepted')
    })

    it('create-invited-checkout enforces one order', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/create-invited-checkout/index.ts'), 'utf8')
      expect(fn).toContain('order_already_paid')
    })

    it('create-invited-checkout checks emergency disable', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/create-invited-checkout/index.ts'), 'utf8')
      expect(fn).toContain('emergency_checkout_disabled')
      expect(fn).toContain('checkout_emergency_disabled')
    })

    it('create-invited-checkout enforces test mode', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/create-invited-checkout/index.ts'), 'utf8')
      expect(fn).toContain("sk_test_")
      expect(fn).toContain('test_mode_required')
    })

    it('revoke-tester-invitation disables allowlist', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/revoke-tester-invitation/index.ts'), 'utf8')
      expect(fn).toContain('payment_pilot_allowlist')
      expect(fn).toContain('enabled: false')
    })

    it('validate-invite-token checks expiration', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/validate-invite-token/index.ts'), 'utf8')
      expect(fn).toContain('invitation_expired')
    })

    it('validate-invite-token checks revocation', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/validate-invite-token/index.ts'), 'utf8')
      expect(fn).toContain('invitation_revoked')
    })
  })

  describe('client service', () => {
    it('testerInvitationClient.ts exists', () => {
      expect(existsSync(resolve(ROOT, 'src/lib/testerInvitationClient.ts'))).toBe(true)
    })

    it('exports required functions', () => {
      const src = readFileSync(resolve(ROOT, 'src/lib/testerInvitationClient.ts'), 'utf8')
      expect(src).toContain('createTesterInvitation')
      expect(src).toContain('validateInviteToken')
      expect(src).toContain('acceptTesterInvitation')
      expect(src).toContain('resendTesterInvitation')
      expect(src).toContain('revokeTesterInvitation')
      expect(src).toContain('createInvitedCheckout')
      expect(src).toContain('loadTesterInvitations')
      expect(src).toContain('loadPilotControls')
      expect(src).toContain('updatePilotControls')
    })

    it('does not expose service role', () => {
      const src = readFileSync(resolve(ROOT, 'src/lib/testerInvitationClient.ts'), 'utf8')
      expect(src).not.toContain('SUPABASE_SERVICE_ROLE')
      expect(src).not.toContain('service_role')
    })
  })

  describe('service offer catalog', () => {
    it('adds invited-readiness-test offer', () => {
      const src = readFileSync(resolve(ROOT, 'src/config/serviceOfferCatalog.ts'), 'utf8')
      expect(src).toContain('invited-readiness-test')
      expect(src).toContain('Invited Readiness Test')
      expect(src).toContain("active: false")
    })

    it('adds real-payment-pilot-1 offer', () => {
      const src = readFileSync(resolve(ROOT, 'src/config/serviceOfferCatalog.ts'), 'utf8')
      expect(src).toContain('real-payment-pilot-1')
      expect(src).toContain('Real Payment Pilot ($1)')
      expect(src).toContain('is_test_pilot_offer: true')
      expect(src).toContain('publicly_visible: false')
      expect(src).toContain('requires_invitation: true')
      expect(src).toContain('requires_allowlist: true')
    })

    it('defines pilot disclosure text', () => {
      const src = readFileSync(resolve(ROOT, 'src/config/serviceOfferCatalog.ts'), 'utf8')
      expect(src).toContain('PILOT_DISCLOSURE_TEXT')
      expect(src).toContain('limited paid product-testing program')
    })

    it('defines HIDDEN_PILOT_OFFERS', () => {
      const src = readFileSync(resolve(ROOT, 'src/config/serviceOfferCatalog.ts'), 'utf8')
      expect(src).toContain('HIDDEN_PILOT_OFFERS')
    })
  })

  describe('admin panel', () => {
    it('TesterInvitationPanel.jsx exists', () => {
      expect(existsSync(resolve(ROOT, 'src/components/TesterInvitationPanel.jsx'))).toBe(true)
    })

    it('panel has create invitation form', () => {
      const src = readFileSync(resolve(ROOT, 'src/components/TesterInvitationPanel.jsx'), 'utf8')
      expect(src).toContain('create-invitation-btn')
      expect(src).toContain('new-inv-name')
      expect(src).toContain('new-inv-email')
      expect(src).toContain('new-inv-level')
    })

    it('panel has payment controls toggles', () => {
      const src = readFileSync(resolve(ROOT, 'src/components/TesterInvitationPanel.jsx'), 'utf8')
      expect(src).toContain('invitations-toggle')
      expect(src).toContain('test-purchases-toggle')
      expect(src).toContain('Invitations ON')
      expect(src).toContain('Test $ ON')
    })

    it('panel shows pilot offers', () => {
      const src = readFileSync(resolve(ROOT, 'src/components/TesterInvitationPanel.jsx'), 'utf8')
      expect(src).toContain('HIDDEN_PILOT_OFFERS')
      expect(src).toContain('Hidden Pilot Offers')
    })

    it('panel shows payment controls', () => {
      const src = readFileSync(resolve(ROOT, 'src/components/TesterInvitationPanel.jsx'), 'utf8')
      expect(src).toContain('payment-safety-strip')
      expect(src).toContain('SAFETY')
      expect(src).toContain('controlled_live_pilot')
      expect(src).toContain('public_live')
    })
  })

  describe('tester pages', () => {
    it('TesterInvitePage exists', () => {
      expect(existsSync(resolve(ROOT, 'src/pages/tester/TesterInvitePage.tsx'))).toBe(true)
    })

    it('TesterAcceptPage exists', () => {
      expect(existsSync(resolve(ROOT, 'src/pages/tester/TesterAcceptPage.tsx'))).toBe(true)
    })

    it('TesterTasksPage exists', () => {
      expect(existsSync(resolve(ROOT, 'src/pages/tester/TesterTasksPage.tsx'))).toBe(true)
    })

    it('invite page extracts token from URL', () => {
      const src = readFileSync(resolve(ROOT, 'src/pages/tester/TesterInvitePage.tsx'), 'utf8')
      expect(src).toContain('extractToken')
      expect(src).toContain('window.location.pathname')
    })

    it('accept page has password inputs', () => {
      const src = readFileSync(resolve(ROOT, 'src/pages/tester/TesterAcceptPage.tsx'), 'utf8')
      expect(src).toContain('password-input')
      expect(src).toContain('confirm-password-input')
      expect(src).toContain('consent-checkbox')
    })

    it('accept page shows Friends & Family terms', () => {
      const src = readFileSync(resolve(ROOT, 'src/pages/tester/TesterAcceptPage.tsx'), 'utf8')
      expect(src).toContain('Friends & Family Preview')
      expect(src).toContain('consent-checkbox')
    })

    it('tasks page has checklist', () => {
      const src = readFileSync(resolve(ROOT, 'src/pages/tester/TesterTasksPage.tsx'), 'utf8')
      expect(src).toContain('TEST_CHECKLISTS')
      expect(src).toContain('start-session-btn')
      expect(src).toContain('feedback-input')
    })

    it('tasks page does not show admin navigation', () => {
      const src = readFileSync(resolve(ROOT, 'src/pages/tester/TesterTasksPage.tsx'), 'utf8')
      expect(src).not.toContain('/admin')
      expect(src).not.toContain('NexusAdminUI')
    })
  })

  describe('app routing', () => {
    it('App.tsx includes tester routes', () => {
      const src = readFileSync(resolve(ROOT, 'src/app/App.tsx'), 'utf8')
      expect(src).toContain('/invite')
      expect(src).toContain('/tester/invite')
      expect(src).toContain('/tester/accept')
      expect(src).toContain('/tester/tasks')
      expect(src).toContain('TesterInvitePage')
      expect(src).toContain('TesterAcceptPage')
      expect(src).toContain('TesterTasksPage')
    })
  })

  describe('admin UI integration', () => {
    it('NexusAdminUI includes tester invitations nav', () => {
      const src = readFileSync(resolve(ROOT, 'src/admin/NexusAdminUI.jsx'), 'utf8')
      expect(src).toContain('tester-invitations')
      expect(src).toContain('Tester Invitations')
      expect(src).toContain('TesterInvitationPanel')
    })
  })

  describe('email templates', () => {
    it('send-client-email includes tester invitation template', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/send-client-email/index.ts'), 'utf8')
      expect(fn).toContain('tester_invitation')
      expect(fn).toContain('invitation_reminder')
      expect(fn).toContain('invitation_revoked')
      expect(fn).toContain('invitation_accepted')
      expect(fn).toContain('test_session_complete')
    })

    it('invitation email contains acceptance link', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/send-client-email/index.ts'), 'utf8')
      expect(fn).toContain('acceptanceUrl')
    })

    it('invitation email does not contain password', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/send-client-email/index.ts'), 'utf8')
      const invStart = fn.indexOf('tester_invitation:')
      const invEnd = fn.indexOf('invitation_reminder:', invStart)
      const invSection = fn.substring(invStart, invEnd)
      expect(invSection).not.toContain('your password is')
      expect(invSection).not.toContain('Your password:')
      expect(invSection).not.toContain('Password: ')
      expect(invSection).not.toContain('password: ')
    })

    it('invitation email contains GoClear Friends & Family content', () => {
      const fn = readFileSync(resolve(ROOT, 'supabase/functions/send-client-email/index.ts'), 'utf8')
      expect(fn).toContain('GoClear')
      expect(fn).toContain('Friends & Family')
      expect(fn).toContain('Accept My Personal Invitation')
    })
  })

  describe('security checks', () => {
    it('no service role in frontend', () => {
      const files = [
        'src/lib/testerInvitationClient.ts',
        'src/pages/tester/TesterInvitePage.tsx',
        'src/pages/tester/TesterAcceptPage.tsx',
        'src/pages/tester/TesterTasksPage.tsx',
        'src/components/TesterInvitationPanel.jsx',
      ]
      files.forEach(file => {
        const src = readFileSync(resolve(ROOT, file), 'utf8')
        expect(src).not.toContain('SUPABASE_SERVICE_ROLE')
        expect(src).not.toContain('service_role')
      })
    })

    it('no raw tokens in reports', () => {
      const reportFiles = [
        'reports/testers/tester_invitation_system_latest.md',
        'reports/testers/invited_test_mode_pilot_latest.md',
        'reports/revenue/hidden_one_dollar_pilot_foundation_latest.md',
      ]
      reportFiles.forEach(file => {
        if (existsSync(resolve(ROOT, file))) {
          const content = readFileSync(resolve(ROOT, file), 'utf8')
          expect(content).not.toContain('sk_live_')
          expect(content).not.toMatch(/sk_test_[a-zA-Z0-9]{20,}/)
          expect(content).not.toMatch(/whsec_[a-zA-Z0-9]{20,}/)
        }
      })
    })

    it('payment controls default to disabled', () => {
      const sql = readFileSync(resolve(ROOT, 'supabase/migrations/20260715200000_tester_invitation_system.sql'), 'utf8')
      expect(sql).toContain('invitations_enabled boolean not null default false')
      expect(sql).toContain('test_mode_purchases_enabled boolean not null default false')
      expect(sql).toContain('controlled_live_pilot_enabled boolean not null default false')
      expect(sql).toContain('public_live_enabled boolean not null default false')
      expect(sql).toContain('emergency_checkout_disabled boolean not null default false')
    })

    it('public live is disabled everywhere', () => {
      const checkoutFn = readFileSync(resolve(ROOT, 'supabase/functions/create-invited-checkout/index.ts'), 'utf8')
      expect(checkoutFn).toContain('public_live_disabled')
    })

    it('hidden offers are not publicly visible', () => {
      const catalog = readFileSync(resolve(ROOT, 'src/config/serviceOfferCatalog.ts'), 'utf8')
      const pilotSection = catalog.substring(catalog.indexOf('HIDDEN_PILOT_OFFERS'))
      expect(pilotSection).toContain('publicly_visible: false')
    })
  })
})
