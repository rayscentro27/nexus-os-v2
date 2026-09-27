export type TabType =
  | 'dashboard'
  | 'profile'
  | 'settings'
  | 'credit-profile'
  | 'credit-utilization'
  | 'documents'
  | 'business-setup'
  | 'business-bankability'
  | 'funding-readiness'
  | 'recommendations'
  | 'resources'
  | 'request-review';

export interface LevelInfo {
  id: string;
  name: string;
  minPoints: number;
  maxPoints: number;
  badge: string;
  description: string;
  benefits: string[];
}

export interface ClientProfile {
  name: string;
  companyName: string;
  role: string;
  ein: string;
  duns: string;
  entityType: string;
  stateOfFormation: string;
  industry: string;
  naicsCode: string;
  memberSince: string;
  readinessPoints: number;
  readinessTarget: number;
  currentLevelIndex: number;
  streakDays: number;
  avatarUrl: string;
  targetFundingAmount: number;
}

export interface JourneyNode {
  id: string;
  label: string;
  tab: TabType;
  status: 'completed' | 'in-progress' | 'pending' | 'locked';
  progress: number;
  scoreWeight: number;
  description: string;
}

export interface Mission {
  id: string;
  title: string;
  category: 'Credit' | 'Bankability' | 'Documents' | 'Setup' | 'Funding';
  points: number;
  impact: 'High' | 'Critical' | 'Medium';
  timeEstimate: string;
  description: string;
  actionText: string;
  targetTab: TabType;
  completed: boolean;
  status?: 'In Progress' | 'Completed' | 'Blocked';
}

export interface Achievement {
  id: string;
  title: string;
  unlockedAt: string;
  description: string;
  iconName: string;
  category: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  category: string;
  status: 'verified' | 'reviewing' | 'required' | 'optional';
  requiredFor: string;
  fileName?: string;
  fileSize?: string;
  updatedAt: string;
  notes?: string;
}

export interface BankabilityPillar {
  id: string;
  name: string;
  score: number;
  maxScore: number;
  weight: string;
  status: 'strong' | 'good' | 'needs-attention' | 'critical';
  details: string;
  keyItems: { label: string; pass: boolean }[];
}

export interface BusinessSetupStep {
  id: string;
  stepNumber: number;
  title: string;
  field: string;
  value: string;
  status: 'completed' | 'attention' | 'pending';
  whyItMatters: string;
  readinessImpact: string;
  points: number;
}

export interface Recommendation {
  id: string;
  title: string;
  priority: 'HIGH IMPACT' | 'QUICK WIN' | 'IMPORTANT' | 'OPTIONAL';
  category: string;
  impactScore: string;
  reason: string;
  actionLabel: string;
  tabTarget: TabType;
  clydePrompt: string;
}

export interface ResourceItem {
  id: string;
  title: string;
  type: 'Executive Guide' | 'Video Masterclass' | 'Underwriting Checklist' | 'Legal Blueprint';
  duration: string;
  stage: string;
  summary: string;
  author: string;
  imageThumbnail: string;
}

export interface ClydeMessage {
  id: string;
  sender: 'clyde' | 'user';
  text: string;
  timestamp: string;
  card?: {
    type: 'blocker' | 'next-action' | 'funding-update' | 'doc-needed';
    title: string;
    description: string;
    actionText: string;
    actionTab?: TabType;
  };
}
