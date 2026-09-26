import type {
  ClientProfile,
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

export type PortalDataMode = 'demo' | 'live';

export interface PortalSnapshot {
  profile?: ClientProfile;
  journeyNodes?: JourneyNode[];
  missions?: Mission[];
  achievements?: Achievement[];
  documents?: DocumentItem[];
  bankabilityPillars?: BankabilityPillar[];
  setupSteps?: BusinessSetupStep[];
  recommendations?: Recommendation[];
  resources?: ResourceItem[];
  clydeMessages?: ClydeMessage[];
  simulatedBalance?: number;
  facts?: {
    creditScore?: number;
    utilizationPercent?: number;
    utilizationTargetPercent?: number;
    documentVerifiedCount?: number;
    documentTotalCount?: number;
    bankabilityScore?: number;
    fundingTargetLabel?: string;
  };
}

export interface PortalActionResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
}

export interface NexusClientPortalBridge {
  mode: PortalDataMode;
  loadSnapshot?: () => Promise<PortalSnapshot>;
  completeMission?: (missionId: string) => Promise<PortalActionResult>;
  uploadDocument?: (docId: string, fileName: string, file?: File) => Promise<PortalActionResult>;
  toggleSetupStep?: (stepId: string) => Promise<PortalActionResult>;
  updateRevolvingBalance?: (newBalance: number) => Promise<PortalActionResult>;
  sendClydeQuery?: (query: string) => Promise<PortalActionResult<ClydeMessage>>;
  requestUnderwritingReview?: (notes: string) => Promise<PortalActionResult>;
}

declare global {
  interface Window {
    __NEXUS_CLIENT_PORTAL_BRIDGE__?: NexusClientPortalBridge;
  }
}

export function getNexusClientPortalBridge(): NexusClientPortalBridge | null {
  if (typeof window === 'undefined') return null;
  return window.__NEXUS_CLIENT_PORTAL_BRIDGE__ ?? null;
}

export async function loadNexusPortalSnapshot(): Promise<PortalSnapshot | null> {
  const bridge = getNexusClientPortalBridge();
  if (!bridge?.loadSnapshot) return null;
  return bridge.loadSnapshot();
}
