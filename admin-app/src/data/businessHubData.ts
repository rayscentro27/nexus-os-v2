import {
  FormalHandoffItem,
  OpportunityItem,
  BankabilityChecklistItem,
  NAICSGovernanceProfile,
  FundingCaseItem,
  FundingProductBankItem
} from '../types';

// ============================================================================
// 1. CANONICAL FORMAL HANDOFFS
// ============================================================================
export const INITIAL_FORMAL_HANDOFFS: FormalHandoffItem[] = [
  {
    id: 'hnd-001',
    from: 'Research',
    to: 'Atlas',
    project: 'B2B Compliance Intelligence API (FinTech)',
    status: 'HANDED OFF',
    nextAction: 'Atlas to finalize lowest-cost entry model and target client pricing tier',
    age: '2h ago',
    departmentOwner: 'Atlas (Commercial)'
  },
  {
    id: 'hnd-002',
    from: 'Atlas',
    to: 'Finance',
    project: 'Automated Medical Billing Audit Feeder',
    status: 'IN REVIEW',
    nextAction: 'Finance checking unit economics and initial gross margin sensitivity',
    age: '4h ago',
    departmentOwner: 'Finance (Treasury)'
  },
  {
    id: 'hnd-003',
    from: 'Atlas',
    to: 'Clyde',
    project: 'Specialty Equipment Leasing Syndication Desk',
    status: 'IN REVIEW',
    nextAction: 'Clyde running non-binary product fit for equipment vendor line ($150k)',
    age: '5h ago',
    departmentOwner: 'Clyde (Funding)'
  },
  {
    id: 'hnd-004',
    from: 'Business Creation',
    to: 'Clyde',
    project: 'Apex Logistics Operations LLC',
    status: 'READY FOR HANDOFF',
    nextAction: 'Tradeline maturation verified (Tier 2 Net-30); package Tier 3 revolving line',
    age: '1d ago',
    departmentOwner: 'Clyde (Funding)'
  },
  {
    id: 'hnd-005',
    from: 'Atlas',
    to: 'Ray',
    project: 'SaaS Contract Intelligence Copilot (White-Label)',
    status: 'READY FOR HANDOFF',
    nextAction: 'Strategic authorization required by Ray to execute reseller agreement',
    age: '3h ago',
    departmentOwner: 'Ray (Strategic Authority)'
  },
  {
    id: 'hnd-006',
    from: 'Clyde',
    to: 'Client',
    project: 'GoClear Institutional Client 104 (Apex Freight)',
    status: 'IN REVIEW',
    nextAction: 'Waiting on client signature on Chase Business Complete checking verification',
    age: '6h ago',
    departmentOwner: 'Client (GoClear Portal)'
  },
  {
    id: 'hnd-007',
    from: 'Clyde',
    to: 'Ray',
    project: 'Nexus Growth Facility ($250k Unsecured Line)',
    status: 'READY FOR HANDOFF',
    nextAction: 'Ray strategic review on PG requirement and terms vs zero-debt runway',
    age: '1h ago',
    departmentOwner: 'Ray (Strategic Authority)'
  }
];

