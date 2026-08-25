export const VOICE_RUNTIME_CONTRACT = {
  version: 'nexus.voice-wake-runtime.v2',
  persistentRollingPreview: false,
  finalSttAfterSilence: true,
  privateLocalVad: true,
} as const;

// Stable, public, minification-safe evidence for release verification. Keep
// this semantic contract independent of implementation variable names.
export const VOICE_RUNTIME_CONTRACT_MARKER = 'NEXUS_VOICE_RUNTIME_CONTRACT|version=nexus.voice-wake-runtime.v2|persistent_rolling_preview=false|final_stt_after_silence=true|private_local_vad=true';

export const BUILD_COMMIT_MARKER = 'NEXUS_BUILD_COMMIT:' + (import.meta.env.VITE_BUILD_COMMIT || 'unversioned');

export const BUILD_METADATA={
  commit:import.meta.env.VITE_BUILD_COMMIT||'unversioned',
  branch:import.meta.env.VITE_BUILD_BRANCH||'unknown',
  timestamp:import.meta.env.VITE_BUILD_TIMESTAMP||'unknown',
  environment:import.meta.env.MODE||'unknown',
  schemaCompatibility:'research-to-clyde-v1',
  voiceRuntimeContract: VOICE_RUNTIME_CONTRACT,
  voiceRuntimeContractMarker: VOICE_RUNTIME_CONTRACT_MARKER,
  buildCommitMarker: BUILD_COMMIT_MARKER,
}
