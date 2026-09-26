import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  TabType,
  ClientProfile,
  LevelInfo,
  JourneyNode,
  Mission,
  Achievement,
  DocumentItem,
  BankabilityPillar,
  BusinessSetupStep,
  Recommendation,
  ResourceItem,
  ClydeMessage
} from '../types/portal';

// Import generated authentic images
import clientAvatarPath from '../assets/images/client_avatar_executive_1790366592448.jpg';
import fundingBlueprintImg from '../assets/images/resource_funding_blueprint_1790366602825.jpg';
import underwritingGuideImg from '../assets/images/resource_underwriting_guide_1790366613726.jpg';
import { getNexusClientPortalBridge, loadNexusPortalSnapshot } from '../integration/nexusClientPortalBridge';

const confetti = (_options: { particleCount: number; spread: number; origin: { y: number }; colors: string[] }) => undefined;

export interface PortalFacts {
  creditScore: number;
  utilizationPercent: number;
  utilizationTargetPercent: number;
  documentVerifiedCount: number;
  documentTotalCount: number;
  bankabilityScore: number;
  fundingTargetLabel: string;
}

export const LEVELS: LevelInfo[] = [
  {
    id: 'starter',
    name: 'Starter',
    minPoints: 0,
    maxPoints: 35,
    badge: 'STAGE 01',
    description: 'Initial intake and baseline business documentation initialized.',
    benefits: ['Portal onboarding', 'Baseline credit audit', 'Clyde AI copilot access']
  },
  {
    id: 'foundation-builder',
    name: 'Foundation Builder',
    minPoints: 36,
    maxPoints: 55,
    badge: 'STAGE 02',
    description: 'Core legal entity structure, compliance registry, and EIN aligned.',
    benefits: ['Entity credibility scoring', 'Secretary of State sync', 'Tier-1 vendor roadmap']
  },
  {
    id: 'credit-ready',
    name: 'Credit Ready',
    minPoints: 56,
    maxPoints: 70,
    badge: 'STAGE 03',
    description: 'Personal credit optimized, revolving utilization disciplined below 20%.',
    benefits: ['Bureau trend radar', 'Inquiry aging simulator', 'Targeted paydown calculations']
  },
  {
    id: 'business-ready',
    name: 'Business Ready',
    minPoints: 71,
    maxPoints: 84,
    badge: 'STAGE 04',
    description: 'Full commercial legitimacy: banking history, NAICS, DUNS, and verified contacts.',
    benefits: ['Tier-1 bankability report', 'Institutional underwriter packet preview', 'Lender match readiness']
  },
  {
    id: 'bankable',
    name: 'Bankable',
    minPoints: 85,
    maxPoints: 92,
    badge: 'STAGE 05',
    description: 'Commercial underwriting standards satisfied for unsecured credit facilities.',
    benefits: ['Prime revolving limits access', 'Fast-track underwriting queue', 'Executive advisor consultation']
  },
  {
    id: 'funding-ready',
    name: 'Funding Ready',
    minPoints: 93,
    maxPoints: 97,
    badge: 'STAGE 06',
    description: 'High-probability match across multiple institutional debt facilities.',
    benefits: ['Direct underwriter submission', 'Term sheet rate negotiation', 'Secondary lender syndication']
  },
  {
    id: 'opportunity-ready',
    name: 'Opportunity Ready',
    minPoints: 98,
    maxPoints: 100,
    badge: 'STAGE 07',
    description: 'Apex corporate capital position: sovereign lines, growth capital, and non-dilutive credit.',
    benefits: ['Sovereign treasury programs', 'VIP Capital concierge', 'Continuous institutional monitoring']
  }
];

interface PortalContextType {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  profile: ClientProfile;
  levels: LevelInfo[];
  currentLevel: LevelInfo;
  nextLevel: LevelInfo | null;
  journeyNodes: JourneyNode[];
  missions: Mission[];
  achievements: Achievement[];
  documents: DocumentItem[];
  bankabilityPillars: BankabilityPillar[];
  setupSteps: BusinessSetupStep[];
  recommendations: Recommendation[];
  resources: ResourceItem[];
  clydeMessages: ClydeMessage[];
  isClydeOpen: boolean;
  setIsClydeOpen: (open: boolean) => void;
  isClydeThinking: boolean;
  activeCelebration: { title: string; points: number; subtitle: string } | null;
  dismissCelebration: () => void;
  completeMission: (missionId: string) => void;
  uploadDocument: (docId: string, fileName: string, file?: File) => void;
  toggleSetupStep: (stepId: string) => void;
  sendClydeQuery: (query: string) => void;
  openClydeWithPrompt: (promptText: string) => void;
  requestUnderwritingReview: (notes: string) => Promise<boolean>;
  updateRevolvingBalance: (newBalance: number) => void;
  simulatedBalance: number;
  liveReady: boolean;
  facts: PortalFacts;
  liveMode: boolean;
}

const PortalContext = createContext<PortalContextType | undefined>(undefined);

