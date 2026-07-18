import { getBrainProfile } from './brainRegistry';
import { getIntelligenceRecord } from '../intelligence/intelligenceRegistry';

export type BrainHandoffEventName = 'BRAIN_HANDOFF_REQUESTED' | 'BRAIN_HANDOFF_APPROVED' | 'BRAIN_HANDOFF_DENIED' | 'BRAIN_HANDOFF_COMPLETED' | 'KNOWLEDGE_PROMOTION_REQUESTED' | 'KNOWLEDGE_PROMOTION_APPROVED' | 'KNOWLEDGE_PROMOTION_REJECTED';

export interface BrainHandoffDecision {
  allowed: boolean;
  event: {
    action: BrainHandoffEventName;
    fromBrainId: string;
    toBrainId: string;
    sanitized: true;
    summary: string;
  };
  reasons: string[];
}

export function evaluateBrainHandoff(fromBrainId: string, toBrainId: string, recordIds: string[]): BrainHandoffDecision {
  const from = getBrainProfile(fromBrainId);
  const to = getBrainProfile(toBrainId);
  const reasons: string[] = [];
  if (!from || !to) reasons.push('Source or target brain profile is missing.');
  const records = recordIds.map((id) => getIntelligenceRecord(id)).filter(Boolean);
  if (fromBrainId === 'alpha_research' && toBrainId === 'nexus_hermes') {
    const unapproved = records.filter((record) => record?.approvalState !== 'APPROVED');
    if (unapproved.length) reasons.push('Alpha findings require review before Hermes may use them as knowledge.');
  }
  const prohibited = records.filter((record) => record?.prohibitedBrainIds.includes(toBrainId));
  if (prohibited.length) reasons.push('One or more records prohibit the target brain.');
  const allowed = reasons.length === 0;
  return {
    allowed,
    event: {
      action: allowed ? 'BRAIN_HANDOFF_APPROVED' : 'BRAIN_HANDOFF_DENIED',
      fromBrainId,
      toBrainId,
      sanitized: true,
      summary: allowed ? 'Brain handoff allowed by profile and record policy.' : reasons.join(' '),
    },
    reasons,
  };
}
