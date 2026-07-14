export const NEXUS_POSITIONING = {
  productName: 'Nexus Funding Readiness',
  shortDescription: 'Nexus provides education, organization tools, credit and business profile workflows, and funding-readiness guidance. It does not guarantee credit score increases, item removals, or funding approval.',
  approvedTerms: ['Funding Readiness', 'Credit Profile', 'Business Profile', 'Tier 1 Funding Prep', 'Tier 2 Funding Prep', 'Credit Report Review Tools', 'Dispute Letter Tools', 'Profile Optimization', 'Utilization Strategy', 'Business Setup Guidance', 'GoClear Review', 'Recommended Resources', 'Partner Resources', 'Documents Vault'],
  restrictedTerms: ['credit repair company', 'guaranteed deletion', 'guaranteed score increase', 'guaranteed funding', 'guaranteed approval', 'we remove negative items', 'we repair your credit', 'credit repair experts'],
  disclaimers: {
    core: 'Nexus provides education, organization tools, and funding-readiness workflows. It does not guarantee credit score increases, item removals, or funding approval.',
    disputeTools: 'Credit report review and draft dispute tools help clients organize and prepare information concerning items that may be inaccurate, outdated, duplicated, unfamiliar, incomplete, or unverifiable. Final action remains the client’s choice.',
    funding: 'Funding readiness does not guarantee approval. Lenders make final decisions based on their own underwriting criteria.',
    draftLetter: 'Draft preview only. This document requires review and approval before use. Nexus does not guarantee deletion, a credit score change, or a specific reporting outcome.',
  },
  workflowLabels: { creditProfile: 'Credit Profile Optimization', creditReportReview: 'Credit Report Review Tools', disputeLetterTool: 'Dispute Letter Tool', adminReview: 'Credit & Funding Readiness Review', reviewQueue: 'Review Queue', profileCases: 'Profile Review Cases', reportAnalysis: 'Report Analysis', reportItems: 'Report Items', draftLetters: 'Draft Letters', mailQueue: 'Mail Queue' },
} as const
