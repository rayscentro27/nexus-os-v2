/**
 * Nexus OS v2 — Approved knowledge model.
 *
 * Researcher AI creates draft/proposed knowledge; the Credit Specialist / Client Chat may only use
 * entries that are `approved` AND flagged usable. Pure / deterministic. No I/O.
 */

export type KnowledgeStatus = 'draft' | 'needs_review' | 'approved' | 'retired' | 'blocked';

export interface ApprovedKnowledgeEntry {
  knowledge_id: string;
  topic: string;
  category: string;
  source_type: string;
  source_url: string | null;
  source_summary: string;
  extracted_rule: string;
  compliance_notes: string;
  approval_status: KnowledgeStatus;
  approved_by: string | null;
  approved_at: string | null;
  usable_by_credit_specialist: boolean;
  usable_by_client_chat: boolean;
  retired_reason: string | null;
}

/** Researcher output always starts as draft/proposed (never directly usable). */
export function proposedKnowledge(partial: Partial<ApprovedKnowledgeEntry> & { knowledge_id: string; topic: string; category: string; extracted_rule: string }): ApprovedKnowledgeEntry {
  return {
    source_type: 'public_research',
    source_url: null,
    source_summary: '',
    compliance_notes: 'Pending compliance review.',
    approval_status: 'draft',
    approved_by: null,
    approved_at: null,
    usable_by_credit_specialist: false,
    usable_by_client_chat: false,
    retired_reason: null,
    ...partial,
  };
}

export function isUsableByCreditSpecialist(k: ApprovedKnowledgeEntry): boolean {
  return k.approval_status === 'approved' && k.usable_by_credit_specialist;
}

export function isUsableByClientChat(k: ApprovedKnowledgeEntry): boolean {
  return k.approval_status === 'approved' && k.usable_by_client_chat;
}

/** Sample/dev knowledge entries (no client data). */
export const SAMPLE_APPROVED_KNOWLEDGE: ApprovedKnowledgeEntry[] = [
  {
    knowledge_id: 'k-fcra-dispute-basics',
    topic: 'FCRA dispute basics',
    category: 'credit_repair',
    source_type: 'public_law',
    source_url: null,
    source_summary: 'Consumers may dispute inaccurate items; bureaus must investigate within set timelines.',
    extracted_rule: 'Disputes target inaccurate/unverifiable items; never advise removing accurate items.',
    compliance_notes: 'Educational only; no deletion guarantees.',
    approval_status: 'approved',
    approved_by: 'ray',
    approved_at: '2026-06-26T00:00:00.000Z',
    usable_by_credit_specialist: true,
    usable_by_client_chat: false,
    retired_reason: null,
  },
  {
    knowledge_id: 'k-business-bankability',
    topic: 'Business bankability fundamentals',
    category: 'business_credit',
    source_type: 'public_research',
    source_url: null,
    source_summary: 'Entity, EIN, address, phone, bank account, and DUNS profile improve bankability.',
    extracted_rule: 'Recommend completing required bankability items before funding applications.',
    compliance_notes: 'Educational only; no funding guarantees.',
    approval_status: 'approved',
    approved_by: 'ray',
    approved_at: '2026-06-26T00:00:00.000Z',
    usable_by_credit_specialist: true,
    usable_by_client_chat: true,
    retired_reason: null,
  },
  {
    knowledge_id: 'k-proposed-draft-example',
    topic: 'Proposed draft (not yet usable)',
    category: 'funding',
    source_type: 'public_research',
    source_url: null,
    source_summary: 'Researcher draft pending review.',
    extracted_rule: 'TBD after review.',
    compliance_notes: 'Pending compliance review.',
    approval_status: 'draft',
    approved_by: null,
    approved_at: null,
    usable_by_credit_specialist: false,
    usable_by_client_chat: false,
    retired_reason: null,
  },
];
