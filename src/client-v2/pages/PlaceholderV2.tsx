import {
  Building2,
  CreditCard,
  FileText,
  MessagesSquare,
  Receipt,
  ShieldCheck,
  Target,
  TrendingUp,
  Wrench,
} from 'lucide-react'
import { EmptyStateV2 } from '../components/primitives'
import { ROUTE_LABELS, navigateV2 } from '../utils/navigate'

const PLACEHOLDER_MAP: Record<string, { icon: any; title: string; body: string; eta: string }> = {
  '/client-v2/credit-review': {
    icon: CreditCard,
    title: 'Credit Review workspace',
    body: 'Your credit snapshot, bureau posture, utilization summary, and discrepancies will be presented here with Nexus analysis.',
    eta: 'Ships in checkpoint 2',
  },
  '/client-v2/credit-improvement': {
    icon: TrendingUp,
    title: 'Credit Improvement tracking',
    body: 'Outsourced fulfillment rounds, verified results, and outreach status will run here. Live progress from the dashboard is already wired.',
    eta: 'Ships in checkpoint 2',
  },
  '/client-v2/business-foundation': {
    icon: Building2,
    title: 'Business Foundation',
    body: 'Entity, EIN, address, banking, and trade-profile milestones will be presented here against your readiness model.',
    eta: 'Ships in checkpoint 2',
  },
  '/client-v2/funding-readiness': {
    icon: Target,
    title: 'Funding Readiness',
    body: 'The full readiness breakdown — strengths, blockers, and requirement list — will be presented here. The arc on your dashboard is live already.',
    eta: 'Ships in checkpoint 2',
  },
  '/client-v2/funding-access': {
    icon: ShieldCheck,
    title: 'Funding Access',
    body: 'Readiness confirmation, recommended funding sequence, and application status will live here.',
    eta: 'Ships in checkpoint 2',
  },
  '/client-v2/documents': {
    icon: FileText,
    title: 'Documents Vault',
    body: 'Upload, replacement, and review status for your document set will be presented here with the full review pipeline.',
    eta: 'Ships in checkpoint 2',
  },
  '/client-v2/resources': {
    icon: Wrench,
    title: 'Resources',
    body: 'Guides, checklists, and reference material are curated here.',
    eta: 'Ships in a later checkpoint',
  },
  '/client-v2/messages': {
    icon: MessagesSquare,
    title: 'Hermes messaging',
    body: 'Hermes is active on your dashboard. A full message center with conversation threads lands in a later checkpoint.',
    eta: 'Ships later',
  },
  '/client-v2/billing': {
    icon: Receipt,
    title: 'Billing & Membership',
    body: 'Subscription status, invoices, and membership details will be presented here.',
    eta: 'Ships later',
  },
}

export function PlaceholderV2({ path }: { path: string }) {
  const config =
    PLACEHOLDER_MAP[path] || {
      icon: Wrench,
      title: 'Workspace',
      body: 'This section is being prepared.',
      eta: 'Comes online soon',
    }
  const Icon = config.icon
  return (
    <div className="v2-fade-in">
      <EmptyStateV2
        icon={Icon}
        title={config.title}
        body={`${config.body} ${config.eta}.`}
        actionLabel="Back to dashboard"
        onAction={() => navigateV2('/client-v2/dashboard')}
      />
    </div>
  )
}

export const currentLabelFor = (path: string) => ROUTE_LABELS[path] || 'Dashboard'