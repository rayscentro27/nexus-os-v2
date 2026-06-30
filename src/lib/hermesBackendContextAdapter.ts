/**
 * Hermes Backend Context Adapter — stub for live backend/model queries.
 *
 * Currently: NO real AI/model access from this chat layer.
 * Future: when a real model endpoint is wired.
 */

export interface BackendContextResult {
  liveBackendAvailable: false;
  reason: string;
  modelAvailable: boolean;
}

/** Check if a real backend/model is available. */
export function isBackendAvailable(): boolean {
  return false;
}

/** Get an honest status message about backend availability. */
export function getBackendStatusMessage(): string {
  return 'I am currently using local bundled Nexus context, page context, browser time, local activity journal, and localStorage memory. I do not yet have live Supabase, live web search, or real AI model access from this chat layer.';
}

/** Check if a real web search is available. */
export function isWebSearchAvailable(): boolean {
  return false;
}
