/** Universal safe-read layer. Thin typed wrappers over listTable so tabs stop inventing their own
 *  data access. Read-only; admin RLS applies; returns [] when unconfigured/blocked. */
import { listTable, type Row } from '../services/db';

type Opts = { limit?: number; order?: string; ascending?: boolean; eq?: [string, string] };

export const nexusData = {
  approvals: (o: Opts = {}) => listTable('approvals', { order: 'created_at', limit: 30, ...o }),
  taskRequests: (o: Opts = {}) => listTable('task_requests', { order: 'created_at', limit: 30, ...o }),
  agentJobs: (o: Opts = {}) => listTable('agent_jobs', { order: 'created_at', limit: 30, ...o }),
  events: (o: Opts = {}) => listTable('nexus_events', { order: 'created_at', limit: 30, ...o }),
  systemHealth: (o: Opts = {}) => listTable('system_health', { order: 'created_at', limit: 30, ...o }),
  researchSources: (o: Opts = {}) => listTable('research_sources', { order: 'created_at', limit: 30, ...o }),
  intakeEvents: (o: Opts = {}) => listTable('intake_events', { order: 'created_at', limit: 30, ...o }),
  transcriptReviews: (o: Opts = {}) => listTable('transcript_reviews', { order: 'created_at', limit: 30, ...o }),
  creativeAssets: (o: Opts = {}) => listTable('creative_assets', { order: 'created_at', limit: 30, ...o }),
  socialPosts: (o: Opts = {}) => listTable('social_posts', { order: 'created_at', limit: 30, ...o }),
  modelRoutes: (o: Opts = {}) => listTable('model_routes', { order: 'created_at', limit: 30, ...o }),
  modelProviders: (o: Opts = {}) => listTable('model_providers', { order: 'provider_key', ascending: true, limit: 30, ...o }),
};

export type { Row };
