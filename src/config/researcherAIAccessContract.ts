/**
 * Nexus OS v2 — Researcher AI "no client PII" access contract.
 * Pure / deterministic. No I/O.
 */

export const RESEARCHER_MAY = [
  'browse_public_sources',
  'research_credit_laws_concepts',
  'research_business_credit_rules',
  'research_funding_rules',
  'research_affiliate_programs',
  'create_proposed_knowledge_records',
  'create_source_summaries',
] as const;

export const RESEARCHER_MUST_NOT = [
  'access_client_records',
  'access_credit_reports',
  'access_smartcredit_imports',
  'access_bank_statements',
  'access_client_letters',
  'access_funding_documents',
  'generate_client_specific_recommendations',
] as const;

export const RESEARCHER_AI_CONTRACT = {
  role: 'researcher_ai',
  internet_allowed: true,
  client_pii_allowed: false,
  knowledge_output: 'proposed_or_draft_only',
  notes: 'Researcher AI produces only PROPOSED/draft knowledge records that must be approved before the Credit Specialist can use them. Never touches client PII or generates client-specific recommendations.',
  may: RESEARCHER_MAY,
  must_not: RESEARCHER_MUST_NOT,
} as const;
