/**
 * Nexus automation categories — the canonical list of every major Nexus category that the
 * automation classification applies to. Automation is classified CATEGORY-BY-CATEGORY, never as
 * one generic switch.
 *
 * Pure / deterministic. No I/O.
 */
import type { NexusDepartment } from './nexusProjectTypes';

export type AutomationCategoryId =
  | 'research_source_intake'
  | 'youtube_research'
  | 'seo_marketing'
  | 'affiliate_marketing'
  | 'content_opportunity_lab'
  | 'creative_studio'
  | 'design_library'
  | 'goclear_revenue_hub'
  | 'goclear_apex_client_intake'
  | 'credit_repair_funding_guidance'
  | 'opportunity_lab'
  | 'agent_jobs'
  | 'integrations'
  | 'events_feed_proof_ledger'
  | 'approvals'
  | 'ray_review_queue'
  | 'hermes_jarvis'
  | 'trading_lab'
  | 'scheduler_automation'
  | 'production_deployment'
  | 'email_sms_dm_social'
  | 'ads_spend'
  | 'database_supabase'
  | 'files_reports_imports'
  | 'notebooklm_research_library'
  | 'grants_funding_opportunities'
  | 'business_credit_vendor_accounts'
  | 'client_portal'
  | 'admin_tenants_users'
  | 'monitoring_health';

export interface AutomationCategoryMeta {
  category_id: AutomationCategoryId;
  category_name: string;
  owner_department: NexusDepartment;
}

/** All 30 categories, in the order Ray listed them. */
export const AUTOMATION_CATEGORIES: AutomationCategoryMeta[] = [
  { category_id: 'research_source_intake', category_name: 'Research / Source Intake', owner_department: 'source_intake' },
  { category_id: 'youtube_research', category_name: 'YouTube Research', owner_department: 'source_intake' },
  { category_id: 'seo_marketing', category_name: 'SEO / Marketing', owner_department: 'growth' },
  { category_id: 'affiliate_marketing', category_name: 'Affiliate Marketing', owner_department: 'opportunity_lab' },
  { category_id: 'content_opportunity_lab', category_name: 'Content Opportunity Lab', owner_department: 'growth' },
  { category_id: 'creative_studio', category_name: 'Creative Studio', owner_department: 'creative_studio' },
  { category_id: 'design_library', category_name: 'Design Library', owner_department: 'design_library' },
  { category_id: 'goclear_revenue_hub', category_name: 'GoClear Revenue Hub', owner_department: 'opportunity_lab' },
  { category_id: 'goclear_apex_client_intake', category_name: 'GoClear / Apex Client Intake', owner_department: 'opportunity_lab' },
  { category_id: 'credit_repair_funding_guidance', category_name: 'Credit Repair / Funding Guidance', owner_department: 'opportunity_lab' },
  { category_id: 'opportunity_lab', category_name: 'Opportunity Lab', owner_department: 'opportunity_lab' },
  { category_id: 'agent_jobs', category_name: 'Agent Jobs', owner_department: 'agent_jobs' },
  { category_id: 'integrations', category_name: 'Integrations', owner_department: 'integrations' },
  { category_id: 'events_feed_proof_ledger', category_name: 'Events Feed / Proof Ledger', owner_department: 'events_feed' },
  { category_id: 'approvals', category_name: 'Approvals', owner_department: 'approvals' },
  { category_id: 'ray_review_queue', category_name: 'Ray Review Queue', owner_department: 'command_center' },
  { category_id: 'hermes_jarvis', category_name: 'Hermes / Jarvis', owner_department: 'command_center' },
  { category_id: 'trading_lab', category_name: 'Trading Lab', owner_department: 'trading_lab' },
  { category_id: 'scheduler_automation', category_name: 'Scheduler / Automation', owner_department: 'ops_improvements' },
  { category_id: 'production_deployment', category_name: 'Production / Deployment', owner_department: 'ops_improvements' },
  { category_id: 'email_sms_dm_social', category_name: 'Email / SMS / DM / Social', owner_department: 'growth' },
  { category_id: 'ads_spend', category_name: 'Ads / Spend', owner_department: 'growth' },
  { category_id: 'database_supabase', category_name: 'Database / Supabase', owner_department: 'ops_improvements' },
  { category_id: 'files_reports_imports', category_name: 'Files / Reports / Imports', owner_department: 'ops_improvements' },
  { category_id: 'notebooklm_research_library', category_name: 'NotebookLM / Research Library', owner_department: 'source_intake' },
  { category_id: 'grants_funding_opportunities', category_name: 'Grants / Funding Opportunities', owner_department: 'opportunity_lab' },
  { category_id: 'business_credit_vendor_accounts', category_name: 'Business Credit / Vendor Accounts', owner_department: 'opportunity_lab' },
  { category_id: 'client_portal', category_name: 'Client Portal', owner_department: 'opportunity_lab' },
  { category_id: 'admin_tenants_users', category_name: 'Admin / Tenants / Users', owner_department: 'ops_improvements' },
  { category_id: 'monitoring_health', category_name: 'Monitoring / Health', owner_department: 'ops_improvements' },
];

export const AUTOMATION_CATEGORY_IDS: AutomationCategoryId[] = AUTOMATION_CATEGORIES.map((c) => c.category_id);

export function getAutomationCategory(id: AutomationCategoryId): AutomationCategoryMeta | undefined {
  return AUTOMATION_CATEGORIES.find((c) => c.category_id === id);
}