// ============================================================================
// 2. ATLAS OPPORTUNITIES
// ============================================================================
export const INITIAL_OPPORTUNITIES: OpportunityItem[] = [
  {
    id: 'opp-101',
    opportunity: 'Automated Medical Billing Pre-Audit & Coding Scanner',
    source: 'SEC EDGAR 10-K R&D Disclosures + CMS Regulatory Digest',
    researchCompleteness: 94,
    notebook: 'NB-RESEARCH-HEALTHCARE-882',
    currentOwner: 'Atlas (Business Opportunities)',
    businessModel: 'B2B SaaS + Per-Audit RevShare ($1.80 per audited claim)',
    customer: 'Independent Billing Services & Multi-Provider Medical Clinics',
    problem: '32% initial claim denial rate due to minor ICD-10 cross-walk errors costing $85k/yr per practice',
    revenueModel: '$499/mo base platform + $0.85 per high-complexity pre-cleared claim batch',
    demandEvidence: 'Validated across 14 independent clinic managers; 3 letters of intent signed in sandbox',
    entryTier: 'Tier 1 (Fast Low-Cap)',
    costFreeOption: 'Partner with existing clearinghouse via open HL7/FHIR API with zero infrastructure upfront',
    capitalRequired: '$4,500 initial setup / serverless infrastructure',
    businessHubReview: 'PASSED',
    financeReview: 'CLEARED',
    fundingReview: 'SELF_FUNDABLE',
    currentState: 'FINAL_SYNTHESIS',
    nextAction: 'Synthesize final go-to-market proposal packet for Ray strategic authorization',
    atlasRecommendation: {
      whyThisCouldWork: [
        'Massive regulatory tailwind: CMS 2026 mandate requires automated prior authorization audit logs.',
        'Immediate ROI for buyer: Eliminates 12 hours/week of manual billing disputes in the first 14 days.',
        'High gross retention (>95%) once integrated into practice management billing workflows.'
      ],
      whatNexusAlreadyHas: [
        'Pre-trained medical NLP rules in Development / Labs extraction suite.',
        'GoClear secure tenant data enclave with HIPAA compliance posture.'
      ],
      affiliateWhiteLabelOptions: 'Can white-label Clearinghouse Gateway Pro API under GoClear Medical branding.',
      lowestCostEntry: 'Deploy serverless rule parser; offer 14-day free trial on first 250 claims with zero upfront licensing.',
      marketingApproach: 'Direct outreach to outsourced billing agencies handling 10-50 clinic accounts via LinkedIn InMail.',
      capitalRequirement: '$4,500 bootstrap capital (zero external debt required).',
      risks: [
        'HIPAA Business Associate Agreement (BAA) execution required before ingestion.',
        'Legacy EHR integration friction on older on-premise clinic systems.'
      ],
      recommendedAction: 'RECOMMENDATION: Submit to Ray for final authorization to launch closed pilot.'
    }
  },
  {
    id: 'opp-102',
    opportunity: 'B2B Compliance Intelligence API (KYB / Anti-Fraud)',
    source: 'Federal Trade Commission Enforcement Actions & FinCEN Advisories',
    researchCompleteness: 88,
    notebook: 'NB-RESEARCH-FINTECH-612',
    currentOwner: 'Atlas (Business Opportunities)',
    businessModel: 'Usage-based REST API + Tiered Annual Contract',
    customer: 'Regional Community Banks, Credit Unions, and Alternative B2B Lenders',
    problem: 'Manual Secretary of State & beneficial ownership verification takes 48 hours per commercial applicant',
    revenueModel: '$2.50 per automated entity verification query; $1,200/mo minimum volume commitment',
    demandEvidence: 'FinCEN BOI regulations expanding compliance burden across 3.2M registered businesses',
    entryTier: 'Tier 2 (Growth Medium-Cap)',
    costFreeOption: 'White-label upstream public records aggregator with 35% margin reseller agreement',
    capitalRequired: '$18,000 for SOC-2 Type 1 audit & dedicated proxy infrastructure',
    businessHubReview: 'PASSED',
    financeReview: 'CLEARED',
    fundingReview: 'CLYDE_REVIEW',
    currentState: 'FUNDING_REVIEW',
    nextAction: 'Clyde evaluating non-dilutive FinTech innovation grant vs Tier 2 vendor line ($25k)',
    atlasRecommendation: {
      whyThisCouldWork: [
        'Direct synergy with GoClear tenant onboarding engine and NAICS verification protocols.',
        'High contractual switching costs once embedded in underwriting workflows.',
        'Strong margin profile (78% gross margin on API calls).'
      ],
      whatNexusAlreadyHas: [
        'Universal entity search scraping pipelines built in Research department.',
        'Established multi-tenant database infrastructure in Supabase.'
      ],
      affiliateWhiteLabelOptions: 'Resell OpenSanctions & LexisNexis commercial risk data under Nexus API wraps.',
      lowestCostEntry: 'Start with Secretary of State real-time scraper before licensing enterprise data feeds.',
      marketingApproach: 'Target BSA/AML compliance officers at regional credit unions with free compliance scorecards.',
      capitalRequirement: '$18,000 working capital for SOC-2 Type 1 audit and legal review.',
      risks: [
        'State-level registry rate-limiting without proxy rotation.',
        'Liability clauses in enterprise client master service agreements (MSAs).'
      ],
      recommendedAction: 'RECOMMENDATION: Route to Clyde for $25k non-PG vendor line structuring.'
    }
  },
  {
    id: 'opp-103',
    opportunity: 'Commercial Fleet Maintenance Telematics Dashboard',
    source: 'Fleet Management Weekly + DOT Commercial Motor Vehicle Data',
    researchCompleteness: 76,
    notebook: 'NB-RESEARCH-FLEET-340',
    currentOwner: 'Atlas (Business Opportunities)',
    businessModel: 'Per-Vehicle Hardware Bundle + SaaS Telematics Subscription',
    customer: 'Last-Mile Delivery Contractors & Regional Courier Services (15-60 vans)',
    problem: 'Unscheduled maintenance downtime costs $840/day per van; OBD-II fault codes ignored until engine failure',
    revenueModel: '$39/month per vehicle subscription + $140 one-time plug-and-play OBD-II sensor markup',
    demandEvidence: '18 regional courier businesses contacted; 11 reported severe downtime in past 90 days',
    entryTier: 'Tier 2 (Growth Medium-Cap)',
    costFreeOption: 'Drop-ship pre-configured Teltonika OBD hardware; software-only monthly recurring subscription',
    capitalRequired: '$12,000 inventory reserve for 100 telematics units',
    businessHubReview: 'PASSED',
    financeReview: 'CLEARED',
    fundingReview: 'DEBT_SUITABLE',
    currentState: 'BUSINESS_PLAN_BUILD',
    nextAction: 'Atlas compiling 12-month cashflow forecast and distributor drop-ship contract terms',
    atlasRecommendation: {
      whyThisCouldWork: [
        'High recurring revenue with low churn; fleet operators rarely switch telematics vendors.',
        'Predictive maintenance rules can be continuously generated by Nexus Systems department.'
      ],
      whatNexusAlreadyHas: [
        'Real-time IoT telemetry chart widgets and alerts adapted from Trading Engine.',
        'Existing client portal infrastructure in GoClear.'
      ],
      affiliateWhiteLabelOptions: 'White-label Geotab or Teltonika firmware with custom Nexus OS dashboard.',
      lowestCostEntry: 'Require upfront hardware payment from fleet customer to eliminate inventory risk.',
      marketingApproach: 'Local fleet yard visits and free OBD diagnostics report for fleet managers.',
      capitalRequirement: '$12,000 for pilot hardware safety stock.',
      risks: [
        'Cellular SIM connectivity latency in rural areas.',
        'Hardware return / warranty fulfillment logistics.'
      ],
      recommendedAction: 'RECOMMENDATION: Atlas to complete business plan build and hand off to Finance.'
    }
  },
  {
    id: 'opp-104',
    opportunity: 'Local Government RFP & Grant Matching Notification Feed',
    source: 'USASpending.gov + SAM.gov API + State Procurement Portals',
    researchCompleteness: 91,
    notebook: 'NB-RESEARCH-GRANTS-109',
    currentOwner: 'Atlas (Business Opportunities)',
    businessModel: 'Niche B2B Subscription ($149/mo - $499/mo)',
    customer: 'Small-to-Mid Sized Government Contractors, DBE/MBE/WBE Certified Enterprises',
    problem: 'Small contractors miss 80% of local municipal RFPs due to fragmentation across 3,000+ county portals',
    revenueModel: '$199/mo per category feed + 1.5% success fee on won sub-contracts (optional)',
    demandEvidence: 'High search volume on "local municipal bidding alerts"; 24 survey respondents ready to buy',
    entryTier: 'Tier 1 (Fast Low-Cap)',
    costFreeOption: 'Build Python RSS/Scraper feeder entirely within Development / Labs with zero external API costs',
    capitalRequired: '$1,200 initial marketing & scraper proxy budget',
    businessHubReview: 'PASSED',
    financeReview: 'CLEARED',
    fundingReview: 'SELF_FUNDABLE',
    currentState: 'RAY_REVIEW_REQUIRED',
    nextAction: 'Waiting on Ray final strategic authorization to launch public landing page and collect deposits',
    atlasRecommendation: {
      whyThisCouldWork: [
        'Extremely low ongoing operating overhead (<$80/mo in proxy costs).',
        'Direct synergies with Nexus Clients and DBE-certified vendors.',
        'Clear, immediate customer ROI: one won bid pays for 10 years of subscription.'
      ],
      whatNexusAlreadyHas: [
        'Research ingestion workers already scraping SAM.gov and state registries daily.',
        'Automated document summarization engine in Nova and Documents pages.'
      ],
      affiliateWhiteLabelOptions: 'Offer co-branded portal access to regional Small Business Development Centers (SBDCs).',
      lowestCostEntry: 'Curate daily email digests manually before deploying fully automated tenant alerts.',
      marketingApproach: 'Target active SAM.gov registrants via public contact emails with curated bid samples.',
      capitalRequirement: '$1,200 bootstrap capital.',
      risks: [
        'Scraper maintenance when municipal portal layouts update.',
        'Procurement officer contact verification.'
      ],
      recommendedAction: 'RECOMMENDATION: Awaiting Ray approval to greenlight production go-to-market.'
    }
  }
];