export const PortalProvider: React.FC<{ children: React.ReactNode; initialTab?: TabType }> = ({ children, initialTab = 'dashboard' }) => {
  const liveBridge = getNexusClientPortalBridge();
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const [isClydeOpen, setIsClydeOpen] = useState<boolean>(false);
  const [isClydeThinking, setIsClydeThinking] = useState<boolean>(false);
  const [activeCelebration, setActiveCelebration] = useState<{ title: string; points: number; subtitle: string } | null>(null);

  // Credit Revolving balance simulator state
  const [simulatedBalance, setSimulatedBalance] = useState<number>(8550);
  const [facts, setFacts] = useState<PortalFacts>({ creditScore: 0, utilizationPercent: 0, utilizationTargetPercent: 10, documentVerifiedCount: 0, documentTotalCount: 0, bankabilityScore: 0, fundingTargetLabel: 'No funding target recorded' });
  const [liveReady, setLiveReady] = useState(liveBridge?.mode !== 'live');
  const liveMode = liveBridge?.mode === 'live';

  // Client Profile
  const [profile, setProfile] = useState<ClientProfile>({
    name: 'David Vance',
    companyName: 'Vance Logistics LLC',
    role: 'Founder & Managing Director',
    ein: '84-2910482',
    duns: '08-234-9182',
    entityType: 'Delaware Multi-Member LLC',
    stateOfFormation: 'Delaware (Domestic) / Texas (Foreign Reg)',
    industry: 'Freight Logistics & Intermodal Transport',
    naicsCode: '484121 (General Freight Trucking, Long-Distance)',
    memberSince: 'November 2025',
    readinessPoints: 78,
    readinessTarget: 100,
    currentLevelIndex: 3, // Business Ready (71-84)
    streakDays: 14,
    avatarUrl: clientAvatarPath,
    targetFundingAmount: 250000
  });

  // Calculate current and next levels
  const currentLevel = LEVELS.find(
    (lvl) => profile.readinessPoints >= lvl.minPoints && profile.readinessPoints <= lvl.maxPoints
  ) || LEVELS[3];

  const currentLevelIndex = LEVELS.findIndex((lvl) => lvl.id === currentLevel.id);
  const nextLevel = currentLevelIndex < LEVELS.length - 1 ? LEVELS[currentLevelIndex + 1] : null;

  // Journey Map Nodes
  const [journeyNodes, setJourneyNodes] = useState<JourneyNode[]>([
    {
      id: 'profile',
      label: 'Profile',
      tab: 'credit-profile',
      status: 'completed',
      progress: 100,
      scoreWeight: 15,
      description: 'Owner identity, SSN & corporate registry verified.'
    },
    {
      id: 'credit',
      label: 'Credit Health',
      tab: 'credit-profile',
      status: 'completed',
      progress: 92,
      scoreWeight: 20,
      description: 'Experian 742, 0 derogatories, pristine 100% on-time history.'
    },
    {
      id: 'business-setup',
      label: 'Business Foundation',
      tab: 'business-setup',
      status: 'completed',
      progress: 88,
      scoreWeight: 15,
      description: 'Delaware LLC, EIN 147C, commercial physical address.'
    },
    {
      id: 'bankability',
      label: 'Bankability',
      tab: 'business-bankability',
      status: 'in-progress',
      progress: 78,
      scoreWeight: 20,
      description: '78/100 composite bankability score across 6 core pillars.'
    },
    {
      id: 'documents',
      label: 'Documents',
      tab: 'documents',
      status: 'in-progress',
      progress: 60,
      scoreWeight: 15,
      description: '3 of 5 foundational files verified. Operating statements pending.'
    },
    {
      id: 'funding-readiness',
      label: 'Funding Ready',
      tab: 'funding-readiness',
      status: 'in-progress',
      progress: 74,
      scoreWeight: 10,
      description: 'Target: $250k commercial line. Awaiting cash flow clearance.'
    },
    {
      id: 'review',
      label: 'Underwriter Review',
      tab: 'request-review',
      status: 'pending',
      progress: 25,
      scoreWeight: 5,
      description: 'Formal underwriter dossier submission & committee audit.'
    }
  ]);

  // Active Missions
  const [missions, setMissions] = useState<Mission[]>([
    {
      id: 'm1',
      title: 'Verify your business banking history',
      category: 'Documents',
      points: 8,
      impact: 'Critical',
      timeEstimate: '4 mins',
      description: 'Upload Vance Logistics LLC last 3 consecutive months of primary operating bank statements to clear underwriter cash flow validation.',
      actionText: 'Upload Statements in Vault',
      targetTab: 'documents',
      completed: false,
      status: 'Blocked'
    },
    {
      id: 'm2',
      title: 'Optimize Revolving Utilization Below 15%',
      category: 'Credit',
      points: 5,
      impact: 'High',
      timeEstimate: 'Immediate',
      description: 'Paying down $2,000 on Chase Ink Business will drop your utilization from 19% to 14.5%, boosting your commercial score.',
      actionText: 'View Utilization Gauge',
      targetTab: 'credit-utilization',
      completed: false,
      status: 'In Progress'
    },
    {
      id: 'm3',
      title: 'Verify 411 Directory & State Registered Agent',
      category: 'Setup',
      points: 3,
      impact: 'High',
      timeEstimate: '3 mins',
      description: 'Ensure public directory match across Dun & Bradstreet, Google Business, and Delaware Division of Corporations records.',
      actionText: 'Inspect Business Roadmap',
      targetTab: 'business-setup',
      completed: false,
      status: 'In Progress'
    },
    {
      id: 'm4',
      title: 'Submit Operating Agreement Addendum',
      category: 'Bankability',
      points: 4,
      impact: 'Medium',
      timeEstimate: '5 mins',
      description: 'Confirm authorized borrowing resolution clause in Section 6.2 of the Vance Logistics LLC operating agreement.',
      actionText: 'Review Bankability Pillars',
      targetTab: 'business-bankability',
      completed: false,
      status: 'In Progress'
    }
  ]);

  // Professional Achievements
  const [achievements, setAchievements] = useState<Achievement[]>([
    {
      id: 'ach-1',
      title: 'Tier-1 Entity Sovereign',
      unlockedAt: '12 days ago',
      description: 'Delaware LLC and Secretary of State filings verified with zero corporate blemishes.',
      iconName: 'Building2',
      category: 'Foundation'
    },
    {
      id: 'ach-2',
      title: 'Prime Credit Custodian',
      unlockedAt: '8 days ago',
      description: 'Crossed 740 FICO / Experian threshold with 100% on-time institutional record.',
      iconName: 'ShieldCheck',
      category: 'Credit'
    },
    {
      id: 'ach-3',
      title: '14-Day Velocity Streak',
      unlockedAt: 'Yesterday',
      description: 'Continuous daily audit compliance and financial readiness progression.',
      iconName: 'Flame',
      category: 'Momentum'
    },
    {
      id: 'ach-4',
      title: 'Commercial D-U-N-S Validated',
      unlockedAt: '3 days ago',
      description: 'D&B PAYDEX commercial registry established with active corporate file.',
      iconName: 'Award',
      category: 'Bankability'
    }
  ]);

  // Vault Documents
  const [documents, setDocuments] = useState<DocumentItem[]>([
    {
      id: 'doc-1',
      title: 'Delaware Articles of Organization & Filing Stamp',
      category: 'Corporate Legal',
      status: 'verified',
      requiredFor: 'Entity Verification',
      fileName: 'Vance_Logistics_Delaware_Articles_Certified.pdf',
      fileSize: '2.4 MB',
      updatedAt: 'Verified 4 days ago',
      notes: 'State seal & entity number #7829104 verified by underwriter.'
    },
    {
      id: 'doc-2',
      title: 'IRS Employer Identification Confirmation (CP 575 / 147C)',
      category: 'Tax Identification',
      status: 'verified',
      requiredFor: 'Federal Tax Identity',
      fileName: 'IRS_EIN_147C_Vance_Logistics.pdf',
      fileSize: '1.1 MB',
      updatedAt: 'Verified 5 days ago',
      notes: 'EIN 84-2910482 matches exact legal corporate name format.'
    },
    {
      id: 'doc-3',
      title: 'Operating Agreement (Signed Multi-Member)',
      category: 'Corporate Legal',
      status: 'verified',
      requiredFor: 'Ownership Structure',
      fileName: 'Vance_Logistics_Operating_Agreement_Executed.pdf',
      fileSize: '4.8 MB',
      updatedAt: 'Verified 3 days ago',
      notes: 'David Vance confirmed as 85% Managing Principal with full borrowing authorization.'
    },
    {
      id: 'doc-4',
      title: 'Last 3 Months Operating Bank Statements (Chase Commercial)',
      category: 'Financial / Cash Flow',
      status: 'required',
      requiredFor: '$250k Prime Line of Credit',
      updatedAt: 'Action Required',
      notes: 'Missing Nov, Dec, Jan PDF statements. Crucial to unlock +8 readiness points.'
    },
    {
      id: 'doc-5',
      title: 'Personal Financial Statement (SBA Form 413 or GoClear PFS)',
      category: 'Underwriting Asset Sheet',
      status: 'reviewing',
      requiredFor: 'Institutional Underwriting',
      fileName: 'GoClear_PFS_David_Vance_Signed.pdf',
      fileSize: '1.9 MB',
      updatedAt: 'Under Review by Analyst',
      notes: 'Submitted 14 hours ago. Current analyst review in progress.'
    }
  ]);

  // Bankability Pillars
  const [bankabilityPillars, setBankabilityPillars] = useState<BankabilityPillar[]>([
    {
      id: 'bp-1',
      name: 'Entity Credibility',
      score: 90,
      maxScore: 100,
      weight: '20%',
      status: 'strong',
      details: 'Delaware LLC registered, active standing in Texas foreign qualification, official corporate records verified.',
      keyItems: [
        { label: 'Secretary of State Active Standing', pass: true },
        { label: 'Registered Agent Physical Address', pass: true },
        { label: 'Corporate Operating Agreement in Place', pass: true },
        { label: 'No Corporate Filings or Lien Discrepancies', pass: true }
      ]
    },
    {
      id: 'bp-2',
      name: 'Contact & Directory Consistency',
      score: 85,
      maxScore: 100,
      weight: '15%',
      status: 'good',
      details: 'Dedicated commercial phone VoIP, company email domain, matching 411 listing.',
      keyItems: [
        { label: 'Matching Physical Commercial Address (No P.O. Box)', pass: true },
        { label: 'Dedicated Business VoIP (800 / Local Carrier)', pass: true },
        { label: 'Custom Domain Email (david@vancelogistics.com)', pass: true },
        { label: 'National 411 / YellowPages Directory Listed', pass: false }
      ]
    },
    {
      id: 'bp-3',
      name: 'Banking & Cash Flow Integrity',
      score: 74,
      maxScore: 100,
      weight: '25%',
      status: 'needs-attention',
      details: 'Active Chase Commercial Checking account with $42,500 average ledger. Awaiting statement upload verification.',
      keyItems: [
        { label: 'Dedicated Business Checking Account', pass: true },
        { label: 'Average Daily Balance > $10,000', pass: true },
        { label: 'Zero Non-Sufficient Funds (NSF) in 12 months', pass: true },
        { label: 'Uploaded Verified 3-Month Bank Statements', pass: false }
      ]
    },
    {
      id: 'bp-4',
      name: 'Business Public Presence',
      score: 80,
      maxScore: 100,
      weight: '15%',
      status: 'good',
      details: 'Modern corporate website, SSL security certified, Google Business Profile claim active.',
      keyItems: [
        { label: 'Live Commercial Website with Privacy Policy', pass: true },
        { label: 'Google Business Profile Claimed & Verified', pass: true },
        { label: 'Active Industry Certifications (DOT/MC Freight)', pass: true },
        { label: 'LinkedIn Corporate Organization Profile', pass: false }
      ]
    },
    {
      id: 'bp-5',
      name: 'Documentation Readiness',
      score: 65,
      maxScore: 100,
      weight: '10%',
      status: 'needs-attention',
      details: '3 of 5 foundational files verified. Operating bank statements pending.',
      keyItems: [
        { label: 'Articles of Organization & Certificate of Good Standing', pass: true },
        { label: 'IRS 147C Tax Verification Letter', pass: true },
        { label: 'Executed Corporate Operating Agreement', pass: true },
        { label: 'Full 90-Day Unredacted Bank Statements', pass: false }
      ]
    },
    {
      id: 'bp-6',
      name: 'Credit Profile Alignment',
      score: 88,
      maxScore: 100,
      weight: '15%',
      status: 'strong',
      details: '742 FICO Experian commercial personal guarantor score, zero late payments, 19% utilization.',
      keyItems: [
        { label: 'FICO Score > 720 Across All 3 Bureaus', pass: true },
        { label: 'Zero Charge-offs / Collections / Public Judgments', pass: true },
        { label: 'Revolving Utilization < 20%', pass: true },
        { label: 'Revolving Utilization < 10% (Target for Tier-1)', pass: false }
      ]
    }
  ]);

  // Business Setup Steps
  const [setupSteps, setSetupSteps] = useState<BusinessSetupStep[]>([
    {
      id: 's-1',
      stepNumber: 1,
      title: 'Legal Business Entity Formation',
      field: 'Entity Type',
      value: 'Delaware Multi-Member LLC (#7829104)',
      status: 'completed',
      whyItMatters: 'Protects personal assets and creates the foundation for commercial borrowing.',
      readinessImpact: '+25 Pts (Verified)',
      points: 25
    },
    {
      id: 's-2',
      stepNumber: 2,
      title: 'Federal Employer Identification Number (EIN)',
      field: 'IRS EIN',
      value: '84-2910482 (Matches 147C Letter)',
      status: 'completed',
      whyItMatters: 'Mandatory federal identity separating business tax liabilities from SSN.',
      readinessImpact: '+20 Pts (Verified)',
      points: 20
    },
    {
      id: 's-3',
      stepNumber: 3,
      title: 'Physical Commercial Address',
      field: 'Business Location',
      value: '4200 North Freeway Blvd, Suite 310, Houston, TX 77022',
      status: 'completed',
      whyItMatters: 'Lenders reject virtual mailboxes and UPS Store drops during fraud screening.',
      readinessImpact: '+15 Pts (Verified)',
      points: 15
    },
    {
      id: 's-4',
      stepNumber: 4,
      title: 'Dedicated Business Telephony (VoIP)',
      field: 'Phone System',
      value: '+1 (800) 419-8291 / Direct Local Carrier Line',
      status: 'completed',
      whyItMatters: 'Banks verify business phone lines via automated directory cross-checks.',
      readinessImpact: '+10 Pts (Verified)',
      points: 10
    },
    {
      id: 's-5',
      stepNumber: 5,
      title: 'Domain & Executive Email',
      field: 'Digital Presence',
      value: 'david@vancelogistics.com (Google Workspace Enterprise)',
      status: 'completed',
      whyItMatters: 'Free email providers (Gmail, Yahoo) immediately trigger risk flags in underwriting.',
      readinessImpact: '+10 Pts (Verified)',
      points: 10
    },
    {
      id: 's-6',
      stepNumber: 6,
      title: 'Professional Corporate Website',
      field: 'Web Address',
      value: 'https://vancelogistics.com (SSL Encrypted)',
      status: 'completed',
      whyItMatters: 'Lenders audit website copy for operational legitimacy, contact info, and clear services.',
      readinessImpact: '+10 Pts (Verified)',
      points: 10
    },
    {
      id: 's-7',
      stepNumber: 7,
      title: 'NAICS & SIC Code Classification',
      field: 'Industry Code',
      value: '484121 (General Freight Trucking, Long-Distance)',
      status: 'completed',
      whyItMatters: 'Prevents automatic lender disqualification for high-risk or restricted industry categories.',
      readinessImpact: '+10 Pts (Verified)',
      points: 10
    },
    {
      id: 's-8',
      stepNumber: 8,
      title: 'Dedicated Commercial Bank Account',
      field: 'Primary Operating',
      value: 'Chase Bank Commercial Business Checking',
      status: 'completed',
      whyItMatters: 'Commercial accounts establish legal commingling protection and build bank rating.',
      readinessImpact: '+15 Pts (Verified)',
      points: 15
    },
    {
      id: 's-9',
      stepNumber: 9,
      title: 'Dun & Bradstreet (D-U-N-S) Number',
      field: 'D&B Registration',
      value: '08-234-9182 (PAYDEX Tracking Active)',
      status: 'completed',
      whyItMatters: 'Primary commercial credit bureau used by institutional suppliers and prime banks.',
      readinessImpact: '+15 Pts (Verified)',
      points: 15
    },
    {
      id: 's-10',
      stepNumber: 10,
      title: 'National 411 Directory Listing',
      field: 'Directory Sync',
      value: 'Pending sync with ListYourself / Neustar',
      status: 'attention',
      whyItMatters: 'Automated bank compliance scanners check 411 listings before issuing unsecured cards.',
      readinessImpact: '+10 Pts (Action Needed)',
      points: 10
    }
  ]);

  // Recommendations
  const [recommendations, setRecommendations] = useState<Recommendation[]>([
    {
      id: 'rec-1',
      title: 'Submit 90-Day Bank Statements to Unlock $250k Line of Credit',
      priority: 'HIGH IMPACT',
      category: 'Institutional Funding',
      impactScore: '+8 Readiness Pts',
      reason: 'Underwriters for Tier-1 Commercial Lines require 3 full months of consecutive operating statements to verify cash flow stability.',
      actionLabel: 'Go to Document Vault',
      tabTarget: 'documents',
      clydePrompt: 'Why do lenders need 3 months of bank statements and what cash flow ratios are they looking for?'
    },
    {
      id: 'rec-2',
      title: 'Pay Down Chase Ink by $2,000 to Push Utilization to 14.5%',
      priority: 'QUICK WIN',
      category: 'Credit Optimization',
      impactScore: '+15 Readiness Pts',
      reason: 'Dropping utilization below 15% lowers your debt-to-credit ratio, often providing a fast 15-20 point bump before committee review.',
      actionLabel: 'Open Utilization Gauge',
      tabTarget: 'credit-utilization',
      clydePrompt: 'How will paying down $2,000 on my Chase Ink card affect my credit score and funding odds?'
    },
    {
      id: 'rec-3',
      title: 'Sync 411 Directory with Exact Delaware Secretary of State Address',
      priority: 'IMPORTANT',
      category: 'Bankability',
      impactScore: '+10 Readiness Pts',
      reason: 'Discrepancies between public telephone directories and state filings cause automated fraud flags with Chase and Amex underwriters.',
      actionLabel: 'View Setup Roadmap',
      tabTarget: 'business-setup',
      clydePrompt: 'How do I submit my 411 directory listing to prevent bank underwriting fraud flags?'
    },
    {
      id: 'rec-4',
      title: 'Establish 2 Secondary Tier-1 Net-30 Vendor Accounts',
      priority: 'OPTIONAL',
      category: 'Commercial Credit',
      impactScore: '+12 Readiness Pts',
      reason: 'Adding accounts like Grainger or Uline reporting to Dun & Bradstreet accelerates your PAYDEX score past 80.',
      actionLabel: 'Inspect Bankability',
      tabTarget: 'business-bankability',
      clydePrompt: 'What Tier-1 Net-30 vendors report fastest to Dun & Bradstreet and Experian Business?'
    }
  ]);

  // Curated Resources
  const [resources, setResources] = useState<ResourceItem[]>([
    {
      id: 'res-1',
      title: 'Institutional Capital & Commercial Credit Architecture',
      type: 'Executive Guide',
      duration: '14 min read',
      stage: 'Funding Ready',
      summary: 'Comprehensive underwriting blueprint detailing how commercial credit committees evaluate debt service coverage ratio (DSCR), bank ratings, and liquidity.',
      author: 'Marcus Vance, GoClear Underwriting Director',
      imageThumbnail: fundingBlueprintImg
    },
    {
      id: 'res-2',
      title: 'Commercial Lending Underwriting Checklist & Risk Scrub',
      type: 'Underwriting Checklist',
      duration: '8 min read',
      stage: 'Bankability',
      summary: 'Exact 24-point internal rubric used by commercial banks (Chase, Wells Fargo, BofA) to screen credit lines from $100k to $1M.',
      author: 'GoClear Risk Advisory Team',
      imageThumbnail: underwritingGuideImg
    },
    {
      id: 'res-3',
      title: 'Mastering the 10% Revolving Utilization Protocol',
      type: 'Video Masterclass',
      duration: '18 min video',
      stage: 'Credit Ready',
      summary: 'How to time statement closing dates versus due dates to report ultra-low utilization without pausing daily company spending.',
      author: 'Elena Rostova, Senior Credit Strategist',
      imageThumbnail: underwritingGuideImg
    }
  ]);

  // Clyde AI Conversation State
  const [clydeMessages, setClydeMessages] = useState<ClydeMessage[]>([
    {
      id: 'cm-1',
      sender: 'clyde',
      text: "Good afternoon, David. I'm Clyde, your GoClear AI Financial Readiness Copilot. You are currently at 72% Funding Readiness (720/1,000 Points) in the Business Ready tier. Your primary blocker for the $250,000 institutional line of credit is your 90-day bank statements verification.",
      timestamp: 'Just now',
      card: {
        type: 'blocker',
        title: 'Top Priority Blocker',
        description: 'Upload Vance Logistics LLC last 3 consecutive months of Chase operating statements in the Vault.',
        actionText: 'Open Document Vault',
        actionTab: 'documents'
      }
    }
  ]);

  // Optional Nexus host bridge. When absent, the original Google AI Studio demo state is preserved exactly.
  useEffect(() => {
    let cancelled = false;
    const bridge = getNexusClientPortalBridge();
    if (!bridge || bridge.mode !== 'live') {
      setLiveReady(true);
      return undefined;
    }

    const clearLiveState = () => {
      setProfile({ name: 'Client', companyName: 'Business name unavailable', role: 'Authorized client', ein: 'Not available', duns: 'Not available', entityType: 'Not available', stateOfFormation: 'Not available', industry: 'Not available', naicsCode: 'Not available', memberSince: 'Not available', readinessPoints: 0, readinessTarget: 100, currentLevelIndex: 0, streakDays: 0, avatarUrl: clientAvatarPath, targetFundingAmount: 0 });
      setJourneyNodes([]);
      setMissions([{ id: 'no-live-task', title: 'No active client task recorded', category: 'Setup', points: 0, impact: 'Medium', timeEstimate: 'Not scheduled', description: 'No executable client task was returned by the authenticated tenant-scoped query.', actionText: 'Review readiness', targetTab: 'dashboard', completed: true, status: 'Completed' }]);
      setAchievements([]);
      setDocuments([]);
      setBankabilityPillars([]);
      setSetupSteps([]);
      setRecommendations([]);
      setResources([]);
      setClydeMessages([]);
      setSimulatedBalance(0);
      setFacts({ creditScore: 0, utilizationPercent: 0, utilizationTargetPercent: 10, documentVerifiedCount: 0, documentTotalCount: 0, bankabilityScore: 0, fundingTargetLabel: 'No funding target recorded' });
    };

    loadNexusPortalSnapshot()
      .then((snapshot) => {
        if (cancelled) return;
        if (!snapshot) clearLiveState();
        if (!snapshot) { setLiveReady(true); return; }
        if (snapshot.profile) setProfile(snapshot.profile);
        if (snapshot.journeyNodes) setJourneyNodes(snapshot.journeyNodes);
        if (snapshot.missions) setMissions(snapshot.missions);
        if (snapshot.achievements) setAchievements(snapshot.achievements);
        if (snapshot.documents) setDocuments(snapshot.documents);
        if (snapshot.bankabilityPillars) setBankabilityPillars(snapshot.bankabilityPillars);
        if (snapshot.setupSteps) setSetupSteps(snapshot.setupSteps);
        if (snapshot.recommendations) setRecommendations(snapshot.recommendations);
        if (snapshot.resources) setResources(snapshot.resources);
        if (snapshot.clydeMessages) setClydeMessages(snapshot.clydeMessages);
        if (typeof snapshot.simulatedBalance === 'number') setSimulatedBalance(snapshot.simulatedBalance);
        if (snapshot.facts) setFacts((previous) => ({ ...previous, ...snapshot.facts }));
        setLiveReady(true);
      })
      .catch((error) => {
        console.error('Nexus client portal bridge hydration failed', error);
        if (!cancelled) {
          clearLiveState();
          setLiveReady(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Trigger celebration feedback
  const triggerCelebration = (title: string, points: number, subtitle: string) => {
    setActiveCelebration({ title, points, subtitle });
    try {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#00D2B4', '#0EA5E9', '#F59E0B', '#10B981']
      });
    } catch {
      // Fallback gracefully if canvas-confetti is constrained
    }
  };

  const dismissCelebration = () => {
    setActiveCelebration(null);
  };

  // Complete a Mission
  const completeMission = (missionId: string) => {
    const bridge = getNexusClientPortalBridge();
    if (bridge?.mode === 'live') {
      void bridge.completeMission?.(missionId);
      return;
    }
    const targetMission = missions.find((m) => m.id === missionId);
    if (!targetMission || targetMission.completed) return;

    setMissions((prev) =>
      prev.map((m) => (m.id === missionId ? { ...m, completed: true, status: 'Completed' } : m))
    );

    const gainedPoints = targetMission.points;
    const newPoints = Math.min(100, profile.readinessPoints + gainedPoints);

    setProfile((prev) => ({
      ...prev,
      readinessPoints: newPoints
    }));

    // Update journey progress
    setJourneyNodes((prev) =>
      prev.map((node) => {
        if (node.tab === targetMission.targetTab) {
          return {
            ...node,
            progress: Math.min(100, node.progress + 15),
            status: node.progress + 15 >= 100 ? 'completed' : 'in-progress'
          };
        }
        return node;
      })
    );

    const isLevelUp = newPoints >= 85 && profile.readinessPoints < 85;

    if (isLevelUp) {
      triggerCelebration(
        'LEVEL UP: BANKABLE TIER UNLOCKED!',
        gainedPoints,
        `Congratulations, David! Vance Logistics LLC has officially unlocked the Bankable Tier at ${newPoints}/100 readiness. Institutional term sheets are now within reach.`
      );
    } else {
      triggerCelebration(
        `Mission Completed: +${gainedPoints} Readiness Points`,
        gainedPoints,
        `Your readiness score jumped to ${newPoints}/100 points.`
      );
    }

    // Contextual Clyde notification
    setClydeMessages((prev) => [
      ...prev,
      {
        id: `cm-${Date.now()}`,
        sender: 'clyde',
        text: isLevelUp
          ? `Incredible milestone, David! Completing "${targetMission.title}" boosted your readiness score to ${newPoints}/100, unlocking the prestigious "Bankable" tier! Your file is now eligible for prime unsecured commercial lines.`
          : `Outstanding work completing "${targetMission.title}"! You just earned +${gainedPoints} Readiness Points. You're now at ${newPoints}/100, bringing Vance Logistics LLC closer to Tier-1 Bankability.`,
        timestamp: 'Just now'
      }
    ]);
  };

  // Upload Document Simulation
  const uploadDocument = (docId: string, fileName: string, file?: File) => {
    const bridge = getNexusClientPortalBridge();
    if (bridge?.mode === 'live') {
      void bridge.uploadDocument?.(docId, fileName, file).then((result) => {
        if (!result.ok) return;
        setDocuments((prev) => prev.map((doc) => doc.id === docId ? { ...doc, status: 'reviewing', fileName, updatedAt: 'Uploaded just now', notes: 'Uploaded to the client-scoped document vault and awaiting GoClear review.' } : doc));
      });
      return;
    }
    setDocuments((prev) =>
      prev.map((doc) => {
        if (doc.id === docId) {
          return {
            ...doc,
            status: 'verified',
            fileName,
            fileSize: '3.4 MB',
            updatedAt: 'Verified just now by GoClear Audit Engine',
            notes: 'Successfully verified 90 days continuous operating deposits. Clean cash flow verified.'
          };
        }
        return doc;
      })
    );

    // If this was doc-4 (the critical bank statements), award points & mark mission
    if (docId === 'doc-4') {
      const addedPoints = 8;
      const newPoints = Math.min(100, profile.readinessPoints + addedPoints);
      setProfile((prev) => ({ ...prev, readinessPoints: newPoints }));

      // Complete mission m1 if not completed
      setMissions((prev) =>
        prev.map((m) => (m.id === 'm1' ? { ...m, completed: true, status: 'Completed' } : m))
      );

      // Update bankability pillar
      setBankabilityPillars((prev) =>
        prev.map((p) => {
          if (p.id === 'bp-3') {
            return {
              ...p,
              score: 92,
              status: 'strong',
              keyItems: p.keyItems.map((item) =>
                item.label.includes('Bank Statements') ? { ...item, pass: true } : item
              )
            };
          }
          if (p.id === 'bp-5') {
            return {
              ...p,
              score: 90,
              status: 'strong',
              keyItems: p.keyItems.map((item) =>
                item.label.includes('Bank Statements') ? { ...item, pass: true } : item
              )
            };
          }
          return p;
        })
      );

      const isLevelUp = newPoints >= 85;
      triggerCelebration(
        isLevelUp ? 'LEVEL UP: BANKABLE TIER UNLOCKED!' : 'Bank Statements Authenticated!',
        addedPoints,
        isLevelUp
          ? `${profile.companyName} reached ${newPoints}/100 readiness and unlocked the Bankable Tier! Prime credit facility term sheets are now accessible.`
          : `Cash flow validation cleared. Your Funding Readiness increased to ${newPoints}/100.`
      );
    }
  };

  // Toggle Business Setup Step
  const toggleSetupStep = (stepId: string) => {
    const bridge = getNexusClientPortalBridge();
    if (bridge?.mode === 'live') {
      void bridge.toggleSetupStep?.(stepId);
      return;
    }
    setSetupSteps((prev) =>
      prev.map((s) => {
        if (s.id === stepId) {
          const nextStatus = s.status === 'completed' ? 'attention' : 'completed';
          if (nextStatus === 'completed' && s.status !== 'completed') {
            triggerCelebration(`Setup Verified: ${s.title}`, s.points, 'Your commercial foundation has strengthened.');
          }
          return { ...s, status: nextStatus };
        }
        return s;
      })
    );
  };

  // Update Revolving Balance (Simulator)
  const updateRevolvingBalance = (newBalance: number) => {
    const bridge = getNexusClientPortalBridge();
    if (bridge?.mode === 'live') {
      void bridge.updateRevolvingBalance?.(newBalance);
      return;
    }
    setSimulatedBalance(newBalance);
  };

  // Open Clyde with Prompt
  const openClydeWithPrompt = (promptText: string) => {
    setIsClydeOpen(true);
    sendClydeQuery(promptText);
  };

  // Send Clyde AI Query
  const sendClydeQuery = async (queryText: string) => {
    if (!queryText.trim()) return;

    const userMsg: ClydeMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: queryText,
      timestamp: 'Just now'
    };

    setClydeMessages((prev) => [...prev, userMsg]);
    setIsClydeThinking(true);

    const bridge = getNexusClientPortalBridge();
    if (bridge?.mode === 'live' && bridge.sendClydeQuery) {
      try {
        const result = await bridge.sendClydeQuery(queryText);
        if (result.ok && result.data) {
          setClydeMessages((prev) => [...prev, result.data!]);
        }
      } finally {
        setIsClydeThinking(false);
      }
      return;
    }

    // Original Google AI Studio demo response engine; used only when no live bridge is connected.
    setTimeout(() => {
      let reply = '';
      let card: ClydeMessage['card'] = undefined;

      const lower = queryText.toLowerCase();

      if (lower.includes('blocking') || lower.includes('blocker') || lower.includes('stop')) {
        reply = `Looking at ${profile.companyName}'s current profile, you have two primary gating factors before commercial underwriters approve your $250,000 credit line:\n\n1. Missing 90-day verified bank statements (Document Vault).\n2. Credit utilization currently sits at 19% ($8,550 on $45,000 total limit), whereas institutional prime rates unlock at <10-15%.\n\nResolving both will elevate your composite bankability score into the 88+ tier.`;
        card = {
          type: 'blocker',
          title: 'Primary Gating Factor',
          description: 'Upload your 3 consecutive Chase commercial statements in the Document Vault.',
          actionText: 'Go to Document Vault',
          actionTab: 'documents'
        };
      } else if (lower.includes('next') || lower.includes('what should i do') || lower.includes('mission')) {
        reply = `Your highest ROI next action is: "Complete Business Banking Verification". By uploading your November, December, and January operating statements, your cash flow stability will be verified and you will immediately gain +8 Readiness Points. Following that, reducing your Chase Ink card balance by $2,000 will optimize your revolving utilization.`;
        card = {
          type: 'next-action',
          title: 'Immediate Next Action',
          description: 'Complete Business Banking Verification (+8 Readiness Points)',
          actionText: 'View Active Mission',
          actionTab: 'dashboard'
        };
      } else if (lower.includes('utilization') || lower.includes('credit') || lower.includes('score')) {
        reply = `Your personal credit is currently in excellent shape: Experian 742, TransUnion 738, and Equifax 748 with zero negative marks. However, your revolving utilization is 19% ($8,550 of $45k limit). In commercial underwriting, keeping your reported utilization under 10% ($4,500) signals supreme liquidity and protects against sudden interest rate increases.`;
        card = {
          type: 'next-action',
          title: 'Utilization Target',
          description: 'Current 19% → Target 10% ($4,050 paydown distance).',
          actionText: 'Open Utilization Gauge',
          actionTab: 'credit-utilization'
        };
      } else if (lower.includes('bankability') || lower.includes('pillar') || lower.includes('411')) {
        reply = `${profile.companyName} currently maintains a Bankability Score of 78/100. Your Entity Credibility (90%) and Credit Profile (88%) are prime strengths. Your primary improvement area is Contact Consistency (85%), specifically listing your company with National 411 directory under the exact Delaware registered agent address.`;
        card = {
          type: 'next-action',
          title: 'Bankability Strengthening',
          description: 'Entity Credibility (90%) · Banking (74%) · Contact (85%)',
          actionText: 'Inspect Bankability Pillars',
          actionTab: 'business-bankability'
        };
      } else if (lower.includes('funding') || lower.includes('capital') || lower.includes('line of credit')) {
        reply = `Based on your Delaware LLC structure, 14 months operating history, and 742 Experian score, ${profile.companyName} qualifies right now for Equipment Financing ($125,000) and Revenue-Based Working Capital ($100,000). To secure the Prime Commercial Line of Credit ($250,000 at Prime + 1.5%), we need your bank statements verified in the vault.`;
        card = {
          type: 'funding-update',
          title: 'Funding Readiness Status',
          description: '2 of 4 Institutional Facilities currently matched. Tier 1 requires bank statement verification.',
          actionText: 'View Funding Matrix',
          actionTab: 'funding-readiness'
        };
      } else {
        reply = `I'm analyzing ${profile.companyName}'s live readiness telemetry. You're at 72% Funding Readiness. To move forward into the "Bankable" tier, I recommend addressing the verified bank statements in your Document Vault and checking off the 411 directory alignment in your Business Setup roadmap. How else can I assist your financial readiness journey today?`;
      }

      const clydeResponse: ClydeMessage = {
        id: `clyde-${Date.now()}`,
        sender: 'clyde',
        text: reply,
        timestamp: 'Just now',
        card
      };

      setClydeMessages((prev) => [...prev, clydeResponse]);
      setIsClydeThinking(false);
    }, 700);
  };

  // Request Underwriting Review
  const requestUnderwritingReview = async (notes: string): Promise<boolean> => {
    const bridge = getNexusClientPortalBridge();
    if (bridge?.mode === 'live' && bridge.requestUnderwritingReview) {
      const result = await bridge.requestUnderwritingReview(notes);
      if (!result.ok) return false;
    }
    return new Promise((resolve) => {
      setTimeout(() => {
        setJourneyNodes((prev) =>
          prev.map((n) => (n.id === 'review' ? { ...n, status: 'in-progress', progress: 65 } : n))
        );
        triggerCelebration(
          'Underwriter Audit Packet Dispatched',
          20,
          `GoClear Credit Committee has received ${profile.companyName} dossier. Formal feedback within 24 business hours.`
        );
        setClydeMessages((prev) => [
          ...prev,
          {
            id: `cm-${Date.now()}`,
            sender: 'clyde',
            text: `Underwriting review requested! Your complete credit dossier, Delaware corporate standing, and verified bank records have been bundled into the GoClear Institutional Packet. An underwriter is assigned to your file.`,
            timestamp: 'Just now'
          }
        ]);
        resolve(true);
      }, 1000);
    });
  };

  return (
    <PortalContext.Provider
      value={{
        activeTab,
        setActiveTab,
        profile,
        levels: LEVELS,
        currentLevel,
        nextLevel,
        journeyNodes,
        missions,
        achievements,
        documents,
        bankabilityPillars,
        setupSteps,
        recommendations,
        resources,
        clydeMessages,
        isClydeOpen,
        setIsClydeOpen,
        isClydeThinking,
        activeCelebration,
        dismissCelebration,
        completeMission,
        uploadDocument,
        toggleSetupStep,
        sendClydeQuery,
        openClydeWithPrompt,
        requestUnderwritingReview,
        updateRevolvingBalance,
        simulatedBalance
        ,liveReady
        ,facts
        ,liveMode
      }}
    >
      {children}
    </PortalContext.Provider>
  );
};

export const usePortal = () => {
  const context = useContext(PortalContext);
  if (!context) {
    throw new Error('usePortal must be used within a PortalProvider');
  }
  return context;
};
