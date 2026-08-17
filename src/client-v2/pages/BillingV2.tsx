import { CalendarClock, Receipt, ShieldCheck, UserRound } from 'lucide-react'
import type { V2ViewData } from '../types/v2-models'
import { PageHeaderV2 } from '../layouts/PageHeaderV2'
import { CardV2, SectionHeaderV2, StatusBadgeV2 } from '../components/primitives'

export function BillingV2({ data }: { data: V2ViewData }) {
  const { profile } = data

  return (
    <div className="v2-fade-in space-y-4">
      <PageHeaderV2
        eyebrow="Account"
        title="Billing & Membership"
        subtitle="Your membership, subscription status, and upcoming review dates — surfaced the same way GoClear sees your account."
      />

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_300px] gap-4">
        <div className="space-y-4 min-w-0">
          <div className="v2-card v2-card--solid-navy p-4">
            <div className="flex flex-wrap items-center gap-4">
              <span className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center">
                <Receipt size={22} className="text-[#9DB8FF]" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-v2lg font-semibold text-white">{profile?.membershipTier || 'GoClear Membership'}</div>
                <div className="text-[12.5px] text-white/60 mt-0.5">{profile?.subscriptionStatus || 'Active'}</div>
              </div>
              <StatusBadgeV2 tone="emerald" dot>Active</StatusBadgeV2>
            </div>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <MemberFact icon={CalendarClock} label="Next review" value={profile?.nextReviewDate || 'TBD'} />
              <MemberFact icon={UserRound} label="Advisor" value={profile?.advisorName || 'GoClear Review Team'} />
              <MemberFact icon={ShieldCheck} label="Status" value={profile?.overallStatus || 'Building readiness'} />
            </div>
          </div>

          <CardV2>
            <SectionHeaderV2 eyebrow="Ledger" title="Invoice & order activity" />
            <div className="mt-4 flex flex-col items-center gap-3 rounded-xl border border-dashed border-[#D9E1F0] px-6 py-8 text-center">
              <span className="w-12 h-12 rounded-xl bg-v2brand-tint text-v2brand flex items-center justify-center">
                <Receipt size={22} />
              </span>
              <div className="text-v2base font-semibold text-v2ink">Order activity syncs here</div>
              <p className="text-[12.5px] text-v2muted max-w-sm">
                Your invoices, consultations, and packet deliveries will appear once they are synchronized from the revenue ledger.
              </p>
            </div>
          </CardV2>
        </div>

        <aside className="space-y-4">
          <CardV2>
            <div className="flex items-start gap-3">
              <span className="w-9 h-9 rounded-lg bg-v2emerald-tint text-[#0E8A65] flex items-center justify-center shrink-0">
                <ShieldCheck size={18} />
              </span>
              <div>
                <div className="text-v2base font-semibold text-v2ink">Membership note</div>
                <p className="mt-1 text-[12px] leading-relaxed text-v2muted">
                  Your membership reflects the plan tied to your funding readiness review. Reach the review queue in Funding Access before any product-specific recommendation.
                </p>
              </div>
            </div>
          </CardV2>
        </aside>
      </div>
    </div>
  )
}

function MemberFact({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white/[0.06] border border-white/10 px-4 py-3 flex items-center gap-3">
      <span className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center shrink-0">
        <Icon size={16} className="text-[#9DB8FF]" />
      </span>
      <div className="min-w-0">
        <div className="text-[10.5px] font-semibold uppercase tracking-wide text-white/50">{label}</div>
        <div className="text-[13px] font-semibold text-white truncate">{value}</div>
      </div>
    </div>
  )
}