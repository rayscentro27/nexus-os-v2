export type HermesBlockerKey =
  | 'youtube_not_proven_live'
  | 'hermes_live_model_not_configured'
  | 'hermes_web_search_not_configured'
  | 'token_rate_limits_unproven'
  | 'plist_loaded_only'
  | 'remote_collector_refresh_not_secure'
  | 'durable_cross_device_memory_missing';

const EXPLANATIONS: Record<HermesBlockerKey, string> = {
  youtube_not_proven_live:
    'Research rows and cached YouTube files can exist without proving the watcher is currently fetching videos or writing new rows. I need current process proof, a recent success log, or a fresh Supabase write receipt before I call it live.',
  hermes_live_model_not_configured:
    'Hermes has router and context logic, but no proven LLM provider is configured through the Hermes chat path yet.',
  hermes_web_search_not_configured:
    'Hermes cannot search the live web until the Hermes search path and provider keys are configured and verified.',
  token_rate_limits_unproven:
    'The tools may be installed, but current quota and rate-limit status is unknown unless config or logs show it. I will not guess token limits.',
  plist_loaded_only:
    'A launchd plist being loaded means the job is installed and scheduled. It does not prove the job ran successfully or is running now.',
  remote_collector_refresh_not_secure:
    'Hermes can read the latest Mac Mini audit report, but the browser does not have a safe remote path to trigger a fresh local collector run yet.',
  durable_cross_device_memory_missing:
    'Hermes can read reports, Supabase events, and local memory, but there is no dedicated long-term cross-device memory table wired yet.',
};

export function explainHermesBlocker(key: HermesBlockerKey): string {
  return EXPLANATIONS[key];
}

export function explainStatusToken(status: string): string {
  const normalized = status.toLowerCase().trim();
  if (normalized === 'not_proven_live') return explainHermesBlocker('youtube_not_proven_live');
  if (normalized === 'not_configured') return 'This is not configured and verified yet; I will not claim it is available.';
  if (normalized === 'unknown' || normalized === 'unproven') return explainHermesBlocker('token_rate_limits_unproven');
  if (normalized === 'loaded_only') return explainHermesBlocker('plist_loaded_only');
  return status;
}