// ============================================================================
// 3. BUSINESS CREATION / BANKABILITY CHECKLIST
// ============================================================================
export const INITIAL_BANKABILITY_CHECKLIST: BankabilityChecklistItem[] = [
  {
    key: 'entity',
    label: 'Legal Entity Formation',
    category: 'Corporate Identity',
    status: 'VERIFIED',
    detail: 'LLC / C-Corp filed with Secretary of State; Articles of Organization stamped',
    lastChecked: 'Today'
  },
  {
    key: 'good_standing',
    label: 'Certificate of Good Standing',
    category: 'Corporate Identity',
    status: 'VERIFIED',
    detail: 'Active state status verified via SoS live registry API; annual franchise report current',
    lastChecked: 'Today'
  },
  {
    key: 'ein',
    label: 'IRS EIN Confirmation (CP-575)',
    category: 'Corporate Identity',
    status: 'VERIFIED',
    detail: 'Federal EIN issued; name and address matches Articles of Organization verbatim',
    lastChecked: 'Oct 02, 2026'
  },
  {
    key: 'business_address',
    label: 'Commercial Physical Business Address',
    category: 'Corporate Identity',
    status: 'VERIFIED',
    detail: 'Dedicated commercial suite / executive office; USPS CMRA flagged as commercial (no P.O. Box)',
    lastChecked: 'Sep 28, 2026'
  },
  {
    key: 'domain',
    label: 'Dedicated Top-Level Domain (.com)',
    category: 'Online Presence',
    status: 'VERIFIED',
    detail: 'Domain registered under corporate name, SSL certificate active, WHOIS privacy enabled',
    lastChecked: 'Today'
  },
  {
    key: 'website',
    label: 'Professional Corporate Website',
    category: 'Online Presence',
    status: 'VERIFIED',
    detail: 'Fully responsive, clear product offerings, terms of service, privacy policy, matching contact info',
    lastChecked: 'Yesterday'
  },
  {
    key: 'professional_email',
    label: 'Corporate Domain Email (Google Workspace)',
    category: 'Online Presence',
    status: 'VERIFIED',
    detail: 'DKIM, SPF, and DMARC records fully authenticated on business domain; no free webmail',
    lastChecked: 'Today'
  },
  {
    key: 'business_phone',
    label: 'Dedicated Business Phone & 411 Listing',
    category: 'Corporate Identity',
    status: 'VERIFIED',
    detail: 'Local landline/VoIP with professional auto-attendant; listed in National 411 Directory',
    lastChecked: 'Oct 01, 2026'
  },
  {
    key: 'bank_account',
    label: 'Business Checking Account',
    category: 'Banking & Treasury',
    status: 'VERIFIED',
    detail: 'Primary commercial checking opened with Tier 1 institution (Chase / BofA / Wells)',
    lastChecked: 'Today'
  },
  {
    key: 'bank_name',
    label: 'Depository Institution Status',
    category: 'Banking & Treasury',
    status: 'VERIFIED',
    detail: 'JPMorgan Chase Commercial Banking · Dedicated treasury management relationship',
    lastChecked: 'Today'
  },
  {
    key: 'account_age',
    label: 'Depository Relationship Age',
    category: 'Banking & Treasury',
    status: 'VERIFIED',
    detail: '9 months active seasoning (6+ months threshold cleared for institutional tiering)',
    lastChecked: 'Today'
  },
  {
    key: 'balances',
    label: 'Average Daily Balance (ADB)',
    category: 'Banking & Treasury',
    status: 'VERIFIED',
    detail: 'Maintained above $15,000 threshold ($28,450 average 90-day balance)',
    lastChecked: 'Today'
  },
  {
    key: 'deposit_activity',
    label: 'Monthly Deposit Frequency & Flow',
    category: 'Banking & Treasury',
    status: 'VERIFIED',
    detail: '12+ recurring commercial deposits per month; zero Non-Sufficient Funds (NSF) or overdrafts',
    lastChecked: 'Today'
  },
  {
    key: 'naics',
    label: 'NAICS & SIC Classification Alignment',
    category: 'Filings & Compliance',
    status: 'ACTION_REQUIRED',
    detail: 'Classification audit active: Confirming primary revenue alignment vs high-risk lender restriction lists',
    notes: 'See NAICS Governance Engine below for defensible multi-code analysis',
    lastChecked: 'Today'
  },
  {
    key: 'duns',
    label: 'Dun & Bradstreet DUNS Number',
    category: 'Filings & Compliance',
    status: 'VERIFIED',
    detail: 'DUNS # 08-142-9901 active; D&B eUpdate profile verified and matching Secretary of State',
    lastChecked: 'Sep 29, 2026'
  },
  {
    key: 'google_business',
    label: 'Google Business Profile & Citations',
    category: 'Online Presence',
    status: 'VERIFIED',
    detail: 'Verified via video postcard; Yelp, Bing Places, and Chamber of Commerce directory synced',
    lastChecked: 'Oct 03, 2026'
  },
  {
    key: 'business_plan',
    label: 'Comprehensive 3-Year Business Plan',
    category: 'Filings & Compliance',
    status: 'VERIFIED',
    detail: 'Executive summary, pro-forma financials, marketing plan, and use of funds documentation archived',
    lastChecked: 'Oct 04, 2026'
  },
  {
    key: 'licensing',
    label: 'Municipal & State Licenses',
    category: 'Filings & Compliance',
    status: 'VERIFIED',
    detail: 'County general business license current; professional state regulatory clearance on file',
    lastChecked: 'Sep 20, 2026'
  },
  {
    key: 'business_credit_file',
    label: 'Experian Commercial & Equifax Business File',
    category: 'Credit File & Tradelines',
    status: 'VERIFIED',
    detail: 'Experian Intelliscore Plus: 88/100 · Equifax Business Credit Risk: Low Risk rating',
    lastChecked: 'Oct 02, 2026'
  },
  {
    key: 'tradelines',
    label: 'Reporting Commercial Tradelines',
    category: 'Credit File & Tradelines',
    status: 'VERIFIED',
    detail: '7 reporting tradelines on D&B PAYDEX (Score: 80); 5 tradelines reporting to Experian Business',
    lastChecked: 'Oct 03, 2026'
  },
  {
    key: 'vendor_accounts',
    label: 'Tier 1 & Tier 2 Vendor Accounts',
    category: 'Credit File & Tradelines',
    status: 'VERIFIED',
    detail: 'Uline Net-30 ($2,500), Grainger Net-30 ($2,000), Quill ($1,500), Nav Prime ($500/mo line)',
    lastChecked: 'Oct 01, 2026'
  },
  {
    key: 'personal_credit_factor',
    label: 'Personal Credit Readiness Tier (Readiness Factor Only)',
    category: 'Personal Credit Factor',
    status: 'NOT_YET_GOVERNED',
    detail: 'Founder Personal FICO: 724 (Experian/Equifax auto-score range). Serves as eligibility check only.',
    notes: 'GOVERNANCE NOTICE: Personal credit repair is NOT yet a governed Nexus workflow. Nexus identifies personal credit score as an underwriting readiness factor but does NOT perform automated credit repair or dispute filings.',
    lastChecked: 'Oct 05, 2026'
  }
];

