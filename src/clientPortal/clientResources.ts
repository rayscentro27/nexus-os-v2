export interface ClientResourceRecommendation {
  title: string
  category: string
  description: string
  ctaLabel: string
  href?: string
  route?: string
  placement: string
  requiresApproval: boolean
  clientVisible: boolean
  partnerDisclosure: string
}

const resources: ClientResourceRecommendation[] = [
  {
    title: 'Credit Monitoring Options',
    category: 'Credit Monitoring',
    description: 'Compare monitoring tools and upload a recent report while secure connection support is being prepared.',
    ctaLabel: 'View monitoring resources',
    route: '/client/resources?category=credit-monitoring',
    placement: 'credit-health',
    requiresApproval: false,
    clientVisible: true,
    partnerDisclosure: 'Some tools may be partner resources. Choose what fits your situation.',
  },
  {
    title: 'Business Banking Starter Options',
    category: 'Business Banking',
    description: 'Review business banking options that can help document cash flow and strengthen readiness.',
    ctaLabel: 'View banking resources',
    route: '/client/resources?category=business-banking',
    placement: 'funding-readiness',
    requiresApproval: false,
    clientVisible: true,
    partnerDisclosure: 'Recommendations are educational and do not open an account for you.',
  },
  {
    title: 'Business Credit Builder Resources',
    category: 'Business Credit Builder',
    description: 'Learn how business credit profiles and trade lines support funding readiness.',
    ctaLabel: 'View credit builder tools',
    route: '/client/resources?category=business-credit-builder',
    placement: 'business-setup',
    requiresApproval: false,
    clientVisible: true,
    partnerDisclosure: 'Tools are optional and should be reviewed before use.',
  },
  {
    title: 'DUNS / Business Profile Setup',
    category: 'DUNS / Business Profile',
    description: 'Get help understanding DUNS and business profile setup requirements.',
    ctaLabel: 'View setup resources',
    route: '/client/resources?category=duns-business-profile',
    placement: 'business-setup',
    requiresApproval: false,
    clientVisible: true,
    partnerDisclosure: 'No profile is created automatically.',
  },
  {
    title: 'EIN / Entity Setup Help',
    category: 'EIN / Entity Setup',
    description: 'Review steps and support options for EIN and entity setup without entering a full EIN.',
    ctaLabel: 'View entity resources',
    route: '/client/resources?category=ein-entity-setup',
    placement: 'profile',
    requiresApproval: false,
    clientVisible: true,
    partnerDisclosure: 'Setup help may involve third-party resources; review before proceeding.',
  },
  {
    title: 'Funding Education Library',
    category: 'Funding Education',
    description: 'Understand readiness, required documents, and what GoClear reviews before funding steps.',
    ctaLabel: 'View funding education',
    route: '/client/resources?category=funding-education',
    placement: 'funding-readiness',
    requiresApproval: false,
    clientVisible: true,
    partnerDisclosure: 'Educational resource only; no funding decision is made here.',
  },
  {
    title: 'Document Prep Checklist',
    category: 'Document Prep',
    description: 'Prepare IDs, address proof, bank statements, tax returns, and business records for review.',
    ctaLabel: 'View document prep',
    route: '/client/resources?category=document-prep',
    placement: 'documents',
    requiresApproval: false,
    clientVisible: true,
    partnerDisclosure: 'Document prep resources are optional.',
  },
  {
    title: 'Credit Repair Support',
    category: 'Credit Repair Support',
    description: 'Learn how dispute review, draft letters, and DocuPost approval gates work.',
    ctaLabel: 'View credit repair support',
    route: '/client/resources?category=credit-repair-support',
    placement: 'credit-repair',
    requiresApproval: true,
    clientVisible: true,
    partnerDisclosure: 'No dispute letter is mailed without approval.',
  },
]

export function getClientResources(context?: { category?: string; placement?: string; limit?: number }): ClientResourceRecommendation[] {
  const filtered = resources.filter(resource => {
    if (context?.category && resource.category.toLowerCase() !== context.category.toLowerCase()) return false
    if (context?.placement && resource.placement !== context.placement) return false
    return resource.clientVisible
  })
  return filtered.slice(0, context?.limit || filtered.length)
}

export function getClientResourceByCategory(category: string): ClientResourceRecommendation | undefined {
  return resources.find(resource => resource.category.toLowerCase() === category.toLowerCase())
}
