import type { AlphaProviderName } from './alphaProviderStatus';

export type AlphaProviderSource='deterministic_local'|'ollama_local'|'groq_backend'|'openrouter_backend'|'web_search_backend'|'url_review_backend'|'unavailable_fallback';
export type AlphaMemorySource='none'|'session_memory'|'local_alpha_memory'|'local_storage'|'report_context';
export type AlphaWebProvider='none'|'duckduckgo_keyless'|'searxng'|'firecrawl'|'firecrawl_keyless'|'brave'|'hermes_agent_skill';
export type AlphaWebStatus='unavailable'|'disabled'|'connector_missing'|'available'|'searched'|'extracted'|'failed';
export type AlphaCostLabel='local_free'|'hosted_estimate'|'search_free_or_keyless'|'unknown_estimate';

export type AlphaRouteTrace={
  message_id:string; timestamp_local:string; timestamp_source:'browser_local'|'server_time'|'fallback'; mode:string;
  selected_provider:AlphaProviderName; provider_used:AlphaProviderName; provider_source:AlphaProviderSource; model_used:string;
  memory_used:boolean; memory_source:AlphaMemorySource; reports_used:boolean; report_sources:string[];
  web_used:boolean; web_provider:AlphaWebProvider; web_status:AlphaWebStatus; web_query:string; web_result_count:number;
  supabase_used:false; client_data_used:false; reason_for_provider_selection:string; fallback_reason:string;
  estimated_hosted_call:boolean; estimated_search_call:boolean; estimated_cost_label:AlphaCostLabel;
};

export function buildTrace(overrides:Partial<AlphaRouteTrace>={}):AlphaRouteTrace { const now=new Date(); return {
  message_id:`alpha-${now.getTime()}`,timestamp_local:now.toISOString(),timestamp_source:'browser_local',mode:'General Conversation',
  selected_provider:'deterministic_local',provider_used:'deterministic_local',provider_source:'deterministic_local',model_used:'deterministic-rules-v2',
  memory_used:false,memory_source:'none',reports_used:false,report_sources:[],web_used:false,web_provider:'none',web_status:'disabled',web_query:'',web_result_count:0,
  supabase_used:false,client_data_used:false,reason_for_provider_selection:'Cost-safe deterministic fallback selected.',fallback_reason:'',estimated_hosted_call:false,estimated_search_call:false,estimated_cost_label:'local_free',...overrides
}; }

export function traceSummary(t:AlphaRouteTrace){const source=t.provider_source==='groq_backend'?'Groq backend':t.provider_source==='openrouter_backend'?'OpenRouter backend':t.provider_source==='ollama_local'?'Ollama local':t.provider_source==='unavailable_fallback'?'deterministic_local fallback':'deterministic_local';const memory=t.memory_used?t.memory_source.replaceAll('_',' '):'none';const web=t.web_used?`${t.web_provider} search`:`${t.web_status==='disabled'?'off':t.web_status}`;return `Response source: ${source} · Memory: ${memory} · Web: ${web} · No Supabase · No client data`;}