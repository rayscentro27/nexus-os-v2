export interface GuidanceItem {
  id: string
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  category: string
}

export function generateClientGuidance(statuses: {
  creditReportUploaded?: boolean
  addressVerified?: boolean
  identityVerified?: boolean
  utilizationHigh?: boolean
  negativeItemsIdentified?: boolean
  businessBankAccount?: boolean
  revenueDocuments?: boolean
  documentsComplete?: boolean
  adminReviewRequired?: boolean
  readinessScore?: number
  profileIncomplete?: boolean
}): GuidanceItem[] {
  const items: GuidanceItem[] = []
  const s = statuses

  if (s.profileIncomplete) {
    items.push({
      id: 'complete-profile',
      title: 'Complete Profile & Business Info',
      description: 'Fill out your profile and business information to improve your readiness score.',
      priority: 'high',
      category: 'profile',
    })
  }

  if (!s.creditReportUploaded) {
    items.push({
      id: 'upload-credit-report',
      title: 'Upload your credit report',
      description: 'Upload a current credit report to begin the readiness review process.',
      priority: 'high',
      category: 'documents',
    })
  }

  if (!s.addressVerified) {
    items.push({
      id: 'verify-address',
      title: 'Upload proof of address',
      description: 'A recent utility bill or bank statement showing your current address.',
      priority: 'high',
      category: 'documents',
    })
  }

  if (!s.identityVerified) {
    items.push({
      id: 'verify-identity',
      title: 'Verify your identity',
      description: 'Upload a government-issued ID to complete identity verification.',
      priority: 'high',
      category: 'documents',
    })
  }

  if (s.utilizationHigh) {
    items.push({
      id: 'reduce-utilization',
      title: 'Reduce credit utilization',
      description: 'Keep revolving credit utilization below 30% to improve funding readiness.',
      priority: 'medium',
      category: 'credit',
    })
  }

  if (s.negativeItemsIdentified) {
    items.push({
      id: 'review-negative-items',
      title: 'Choose items to challenge',
      description: 'Tell Clyde which negative items you want challenged so Nexus can prepare dispute options for GoClear review.',
      priority: 'medium',
      category: 'credit',
    })
  }

  if (!s.businessBankAccount) {
    items.push({
      id: 'open-business-bank',
      title: 'Open a business bank account',
      description: 'A business banking relationship supports your funding readiness profile.',
      priority: 'high',
      category: 'business',
    })
  }

  if (!s.revenueDocuments) {
    items.push({
      id: 'upload-revenue-docs',
      title: 'Upload revenue documentation',
      description: 'Provide revenue summary or bank statements to support your funding readiness.',
      priority: 'medium',
      category: 'business',
    })
  }

  if (s.adminReviewRequired) {
    items.push({
      id: 'admin-review',
      title: 'Specialist review required',
      description: 'Drafts and dispute options still need GoClear specialist review before client approval or mailing.',
      priority: 'low',
      category: 'status',
    })
  }

  if (s.creditReportUploaded && s.negativeItemsIdentified) {
    items.push({
      id: 'prepare-dispute-options',
      title: 'Prepare dispute options',
      description: 'Choose the reason an item should be removed or corrected; Clyde can package options without auto-sending anything.',
      priority: 'medium',
      category: 'credit',
    })
  }

  if (s.readinessScore !== undefined && s.readinessScore < 50) {
    items.push({
      id: 'improve-readiness',
      title: 'Focus on top blockers',
      description: 'Complete the highest-priority items first to improve your readiness score.',
      priority: 'high',
      category: 'status',
    })
  }

  return items.sort((a, b) => {
    const p = { high: 0, medium: 1, low: 2 }
    return p[a.priority] - p[b.priority]
  })
}
