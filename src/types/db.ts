// Row types mirroring supabase/migrations/0001_nexus_os_v2_core.sql.

export type Lane = 'communication' | 'monetization' | 'automation' | 'social' | 'trading' | 'system';

export interface NexusEvent {
  id: string;
  created_at: string;
  lane: Lane | string;
  source: string | null;
  action: string;
  status: string;
  title: string | null;
  summary: string | null;
  payload: Record<string, unknown>;
  visible_to_ray: boolean;
  severity: string;
  correlation_id: string | null;
  job_id: string | null;
  approval_id: string | null;
}

export interface AgentJob {
  id: string;
  created_at: string;
  updated_at: string;
  lane: string;
  job_type: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error: string | null;
  locked_by: string | null;
  locked_at: string | null;
  completed_at: string | null;
}

export interface Approval {
  id: string;
  created_at: string;
  lane: string;
  item_type: string;
  item_id: string | null;
  status: string;
  title: string | null;
  summary: string | null;
  payload: Record<string, unknown>;
  approved_by: string | null;
  decided_at: string | null;
}

export interface SocialAccount {
  id: string;
  created_at: string;
  platform: string;
  account_name: string;
  account_id: string;
  username: string | null;
  status: string;
  token_env_key: string | null;
  publish_enabled: boolean;
  last_verified_at: string | null;
  metadata: Record<string, unknown>;
}

export interface SocialPost {
  id: string;
  created_at: string;
  platform: string;
  account_id: string | null;
  content: string;
  media_url: string | null;
  status: string;
  score: number | null;
  reason: string | null;
  approval_id: string | null;
  published_url: string | null;
  published_external_id: string | null;
  payload: Record<string, unknown>;
}

export interface CreativeAsset {
  id: string;
  created_at: string;
  asset_type: string;
  title: string | null;
  content: string | null;
  platform: string | null;
  offer: string | null;
  score: number | null;
  status: string;
  payload: Record<string, unknown>;
}

export interface BusinessOpportunity {
  id: string;
  created_at: string;
  title: string;
  summary: string | null;
  score: number | null;
  status: string;
  plan: Record<string, unknown>;
  payload: Record<string, unknown>;
}

export interface TradingSignal {
  id: string;
  created_at: string;
  market: string | null;
  instrument: string | null;
  strategy: string | null;
  side: string | null;
  confidence: number | null;
  entry: Record<string, unknown>;
  risk: Record<string, unknown>;
  status: string;
  payload: Record<string, unknown>;
}

export interface DemoTrade {
  id: string;
  created_at: string;
  signal_id: string | null;
  broker: string;
  environment: string;
  instrument: string | null;
  side: string | null;
  units: number | null;
  status: string;
  external_trade_id: string | null;
  pnl: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  payload: Record<string, unknown>;
}

export interface TelegramMessage {
  id: string;
  created_at: string;
  purpose: string;
  chat_label: string | null;
  message_hash: string;
  body_preview: string | null;
  status: string;
  suppressed: boolean;
  payload: Record<string, unknown>;
}

export interface SystemHealth {
  id: string;
  created_at: string;
  component: string;
  status: string;
  summary: string | null;
  payload: Record<string, unknown>;
}
