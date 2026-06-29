export const CLIENT_DATA_MODES = Object.freeze({
  DEMO_STATIC: 'demo_static',
  MANUAL_CLIENT: 'manual_client',
  SUPABASE_READY: 'supabase_ready',
  LIVE_SUPABASE_PENDING: 'live_supabase_pending',
})

export const clientDataMode = {
  current: CLIENT_DATA_MODES.LIVE_SUPABASE_PENDING,
  supported: Object.values(CLIENT_DATA_MODES),
  usesRealClientData: false,
  supabaseSchemaReady: true,
  supabaseLiveReadsEnabled: false,
  liveSupabaseTestClientEnabled: false,
  firstLiveReadRoute: '/client/dashboard',
  adminOrDemoPreview: true,
  internalLabel: 'Live Data Pending',
}

export const shouldShowInternalDataBadge = clientDataMode.adminOrDemoPreview && !clientDataMode.supabaseLiveReadsEnabled