// ============================================================================
// 4. NAICS GOVERNANCE PROFILES (TRUTHFUL CLASSIFICATION FIRST)
// ============================================================================
export const INITIAL_NAICS_GOVERNANCE: NAICSGovernanceProfile[] = [
  {
    id: 'naics-001',
    entityName: 'Apex Data Intelligence LLC',
    currentNaics: '541511 - Custom Computer Programming Services',
    actualPrimaryBusinessActivity: 'B2B Software Development, Data Pipeline Architecture, and Hosted Analytics Dashboards',
    truthfullyDefensibleAlternatives: [
      {
        code: '541512',
        title: 'Computer Systems Design Services',
        defensibilityScore: 98,
        fundingSuitability: 'VERY HIGH (Tier 1 Prime Lenders, SBA Preferred, Low Loss Rates)',
        description: 'Accurately describes designing full turnkey data platforms and multi-tenant architectures for commercial clients.'
      },
      {
        code: '518210',
        title: 'Computing Infrastructure, Data Processing, and Web Hosting Services',
        defensibilityScore: 92,
        fundingSuitability: 'HIGH (Tech Infrastructure underwriting, strong equipment lease affinity)',
        description: 'Reflects revenue generated from hosting client analytics portals and managing automated data streams.'
      },
      {
        code: '541611',
        title: 'Administrative Management and General Management Consulting',
        defensibilityScore: 74,
        fundingSuitability: 'MODERATE (Can trigger higher scrutiny if mischaracterized as general consulting)',
        description: 'Applies to strategic workflow advisory; however, software development remains the dominant revenue driver.'
      }
    ],
    recommendedNaics: '541512 - Computer Systems Design Services',
    whyItFits: 'Matches 82% of current commercial contract scopes (custom systems design + data pipeline integration). Accurately conveys technical engineering depth while opening institutional credit lines without high-risk exclusions.',
    fundingImplication: 'Unlocks Tier 1 bank lines (Chase, Bank of America, U.S. Bank) with 0% introductory terms and SBA 7(a) small loan programs without triggering restricted coding flags.',
    complianceConcerns: 'Ensure all tax filings (Form 1065 / 1120-S) and state annual reports update to 541512 concurrently so underwriters find 100% cross-bureau concordance.',
    classificationIntegrity: 'ACCURATE_CLASSIFICATION_FIRST'
  },
  {
    id: 'naics-002',
    entityName: 'Nexus Global Logistics Solutions',
    currentNaics: '488510 - Freight Transportation Arrangement',
    actualPrimaryBusinessActivity: 'Supply Chain Software, Dispatch Coordination, and Route Optimization Advisory',
    truthfullyDefensibleAlternatives: [
      {
        code: '541614',
        title: 'Process, Physical Distribution, and Logistics Consulting Services',
        defensibilityScore: 95,
        fundingSuitability: 'HIGH (Management advisory tier with clean non-asset credit appetite)',
        description: 'Truthfully captures software advisory and supply chain route audits without implying ownership of physical rolling stock.'
      },
      {
        code: '541519',
        title: 'Other Computer Related Services',
        defensibilityScore: 89,
        fundingSuitability: 'HIGH (Technology sector tiering with low lender default history)',
        description: 'Accurately covers dispatch algorithm licensing and automated carrier portal software modules.'
      }
    ],
    recommendedNaics: '541614 - Logistics & Physical Distribution Consulting Services',
    whyItFits: 'The entity provides route optimization intelligence and dispatch technology rather than acting as a liability-bearing freight forwarder. Accurately reflects lack of cargo risk.',
    fundingImplication: 'Dramatically reduces commercial line underwriting friction; freight brokers often face high bonding requirements and merchant advance predatory lending traps.',
    complianceConcerns: 'Do not misrepresent if the entity enters physical brokerage agreements or takes legal custody of bills of lading.',
    classificationIntegrity: 'ACCURATE_CLASSIFICATION_FIRST'
  }
];

