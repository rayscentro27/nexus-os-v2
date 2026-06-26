export interface NexusResearchReportDefinition {
  report_id: string;
  title: string;
  department: string;
  source_reports: string[];
  default_limit: number;
  approval_required: false;
}

export const NEXUS_RESEARCH_REPORTS: NexusResearchReportDefinition[] = [
  {
    report_id: 'weekly_top_research',
    title: 'Weekly Top Research Report',
    department: 'command_center',
    source_reports: [
      'youtube_transcript_review',
      'seo_keyword_scout',
      'affiliate_opportunity_tracker',
      'seo_affiliate_content_planner',
      'research_to_experiment',
      'content_opportunity_lab',
    ],
    default_limit: 10,
    approval_required: false,
  },
  {
    report_id: 'department_top_n',
    title: 'Department Top-N Report',
    department: 'selected_department',
    source_reports: ['task_requests', 'research_sources', 'local_runtime_reports'],
    default_limit: 10,
    approval_required: false,
  },
];

export function researchReportStatusSummary(): string {
  return 'Research reports are internal summaries. They do not publish, send, trade, deploy, or activate schedulers.';
}
