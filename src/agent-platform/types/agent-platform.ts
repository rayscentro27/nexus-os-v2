// Nexus Agent Platform — TypeScript adapter types
// These types mirror the Python-side adapter interfaces for frontend/TypeScript usage.

export interface AgentState {
  agent_id: string;
  mission_id: string;
  thread_id: string;
  messages: Array<{ role: string; content: string }>;
  user_message: string;
  assistant_response: string;
  intent: string | null;
  context: Record<string, any>;
  active_context: Record<string, any>;
  search_results: Array<Record<string, any>>;
  research_synthesis: string;
  tool_calls: Array<Record<string, any>>;
  tool_results: Array<Record<string, any>>;
  slots: Record<string, any>;
  slot_fill_target: string | null;
  trace_id: string;
  span_id: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

export interface Capability {
  name: string;
  description: string;
  requires_approval: boolean;
  safety_boundary: string;
}

export interface Mission {
  mission_id: string;
  agent_id: string;
  status: "RECEIVED" | "AUTHORIZED" | "ROUTED" | "EXECUTING" | "RESULT_STORED" | "RESPONSE_COMPOSED" | "RESPONSE_SENT" | "COMPLETED" | "FAILED";
  user_message: string;
  result: string | null;
  telegram_message_id: number | null;
  created_at: string;
  updated_at: string;
  error: string | null;
  metadata: Record<string, any>;
}

export interface FeatureFlags {
  NEXUS_AGENT_PLATFORM_ENABLED: boolean;
  NEXUS_HERMES_LANGGRAPH_ENABLED: boolean;
  ALPHA_LANGGRAPH_ENABLED: boolean;
  TEMPORAL_WORKFLOWS_ENABLED: boolean;
  LITELLM_GATEWAY_ENABLED: boolean;
  LANGFUSE_TRACING_ENABLED: boolean;
  LEGACY_HERMES_ROUTER_FALLBACK_ENABLED: boolean;
}

export interface CeoReport {
  headline: string;
  working?: string;
  needs_attention?: string;
  changed?: string;
  recommendation?: string;
  action_required?: string;
  phoenix_time: string;
  detail?: string;
}