// ============================================================================
// 5. BUSINESS FUNDING / CLYDE RECOMMENDATIONS (NON-BINARY MATCHING)
// ============================================================================
export const INITIAL_FUNDING_CASES: FundingCaseItem[] = [
  // Lane 1: CLIENT / GOCLEAR
  {
    id: 'fnd-c-001',
    lane: 'CLIENT / GOCLEAR',
    lenderProgram: 'Chase Business Banking',
    product: 'Chase Ink Business Cash / Premier Line',
    productCategory: 'Revolving Card',
    potentialAmount: '$25,000 - $50,000',
    currentFit: 'CURRENT MATCH',
    requirementsMet: [
      '2+ years time in business or established legal entity with seasoned EIN',
      'Average daily checking balance > $12,000',
      'Clean deposit history with zero returned items',
      'Good standing certificate verified'
    ],
    requirementsMissing: [],
    improvableRequirements: [
      'Maintaining balance above $25k for next 30 days increases initial auto-approval limit by 40%'
    ],
    exactNextAction: 'Submit verified Chase Ink application via direct banker relationship with supporting Q3 financials',
    milestone: 'Milestone: Prime Tier 1 Revolving Line Opening',
    alternativeOptions: ['U.S. Bank Business Triple Cash ($20,000)', 'American Express Blue Business Cash ($30,000)'],
    evidenceStatus: 'VERIFIED',
    lastVerifiedDate: 'Oct 04, 2026',
    decisionAuthority: 'WAITING ON CLIENT',
    recommendationNote: 'Clyde recommendation: Current requirements fully met. Client review and signature required to proceed.'
  },
  {
    id: 'fnd-c-002',
    lane: 'CLIENT / GOCLEAR',
    lenderProgram: 'National Bank of California / SBA Microloan Intermediary',
    product: 'SBA Community Advantage Microloan',
    productCategory: 'SBA 7(a)',
    potentialAmount: '$50,000 - $100,000',
    currentFit: 'NEAR MATCH',
    requirementsMet: [
      'Active commercial checking account',
      'Defensible NAICS code with low default history',
      'Clear corporate ownership structure'
    ],
    requirementsMissing: [
      'Trailing 6-month debt schedule breakdown required',
      'Updated 12-month projected cash flow statement'
    ],
    improvableRequirements: [
      'Finance department can generate standardized 12-month pro-forma within 24 hours'
    ],
    exactNextAction: 'Package Finance pro-forma cashflow workbook and schedule client review meeting',
    milestone: 'Milestone: Low-Interest Government-Backed Growth Capital',
    alternativeOptions: ['Accion Opportunity Fund Term Loan ($40,000)', 'Kiva 0% Community Loan ($15,000)'],
    evidenceStatus: 'CROSS-SUPPORTED',
    lastVerifiedDate: 'Oct 03, 2026',
    decisionAuthority: 'WAITING ON CLIENT',
    recommendationNote: 'Clyde recommendation: Strong candidate once cash flow schedule is attached. Waiting on client confirmation.'
  },
  {
    id: 'fnd-c-003',
    lane: 'CLIENT / GOCLEAR',
    lenderProgram: 'Dell Financial Services / Cisco Capital',
    product: 'Server & Workstation Equipment Line of Credit',
    productCategory: 'Equipment Financing',
    potentialAmount: '$35,000',
    currentFit: 'PATH TO ELIGIBILITY',
    requirementsMet: [
      'Valid DUNS number with active D&B profile',
      'Commercial corporate address'
    ],
    requirementsMissing: [
      'D&B PAYDEX score currently based on 3 tradelines; Dell prefers 4+ reporting tradelines'
    ],
    improvableRequirements: [
      'Wait 18 days for Grainger Tier 1 tradeline to report on next monthly D&B sync'
    ],
    exactNextAction: 'Track next D&B cycle on Oct 22; trigger auto-application once 4th tradeline confirms',
    milestone: 'Milestone: Dedicated Tech Asset Equipment Financing',
    alternativeOptions: ['Balboa Capital Equipment Line', 'CIT Small Business Solutions'],
    evidenceStatus: 'SOURCE CLAIM',
    lastVerifiedDate: 'Oct 01, 2026',
    decisionAuthority: 'WAITING ON CLIENT',
    recommendationNote: 'Clyde recommendation: Path to eligibility clear. Maturation milestone projected Oct 22.'
  },
  {
    id: 'fnd-c-004',
    lane: 'CLIENT / GOCLEAR',
    lenderProgram: 'High-Volume Merchant Cash Advance (MCA) Aggregators',
    product: 'Daily ACH Revenue Advance',
    productCategory: 'Merchant Advance',
    potentialAmount: '$45,000',
    currentFit: 'NOT APPROPRIATE',
    requirementsMet: [
      'Monthly bank deposits > $20,000'
    ],
    requirementsMissing: [
      'Violates Nexus OS risk and financial governance principles'
    ],
    improvableRequirements: [],
    exactNextAction: 'Flag as predatory; exclude from client recommendations. Route to zero-APR bank alternatives.',
    milestone: 'Milestone: Risk Exclusion & Governance Enforcement',
    alternativeOptions: ['Revolving Bank Line', 'Equipment Sale-Leaseback'],
    evidenceStatus: 'VERIFIED',
    lastVerifiedDate: 'Oct 05, 2026',
    decisionAuthority: 'WAITING ON CLIENT',
    recommendationNote: 'Clyde recommendation: NOT APPROPRIATE. Factor rate of 1.38x creates destructive capital drain.'
  },

  // Lane 2: NEXUS / RAY
  {
    id: 'fnd-n-001',
    lane: 'NEXUS / RAY',
    lenderProgram: 'PNC Bank Commercial Treasury',
    product: 'Business Choice Unsecured Revolving Line of Credit',
    productCategory: 'Unsecured Line',
    potentialAmount: '$100,000 - $150,000',
    currentFit: 'CURRENT MATCH',
    requirementsMet: [
      'Full bankability checklist cleared (Entity, EIN, DUNS, SoS Good Standing)',
      'Experian Intelliscore Plus 88/100',
      'Depository relationship > 6 months with Tier 1 commercial balances',
      'Zero tax liens or adverse UCC filings'
    ],
    requirementsMissing: [],
    improvableRequirements: [
      'Option to submit with Ray personal guarantee for $150k vs no-PG option capped at $75k'
    ],
    exactNextAction: 'Submit underwriting package for Ray strategic review and decision on PG threshold',
    milestone: 'Milestone: Primary Operational Liquidity Buffer',
    alternativeOptions: ['Wells Fargo Prime Line ($100k)', 'Truist Business Line ($75k)'],
    evidenceStatus: 'VERIFIED',
    lastVerifiedDate: 'Today',
    decisionAuthority: 'WAITING ON RAY',
    recommendationNote: 'Clyde recommendation: Full requirements met. Ray review required to authorize submission.'
  },
  {
    id: 'fnd-n-002',
    lane: 'NEXUS / RAY',
    lenderProgram: 'SBA 7(a) Working Capital Express Desk',
    product: 'SBA Express Rapid Line',
    productCategory: 'SBA 7(a)',
    potentialAmount: '$250,000 - $350,000',
    currentFit: 'NEAR MATCH',
    requirementsMet: [
      'For-profit US operating enterprise',
      'Clean NAICS coding (541512 Computer Systems Design)',
      'Comprehensive 3-year financial model approved by Finance'
    ],
    requirementsMissing: [
      'Final Ray strategic sign-off on 10-year term amortization structure'
    ],
    improvableRequirements: [
      'Consolidating two minor vendor tradelines enhances debt-service coverage ratio (DSCR) to 1.85x'
    ],
    exactNextAction: 'Present term sheet comparison and covenants to Ray in Executive Briefing',
    milestone: 'Milestone: Enterprise Growth Capital Expansion',
    alternativeOptions: ['Live Oak Bank Tech Facility', 'First Citizens Bank SBA Desk'],
    evidenceStatus: 'CROSS-SUPPORTED',
    lastVerifiedDate: 'Oct 04, 2026',
    decisionAuthority: 'WAITING ON RAY',
    recommendationNote: 'Clyde recommendation: Highly advantageous 8.25% variable rate structure. Ready for Ray review.'
  },
  {
    id: 'fnd-n-003',
    lane: 'NEXUS / RAY',
    lenderProgram: 'NIST MEP / State Technology Innovation Commercialization Grant',
    product: 'Non-Dilutive SBIR Phase 0 / State Match Innovation Award',
    productCategory: 'Term Loan',
    potentialAmount: '$75,000 (Non-Dilutive Grant)',
    currentFit: 'ALTERNATIVE PRODUCT MATCH',
    requirementsMet: [
      'SAM.gov CAGE Code active',
      'Clean entity registration',
      'Technical innovation in automated compliance verified'
    ],
    requirementsMissing: [
      'Formal academic or research partnership letter required for fast-track'
    ],
    improvableRequirements: [
      'Atlas can draft partnership memo with regional university incubator'
    ],
    exactNextAction: 'Review grant submission window opening Nov 01; prepare draft narrative for Ray review',
    milestone: 'Milestone: 100% Non-Dilutive Public Capital Grant',
    alternativeOptions: ['State Economic Development Seed Fund', 'NSF Regional Innovation Engine'],
    evidenceStatus: 'RESEARCH REQUIRED',
    lastVerifiedDate: 'Oct 02, 2026',
    decisionAuthority: 'WAITING ON RAY',
    recommendationNote: 'Clyde recommendation: 0% cost of capital. Alternative non-dilutive product worthy of Ray evaluation.'
  },
  {
    id: 'fnd-n-004',
    lane: 'NEXUS / RAY',
    lenderProgram: 'Subordinated Mezzanine Venture Debt Syndicates',
    product: 'Warrant-Backed Venture Debt Line',
    productCategory: 'Term Loan',
    potentialAmount: '$500,000',
    currentFit: 'NOT APPROPRIATE',
    requirementsMet: [
      'Scalable recurring software architecture'
    ],
    requirementsMissing: [
      'Requires 2.5% equity warrant grant and board observer seat',
      'Rigorous covenants restricting software asset sales'
    ],
    improvableRequirements: [],
    exactNextAction: 'Reject proposal in Clyde register. Maintain 100% founder equity sovereignty for Ray.',
    milestone: 'Milestone: Equity Preservation & Strategic Autonomy',
    alternativeOptions: ['Unsecured Bank Revolver', 'Cash Flow Self-Funding'],
    evidenceStatus: 'VERIFIED',
    lastVerifiedDate: 'Oct 03, 2026',
    decisionAuthority: 'WAITING ON RAY',
    recommendationNote: 'Clyde recommendation: Strongly recommend REJECTION. High dilution risk contrary to Ray charter.'
  }
];

