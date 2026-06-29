export const CLIENT_DATA_MODES = Object.freeze({
  DEMO_STATIC: 'demo_static',
  MANUAL_CLIENT: 'manual_client',
  SUPABASE_READY: 'supabase_ready',
  LIVE_SUPABASE_PENDING: 'live_supabase_pending',
})

const LIVE_TEST_CLIENT_ENABLED = import.meta.env.VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT === 'true'

export const clientDataMode = {
  current: CLIENT_DATA_MODES.LIVE_SUPABASE_PENDING,
  supported: Object.values(CLIENT_DATA_MODES),
  usesRealClientData: false,
  supabaseSchemaReady: true,
  supabaseLiveReadsEnabled: LIVE_TEST_CLIENT_ENABLED,
  liveSupabaseTestClientEnabled: LIVE_TEST_CLIENT_ENABLED,
  firstLiveReadRoute: '/client/dashboard',
  adminOrDemoPreview: true,
  internalLabel: LIVE_TEST_CLIENT_ENABLED ? 'Live Test Data' : 'Live Data Pending',
}

export const shouldShowInternalDataBadge = clientDataMode.adminOrDemoPreview && !clientDataMode.supabaseLiveReadsEnabled
