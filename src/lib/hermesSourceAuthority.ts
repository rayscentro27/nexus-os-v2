import type { IntentDomain } from './hermesIntentFrame';

export type SourceLevel = 'live_supabase' | 'latest_report' | 'local_registry' | 'static_context' | 'page_context' | 'local_trace' | 'general_reasoning' | 'unknown';

export interface SourceAuthorityEntry {
  domain: IntentDomain;
  levels: SourceLevel[];
  label: string;
}

export const SOURCE_AUTHORITY_TABLE: Record<IntentDomain, SourceAuthorityEntry> = {
  business_opportunities: {
    domain: 'business_opportunities',
    levels: ['live_supabase', 'latest_report', 'static_context', 'unknown'],
    label: 'business opportunity data',
  },
  approvals: {
    domain: 'approvals',
    levels: ['live_supabase', 'latest_report', 'static_context', 'unknown'],
    label: 'approval and Ray Review records',
  },
  clients: {
    domain: 'clients',
    levels: ['live_supabase', 'latest_report', 'unknown'],
    label: 'client profiles',
  },
  monetization: {
    domain: 'monetization',
    levels: ['live_supabase', 'latest_report', 'static_context', 'unknown'],
    label: 'monetization and revenue data',
  },
  research: {
    domain: 'research',
    levels: ['live_supabase', 'latest_report', 'local_registry', 'unknown'],
    label: 'research sources and runs',
  },
  trading: {
    domain: 'trading',
    levels: ['latest_report', 'local_registry', 'unknown'],
    label: 'trading strategies and proofs',
  },
  credit_funding: {
    domain: 'credit_funding',
    levels: ['live_supabase', 'latest_report', 'static_context', 'unknown'],
    label: 'credit and funding readiness',
  },
  nexus_product_build: {
    domain: 'nexus_product_build',
    levels: ['local_registry', 'static_context', 'unknown'],
    label: 'Nexus product build status',
  },
  system_health: {
    domain: 'system_health',
    levels: ['live_supabase', 'latest_report', 'local_registry', 'unknown'],
    label: 'system health status',
  },
  reports: {
    domain: 'reports',
    levels: ['local_registry', 'latest_report', 'unknown'],
    label: 'reports and audits',
  },
  ray_review: {
    domain: 'ray_review',
    levels: ['live_supabase', 'latest_report', 'unknown'],
    label: 'Ray Review records',
  },
  current_page: {
    domain: 'current_page',
    levels: ['page_context', 'unknown'],
    label: 'current page metadata',
  },
  specialist_agents: {
    domain: 'specialist_agents',
    levels: ['local_registry', 'unknown'],
    label: 'specialist agent registry',
  },
  trace: {
    domain: 'trace',
    levels: ['local_trace', 'unknown'],
    label: 'routing trace and provenance',
  },
  general_conversation: {
    domain: 'general_conversation',
    levels: ['general_reasoning', 'unknown'],
    label: 'general reasoning',
  },
  external_info: {
    domain: 'external_info',
    levels: ['unknown'],
    label: 'external information',
  },
  unknown: {
    domain: 'unknown',
    levels: ['unknown'],
    label: 'unknown domain',
  },
};

export function getSourceAuthorityLabel(level: SourceLevel): string {
  switch (level) {
    case 'live_supabase': return 'I used live Supabase data.';
    case 'latest_report': return 'I used the latest local report.';
    case 'local_registry': return 'I used the local registry.';
    case 'static_context': return 'I used static Nexus context because live and report data were not available.';
    case 'page_context': return 'I used page metadata passed by the UI.';
    case 'local_trace': return 'I used the last routing trace.';
    case 'general_reasoning': return 'I used general reasoning.';
    case 'unknown': return 'The source is unverified.';
  }
}

export function getSourceAuthorityForDomain(domain: IntentDomain): SourceAuthorityEntry {
  return SOURCE_AUTHORITY_TABLE[domain] || SOURCE_AUTHORITY_TABLE.unknown;
}