// ============================================================================
// 6. FUNDING PRODUCT BANK & KNOWLEDGE BANKS
// ============================================================================
export const INITIAL_FUNDING_PRODUCTS: FundingProductBankItem[] = [
  {
    id: 'fpb-001',
    lender: 'JPMorgan Chase',
    product: 'Chase Ink Business Unlimited',
    productType: 'Revolving Business Credit Card',
    limit: '$15,000 - $75,000',
    creditRequirements: '680+ FICO · Clean Personal & Business',
    bureaus: 'Experian Business + Experian Personal',
    timeInBusiness: '6+ months (New LLC eligible with depository)',
    revenue: '$50,000+ stated annual revenue',
    bankRelationship: 'Preferred: Active Chase business checking',
    geographicRestrictions: 'National (All 50 US States)',
    documentation: 'Stated income (Tax returns required if >$50k initial limit)',
    pgCollateral: 'Personal Guarantee required · No blanket UCC-1 lien',
    rateFees: '0% Intro APR for 12 months · 18.49% - 24.49% variable after',
    verificationStatus: 'ACTIVE',
    evidenceStatus: 'VERIFIED',
    lastVerified: 'Oct 04, 2026',
    nextRefresh: 'Nov 04, 2026'
  },
  {
    id: 'fpb-002',
    lender: 'PNC Bank',
    product: 'Business Choice Line of Credit',
    productType: 'Unsecured Revolving Line of Credit',
    limit: '$20,000 - $100,000',
    creditRequirements: '700+ FICO · D&B Paydex 75+',
    bureaus: 'Equifax Commercial + Experian Hard Pull',
    timeInBusiness: '2+ years preferred (1 year with strong balances)',
    revenue: '$100,000+ verifiable gross revenue',
    bankRelationship: 'Required: Depository relationship within 60 days',
    geographicRestrictions: 'PNC footprint states (East, Midwest, Southeast, Southwest)',
    documentation: '2 years business tax returns + 6 months bank statements',
    pgCollateral: 'PG required for limits >$50k · Unsecured (no specific asset lien)',
    rateFees: 'Prime + 1.75% to Prime + 4.50% · $175 annual renewal fee',
    verificationStatus: 'ACTIVE',
    evidenceStatus: 'VERIFIED',
    lastVerified: 'Oct 02, 2026',
    nextRefresh: 'Nov 02, 2026'
  },
  {
    id: 'fpb-003',
    lender: 'Live Oak Bank',
    product: 'SBA 7(a) Working Capital Express',
    productType: 'SBA 7(a) Working Capital',
    limit: '$50,000 - $350,000',
    creditRequirements: '680+ FICO · SBSS Score 155+',
    bureaus: 'All 3 personal bureaus + Dun & Bradstreet',
    timeInBusiness: '2+ years operating history',
    revenue: '$150,000+ verifiable revenue with positive cash flow',
    bankRelationship: 'Not required',
    geographicRestrictions: 'National (All 50 US States)',
    documentation: 'Full documentation: 3 yrs tax returns, debt schedule, P&L, balance sheet',
    pgCollateral: '20%+ owners must PG · Blanket business lien on assets',
    rateFees: 'Prime + 2.75% to Prime + 3.75% variable · 10-year term',
    verificationStatus: 'ACTIVE',
    evidenceStatus: 'CROSS-SUPPORTED',
    lastVerified: 'Sep 29, 2026',
    nextRefresh: 'Oct 29, 2026'
  },
  {
    id: 'fpb-004',
    lender: 'Uline Commercial',
    product: 'Corporate Net-30 Billing Account',
    productType: 'Tier 1 Vendor Credit Tradeline',
    limit: '$1,000 - $5,000',
    creditRequirements: 'No personal credit check · Valid EIN + D&B DUNS',
    bureaus: 'Dun & Bradstreet (Reports monthly to PAYDEX)',
    timeInBusiness: 'Immediate (Day 1 of incorporation)',
    revenue: 'No minimum revenue requirement',
    bankRelationship: 'None required',
    geographicRestrictions: 'National US & Canada',
    documentation: 'Articles of Organization & Federal EIN CP-575 letter',
    pgCollateral: 'Zero PG · 100% Corporate liability only',
    rateFees: 'Net-30 days payment terms · 0% interest if paid on time',
    verificationStatus: 'ACTIVE',
    evidenceStatus: 'VERIFIED',
    lastVerified: 'Oct 05, 2026',
    nextRefresh: 'Nov 05, 2026'
  },
  {
    id: 'fpb-005',
    lender: 'Grainger Industrial Supply',
    product: 'Business Credit Line Net-30',
    productType: 'Tier 1 Vendor Credit Tradeline',
    limit: '$1,000 - $3,500',
    creditRequirements: 'Clean entity standing · Active physical business address',
    bureaus: 'Dun & Bradstreet + Experian Business',
    timeInBusiness: 'Immediate upon entity verification',
    revenue: 'Stated purchasing volume',
    bankRelationship: 'None required',
    geographicRestrictions: 'National US',
    documentation: 'Online application with EIN and state registration #',
    pgCollateral: 'Zero PG · Corporate liability',
    rateFees: 'Net-30 invoice terms',
    verificationStatus: 'ACTIVE',
    evidenceStatus: 'VERIFIED',
    lastVerified: 'Oct 04, 2026',
    nextRefresh: 'Nov 04, 2026'
  },
  {
    id: 'fpb-006',
    lender: 'Nav Technologies / Bluevine',
    product: 'Nav Prime Tradeline & Bluevine Line',
    productType: 'Commercial Tradeline & Line',
    limit: '$5,000 - $25,000',
    creditRequirements: 'Active business checking + 650+ FICO',
    bureaus: 'D&B + Experian Business + Equifax Business',
    timeInBusiness: '6+ months in business',
    revenue: '$10,000/mo minimum monthly deposits',
    bankRelationship: 'Plaid banking link required for live underwriting',
    geographicRestrictions: 'National (excl. NV, ND, SD for certain lines)',
    documentation: 'Online bank connection + entity documentation',
    pgCollateral: 'Owner guarantee on line component',
    rateFees: '6.9% - 14.9% APR equivalent · $49.99/mo Nav Prime service fee',
    verificationStatus: 'FLAGGED',
    evidenceStatus: 'CROSS-SUPPORTED',
    lastVerified: 'Oct 01, 2026',
    nextRefresh: 'Oct 15, 2026'
  }
];

// ============================================================================
// 7. BUSINESS CREDIT PRODUCT BANK
// ============================================================================
export const INITIAL_BUSINESS_CREDIT_PRODUCTS = [
  {
    id: 'bcp-01',
    tier: 'Tier 1: Starter Vendor Tradelines (No PG, Reports to D&B / Experian)',
    vendors: [
      { name: 'Uline', terms: 'Net-30', bureau: 'D&B', depositReq: '$0', speed: '5-7 Days', notes: 'Place initial order over $100 to trigger auto-report' },
      { name: 'Grainger', terms: 'Net-30', bureau: 'D&B + Experian', depositReq: '$0', speed: '3-5 Days', notes: 'Customer number assigned instantly; invoices report within 30 days' },
      { name: 'Quill', terms: 'Net-30', bureau: 'D&B', depositReq: '$0', speed: '7 Days', notes: 'Office supplies; minimum $100 purchase recommended' },
      { name: 'Summa Office Supplies', terms: 'Net-30', bureau: 'Equifax Business', depositReq: '$0', speed: '7 Days', notes: 'Digital catalog purchases; reports reliably each billing cycle' }
    ]
  },
  {
    id: 'bcp-02',
    tier: 'Tier 2: Advanced Store & Fuel Fleet Accounts (Requires 3-5 Tier 1 Tradelines)',
    vendors: [
      { name: 'Home Depot Commercial Pro', terms: 'Revolving / Net-30', bureau: 'D&B + Experian', depositReq: 'None', speed: 'Immediate online', notes: 'Citibank-underwritten; requires verified DUNS and PAYDEX 75+' },
      { name: 'WEX Fleet Card / Shell Fleet', terms: 'Revolving Fuel', bureau: 'Experian Business', depositReq: 'None', speed: '48 Hours', notes: 'Covers national fuel stations; builds high-frequency payment records' },
      { name: 'Office Depot / OfficeMax', terms: 'Net-30 Account', bureau: 'D&B + Equifax', depositReq: 'None', speed: 'Online', notes: 'Underwritten by Citibank Commercial' }
    ]
  },
  {
    id: 'bcp-03',
    tier: 'Tier 3: Tier 1 Bank Revolving Cards & Cash Lines (Requires 5-8 Tradelines, 80 PAYDEX)',
    vendors: [
      { name: 'Chase Ink Business Preferred / Cash', terms: 'Revolving Credit Card', bureau: 'Experian Business', depositReq: 'Chase Business Checking', speed: 'Instant / 7 Days', notes: 'Industry standard corporate card; unlocks high travel points & $50k+ lines' },
      { name: 'American Express Business Gold / Platinum', terms: 'Charge / Revolving Line', bureau: 'Experian Business + D&B', depositReq: 'None', speed: 'Instant', notes: 'Flexible spending limit tied to monthly deposit velocity' },
      { name: 'Bank of America Business Advantage', terms: 'Revolving Cash Line', bureau: 'Experian Business', depositReq: 'BofA Checking ($20k+)', speed: '5 Days', notes: 'Low interest cash advance capability with 0% introductory rate' }
    ]
  }
];

// ============================================================================
// 8. OPPORTUNITY BANK & COMPONENT BANK
// ============================================================================
export const INITIAL_OPPORTUNITY_COMPONENTS = [
  {
    component: 'Front-End Intelligence Engine',
    description: 'Autonomous React/TypeScript dashboard scaffold with real-time websocket and polling sync',
    nexusAsset: 'Nexus OS UI Library & Shell Component Architecture',
    reuseReadiness: '100% Ready'
  },
  {
    component: 'Data Ingestion & Extraction Worker',
    description: 'Deterministic FIFO queue processor for YouTube, Web scraping, SEC EDGAR, and Gov API feeds',
    nexusAsset: 'Research Ingestion Core & Supabase Canonical Pipeline',
    reuseReadiness: '95% Ready'
  },
  {
    component: 'Client Multitenancy & Onboarding',
    description: 'Isolated client tenant directories with encrypted API credential storage and auth RBAC',
    nexusAsset: 'GoClear / Apex Multi-Tenant Enclave',
    reuseReadiness: '90% Ready'
  },
  {
    component: 'Bankability & Tradeline Matcher',
    description: 'Non-binary rules engine cross-referencing bureau underwriting criteria with entity profile',
    nexusAsset: 'Clyde Decision Logic & NAICS Governance Core',
    reuseReadiness: '100% Ready'
  }
];

// ============================================================================
// 9. 15-SOURCE TEST BATCH FOR RESEARCH PAGE FEEDER MODEL
// ============================================================================
export const INITIAL_RESEARCH_FEEDERS = [
  {
    id: 'feeder-1',
    category: 'BUSINESS OPPORTUNITIES',
    status: 'ACTIVE',
    sourcesAdded: 8,
    queued: 3,
    questionnaireComplete: 5,
    researchRequired: 2,
    handedOff: 3, // Handed off to Atlas
    blocked: 0,
    testBatchProgress: { completed: 2, target: 3 },
    notebook: 'NB-FEEDER-OPPORTUNITIES-01',
    description: 'Inward scanning of commercial niche problems, underserved B2B workflows, and SaaS arbitrage.'
  },
  {
    id: 'feeder-2',
    category: 'BUSINESS FUNDING',
    status: 'ACTIVE',
    sourcesAdded: 6,
    queued: 2,
    questionnaireComplete: 4,
    researchRequired: 1,
    handedOff: 3, // Handed off to Clyde
    blocked: 0,
    testBatchProgress: { completed: 3, target: 3 },
    notebook: 'NB-FEEDER-FUNDING-02',
    description: 'Lender underwriting matrices, unadvertised bank credit programs, and SBA regional guidelines.'
  },
  {
    id: 'feeder-3',
    category: 'BUSINESS CREATION',
    status: 'ACTIVE',
    sourcesAdded: 5,
    queued: 1,
    questionnaireComplete: 4,
    researchRequired: 1,
    handedOff: 2, // Handed off to Business Creation
    blocked: 0,
    testBatchProgress: { completed: 1, target: 3 },
    notebook: 'NB-FEEDER-CREATION-03',
    description: 'State Secretary of State API documentation, registered agent portals, and NAICS alignment rules.'
  },
  {
    id: 'feeder-4',
    category: 'FOREX / INDICATOR STRATEGIES',
    status: 'ACTIVE',
    sourcesAdded: 7,
    queued: 3,
    questionnaireComplete: 4,
    researchRequired: 2,
    handedOff: 2, // Handed off to Trading Engine (Mercury/Alpha)
    blocked: 0,
    testBatchProgress: { completed: 2, target: 3 },
    notebook: 'NB-FEEDER-FOREX-04',
    description: 'Institutional Fair Value Gap (FVG), order-block math, and PineScript indicator conversions.'
  },
  {
    id: 'feeder-5',
    category: 'OPTIONS STRATEGIES',
    status: 'ACTIVE',
    sourcesAdded: 4,
    queued: 2,
    questionnaireComplete: 2,
    researchRequired: 1,
    handedOff: 1, // Handed off to Trading Engine
    blocked: 0,
    testBatchProgress: { completed: 1, target: 3 },
    notebook: 'NB-FEEDER-OPTIONS-05',
    description: 'Zero-DTE gamma flow, implied volatility skew, and theta decay hedging structures.'
  }
];

export const RAY_NOVA_OPPORTUNITY_INTAKE = {
  activeSubmissions: 3,
  sourcesInReview: 2,
  priorityGate: 'STRATEGIC_AUTHORIZATION_REQUIRED',
  lastIntake: '18m ago via Nova Voice',
  items: [
    {
      title: 'Automated Commercial Sub-Contractor DBE Portal (Ray Submission)',
      origin: 'Ray Direct Directive',
      status: 'HANDED_OFF_TO_ATLAS',
      notes: 'Initial prompt transcribed by Nova; structured questionnaire completed; assigned to Atlas.'
    },
    {
      title: 'Commodity Freight Rate Arbitrage Engine',
      origin: 'Nova Market Intelligence Scan',
      status: 'RESEARCH_CLOSES_GAPS',
      notes: 'Research identifying API rate limits on FreightWaves SONAR before department packaging.'
    }
  ]
};
